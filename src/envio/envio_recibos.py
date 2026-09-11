import os
import sys
import time
import glob

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
from src.common.config import OUTPUT_DIR_RECIBOS

load_dotenv()
MODO_TEST = os.getenv("MODO_TEST", "False").lower() in ("true", "1")
EMAIL_TEST = os.getenv("GMAIL_PRUEBA", "")

URL = os.getenv("ONEFLOW_URL")
EMAIL = os.getenv("ONEFLOW_EMAIL")
PASSWORD = os.getenv("ONEFLOW_PASSWORD")

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
carpeta = os.path.join(ROOT, OUTPUT_DIR_RECIBOS)
pdfs = glob.glob(os.path.join(carpeta, "*.pdf"))

if not pdfs:
    print(f"No se encontraron PDFs en: {carpeta}")
    exit(0)

LOG_ENVIADOS = os.path.join(carpeta, "enviados.txt")
if os.path.exists(LOG_ENVIADOS):
    with open(LOG_ENVIADOS, "r", encoding="utf-8") as f:
        emails_ya_enviados = {line.strip() for line in f if line.strip()}
else:
    emails_ya_enviados = set()

pendientes = []
for p in pdfs:
    base = os.path.splitext(os.path.basename(p))[0]
    email = base.split("__$__")[1] if "__$__" in base else ""
    if email in emails_ya_enviados:
        print(f"  -> Ya enviado: {email} (saltando)")
    else:
        pendientes.append(p)

print(f"PDFs encontrados: {len(pdfs)} | Ya enviados: {len(emails_ya_enviados)} | Pendientes: {len(pendientes)}")

if not pendientes:
    print("No hay recibos pendientes de enviar.")
    exit(0)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.set_default_timeout(15000)

    # Login
    print("Iniciando sesión en OneFlow...")
    page.goto(URL)
    page.locator("input[name='email']").fill(EMAIL)
    page.locator("button[data-testid='submit-button']").click()
    page.locator("input[name='password']").fill(PASSWORD)
    page.locator("button[data-testid='submit-button']").click()
    page.wait_for_selector("button[data-testid='template-launcher']")
    print("Sesión iniciada.\n")

    for pdf_path in pendientes:
        basename = os.path.basename(pdf_path)
        base_sin_ext = os.path.splitext(basename)[0]
        if "__$__" in base_sin_ext:
            nombre_completo, email = base_sin_ext.split("__$__")
        else:
            nombre_completo, email = base_sin_ext, ""

        print(f"Nombre: {nombre_completo}")
        print(f"Correo: {email}")

        if MODO_TEST and email != EMAIL_TEST:
            print("  ->Saltando (modo test)\n")
            continue
        if not MODO_TEST and email == EMAIL_TEST:
            print("  ->Saltando (recibo propio)\n")
            continue

        #input(f"Enviar a {email} -- pulsa Enter para continuar")

        print("  [1/7] Abriendo nueva plantilla...")
        page.locator("button[data-testid='template-launcher']").click()
        page.locator("button[data-testid='create-document-button']").click()

        print("  [2/7] Subiendo PDF...")
        page.locator("button[data-testid='upload-pdf']").click()
        page.locator("input[type='file']").set_input_files(pdf_path)
        time.sleep(2)

        print("  [3/7] Añadiendo participante...")
        page.get_by_role("button", name="Añadir contraparte").click()
        page.screenshot(path="debug_modal.png")
        # Radix UI radio group — el input real tiene aria-hidden, hay que clickar el button
        page.locator("button[data-slot='radio-group-item'][value='individual']").click()
        page.locator("[name='fullname']").fill(nombre_completo)
        page.locator("[name='email']").fill(email)
        page.locator("[class*='_Footer'] button[data-testid='confirm']").click()
        time.sleep(2)

        print("  [4/7] Confirmando participante...")
        page.locator("[class*='_RightSide'] button[data-testid='confirm']").click()
        time.sleep(2)

        print("  [5/7] Enviando documento...")
        page.locator("button[class*='_SendDocumentButton']").click()
        page.locator("#select-messageTemplateSelectField").click()
        page.locator(".ReactSelect__option").first.wait_for(state="visible")
        page.locator(".ReactSelect__option").first.click()
        confirm = page.locator("[class*='_Footer'] button[data-testid='confirm']")
        confirm.wait_for(state="visible")
        confirm.scroll_into_view_if_needed()
        confirm.click()

        print("  [6/7] Firmando documento...")
        try:
            page.locator("[class*='_RightSide'] button[class*='_SignButton']").wait_for(state="visible", timeout=60000)
        except Exception:
            page.screenshot(path=f"debug_timeout_{email}.png")
            texto = page.inner_text("body")[:600]
            print(f"  Texto en pantalla al timeout:\n{texto}")
            print(f"  Captura guardada: debug_timeout_{email}.png")
            raise
        page.locator("[class*='_RightSide'] button[class*='_SignButton']").click()
        page.locator("[class*='_Footer'] button[data-testid='confirm']").click()
        time.sleep(2)

        print("  [7/7] Confirmando firma...")
        page.locator("[class*='_ModalContainer'] button[data-testid='confirm']").click()

        with open(LOG_ENVIADOS, "a", encoding="utf-8") as f:
            f.write(email + "\n")
        print(f"  OK Recibo enviado a {nombre_completo} ({email})\n")

    print("Todos los recibos enviados. Cerrando navegador...")
    browser.close()
