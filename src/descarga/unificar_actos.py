# ==========================
# unificar_actos.py 
# ==========================
# Autor: Raul Mendez 
# GitHub: https://github.com/raulml2
# Fecha: 08/12/2025
# Version: 1.1
# Descripción: Script para procesar los archivos de asistencia de actos y generar un archivo con los asistentes de cada acto en un solo archivo listo para copiar y pegar en el fichero Excel de control.
# Notas: 
#       - Se requiere tener instalado el paquete pandas
# ==========================

import re
from datetime import datetime
from pathlib import Path
import pandas as pd
import logging
import os
import sys

# Añadir directorio raíz al path para importar config
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(BASE_DIR)

from src.common.config import OUTPUT_DIR_ASISTENCIAS, PAGO

# ==========================
# CONFIGURACIÓN GENERAL
# ==========================

COLUMNA_ASISTENCIA = "Pasar lista" # Columna que indica asistencia en los Excel del Glissandoo
VALOR_ASISTIO = "Ha asistido"
COLUMNA_CORREO = "Email" 

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s" # %(asctime)s [%(levelname)s] %(message)s
)

# ==========================
# FUNCIONES
# ==========================

def extraer_fecha_y_nombre(filename: str):
    """ Extrae la fecha y el nombre del acto desde un nombre de archivo.
        Ejemplo esperado de nombre: 'Acto general 12_10_25.xlsx' """

    # Buscar fecha con regex (dd_mm_yy)
    match = re.search(r"(\d{2}_\d{2}_\d{2})", filename)
    if not match:
        raise ValueError(f"No se encontró fecha válida en el nombre: {filename}")

    fecha_raw = match.group(1)
    fecha = datetime.strptime(fecha_raw.replace("_", "/"), "%d/%m/%y")

    # El nombre del acto es todo lo que no es la fecha
    nombre = filename.replace(match.group(1), "").replace(".xlsx", "")
    nombre = nombre.rstrip("_ ").strip()

    return fecha, nombre

def cargar_excel(path: Path):
    """ Lee el Excel con pandas y normaliza los nombres de columnas."""
    df = pd.read_excel(path)
    df.columns = [str(c).strip() for c in df.columns]  # limpieza básica
    return df

def obtener_asistentes(df: pd.DataFrame, columna_asistencia: str, valor_asistio: str):
    """ Devuelve una lista de correos de asistentes según la columna de asistencia. """
    if columna_asistencia not in df.columns:
        raise KeyError(f"No se encontró la columna '{columna_asistencia}' en el Excel.")

    asistentes = (
        df[df[columna_asistencia].str.lower() == valor_asistio.lower()]
        .iloc[:, 2]  # tercera columna = email
        .dropna()
        .astype(str)
        .str.strip()
        .str.lower()
        .tolist()
    )
    return asistentes

def procesar_archivos(carpeta_asistencia: Path, columna_asistencia: str, valor_asistio: str):
    data_actos = {}
    carpeta_asistencia = Path(carpeta_asistencia)
    for archivo in carpeta_asistencia.glob("*.xlsx"):
        nombre_archivo = archivo.name

        try:
            fecha, nombre = extraer_fecha_y_nombre(nombre_archivo)
        except Exception as e:
            logging.warning(f"Error parsing del archivo '{nombre_archivo}': {e}")
            continue

        logging.info(f"Procesando acto: {nombre} ({fecha.strftime('%d/%m/%y')})")

        try:
            df = cargar_excel(archivo)
            asistentes = obtener_asistentes(df, columna_asistencia, valor_asistio)
            if len(asistentes) == 0:
                logging.warning(f"No se encontraron asistentes en el acto {nombre} ({fecha.strftime('%d/%m/%y')})")
                continue
            data_actos[(fecha, nombre)] = asistentes
        except Exception as e:
            logging.warning(f"Error leyendo {nombre_archivo}: {e}")
            continue

    # Ordenar por fecha
    return dict(sorted(data_actos.items(), key=lambda x: x[0][0]))

def generar_tabla(data_actos: dict):
    """Construye la tabla completa (fechas, nombres, asistentes)."""
    fechas = [fecha.strftime("%d/%m/%y") for fecha, _ in data_actos.keys()]
    nombres = [nombre for _, nombre in data_actos.keys()]

    # Determinar el máximo de asistentes en algún acto
    max_asist = max(len(a) for a in data_actos.values())

    filas_asist = []
    for i in range(max_asist):
        fila = [
            asistentes[i] if i < len(asistentes) else ""
            for asistentes in data_actos.values()
        ]
        filas_asist.append(fila)

    # Construir DataFrame final
    df_final = pd.DataFrame([fechas, nombres] + filas_asist)
    return df_final

def guardar_excel(df_final: pd.DataFrame, pago: str):
    output = f"_asistentes_actos_{pago}.xlsx"
    df_final.to_excel(output, index=False, header=False)
    logging.info(f"Archivo generado: {output}")

def mostrar_resumen(data_actos: dict):
    print("\nResumen de asistentes por acto:")
    for (fecha, nombre), asistentes in data_actos.items():
        print(f"- {nombre} ({fecha.strftime('%d/%m/%Y')}): {len(asistentes)} asistentes")

# ==========================
# MAIN
# ==========================

def unificar_actos():
    logging.info("------- INICIO PROCESO UNIFICACION DE ACTOS -------")
    data_actos = procesar_archivos(OUTPUT_DIR_ASISTENCIAS, COLUMNA_ASISTENCIA, VALOR_ASISTIO)
    logging.info(f"------- {len(data_actos)} ACTOS PROCESADOS -------")
    df_final = generar_tabla(data_actos)
    guardar_excel(df_final, PAGO)
    mostrar_resumen(data_actos)
    logging.info("------- FIN PROCESO UNIFICACION DE ACTOS -------")

if __name__ == "__main__":
    unificar_actos()
