# ==========================
# descargar_actos.py
# ==========================
# Autor: Raul Mendez 
# GitHub: https://github.com/raulml2
# Fecha: 08/12/2025
# Version: 1.1
# Descripción: Descarga los listados de asistencia de actos de una fecha inicial hasta una fecha final de una agrupación de Glissandoo y los mueve a una carpeta especifica (DESCARGAS_DIR).
# Notas: 
#       - Se requiere tener configuradas las variables de entorno GLISSANDOO_EMAIL, GLISSANDOO_PASSWORD, GLISSANDOO_URL y GLISSANDOO_AGRUPACION en un archivo .env
#       - Se requiere tener instalado el paquete seleniumbase
#       - Se deben indicar las variables FECHA_INICIO y FECHA_FIN en formato dd/mm/yyyy
# ==========================

import os
import sys
import time
from datetime import datetime
from pathlib import Path
from seleniumbase import Driver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import shutil
from dotenv import load_dotenv
import logging

# Añadir directorio raíz al path para importar config
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(BASE_DIR)

from src.common.config import PAGO, FECHA_INICIO as FECHA_INICIO_STR, FECHA_FIN as FECHA_FIN_STR, OUTPUT_DIR_ASISTENCIAS

# ==========================
# CONFIGURACIÓN INICIAL
# ==========================

DESCARGAS_DIR = Path(OUTPUT_DIR_ASISTENCIAS)
TEMP_DIR = Path("downloaded_files")

# Rango de fechas configurable
FECHA_INICIO = datetime.strptime(FECHA_INICIO_STR, "%d/%m/%Y")
FECHA_FIN = datetime.strptime(FECHA_FIN_STR, "%d/%m/%Y") 

load_dotenv()
EMAIL = os.getenv("GLISSANDOO_EMAIL")
PASSWORD = os.getenv("GLISSANDOO_PASSWORD")
URL = os.getenv("GLISSANDOO_URL")
AGRUPACION = os.getenv("GLISSANDOO_AGRUPACION")

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s" # %(asctime)s [%(levelname)s] %(message)s
)

# ==========================
# FUNCIONES
# ==========================

def reiniciar_carpetas_descargas(dir_asistencias: Path, dir_temp: Path):
    """Limpia directorios antiguos y asegura que existan las carpetas necesarias."""
    for carpeta in [dir_asistencias, dir_temp]:
        if carpeta.exists():
            shutil.rmtree(carpeta)
            logging.info(f"Carpeta '{carpeta}' eliminada para empezar desde cero.")

        carpeta.mkdir(exist_ok=True)

def mover_descargas(dir_asistencias: Path, dir_temp: Path):
    """Mueve todos los .xlsx a la carpeta Asistencia/<PAGO>, evitando sobrescribir."""
    archivos = list(dir_temp.glob("*.xlsx"))

    if not archivos:
        logging.warning("No hay archivos descargados para mover.")
        return

    dir_asistencias.mkdir(parents=True, exist_ok=True)

    for archivo in archivos:
        destino = dir_asistencias / archivo.name

        # Si el archivo ya existe, renombra con sufijo incremental
        base = archivo.stem
        ext = archivo.suffix
        i = 1
        while destino.exists():
            destino = dir_asistencias / f"{base}_{i}{ext}"
            i += 1

        shutil.move(str(archivo), destino)
        logging.info(f"Descarga movida → {destino.name}")

    shutil.rmtree(dir_temp)
    logging.info(f"Carpeta '{dir_temp}' eliminada.")

def iniciar_sesion_glissando(driver: Driver, url: str, email: str, password: str, agrupacion: str):
    driver.get(url)
    # Esperar a que los campos de correo o contraseña estén presentes
    WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "email"))).send_keys(email)
    driver.find_element(By.ID, "password").send_keys(password)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    # Esperar hasta que cargue el panel principal o un elemento conocido post-login
    WebDriverWait(driver, 10).until(EC.url_contains(agrupacion))
    logging.info("Inicio de sesión correcto.")

def obtener_fecha_evento(elemento_evento):
    """ Extrae y devuelve la fecha del evento como objeto datetime desde el elemento del evento. """
    try:
        dia = elemento_evento.find_element(By.CLASS_NAME, "containerDayDate").text.strip()
        mes = elemento_evento.find_element(By.CLASS_NAME, "containerMonthDate").text.strip().lower()
        anio = elemento_evento.find_element(By.XPATH, ".//span[contains(text(),'202')]").text.strip()

        meses = {
            "ene": "01", "feb": "02", "mar": "03", "abr": "04", "may": "05", "jun": "06",
            "jul": "07", "ago": "08", "sep": "09", "oct": "10", "nov": "11", "dic": "12"
        }

        mes_num = meses.get(mes[:3])
        if not mes_num:
            return None

        fecha_str = f"{dia.zfill(2)}/{mes_num}/{anio}"
        return datetime.strptime(fecha_str, "%d/%m/%Y")

    except Exception as e:
        logging.error(f"No se pudo extraer fecha: {e}")
        return None

def cargar_eventos(driver, fecha_limite: datetime, agrupacion: str):
    """Carga los eventos pasados haciendo clic en 'Cargar más' hasta llegar a la fecha límite (fecha_inicio)."""
    # Ir a la página de eventos
    driver.get(f"https://app.glissandoo.com/group/{agrupacion}/events?type=performance&past=true&lang=es")
    WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.XPATH, "//span[text()='Cargar más']/..")))    
    while True:
        eventos = driver.find_elements(By.CSS_SELECTOR, "ul.ant-list-items > li")
        if not eventos:
            break

        # Último evento visible
        ultimo_evento = eventos[-1]
        fecha_ultimo = obtener_fecha_evento(ultimo_evento)

        if not fecha_ultimo:
            logging.error("No se pudo leer la fecha del último evento. Deteniendo carga.")
            break

        if fecha_ultimo < fecha_limite:
            logging.info(f"Fecha límite alcanzada, no se cargarán más eventos. {fecha_ultimo} < {fecha_limite}")
            break

        # Intentar hacer clic en el botón "Cargar más"
        try:
            boton = driver.find_element(By.XPATH, "//span[text()='Cargar más']/..")
            driver.execute_script("arguments[0].scrollIntoView(true);", boton)
            boton.click()
            WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.XPATH, "//span[text()='Cargar más']/..")))
        except Exception as e:
            logging.error(f"Error al cargar más eventos: {e}")
            break

    logging.info("Carga de eventos completada.")

def descargar_evento(driver, evento, dir_temp: Path):
    """Hace clic en el evento, descarga su Excel y vuelve atrás."""
    evento.click()

    selector = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".ant-select-selector")))
    selector.click()

    opcion_excel = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//div[@title='Excel']")))
    opcion_excel.click()

    # Esperar a la descarga real
    if not esperar_descarga_completa(dir_temp):
        logging.warning("La descarga no parece haberse completado a tiempo.")

def esperar_descarga_completa(dir_temp: Path, timeout: int = 20):
    """Espera hasta que aparezca un .xlsx en downloaded_files."""
    start = time.time()

    while time.time() - start < timeout:
        archivos = list(dir_temp.glob("*.xlsx"))
        if archivos:
            return True
        time.sleep(0.2)

    return False

def procesar_eventos(driver, fecha_inicio: datetime, fecha_fin: datetime, dir_temp: Path):
    event_elements = driver.find_elements(By.CSS_SELECTOR, "ul.ant-list-items > li")
    event_count = len(event_elements)

    for index in range(event_count):
        try:
            event_elements = driver.find_elements(By.CSS_SELECTOR, "ul.ant-list-items > li")
            evento = event_elements[index]

            fecha_evento = obtener_fecha_evento(evento)
            if not fecha_evento:
                logging.warning(f"Evento {index + 1}: no se pudo leer la fecha. Se omite.")
                continue

            # Saltar conciertos
            nombre = evento.find_element(By.TAG_NAME, "h5").text.strip().lower()
            if any(keyword in nombre for keyword in ["concierto", "anulado", "suspendido", "cancelado"]):
                logging.warning(f"Omitido → {nombre}")
                continue

            # Rango de fechas
            if not (fecha_inicio <= fecha_evento <= fecha_fin):
                logging.warning("Evento fuera del rango de fechas")
                continue

            logging.info(f"Descargando evento del {fecha_evento.strftime('%d/%m/%Y')} - {nombre}")

            try:
                descargar_evento(driver, evento, dir_temp)
            except Exception as e:
                logging.error(f"Error descargando evento {index + 1}: {e}")
            
            driver.back()
            WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.XPATH, "//span[text()='Cargar más']/..")))
            
        except Exception as e:
            logging.error(f"Error al procesar evento {index + 1}: {e}")
            continue
    
    logging.info("Todos los eventos han sido procesados.")
    driver.quit()

# ==========================
# MAIN
# ==========================

def descargar_actos():
    logging.info("------- INICIO PROCESO DESCARGA DE ACTOS -------")
    reiniciar_carpetas_descargas(DESCARGAS_DIR, TEMP_DIR)
    driver = Driver(browser="chrome", uc=True, headless=False)
    iniciar_sesion_glissando(driver, URL, EMAIL, PASSWORD, AGRUPACION)
    cargar_eventos(driver, FECHA_INICIO, AGRUPACION)
    procesar_eventos(driver, FECHA_INICIO, FECHA_FIN, TEMP_DIR)
    mover_descargas(DESCARGAS_DIR, TEMP_DIR)
    logging.info("------- FIN PROCESO DESCARGA DE ACTOS -------")

if __name__ == "__main__":
    descargar_actos()
