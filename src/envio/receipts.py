import os
from datetime import datetime
from docxtpl import DocxTemplate
from docx2pdf import convert
import time
import sys

# Añadir directorio raíz al path para importar config
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(BASE_DIR)

from src.common.config import PLANTILLA_WORD, OUTPUT_DIR_RECIBOS

def fecha_larga(dt):
    meses = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio",
             "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    return f"{dt.day} de {meses[dt.month]} de {dt.year}"


def crear_recibo_pdf(musico, importe_total, fecha_inicio, fecha_fin, fecha_hoy=None):
    if fecha_hoy is None:
        fecha_hoy = datetime.today().strftime("%d/%m/%Y")
    
    # Asegura que fecha_hoy es un objeto fecha
    if isinstance(fecha_hoy, str):
        try:
            fecha_hoy_dt = datetime.strptime(fecha_hoy, "%d/%m/%Y")
        except ValueError:
            fecha_hoy_dt = datetime.strptime(fecha_hoy, "%Y-%m-%d")
    else:
        fecha_hoy_dt = fecha_hoy
    # Convierte fechas a datetime.date si vienen en string
    if isinstance(fecha_inicio, str):
        fecha_inicio_dt = datetime.strptime(fecha_inicio, "%d/%m/%Y")
    else:
        fecha_inicio_dt = fecha_inicio
    if isinstance(fecha_fin, str):
        fecha_fin_dt = datetime.strptime(fecha_fin, "%d/%m/%Y")
    else:
        fecha_fin_dt = fecha_fin
    os.makedirs(OUTPUT_DIR_RECIBOS, exist_ok=True)

    context = {
        "nombre": musico["nombre"].capitalize(),
        "apellidos": musico["apellidos"],
        "dni": musico["dni"],
        "email": musico.get("email", ""),
        "n_cuenta": musico.get("iban", musico.get("n_cuenta", "")),
        "importe_total": f"{importe_total:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.') if isinstance(importe_total, float) else importe_total,
        "today": fecha_larga(fecha_hoy_dt),
        "f_init": fecha_larga(fecha_inicio_dt),
        "f_end": fecha_larga(fecha_fin_dt),
        "y": fecha_hoy_dt.year
    }

    output_docx = os.path.join(OUTPUT_DIR_RECIBOS, f"{musico['nombre']} {musico['apellidos']}__$__{musico['email']}.docx")
    output_pdf = output_docx.replace(".docx", ".pdf")

    doc = DocxTemplate(PLANTILLA_WORD)
    doc.render(context)
    doc.save(output_docx)

    # Convertir a PDF solo si hay Word instalado (en Windows)
    try:
        convert(output_docx, output_pdf)
        time.sleep(1) # Espera para asegurar que el PDF se genera correctamente
        os.remove(output_docx)  # Opcional: elimina el .docx temporal
        time.sleep(1)
    except Exception as e:
        print(f"Error convirtiendo a PDF: {e}")

    return output_pdf
