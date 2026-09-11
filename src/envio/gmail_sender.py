"""
gmail_sender.py
Integración con Gmail API para enviar correos HTML con adjuntos mediante OAuth2 (Installed App).
Usa credentials.json (OAuth client) y guarda token en token.json tras autorizar.
"""

import os
import time
import base64
import mimetypes
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import webbrowser
import subprocess

# Scope mínimo necesario para enviar correos
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

# Rutas por defecto - modifica si quieres otra ubicación
CREDENTIALS_PATH = os.getenv("GMAIL_CREDENTIALS", "credentials.json")
TOKEN_PATH = os.getenv("GMAIL_TOKEN", "token_gmail.json")


def get_gmail_service(credentials_path: str = CREDENTIALS_PATH, token_path: str = TOKEN_PATH):
    """
    Devuelve un servicio Gmail autenticado. Si no hay token, inicia flujo interactivo.
    Guarda token en token_path.
    """
    creds = None
    token_file = Path(token_path)
    
    if token_file.exists():
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    # Si no hay credenciales válidas, inicia flujo
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                # Token revocado o expirado — eliminar y reautenticar
                token_file.unlink(missing_ok=True)
                creds = None
        if not creds or not creds.valid:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            auth_url, _ = flow.authorization_url(
                access_type="offline",
                prompt="consent",
            )
            subprocess.Popen([
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                '--profile-directory=Profile 3', # <-- perfil de chrome (cambiar si es necesario)
                auth_url
            ])

            creds = flow.run_local_server(port=0)
        # Guardar token
        with open(token_path, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    return service


def create_message_with_attachment(sender: str, to: str, subject: str, html_body: str, attachments: list = None):
    """
    Construye un MIME message con attachments list = ["/path/to/file1.pdf", ...]
    Devuelve el raw (base64 urlsafe) listo para enviar con Gmail API.
    """
    if attachments is None:
        attachments = []

    message = MIMEMultipart()
    message["To"] = to
    message["From"] = sender
    message["Subject"] = subject

    # HTML body
    msg_html = MIMEText(html_body, "html", "utf-8")
    message.attach(msg_html)

    # Adjuntos
    for path in attachments:
        path = Path(path)
        if not path.exists():
            continue
        content_type, encoding = mimetypes.guess_type(path)
        if content_type is None:
            content_type = "application/octet-stream"
        main_type, sub_type = content_type.split("/", 1)

        with open(path, "rb") as f:
            part = MIMEBase(main_type, sub_type)
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f'attachment; filename="{path.name}"')
            message.attach(part)

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {"raw": raw}


def send_message(service, user_id: str, message_body: dict, max_retries: int = 5):
    """
    Envía el mensaje (message_body dict con 'raw') usando Gmail API.
    Implementa reintentos exponenciales ante HttpError.
    Retorna la respuesta del API.
    """
    attempt = 0
    backoff = 1
    while True:
        try:
            sent = service.users().messages().send(userId=user_id, body=message_body).execute()
            return sent
        except HttpError as e:
            status = getattr(e, "status_code", None) or e.resp.status if hasattr(e, "resp") else None
            if status and 400 <= status < 500:
                raise  # errores del cliente no son recuperables con reintentos
            attempt += 1
            if attempt > max_retries:
                raise
            # Backoff exponencial con jitter
            sleep_for = backoff + (0.5 * attempt)
            print(f"[gmail_sender] HttpError {status}, retrying in {sleep_for:.1f}s (attempt {attempt})")
            time.sleep(sleep_for)
            backoff *= 2


def send_email_safely(sender: str, to: str, subject: str, html_body: str, attachments: list = None,
                      credentials_path: str = CREDENTIALS_PATH, token_path: str = TOKEN_PATH):
    """
    Conveniencia: crea el service si es necesario, construye el mensaje y lo envía.
    """
    service = get_gmail_service(credentials_path, token_path)
    msg = create_message_with_attachment(sender, to, subject, html_body, attachments)
    result = send_message(service, "me", msg)
    return result


def send_batch(service, emails: list, sender: str, min_pause_seconds: float = 1.0, max_per_minute: int = 100):
    """
    Enviar en lote con rate limiting:
    - emails: lista de dicts { 'to':..., 'subject':..., 'html':..., 'attachments': [...] }
    - min_pause_seconds: pausa mínima entre envíos
    - max_per_minute: máximo recomendado (Gmail suele limitar a ~100-150/day; por minuto también hay límites)
    """
    sent = []
    delay = max(min_pause_seconds, 60.0 / max_per_minute)
    for i, e in enumerate(emails, start=1):
        try:
            msg = create_message_with_attachment(sender, e["to"], e["subject"], e["html"], e.get("attachments", []))
            res = send_message(service, "me", msg)
            sent.append(res)
            print(f"[gmail_sender] Enviado {i}/{len(emails)} → {e['to']}")
        except Exception as ex:
            print(f"[gmail_sender] Error enviando a {e['to']}: {ex}")
        time.sleep(delay)
    return sent