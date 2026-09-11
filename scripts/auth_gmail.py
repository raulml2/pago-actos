# Script para autenticar y obtener el token de Gmail.

import sys
import os
import logging

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(BASE_DIR)

from src.envio.gmail_sender import get_gmail_service

if __name__ == "__main__":
    # Paths relativas al proyecto
    credentials_path = os.path.join(BASE_DIR, 'credentials.json')
    token_path = os.path.join(BASE_DIR, 'token_gmail.json')

    logging.info(f"Buscando credenciales en: {credentials_path}")
    
    # Comprueba si el archivo de credenciales existe
    if not os.path.exists(credentials_path):
        logging.error(f"No se encontró el archivo de credenciales en {credentials_path}")
        sys.exit(1)

    svc = get_gmail_service(credentials_path=credentials_path, token_path=token_path)
    logging.info("Autorización completada. Servicio Gmail listo.")
