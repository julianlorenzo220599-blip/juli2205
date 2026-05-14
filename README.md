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

### Si el parser no reconoce la distribuidora

Configurá la API key de Claude para el fallback LLM:

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
```

El parser híbrido intenta primero el parser específico (EDENOR está implementado
como base; el resto vía LLM) y solo cae al LLM cuando es necesario.

## Estructura del paquete

```
rv_propuestas/
├── config.py                  # Márgenes (18/25/30/10), IVA (10.5/21), módulo y catálogo de inversores
├── pipeline.py                # Orquestador
├── cli.py                     # Entry point: `py -m rv_propuestas.cli ...`
├── inputs/
│   ├── facturas.py            # Parser híbrido + fallback Claude API
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
└── test_smoke.py              # 4 casos (30 kW / 250 kW / 1 MW / 3 MW)
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

## Próximos pasos (no incluidos en este MVP)

1. **Calibrar precios reales** en `data/precios.yaml` (renombrar `.example.yaml`).
2. **Sumar parsers de distribuidoras** prioritarias (EDESUR, EPEC) con PDFs reales.
3. **Template PPT corporativo** — pasar via `--template` para usar el master de RV.
4. **Integración PVSyst** — bridge para validar proyectos >100 kW antes de firmar.
5. **Integración ClickUp** — empujar el resumen al pipeline (workspace `90132555978`).

## Notas de entorno

- **Desarrollo cross-platform**: el código Python corre en Linux y Windows.
- **Producción Windows**: usar `py.exe` (Python Launcher). Si querés un wrapper
  PowerShell, podemos sumar `Run-Propuesta.ps1` que invoque `py -m rv_propuestas.cli`.
- **Encoding**: todos los archivos UTF-8. Si se agregan `.ps1`, guardarlos
  con BOM UTF-8 (convención RV).
