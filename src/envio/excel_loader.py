import pandas as pd
from openpyxl import load_workbook
import os
import sys

# Añadir directorio raíz al path para importar config
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(BASE_DIR)

from src.common.config import (
    COL_INIT_ACTOS, COL_END_ACTOS, N_OTROS, N_ACTOS_GENERALES, RUTA_EXCEL
)

def load_excel_control_actos(ruta_excel=RUTA_EXCEL):
    """
    Carga la hoja CONTROL ACTOS MUSICOS y devuelve:
    - nombres_actos
    - importes
    - fechas
    - otros
    - actos_generales
    """
    libro = load_workbook(ruta_excel, data_only=True)
    hoja = libro["CONTROL ACTOS MUSICOS"]

    nombres_actos = [cell.value for cell in hoja[2][COL_INIT_ACTOS:COL_END_ACTOS] if cell.value]
    importes = [cell.value for cell in hoja[3][COL_INIT_ACTOS:COL_END_ACTOS] if isinstance(cell.value, (int, float))]
    fechas = [cell.value for cell in hoja[5][COL_INIT_ACTOS:COL_END_ACTOS] if cell.value]

    otros = [cell.value for cell in hoja[2][COL_END_ACTOS:COL_END_ACTOS + N_OTROS] if cell.value]
    actos_generales = nombres_actos[-N_ACTOS_GENERALES:]

    return nombres_actos, importes, fechas, otros, actos_generales, hoja


def parse_musicos_from_sheet(hoja, nombres_actos, importes, fechas, otros):
    """
    Parsea todas las filas de músicos desde la hoja Excel.
    Devuelve una lista de dicts con datos básicos + actos + otros.
    """
    datos_musicos = []

    for fila in hoja.iter_rows(min_row=9, values_only=True):
        if not any(fila):
            continue

        datos_basicos = {
            "nombre": fila[1],
            "apellidos": fila[2],
            "dni": fila[3],
            "email": fila[4],
            "telefono": fila[5],
            "n_cuenta": fila[6],
        }

        asistencias = fila[COL_INIT_ACTOS:COL_END_ACTOS + N_OTROS]

        actos_asistidos = []
        for idx, (nombre, imp, fecha) in enumerate(zip(nombres_actos, importes, fechas)):
            valor_asistencia = asistencias[idx * 2]
            valor_importe = asistencias[idx * 2 + 1]
            actos_asistidos.append({
                "nombre_acto": nombre,
                "fecha": fecha,
                "importe_base": float(imp),
                "importe_cobrado": valor_importe,
                "asistio": valor_asistencia in ("X", "D")
            })

        # Otros
        otros_data = []
        start_idx = COL_END_ACTOS - COL_INIT_ACTOS
        for idx2, nombre_otro in enumerate(otros):
            importe_otro = asistencias[start_idx + idx2] or 0.0
            otros_data.append({
                "nombre_acto": nombre_otro,
                "importe_cobrado": float(importe_otro)
            })

        datos_basicos["actos"] = actos_asistidos
        datos_basicos["otros"] = otros_data
        datos_musicos.append(datos_basicos)

    return datos_musicos
