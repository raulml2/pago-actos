# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Automation system for the Banda Sinfónica del Círculo Católico de Torrent (CCT) that manages musician payment per performance. The full flow is: download attendance data from Glissandoo → unify into a spreadsheet → generate receipts (PDF from Word template) → send emails with act summaries via Gmail API → send receipts via OneFlow → generate the bank payment remittance Excel.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run download pipeline (Selenium + Glissandoo)
python -m src.descarga.pipeline_descarga

# Run send pipeline (emails, receipts, remittance)
python -m src.envio.pipeline_envio

# Send receipts via OneFlow (Selenium)
python -m src.envio.envio_recibos
```

There are no automated tests in this project.

## Configuration Before Each Payment Period

All payment-specific settings live in [src/common/config.py](src/common/config.py) and must be updated at the start of each payment cycle:

- `PAGO` — period identifier (e.g. `"2026A"`), used to name output directories
- `FECHA_INICIO` / `FECHA_FIN` — date range for acts in `dd/mm/yyyy` format
- `COL_INIT_ACTOS` / `COL_END_ACTOS` — column indices in the Excel control sheet (change if columns shift)
- `N_ACTOS_GENERALES` / `N_OTROS` — count of general acts and "otros" columns at the end of the act range
- `RUTA_EXCEL` — path to the private `.xlsm` control file (not in git)

Execution flags in `config.py` act as a safety switch — set each to `True` only when ready to run that stage:

| Flag | Effect |
|---|---|
| `CREAR_RECIBOS` | Generate PDF receipts |
| `GENERAR_CORREO_PREVIA` | Open a random musician's email preview in browser |
| `ENVIAR_CORREOS` | Send emails via Gmail API |
| `GENERAR_REMESA` | Write the bank remittance Excel |

## Architecture

### Two independent pipelines

**`src/descarga/`** — Selenium-based scraper for [app.glissandoo.com](https://app.glissandoo.com):
- `descargar_actos.py`: Logs into Glissandoo, iterates past performance events within `FECHA_INICIO`–`FECHA_FIN`, downloads each as `.xlsx` to a temp folder, then moves them to `data/asistencias/<PAGO>/`.
- `unificar_actos.py`: Reads all downloaded `.xlsx` files, extracts attendance per act (column `"Pasar lista"` / value `"Ha asistido"`), and outputs a consolidated `_asistentes_actos_<PAGO>.xlsx` at the project root — ready to paste into the control Excel.

**`src/envio/`** — Data processing and communication:
- `excel_loader.py`: Reads the private `.xlsm` control file using openpyxl. Row 2 = act names, row 3 = rates, row 5 = dates; musicians start at row 9. Attendance is encoded as `"X"` or `"D"` in the cell value.
- `transform_data.py`: Builds DataFrames from the parsed musician data, normalizing acts into `df_norm` (per-musician per-act), `df_gen` (general acts), and `df_otros` (extra items).
- `html_builder.py`: Renders the per-musician act table as HTML for email body.
- `receipts.py`: Fills the Word template (`src/assets/templates/Recibo_Template.docx`) with `python-docx-template` and converts to PDF with `docx2pdf`. Output files are named `"NOMBRE Apellidos__$__email.pdf"` — the `__$__` separator is later parsed by `envio_recibos.py`.
- `gmail_sender.py`: Authenticates with the Gmail API (`credentials.json` + `token_gmail.json`), builds MIME messages, and sends in batches respecting rate limits.
- `remesa.py`: Generates the bank remittance Excel file.
- `envio_recibos.py`: Selenium automation for OneFlow — uploads each PDF, adds participant (name/email parsed from filename), and sends for e-signature.

### Data flow

```
Glissandoo (web)
    └─ descargar_actos → data/asistencias/<PAGO>/*.xlsx
                           └─ unificar_actos → _asistentes_actos_<PAGO>.xlsx
                                                └─ [manual paste into RUTA_EXCEL]

RUTA_EXCEL (.xlsm)
    └─ excel_loader → transform_data → html_builder → gmail_sender (emails)
                                     └─ receipts → data/recibos/<PAGO>/*.pdf
                                                     └─ envio_recibos (OneFlow)
                                     └─ remesa → data/remesas/<PAGO>/*.xlsx
```

### Required environment variables (`.env`)

```
GLISSANDOO_EMAIL=
GLISSANDOO_PASSWORD=
GLISSANDOO_URL=
GLISSANDOO_AGRUPACION=
GMAIL_FROM=
ONEFLOW_URL=
ONEFLOW_EMAIL=
ONEFLOW_PASSWORD=
```

Gmail also requires `credentials.json` and `token_gmail.json` (OAuth2) at the project root.

## Private data not in git

- `data/private/CONTROL_ACTOS_2025.xlsm` — the master Excel with all musician data
- `.env` — credentials
- `credentials.json` / `token_gmail.json` — Gmail OAuth tokens
