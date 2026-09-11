import os
import sys
import logging

# Añadir el directorio raíz al path para permitir ejecuciones directas e importaciones de src
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from descargar_actos import descargar_actos
from unificar_actos import unificar_actos

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s"
)

def main():
    logging.info("====== PIPELINE ACTOS INICIADO ======")

    logging.info("Paso 1: Descarga de actos desde Glissandoo")
    descargar_actos()

    logging.info("Paso 2: Procesado y control de asistentes. Unificar en un solo archivo")
    unificar_actos()

    logging.info("====== PIPELINE ACTOS FINALIZADO ======")

if __name__ == "__main__":
    main()