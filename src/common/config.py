from datetime import datetime, timedelta
import locale
from dotenv import load_dotenv

load_dotenv()

# ==========================
# CONFIGURACIÓN DEL PAGO (Cambiar según el pago)
# ==========================
PAGO = "2026A"
FECHA_INICIO = "01/12/2025"
FECHA_FIN = "01/05/2026"
DIAS_LIMITE = 5

locale.setlocale(locale.LC_TIME, 'Spanish_Spain')
FECHA_LIMITE = (datetime.today() + timedelta(days=DIAS_LIMITE)).strftime("%A %d de %B").capitalize()

# ==========================
# PATHS DEL PROYECTO
# ==========================
PLANTILLA_WORD = "src/assets/templates/Recibo_Template.docx"
OUTPUT_DIR_RECIBOS = f"data/recibos/{PAGO}"
OUTPUT_DIR_REMESAS = f"data/remesas/{PAGO}"
OUTPUT_DIR_ASISTENCIAS = f"data/asistencias/{PAGO}"

_EXCEL_POR_PAGO = {
    "2025B": "data/private/CONTROL_ACTOS_2025.xlsm",
    "2026A": "data/private/CONTROL_ACTOS_2026.xlsm",
}
RUTA_EXCEL = _EXCEL_POR_PAGO.get(PAGO, f"data/private/CONTROL_ACTOS_{PAGO[:4]}.xlsm")

# ==========================
# ESTRUCTURA DEL EXCEL (columnas por período de pago)
# ==========================
_ESTRUCTURA_POR_PAGO = {
    "2025B": {"COL_INIT_ACTOS": 103, "COL_END_ACTOS": 151, "N_ACTOS_GENERALES": 3, "N_OTROS": 5},
    "2026A": {"COL_INIT_ACTOS": 9,   "COL_END_ACTOS": 99,  "N_ACTOS_GENERALES": 2, "N_OTROS": 4},
}

if PAGO not in _ESTRUCTURA_POR_PAGO:
    raise ValueError(f"Período '{PAGO}' no tiene estructura de Excel definida. Añádela en _ESTRUCTURA_POR_PAGO.")

_e = _ESTRUCTURA_POR_PAGO[PAGO]
COL_INIT_ACTOS   = _e["COL_INIT_ACTOS"]
COL_END_ACTOS    = _e["COL_END_ACTOS"]
N_ACTOS_GENERALES = _e["N_ACTOS_GENERALES"]
N_OTROS          = _e["N_OTROS"]

# ==========================
# FLAGS DE EJECUCIÓN (Cambiar a True para ejecutar)
# ==========================
CREAR_RECIBOS = True
GENERAR_CORREO_PREVIA = False
ENVIAR_CORREOS = False
GENERAR_REMESA = False
MODO_TEST = False  # True: envía solo a GMAIL_FROM para verificar

# Correos ya enviados en una ejecución anterior (se omiten en modo normal)
EMAILS_YA_ENVIADOS = []

# Correos a los que reenviar correcciones (vaciar cuando no se use)
EMAILS_CORRECCIONES = []

# DNIs a incluir en la remesa (vaciar para incluir a todos)
DNIS_REMESA = []
