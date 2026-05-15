# RV Energía — Automatización de propuestas (30 kW – 3 MW)

Pipeline end-to-end:

```
Facturas eléctricas (PDF)              ┐
Ubicación (lat, lon)                   │──► sizing ──► BOM ──► costeo ──┐
PDI (tensión / fases / capacidad)      ┘                                │
                                                                        ▼
                                              ┌────────────────────────┴────────────┐
                                              ▼                                     ▼
                                  REVISION_INTERNA_<proy>.xlsx          PROPUESTA_<proy>.pptx
                                  (con márgenes, IVA, alertas)          (vista cliente, sin márgenes)
```

## Instalación

```powershell
py -m pip install -r requirements.txt
```

## Uso rápido — caso demo

```powershell
py -m rv_propuestas.cli demo --salida .\output
```

Genera dos archivos en `./output/`:

- `REVISION_INTERNA_Demo_200_kW.xlsx` — vista Gabriel con márgenes, contingencia, IVA y alertas.
- `PROPUESTA_Demo_200_kW.pptx` — vista cliente con resumen técnico e inversión.

## Uso real — desde factura PDF

```powershell
py -m rv_propuestas.cli desde-factura `
    --pdf "C:\path\factura.pdf" `
    --lat -34.6 --lon -58.4 --ubicacion "Buenos Aires" `
    --tension-pdi 0.38 --fases 3 --capacidad-pdi 300 `
    --distancia 25 `
    --cliente "Cliente S.A." `
    --proyecto "Planta 250 kW" `
    --salida .\output
```

## Ingesta de facturas

### Distribuidoras con parser nativo (gratis, offline)

| Distribuidora | Cobertura                       | Estado |
|---|---|---|
| EDESUR        | CABA + GBA Sur                  | ✓ T3 grandes clientes (tabla 6 meses) + T1 residencial |
| EDESA         | Salta                           | ✓ T1/T2/T3 mensual |
| EDEN          | Norte Pcia. Bs As (Junín, S.N.) | ✓ T1RM mensual |
| EDENOR        | CABA + GBA Norte                | ✓ T1-R1 residencial (Cuenta XXX XXX XXX) — calibrado con PDF real |
| ENERSA        | Entre Ríos (GU industrial)      | ✓ T3 con tabla histórica 13 meses + potencias punta/fuera-punta |
| EPEC          | Córdoba (T3 MT/AT)              | ⚠ stub inferido de factura escaneada — calibrar con PDF real |
| PAMPA         | Mercado a Término (GU)          | ✓ Energía contratada MATE — combinar con factura de distribución local |
| CAMMESA       | Mercado Eléctrico Mayorista     | ⚠ stub — solo aporta potencia, no kWh (combinar con distribuidora) |

Las demás (EDEA, EDET, EDEMSA, EJESA, cooperativas) usan automáticamente
el fallback LLM si está disponible. PDFs escaneados (sin texto extraíble por
pypdf/pdftotext) caen al modo Vision del LLM con el PDF adjunto directo.

### Fallback LLM (Claude API)

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
# Opcional: cambiar modelo (default haiku-4-5-20251001)
$env:RV_LLM_MODEL = "claude-haiku-4-5-20251001"
```

El subsistema intenta primero el parser específico; si falla, llama a Claude
con el texto extraído. PDFs escaneados (sin texto) se mandan como documento
PDF directo (modo vision). Las respuestas se cachean por SHA-256 en
`~/.rv_cache/facturas/` para no re-pagar la API.

### Sin API key — fallback CSV manual

```python
from pathlib import Path
from rv_propuestas.inputs.facturas import interactivo

interactivo.crear_plantilla_csv(Path("kwh.csv"))   # 12 filas vacías
# editás kwh.csv a mano
factura = interactivo.leer_csv(Path("kwh.csv"), distribuidora="COOP_LA_CALDERA")
```

### Cliente con varias facturas mensuales

Si el cliente manda 12 PDFs (uno por mes, típico T1/T2), parseá cada uno y
consolidá:

```python
from rv_propuestas.inputs.facturas import parse_pdf, merge_facturas

facturas = [parse_pdf(p) for p in pdfs]
combo = merge_facturas(facturas)   # consumos unificados por mes
```

### Sumar una nueva distribuidora

1. Crear `rv_propuestas/inputs/facturas/parsers/<nombre>.py`.
2. Implementar `parse(texto: str) -> Optional[Factura]` decorado con
   `@register("NOMBRE", [patrones_de_deteccion])` desde `..registry`.
3. Importarlo en `parsers/__init__.py`.
4. Sumar test en `tests/test_facturas.py` con un excerpt real del PDF.

## Template PPT corporativo

El renderer detecta automáticamente si el `.pptx` que pasás con `--template`
contiene placeholders `{{clave}}`:

- **Con placeholders** → modo plantilla: rellena los placeholders in-place,
  preserva 100% el layout del diseñador, NO agrega slides programáticas.
- **Sin placeholders** → modo legacy: agrega 5 slides estándar sobre el tema
  del template.

### Ejemplo de uso

```powershell
py -m rv_propuestas.cli desde-factura `
    --pdf factura.pdf --lat -34.6 --lon -58.4 `
    --tension-pdi 0.38 --fases 3 --capacidad-pdi 300 `
    --cliente "ACME SA" --proyecto "Planta 250 kW" `
    --template .\plantillas\propuesta_rv_2026.pptx `
    --salida .\output
```

### Sintaxis de placeholders

| Sintaxis | Resultado de ejemplo |
|---|---|
| `{{cliente}}` | `ACME SA` |
| `{{kwp\|1}} kWp` | `242,4 kWp` |
| `{{kwp\|kwp}}` | `242,4 kWp` |
| `{{generacion_anual\|kwh}}` | `456.750 kWh` |
| `{{total_usd\|usd}}` | `USD 229.688` |
| `{{cobertura_pct\|pct}}` | `95%` |
| `{{cobertura_pct\|pct1}}` | `95.2%` |
| `{{n_paneles}}` | `420` |

### Claves disponibles

**Cliente/proyecto**: `cliente`, `titular`, `proyecto`, `direccion`, `nis`, `fecha`, `anio`

**Consumo**: `distribuidora`, `categoria_tarifaria`, `tension`, `potencia_contratada`, `consumo_anual`, `consumo_mensual_promedio`

**Sizing**: `kwp`, `n_paneles`, `wp_panel`, `generacion_anual`, `cobertura_pct`

**Equipamiento**: `n_inversores`, `inversor_sku`, `inversor_descripcion`

**Inversión** (vista cliente, sin márgenes): `neto_usd`, `iva_usd`, `total_usd`, `usd_kwp`

### Inspeccionar un template

```powershell
py -m rv_propuestas.cli placeholders --template .\plantillas\propuesta_rv_2026.pptx -v
```

Salida:
```
Placeholders detectados en propuesta_rv_2026.pptx:
  ✓  {{cliente}}
  ✓  {{kwp}}
  ✓  {{total_usd}}
  ✗ DESCONOCIDO  {{xyz_typo}}      ← typo, no se va a sustituir

Disponibles pero no usados:
     {{cobertura_pct}}
     {{generacion_anual}}
     ...
```

Útil para que el diseñador valide su `.pptx` antes de mandárselo al
comercial — los `✗ DESCONOCIDO` son typos que pasarían como literal `—`.

## Estructura del paquete

```
rv_propuestas/
├── config.py                  # Márgenes (18/25/30/10), IVA (10.5/21), módulo y catálogo de inversores
├── pipeline.py                # Orquestador
├── cli.py                     # Entry point: `py -m rv_propuestas.cli ...`
├── inputs/
│   ├── facturas/              # Subsistema multi-distribuidora
│   │   ├── api.py             # parse_pdf, from_manual, merge_facturas
│   │   ├── modelo.py          # Factura, ConsumoMensual
│   │   ├── registry.py        # @register, detectar()
│   │   ├── pdf_text.py        # extraer_texto + parece_escaneado
│   │   ├── llm.py             # Claude API (texto/vision) + caché SHA-256
│   │   ├── validacion.py      # Sanity checks
│   │   ├── interactivo.py     # Fallback CSV manual
│   │   ├── util.py            # parse_num_ar (formato AR)
│   │   └── parsers/           # Plugins por distribuidora (auto-registro)
│   │       ├── edenor.py    # CABA + GBA Norte (T1-R1 residencial)
│   │       ├── edesur.py    # CABA + GBA Sur (T1 res + T3 GU)
│   │       ├── edesa.py     # Salta
│   │       ├── eden.py      # Norte Pcia. Bs As
│   │       ├── enersa.py    # Entre Ríos (T3 GU industrial)
│   │       ├── epec.py      # Córdoba (T3 MT/AT) — stub
│   │       ├── pampa.py     # MATE — Grandes Usuarios (Pampa Energía SA)
│   │       └── cammesa.py   # Mercado Eléctrico Mayorista (potencia GU)
│   ├── ubicacion.py           # PVGIS API + estimación offline
│   └── pdi.py                 # BT/MT, capacidad disponible, trafo
├── integraciones/
│   ├── pvsyst.py              # Memo + parser CSV + comparador con sizing interno
│   └── clickup.py             # Push automático de task + adjuntos al workspace
├── sizing/
│   ├── engine.py              # kWp objetivo + cobertura + tope por PDI
│   └── topologia.py           # Selección inversores GoodWe + string sizing
├── bom/
│   └── epc.py                 # BOM categorizado: equipos/eléctrico/ingeniería/logística
├── costeo/
│   └── calculo.py             # Aplica márgenes + contingencia + financiero + IVA diferencial
└── render/
    ├── revision_interna.py    # Excel para Gabriel (con márgenes)
    ├── propuesta_cliente.py   # PPT cliente (sin márgenes)
    └── template.py            # Motor de placeholders {{clave|filtro}} en .pptx

data/
└── precios.example.yaml       # Catálogo de precios USD — editar con datos reales

tests/
├── test_smoke.py              # 4 casos pipeline end-to-end (30 kW / 250 kW / 1 MW / 3 MW)
├── test_facturas.py           # 27 tests: detección + parsers + validación
├── test_template.py           # 15 tests: filtros, sustitución, persistencia .pptx
├── test_precios.py            # 7 tests: integridad SKU/precio del catálogo
├── test_pvsyst.py             # 14 tests: parser CSV + memo + comparador
└── test_clickup.py            # 12 tests: payload, tags, HTTP mocks, attachments
```

## Reglas de negocio implementadas

| Regla | Fuente | Módulo |
|---|---|---|
| Márgenes 18/25/30/10 | Contexto §8 | `config.MARGENES` |
| Contingencia +5% | Contexto §8 | `config.CONTINGENCIA` |
| Costo financiero +4% | Contexto §8 | `config.COSTO_FINANCIERO` |
| IVA 10.5% paneles + smart meter | Ley 27.191 | `config.SKU_IVA_REDUCIDO_PATTERNS` |
| IVA 21% resto | — | `config.IVA_GENERAL` |
| Formato AR (coma decimal) | Contexto §8 | `config.fmt_ar()` |
| Módulo TCL 720 W referencia | Catálogo Main Components D03.26 | `config.MODULO_REF` |
| Ratio DC/AC ≤ 1.30 | Datasheet GoodWe | `sizing.topologia` |

## Integración PVSyst

Para proyectos >100 kW conviene validar el sizing en PVSyst antes de firmar.
La pipeline tiene un bridge bidireccional:

### Export — Memo para alimentar PVSyst

```powershell
py -m rv_propuestas.cli desde-factura `
    --pdf factura.pdf --lat -34.6 --lon -58.4 `
    --tension-pdi 0.38 --fases 3 --capacidad-pdi 300 `
    --pvsyst-memo                                    # ← genera PVSYST_INPUT_*.txt
```

Salida `PVSYST_INPUT_<proyecto>.txt`:
```
═══════════════════════════════════════════════════════
PVSYST INPUT MEMO · RV Energía · Planta ACME 250 kW
═══════════════════════════════════════════════════════

GEOGRAPHIC SITE
  Location:        Buenos Aires, Argentina
  Latitude:        -34.6000°
  Longitude:       -58.4000°
  Altitude:        — (cargar de mapa)
  Meteo:           PVGIS-SARAH3 · 4.85 kWh/m²/día prom

SYSTEM SIZING
  Total Pnom (DC): 304.6 kWp
  Inverters (AC):  2 × GoodWe HTH 136 kW 3F (cotizar) = 272 kW
  DC/AC ratio:     1.12

MODULE
  Manufacturer:    TCL SOLAR
  Model:           TCL-MG720DT210-68NS
  ...

STRING CONFIGURATION
  Modules/string:     18
  Total strings:      24
  ...

NEXT STEPS
  1. Crear proyecto en PVSyst con met data PVGIS-SARAH3 del lat/lon arriba.
  ...
```

El ingeniero usa el memo para setear el proyecto en PVSyst sin re-tipear specs.

### Import — Override con reporte validado

Tras correr la simulación, exportar "Main results, per month" como CSV y pasarlo:

```powershell
py -m rv_propuestas.cli desde-factura `
    ... `
    --pvsyst-report .\reportes\acme_pvsyst.csv
```

El parser detecta automáticamente:
- Delimitador (`;` europeo, `,` US, tab)
- Decimales (coma EU o punto US)
- Unidades (MWh vs kWh)
- Meses (inglés, español, francés)

Y reemplaza `sizing.generacion_anual_kwh` por el valor PVSyst, recalculando cobertura. Si la diferencia con nuestra estimación supera 10%, emite un warning:

```
✓ PVSyst: 432,670 kWh anuales · PR 0.832
⚠ Δ -12.3%: PVSyst da 432,670 kWh vs estimación interna 493,500 kWh.
  Revisar PR, irradiación o pérdidas.
```

## Integración ClickUp

Al cerrar la pipeline, opcionalmente crea una task con el resumen de la
propuesta + Excel + PPT adjuntos. Útil para tracking comercial sin doble
carga manual.

### Setup (una vez)

```powershell
$env:CLICKUP_API_TOKEN = "pk_..."          # User Settings → Apps → API Token
$env:CLICKUP_LIST_ID   = "900200123456"    # ID de la lista de propuestas
```

### Uso

```powershell
py -m rv_propuestas.cli desde-factura `
    --pdf factura.pdf --lat -34.6 --lon -58.4 `
    --tension-pdi 0.38 --fases 3 --capacidad-pdi 300 `
    --clickup                                   # ← push automático al final
```

Salida en consola:
```
→ Revisión interna: ./output/REVISION_INTERNA_X.xlsx
→ Propuesta cliente: ./output/PROPUESTA_X.pptx
→ ClickUp task:     https://app.clickup.com/t/abc123 (2 adjunto/s)
```

La task contiene:
- **Título**: `<proyecto> · <kWp> kWp`
- **Body markdown** con cliente, NIS, distribuidora, sizing, generación,
  cobertura, inversión, USD/kWp, SKUs sin precio (si los hay) y notas técnicas.
- **Tags**: `propuesta-auto`, `<distribuidora>`, rango de tamaño
  (`kwp-0-50` / `kwp-50-250` / `kwp-250-1000` / `kwp-1000+`),
  `media-tension` si aplica.
- **Adjuntos**: Excel revisión interna + PPT propuesta cliente.

### Comportamiento defensivo

- Si falta `CLICKUP_API_TOKEN` → skip silencioso (no rompe la pipeline).
- Si falta `CLICKUP_LIST_ID` (y tampoco se pasó `--clickup-list`) → skip.
- Si ClickUp responde con error HTTP → loggea y sigue (no aborta).

Los archivos se generan localmente igual; solo el push se omite.

## Catálogo de precios

`data/precios.example.yaml` viene cargado con los precios del **Catálogo
Main Components RV Energía D03.26** (módulos TCL, inversores GoodWe 8–125
kW, smart meters GMK110/330, estructuras residenciales).

Los items de BoS (cables, tableros, trafos, mano de obra, ingeniería,
logística) están marcados como `(estimado)` — RV debe validarlos contra
cotizaciones reales antes de cerrar oferta.

**Inversores >125 kW** (GW136K-HTH, GW225K-HTH, GW250K-HTH) NO están en el
catálogo retail; los proyectos que los requieran (>250 kW DC con un solo
inversor) aparecen en la hoja "Notas" del Excel de revisión interna para
que RV los cotice a fábrica.

Para overridear precios en un install productivo: copiar
`data/precios.example.yaml` a `data/precios.yaml` (ignorado por git) y
pasarlo con `--precios data/precios.yaml`.

## Próximos pasos

1. **Validar BoS estimados** con cotizaciones reales de RV (cables, trafos,
   MO eléctrica, ingeniería).
2. **Sumar parsers**: EDEA, EDET, EDEMSA, EJESA — esperar PDFs reales.
3. **Calibrar stubs**: EPEC, CAMMESA con PDFs reales (EDENOR ya calibrado).
4. **Obtener CLICKUP_LIST_ID** de la lista de propuestas en producción.

## Notas de entorno

- **Desarrollo cross-platform**: el código Python corre en Linux y Windows.
- **Producción Windows**: usar `py.exe` (Python Launcher). Si querés un wrapper
  PowerShell, podemos sumar `Run-Propuesta.ps1` que invoque `py -m rv_propuestas.cli`.
- **Encoding**: todos los archivos UTF-8. Si se agregan `.ps1`, guardarlos
  con BOM UTF-8 (convención RV).
