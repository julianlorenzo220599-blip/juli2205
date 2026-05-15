# Changelog — rv_propuestas

Histórico ordenado por sprint. Branch de trabajo: `claude/research-rv-energia-h2eyM`.

## Sprint cerrado · 2026-05-15

Sprint focal: pasar del MVP demo a un automatizador productivo que
procese facturas reales, dimensione, costee con catálogo real, genere
propuesta cliente con plantilla corporativa y opcionalmente valide en
PVSyst + cierre con task automática en ClickUp.

### Capacidades nuevas

**Ingesta de facturas multi-distribuidora**
- Framework de plugins con auto-registro vía decorador `@register`.
- Parsers nativos calibrados contra PDFs reales:
  EDESUR (T3 grandes clientes + T1 residencial), EDESA, EDEN, EDENOR,
  ENERSA (T3 GU industrial con tabla 13 meses), PAMPA (Mercado a
  Término).
- Stubs sin calibrar (necesitan PDFs reales): EPEC, CAMMESA.
- Fallback LLM con Claude API: texto normal + modo Vision para PDFs
  escaneados, caché por SHA-256 en `~/.rv_cache/facturas/`.
- Fallback CSV manual para cooperativas sin parser ni API key.
- Validación de salida (mes ISO, kWh positivos, consistencia con
  potencia contratada).
- `merge_facturas()` consolida varias facturas mensuales del mismo NIS.

**Template engine para propuesta PPT**
- Detecta automáticamente placeholders `{{clave|filtro}}` en cualquier
  `.pptx`. Si existen → rellena in-place preservando el layout del
  diseñador. Si no → modo legacy (slides programáticas).
- 8 filtros: `|0..2` decimales, `|usd`, `|pct[0-2]`, `|kwh`, `|kwp`,
  default smart.
- Maneja `runs` partidos por PowerPoint + texto en celdas de tabla.
- CLI `placeholders --template foo.pptx -v` para que el diseñador
  valide su `.pptx` antes de producción (marca typos con `✗ DESCONOCIDO`).

**Catálogo de precios real**
- Cargado desde 5 fuentes oficiales:
  - Catálogo Main Components RV D03.26 (módulos TCL + inversores
    GoodWe + baterías + smart meters + estructuras).
  - Brief Kit Solares 2026 v3 (12 kits packaged llave-en-mano).
  - Slocable SP2026030401 (cables solares 1500 VDC + MC4 + herramientas,
    nacionalizado AR vs local).
  - ABB / Técnicas Modernas (TGBT + AC Combiner + Celdas MT UNISEC
    13.2 kV + Shelter, parque 1.8 MWp ref).
  - FREMTEC (cotización terciarizado residencial — comentado como ref).
- Items pendientes de cotización RV: cables AC, tableros chicos,
  trafos, MO eléctrica industrial, ingeniería, logística (marcados
  `(estimado)`).

**Integración PVSyst (bidireccional)**
- EXPORT `--pvsyst-memo`: genera `PVSYST_INPUT_<proy>.txt` con todas
  las specs (site, módulo, inversor, strings, pérdidas sugeridas).
- IMPORT `--pvsyst-report path.csv`: parsea export "Main results, per
  month", tolerante a delim/decimal EU vs US, MWh/kWh, meses
  EN/ES/FR. Reemplaza `sizing.generacion_anual_kwh` por la simulación
  validada y recalcula cobertura.
- CROSS-CHECK con warning si |Δ| > 10%.

**Integración ClickUp**
- Push automático con `--clickup`: crea task con markdown summary +
  Excel + PPT adjuntos al workspace de RV.
- Tags automáticos: `propuesta-auto`, distribuidora, rango kWp,
  `media-tension` si aplica.
- Diseño defensivo: skip silencioso si falta token/lista o si la red
  cae — no rompe la pipeline.

### Métricas del sprint

| Item | Cantidad |
|---|---|
| Commits pushed | 13 |
| Líneas Python agregadas | ~2.500 |
| Tests verdes | 85 (27 facturas + 15 template + 13 precios + 14 pvsyst + 12 clickup + 4 smoke) |
| Distribuidoras AR cubiertas | 8 (EDESUR, EDESA, EDEN, EDENOR, ENERSA, EPEC, PAMPA, CAMMESA) |
| SKUs en catálogo precios | 80+ |
| Kits Brief 2026 referenciados | 12 |

### Validación end-to-end

Smoke en 4 casos representativos:

| Caso | kWp | Inversores | USD/kWp |
|---|---|---|---|
| 30 kW BT residencial-PYME | 35,3 | 1×GW30K-SDT-C30 | 1.387 |
| 250 kW BT industrial | 241,9 | 1×GW225K-HTH | 655 |
| 1 MW MT 13.2 kV | 1.077,1 | 4×GW225K-HTH | 642 |
| 3 MW MT 33 kV | 3.294,0 | 11×GW250K-HTH | 594 |

E2E con PDF real Pampa Energía (MOLINOS MARIMBO, feb-26): parseado
correctamente, 443.520 kWh extraídos.

E2E con CSV sintético PVSyst: override de 456.840 → 432.670 kWh,
cobertura recalculada de 95,2% → 90,1%.

### Pendientes externos (no son tareas de código)

- PDFs reales de EPEC y CAMMESA para calibrar los stubs.
- Cotizaciones BoS reales (cables AC, trafos, ingeniería, logística).
- `CLICKUP_API_TOKEN` + `CLICKUP_LIST_ID` configurados en producción.
- `ANTHROPIC_API_KEY` configurada para activar fallback LLM/Vision.
- Template `.pptx` corporativo con placeholders `{{...}}`.
- Validar EDENOR T3 (parser calibrado con T1 residencial; T3 falta PDF).
