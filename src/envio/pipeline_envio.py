import os
import sys
from collections import defaultdict

# Añadir el directorio raíz al path para permitir ejecuciones directas e importaciones de src
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from src.common.config import *
from src.envio.excel_loader import load_excel_control_actos, parse_musicos_from_sheet
from src.envio.transform_data import build_dataframes, normalize_datasets, tabla_unificada
from src.envio.html_builder import tabla_html_moderno, cuerpo_correo_moderno
from src.envio.receipts import crear_recibo_pdf
from src.envio.gmail_sender import get_gmail_service, send_batch
from src.envio.remesa import generar_remesa_pagos

import pandas as pd
import webbrowser
from tempfile import NamedTemporaryFile

def _abrir_preview(df_norm, df_gen, df_otros, dni, label, fecha_inicio, fecha_fin, fecha_limite):
    g_norm  = df_norm[df_norm.dni == dni]
    g_gen   = df_gen[df_gen.dni == dni]
    g_otros = df_otros[df_otros.dni == dni]

    musico = {
        "nombre":    g_norm.nombre.iloc[0],
        "apellidos": g_norm.apellidos.iloc[0],
        "dni":       dni,
        "email":     g_norm.email.iloc[0],
        "n_cuenta":  g_norm.n_cuenta.iloc[0],
    }

    tabla     = tabla_unificada(g_norm, g_gen, g_otros)
    cuerpo    = cuerpo_correo_moderno([tabla_html_moderno(tabla)], musico, fecha_inicio, fecha_fin, fecha_limite)

    with NamedTemporaryFile("w", delete=False, suffix=".html", encoding="utf-8") as f:
        f.write(f"<html><body>{cuerpo}</body></html>")
        temp_path = f.name

    print(f"🌐 [{label}] {musico['nombre']} {musico['apellidos']} → {temp_path}")
    webbrowser.open(temp_path)


def previsualizar_musico(df_norm, df_gen, df_otros, fecha_inicio, fecha_fin, fecha_limite):
    # --- Preview 1: músico con algún importe < 0 en actos generales ---
    dni_gen = next(
        (dni for dni in df_norm["dni"].unique()
         if (df_gen[df_gen.dni == dni]["Percibido"] < 0).any()),
        None
    )
    if dni_gen:
        _abrir_preview(df_norm, df_gen, df_otros, dni_gen, "Actos generales con negativo", fecha_inicio, fecha_fin, fecha_limite)
    else:
        print("⚠️  No hay músico con acto general negativo.")

    # --- Preview 2: músico con algún importe != 0 en otros ---
    dni_otros = next(
        (dni for dni in df_norm["dni"].unique()
         if (df_otros[df_otros.dni == dni]["Percibido"] != 0).any()),
        None
    )
    if dni_otros:
        _abrir_preview(df_norm, df_gen, df_otros, dni_otros, "Otros con importe != 0", fecha_inicio, fecha_fin, fecha_limite)
    else:
        print("⚠️  No hay músico con importe en otros distinto de 0.")

def enviar_correos_gmail(tablas_por_email, musicos_por_email, test_only=None, emails_correcciones=None):
    service = get_gmail_service()
    emails = []
    sender = os.getenv("GMAIL_FROM")

    # ---------------------------------------------------------
    #  MODO TEST: enviar solo tu propia información
    # ---------------------------------------------------------
    if test_only:
        input(f"Modo TEST activado: enviando SOLO a {test_only} (1 correo).\nPresiona Enter para continuar...")

        # Buscar si el email existe entre los músicos
        if test_only not in tablas_por_email:
            raise ValueError(
                f"El email {test_only} NO aparece en los datos de músicos.\n"
                "Asegúrate de que tu email está en el Excel."
            )

        tablas = tablas_por_email[test_only]
        musico = musicos_por_email[test_only][0]

        cuerpo = cuerpo_correo_moderno(
            tablas, musico, FECHA_INICIO, FECHA_FIN, FECHA_LIMITE
        )

        emails.append({
            "to": test_only,
            "subject": f"Listado Actos {PAGO}",
            "html": cuerpo,
            "attachments": []
        })

        return send_batch(service, emails, sender, min_pause_seconds=1.0, max_per_minute=60)
    
    # ---------------------------------------------------------
    #  MODO CORRECCIÓN: enviar solo correcciones
    # ---------------------------------------------------------
    if emails_correcciones:
        if emails_correcciones:
            input(
                f"MODO CORRECCIONES: se enviará SOLO a ({len(emails_correcciones)} correos):\n"
                f"{emails_correcciones}\n"
                f"Pulsa Enter para continuar..."
            )

            for email in emails_correcciones:
                if email not in tablas_por_email:
                    print(f"{email} no existe en datos, se omite")
                    continue

                musico = musicos_por_email[email][0]
                tablas = tablas_por_email[email]

                cuerpo = cuerpo_correo_moderno(
                    tablas, musico, FECHA_INICIO, FECHA_FIN, FECHA_LIMITE
                )

                emails.append({
                    "to": email,
                    "subject": f"[CORRECCIÓN] Listado Actos {PAGO}",
                    "html": cuerpo,
                    "attachments": []
                })

            if not emails:
                print("No hay correos válidos para correcciones")
                return []

            return send_batch(service, emails, sender, 1.0, 60)


    # ---------------------------------------------------------
    #  MODO NORMAL: enviar a todos
    # ---------------------------------------------------------
    excluir = set(EMAILS_YA_ENVIADOS)
    pendientes = {e: t for e, t in tablas_por_email.items() if e not in excluir}
    if excluir:
        print(f"Omitiendo {len(excluir)} correos ya enviados.")
    n_total = len(pendientes)
    input(f"MODO NORMAL: se enviarán {n_total} correos. Presiona Enter para continuar...")
    for email, tablas in pendientes.items():
        musico = musicos_por_email[email][0]

        cuerpo = cuerpo_correo_moderno(
            tablas, musico, FECHA_INICIO, FECHA_FIN, FECHA_LIMITE
        )

        emails.append({
            "to": email,
            "subject": f"Listado Actos {PAGO}",
            "html": cuerpo,
            "attachments": []
        })
    return send_batch(service, emails, sender, min_pause_seconds=1.0, max_per_minute=60)

def main():
    print("Cargando Excel...")
    nombres_actos, importes, fechas, otros, actos_generales, hoja = load_excel_control_actos(RUTA_EXCEL)
    datos_musicos = parse_musicos_from_sheet(hoja, nombres_actos, importes, fechas, otros)
    df_actos, df_otros = build_dataframes(datos_musicos)
    df_norm, df_gen, df_otros = normalize_datasets(df_actos, df_otros, actos_generales)

    tablas_por_email = defaultdict(list)
    musicos_por_email = defaultdict(list)
    musicos_export = []

    for dni, g_norm in df_norm.groupby("dni"):
        g_gen = df_gen[df_gen.dni == dni]
        g_otros = df_otros[df_otros.dni == dni]

        tabla = tabla_unificada(g_norm, g_gen, g_otros)
        suma = pd.to_numeric(tabla["Percibido"], errors="coerce").fillna(0).sum()

        if suma <= 0:
            continue

        html = tabla_html_moderno(tabla)

        correo = g_norm.email.iloc[0]
        if not correo or not isinstance(correo, str) or "@" not in correo:
            print(f"⚠️  Email inválido para {g_norm.nombre.iloc[0]} {g_norm.apellidos.iloc[0]!r}: {correo!r} — omitido")
            continue
        tablas_por_email[correo].append(html)
        musicos_por_email[correo].append(g_norm.iloc[0].to_dict())

        emails_recibos = EMAILS_CORRECCIONES if EMAILS_CORRECCIONES else None
        if suma > 0 and CREAR_RECIBOS:
            if emails_recibos is None or correo in emails_recibos:
                musico = g_norm.iloc[0].to_dict()
                crear_recibo_pdf(musico, suma, FECHA_INICIO, FECHA_FIN)

        if GENERAR_REMESA:
            if not DNIS_REMESA or dni in DNIS_REMESA:
                musico = g_norm.iloc[0].to_dict()
                musicos_export.append({
                    "nombre": musico["nombre"],
                    "apellidos": musico["apellidos"],
                    "dni": musico["dni"],
                    "n_cuenta": musico["n_cuenta"],
                    "total_pago": suma
                })

    if GENERAR_REMESA:
        output_remesa = os.path.join(OUTPUT_DIR_REMESAS, f"Remesa_{PAGO}.xlsx")
        os.makedirs(OUTPUT_DIR_REMESAS, exist_ok=True)
        generar_remesa_pagos(musicos_export, output_remesa)

    if GENERAR_CORREO_PREVIA:
        correcciones_preview = EMAILS_CORRECCIONES if EMAILS_CORRECCIONES else None
        if correcciones_preview:
            print(f"\nGenerando previsualización de {len(correcciones_preview)} correo(s) de corrección...")
            for email in correcciones_preview:
                if email not in tablas_por_email:
                    print(f"⚠️  {email} no tiene datos, se omite")
                    continue
                musico = musicos_por_email[email][0]
                tablas = tablas_por_email[email]
                cuerpo = cuerpo_correo_moderno(tablas, musico, FECHA_INICIO, FECHA_FIN, FECHA_LIMITE)
                with NamedTemporaryFile("w", delete=False, suffix=".html", encoding="utf-8") as f:
                    f.write(f"<html><body>{cuerpo}</body></html>")
                    temp_path = f.name
                print(f"🌐 [Corrección] {musico['nombre']} {musico['apellidos']} ({email}) → {temp_path}")
                webbrowser.open(temp_path)
            input("Revisa los correos en el navegador y pulsa Enter para continuar...")
        else:
            print("\nGenerando previsualización de un músico aleatorio...")
            previsualizar_musico(df_norm, df_gen, df_otros, FECHA_INICIO, FECHA_FIN, FECHA_LIMITE)
            input("Pulsa Enter para continuar...")
    if ENVIAR_CORREOS:
        test_email = os.getenv("GMAIL_PRUEBA") if MODO_TEST else None
        correcciones = EMAILS_CORRECCIONES if EMAILS_CORRECCIONES else None
        enviar_correos_gmail(tablas_por_email, musicos_por_email, test_only=test_email, emails_correcciones=correcciones)
            
    print("Proceso finalizado.")


if __name__ == "__main__":
    main()

