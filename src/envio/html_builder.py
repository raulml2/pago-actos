import pandas as pd
import numpy as np

def tabla_html(df):
    df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce').dt.strftime('%d/%m/%Y').fillna("")
    df['Valor'] = df['Valor'].apply(lambda x: f"{x:,.2f} €" if pd.notnull(x) else '')
    df['Percibido'] = df['Percibido'].apply(lambda x: f"{x:,.2f} €" if pd.notnull(x) else '')

    total = df['Percibido'].replace("", "0").str.replace("€", "").replace(",", ".", regex=True).astype(float).sum()

    rows = ""
    for _, row in df.iterrows():
        if row["Acto"] in ["ACTOS GENERALES", "OTROS"]:
            color = "#c0392b" if row["Acto"] == "ACTOS GENERALES" else "#4b4b4b"
            rows += f"""
                <tr style="background:{color};color:white;font-weight:bold;"><td colspan="4">{row['Acto']}</td></tr>
            """
        else:
            rows += f"""
            <tr>
                <td>{row['Fecha']}</td>
                <td>{row['Acto']}</td>
                <td>{row['Valor']}</td>
                <td>{row['Percibido']}</td>
            </tr>
            """

    return f"""
    <table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse;">
        <thead style="background:#2c3e50;color:white;">
            <tr>
                <th>FECHA</th><th>ACTO</th><th>VALOR</th><th>PERCIBIDO</th>
            </tr>
        </thead>
        <tbody>
            {rows}
            <tr><td colspan="3"><b>TOTAL</b></td><td><b>{total:,.2f} €</b></td></tr>
        </tbody>
    </table>
    """


def cuerpo_correo(tablas_html, musico, fecha_inicio, fecha_fin, fecha_limite):
    m = musico
    tablas = "<hr>".join(tablas_html)
    return f"""
    <p>Estimado/a <b>{m['nombre']} {m['apellidos']}</b>,</p>
    <p>Adjuntamos el listado de actos realizados entre <b>{fecha_inicio}</b> y <b>{fecha_fin}</b>.</p>
    {tablas}
    <p>Revisa y responde antes del <b>{fecha_limite}</b>.</p>
    """

def tabla_html_moderno(df):

    
    df = df.copy()
    
    # --- CORRECCIÓN 1: FECHAS ---
    # dayfirst=True ayuda a interpretar "01/02" como 1 de Feb, no 2 de Ene.
    df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=True, errors='coerce').dt.strftime('%d/%m/%Y').fillna("")
    
    # Procesamiento de columnas numéricas
    # Guardamos una versión numérica pura para la lógica y el total
    df['Percibido_num'] = pd.to_numeric(df['Percibido'], errors='coerce').fillna(0)
    df['Valor_str'] = df['Valor'].apply(lambda x: f"{x:.2f} €" if pd.notnull(x) else '')
    df['Percibido_str'] = df['Percibido_num'].map(lambda x: f"{x:.2f} €")
    
    # Lógica base de asistencia (se sobrescribirá según la sección)
    if 'asistio' in df.columns:
        df['Asistencia_base'] = df['asistio'].apply(lambda x: "Sí" if bool(x) else "No")
    else:
        df['Asistencia_base'] = ""

    total = df['Percibido_num'].sum()

    rows = ""
    # Variable para controlar en qué sección estamos (ACTOS GENERALES u OTROS)
    seccion_actual = "" 

    for _, row in df.iterrows():
        
        # --- SECCIONES ESPECIALES (ENCABEZADOS) ---
        if row["Acto"] == "ACTOS GENERALES":
            seccion_actual = "GENERALES"
            # --- CORRECCIÓN 2: CENTRADO EN COLUMNA ACTO ---
            # Usamos 5 celdas individuales con el mismo fondo para poder centrar el texto solo en la 2ª columna
            rows += f"""
            <tr style="background:#1a1a1a;color:white;font-weight:bold;">
                <td style="padding:10px 14px;"></td> <td style="padding:10px 14px; text-align:center;">{row['Acto']}</td> <td style="padding:10px 14px;"></td>
                <td style="padding:10px 14px;"></td>
                <td style="padding:10px 14px;"></td>
            </tr>
            """
            continue
        
        if row["Acto"] == "OTROS":
            seccion_actual = "OTROS"
            rows += f"""
            <tr style="background:#1a1a1a;color:white;font-weight:bold;">
                <td style="padding:10px 14px;"></td>
                <td style="padding:10px 14px; text-align:center;">{row['Acto']}</td>
                <td style="padding:10px 14px;"></td>
                <td style="padding:10px 14px;"></td>
                <td style="padding:10px 14px;"></td>
            </tr>
            """
            continue

        # --- LÓGICA DE FILAS NORMALES ---
        
        # Determinamos qué mostrar en Asistencia según la sección actual
        asistencia_mostrar = row['Asistencia_base']

        if seccion_actual == "OTROS":
            # Petición: Que no se muestre nada en OTROS
            asistencia_mostrar = ""
            
        elif seccion_actual == "GENERALES":
            # Petición: "si es 0 el percibido es que si ha asistido"
            if row['Percibido_num'] == 0:
                asistencia_mostrar = "Sí"
            else:
                asistencia_mostrar = "No"

        rows += f"""
        <tr style="border-bottom:1px solid #e5e7eb;">
            <td style="padding:10px 14px;text-align:center;">{row['Fecha']}</td>
            <td style="padding:10px 14px;">{row['Acto']}</td>
            <td style="padding:10px 14px;text-align:center;">{asistencia_mostrar}</td> <td style="padding:10px 14px;text-align:center;">{row['Valor_str']}</td>
            <td style="padding:10px 14px;text-align:center;">{row['Percibido_str']}</td>
        </tr>
        """

    # Fila de TOTAL
    rows += f"""
    <tr style="font-weight:bold;background:#f3f4f6;">
        <td colspan="4" style="padding:10px 14px;text-align:right;">TOTAL PROVISIONAL</td>
        <td style="padding:10px 14px;">{total:.2f} €</td>
    </tr>
    """

    tabla = f"""
    <table width="100%" cellpadding="0" cellspacing="0" 
           style="border-collapse:collapse;font-family:Arial, sans-serif;font-size:14px;color:#1a1a1a;">
        <thead>
            <tr style="background:#1a1a1a;color:white;">
                <th style="padding:10px 14px;text-align:center;">FECHA</th>
                <th style="padding:10px 14px;text-align:center;">ACTO</th>
                <th style="padding:10px 14px;text-align:center;">ASISTENCIA</th>
                <th style="padding:10px 14px;text-align:center;">IMPORTE</th>
                <th style="padding:10px 14px;text-align:center;">PERCIBIDO</th>
            </tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>
    """
    return tabla


def cuerpo_correo_moderno(tablas_html, musico, fecha_inicio, fecha_fin, fecha_limite):
    tablas = "<br><br>".join(tablas_html)
    # Estilo para la caja de datos personales
    estilo_caja_datos = "background:#f3f4f6; padding:15px; border-radius:4px; border:1px solid #e5e7eb;"
    
    return f"""
    <div style="max-width:780px;margin:auto;padding:20px;font-family:Arial, sans-serif;color:#1a1a1a;line-height:1.5;">
        
        <!-- CABECERA -->
        <div style="text-align:center;margin-bottom:30px;">
            <img src="https://bandacirculotorrent.com/wp-content/uploads/2019/11/cabecera-circulo.png" 
                 alt="Banda CCT" 
                 style="max-width:160px;margin-bottom:10px;">
            <h2 style="color:#1a1a1a;font-weight:700;margin:0;">Banda Sinfónica Círculo Católico de Torrent</h2>
            <hr style="border:none;border-top:1px solid #e5e7eb;margin:20px 0;">
        </div>

        <!-- INTRO -->
        <p>Hola <b>{musico['nombre'].capitalize()}</b>,</p>
        <p style="text-align:justify;">
            Te enviamos tu resumen de asistencia a los actos realizados en la banda desde el <b>{fecha_inicio}</b> hasta el <b>{fecha_fin}</b>, así como los datos que usaremos para procesar el pago. Por favor, revisa que todo sea correcto.
        </p>

        <h3>1. Datos personales</h3>
        <div style="{estilo_caja_datos}">
            <p style="margin:5px 0;">
                Nombre: <b>{musico['nombre'].capitalize()}</b>
            </p>
            <p style="margin:5px 0;">
                Apellidos: <b>{musico['apellidos']}</b>
            </p>
            <p style="margin:5px 0;">
                Email: <b>{musico['email']}</b>
            </p>
            <p style="margin:5px 0;">
                DNI: <b>{musico['dni']}</b>
            </p>
            <p style="margin:5px 0;">
                Nº de Cuenta (IBAN): <b>{musico['n_cuenta']}</b>
            </p>
        </div>
        <h3>2. Listado de actos</h3>
        <!-- TABLA -->
        <div style="margin-top:30px;margin-bottom:30px;align-items:center;">
            {tablas}
        </div>

        <!-- NOTA -->
        <div style="background:#fff3cd; border:1px solid #ffeeba; padding:15px; border-radius:5px; margin-top:30px;">
            <p style="font-weight:bold; margin-top:0; color:#856404;">
                IMPORTANTE
            </p>
            <p style="margin-bottom:0;text-align:justify;">
                Si encuentras <b>algún error</b> en los datos personales o en el listado de actos, por favor, <b>responde a este correo</b> antes del <b>{fecha_limite}</b>.
            </p>
            <p style="margin-top:5px; font-style:italic;text-align:justify;">
                Si no recibimos respuesta antes de esa fecha, entenderemos que confirmas que toda la información es correcta.
            </p>
        </div>
    
        <p style="margin-top:30px;margin-bottom:5px;text-align:justify;">
            A partir de la fecha límite de respuesta, recibirás un correo electrónico a través de <i>Oneflow</i> con un enlace para que puedas <b>firmar digitalmente el recibo de cobro</b>. Haremos la transferencia tan pronto como esté la firma.
        </p>
        <br>
        <p>
            Gracias por tu trabajo y colaboración.
        </p>
        <br>
        <p>
            Un saludo,
        </p>
        <p>
            <i>La Junta Directiva</i><br>
            <i>Banda Sinfónica Círculo Católico de Torrent</i>
        </p>

        <!-- FOOTER -->
        <div style="margin-top:40px;text-align:center;font-size:12px;color:#6b7280;">
            <hr style="border:none;border-top:1px solid #e5e7eb;margin:20px 0;">
            <p style="margin:5px 0;">
                Mensaje enviado automáticamente por el sistema de gestión de actos de la Banda Sinfónica del Círculo Católico de Torrent.
            </p>
            <p style="margin:5px 0;">
                © {__import__('datetime').datetime.now().year} Banda CCT. Todos los derechos reservados.
            </p>
        </div>
    </div>
    """
