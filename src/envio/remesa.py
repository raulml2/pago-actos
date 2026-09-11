import pandas as pd
from src.common.config import PAGO


def generar_remesa_pagos(musicos, output_path, year=None):
    '''
    Genera un archivo Excel para la remesa de pagos SEPA.
    - musicos: lista de dicts con las claves 'nombre', 'apellidos', 'dni', 'n_cuenta', 'total_pago'
    - output_path: ruta donde guardar el excel
    - year: año actual (opcional, si None se toma el año actual)
    '''
    from datetime import date
    if year is None:
        year = date.today().year

    rows = []
    for m in musicos:
        row = {
                "NOMBRE": m["nombre"],
                "APELLIDOS": m["apellidos"],
                "DNI": m["dni"],
                "N_CUENTA": m.get("n_cuenta", m.get("iban", "")),
                "TOTAL_PAGO": m["total_pago"],
                "GASTOS": 1,
                "CONCEPTO": f"{'Primer' if PAGO.endswith('A') else 'Segundo'} Pago {year} a {m['nombre']} {m['apellidos']} DNI - {m['dni']}",
                "NOMBRE COMPLETO": f"{m['nombre']} {m['apellidos']}",
            }
        rows.append(row)

    df = pd.DataFrame(rows)
    df.to_excel(output_path, index=False)
    print(f"Archivo generado: {output_path}")
    return df
