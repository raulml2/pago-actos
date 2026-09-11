import pandas as pd


def clasificar_actos(df, actos_generales):
    df['nombre_acto'] = df['nombre_acto'].str.strip()
    actos_generales = [a.strip() for a in actos_generales]
    df_generales = df[df['nombre_acto'].isin(actos_generales)]
    df_normales = df[~df['nombre_acto'].isin(actos_generales)]
    return df_normales, df_generales


def build_dataframes(datos_musicos):
    df_actos = pd.json_normalize(datos_musicos, record_path='actos', meta=['nombre', 'apellidos', 'email', 'dni', 'n_cuenta'])
    df_otros = pd.json_normalize(datos_musicos, record_path='otros', meta=['nombre', 'apellidos', 'email', 'dni', 'n_cuenta'])
    return df_actos, df_otros


def normalize_datasets(df_actos, df_otros, actos_generales):
    df_actos["importe_cobrado"] = df_actos.apply(
        lambda r: r["importe_cobrado"] if r["asistio"] else 0, axis=1
    )

    df_norm, df_gen = clasificar_actos(df_actos, actos_generales)

    df_norm = df_norm.rename(columns={
        'fecha': 'Fecha', 'nombre_acto': 'Acto', 'importe_base': 'Valor', 'importe_cobrado': 'Percibido'
    })
    df_gen = df_gen.rename(columns={
        'fecha': 'Fecha', 'nombre_acto': 'Acto', 'importe_base': 'Valor', 'importe_cobrado': 'Percibido'
    })
    df_otros = df_otros.rename(columns={
        'nombre_acto': 'Descripción', 'importe_cobrado': 'Percibido'
    })

    df_norm["Percibido"] = pd.to_numeric(df_norm["Percibido"], errors="coerce").fillna(0)
    df_gen["Percibido"]  = pd.to_numeric(df_gen["Percibido"], errors="coerce").fillna(0)
    df_otros["Percibido"] = pd.to_numeric(df_otros["Percibido"], errors="coerce").fillna(0)

    return df_norm, df_gen, df_otros


def insertar_fila_seccion(titulo):
    return pd.DataFrame([{"Fecha": "", "Acto": titulo, "Valor": None, "Percibido": None}])


def tabla_unificada(norm, gen, otros):
    otros = otros.rename(columns={'Descripción': 'Acto'})
    otros['Fecha'] = ""
    otros['Valor'] = None
    otros = otros[['Fecha', 'Acto', 'Valor', 'Percibido']]

    df = pd.concat([
        norm,
        insertar_fila_seccion("ACTOS GENERALES"),
        gen,
        insertar_fila_seccion("OTROS"),
        otros
    ], ignore_index=True)

    return df
