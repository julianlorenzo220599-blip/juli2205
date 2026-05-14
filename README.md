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
| EDESUR        | CABA + GBA Sur                  | ✓ T3 BT/MT con tabla histórica 6 meses |
| EDESA         | Salta                           | ✓ T1/T2/T3 mensual |
| EDEN          | Norte Pcia. Bs As (Junín, S.N.) | ✓ T1RM mensual |
| EDENOR        | CABA + GBA Norte                | ⚠ esqueleto genérico — validar con PDF real |

Las demás (EDEA, EPEC, EDET, EDEMSA, EJESA, cooperativas) usan automáticamente
el fallback LLM si está disponible.

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
│   │       ├── edenor.py
│   │       ├── edesur.py
│   │       ├── edesa.py
│   │       └── eden.py
│   ├── ubicacion.py           # PVGIS API + estimación offline
│   └── pdi.py                 # BT/MT, capacidad disponible, trafo
├── sizing/
│   ├── engine.py              # kWp objetivo + cobertura + tope por PDI
│   └── topologia.py           # Selección inversores GoodWe + string sizing
├── bom/
│   └── epc.py                 # BOM categorizado: equipos/eléctrico/ingeniería/logística
├── costeo/
│   └── calculo.py             # Aplica márgenes + contingencia + financiero + IVA diferencial
└── render/
    ├── revision_interna.py    # Excel para Gabriel (con márgenes)
    └── propuesta_cliente.py   # PPT cliente (sin márgenes)

data/
└── precios.example.yaml       # Catálogo de precios USD — editar con datos reales

tests/
├── test_smoke.py              # 4 casos pipeline end-to-end (30 kW / 250 kW / 1 MW / 3 MW)
└── test_facturas.py           # 17 tests: detección + parsers + validación
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
| Módulo TCL 725 W referencia | Contexto §3 | `config.MODULO_REF` |
| Ratio DC/AC ≤ 1.30 | Datasheet GoodWe | `sizing.topologia` |

## Próximos pasos

1. **Calibrar precios reales** en `data/precios.yaml` (renombrar `.example.yaml`).
2. **Sumar parsers**: EPEC, EDEA, EDET, EDEMSA, EJESA — esperar PDFs reales.
3. **Validar EDENOR** contra una factura real (el parser actual es genérico).
4. **Template PPT corporativo** — pasar via `--template` para usar el master de RV.
5. **Integración PVSyst** — bridge para validar proyectos >100 kW antes de firmar.
6. **Integración ClickUp** — empujar el resumen al pipeline (workspace `90132555978`).

## Notas de entorno

- **Desarrollo cross-platform**: el código Python corre en Linux y Windows.
- **Producción Windows**: usar `py.exe` (Python Launcher). Si querés un wrapper
  PowerShell, podemos sumar `Run-Propuesta.ps1` que invoque `py -m rv_propuestas.cli`.
- **Encoding**: todos los archivos UTF-8. Si se agregan `.ps1`, guardarlos
  con BOM UTF-8 (convención RV).
