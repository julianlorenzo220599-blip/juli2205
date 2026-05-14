"""Bridge bidireccional con PVSyst.

EXPORT — `generar_memo()` → texto estructurado que el diseñador pega en los
diálogos de PVSyst para setear el proyecto sin re-tipear datos.

IMPORT — `parsear_reporte_csv()` → lee el export "Main results, per month"
de PVSyst y devuelve un `ResultadoPVSyst` con yield anual + PR + array
mensual. Lo usa la pipeline para reemplazar nuestra estimación heurística
por la simulación validada.

CROSS-CHECK — `comparar()` flaggea deltas >10% entre nuestra estimación
y PVSyst, alertando al ingeniero antes de firmar.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ──────────────────────────────────────────────────────────────────────────────
# Modelo de resultado
# ──────────────────────────────────────────────────────────────────────────────
@dataclass
class ResultadoPVSyst:
    """Salida típica de PVSyst Main Results: yield + PR + perfil mensual."""

    energia_anual_kwh: float
    pr_anual: Optional[float] = None
    energia_mensual_kwh: list[float] = field(default_factory=list)   # 12 elementos
    pr_mensual: list[Optional[float]] = field(default_factory=list)
    glob_inc_anual: Optional[float] = None
    temperatura_media: Optional[float] = None
    fuente: str = "pvsyst:csv"

    def yield_especifico(self, kwp_dc: float) -> Optional[float]:
        return self.energia_anual_kwh / kwp_dc if kwp_dc > 0 else None


@dataclass
class ComparacionPVSyst:
    nuestra_estimacion_kwh: float
    pvsyst_kwh: float
    delta_pct: float          # (pvsyst - nuestra) / nuestra * 100
    pr_pvsyst: Optional[float]
    warning: Optional[str]    # mensaje si |delta| > umbral


# ──────────────────────────────────────────────────────────────────────────────
# IMPORT — parser del reporte CSV de PVSyst
# ──────────────────────────────────────────────────────────────────────────────
_MESES = {
    # Inglés
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
    # Español
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
    "ene": 1, "abr": 4, "ago": 8, "set": 9, "dic": 12,
    # Francés (PVSyst es de origen suizo)
    "janvier": 1, "février": 2, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
    "juillet": 7, "août": 8, "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11,
    "décembre": 12, "decembre": 12,
}

_TOTAL_LABELS = {"year", "año", "ano", "annee", "année", "anual", "total"}


def parsear_reporte_csv(path: str | Path) -> ResultadoPVSyst:
    """Parsea un export 'Main results, per month' de PVSyst.

    Robusto a: delimitador `;` / `,` / tab, decimales europeos (`,`) y de
    estilo US (`.`), unidades MWh o kWh, meses en EN/ES/FR. Si encuentra una
    fila Year/Total la usa para el anual; sino suma los 12 meses.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    raw = path.read_text(encoding="utf-8", errors="replace")
    return parsear_reporte_texto(raw, fuente=f"pvsyst:csv:{path.name}")


def parsear_reporte_texto(texto: str, fuente: str = "pvsyst:csv") -> ResultadoPVSyst:
    """Versión que recibe el texto directamente — útil para tests sin tocar disco."""
    delim = _detectar_delim(texto)
    lineas = [ln for ln in texto.splitlines() if ln.strip()]

    idx_header = _localizar_header(lineas, delim)
    if idx_header is None:
        raise ValueError(
            "No se encontró columna 'E_Grid' en el reporte. "
            "¿Exportaste 'Main results, per month' desde PVSyst?"
        )

    header = [c.strip() for c in lineas[idx_header].split(delim)]
    idx_e_grid = _buscar_col(header, [r"E[\s_]*Grid", r"EnergyToGrid"])
    idx_pr = _buscar_col(header, [r"^PR$", r"Performance\s*Ratio"])
    idx_glob_inc = _buscar_col(header, [r"GlobInc"])
    idx_t_amb = _buscar_col(header, [r"T[\s_]*Amb"])

    # Detectar fila de unidades (la siguiente, si su primera celda no es un mes)
    inicio_datos = idx_header + 1
    factor_e = 1
    if inicio_datos < len(lineas):
        primera_col = lineas[inicio_datos].split(delim)[0].strip().lower()
        if not _es_mes(primera_col) and primera_col not in _TOTAL_LABELS:
            unidades = [c.strip().lower() for c in lineas[inicio_datos].split(delim)]
            if idx_e_grid is not None and idx_e_grid < len(unidades):
                if "mwh" in unidades[idx_e_grid]:
                    factor_e = 1000
                elif "gwh" in unidades[idx_e_grid]:
                    factor_e = 1_000_000
            inicio_datos += 1

    mensual_e: dict[int, float] = {}
    mensual_pr: dict[int, float] = {}
    anual_e: Optional[float] = None
    anual_pr: Optional[float] = None
    glob_inc_anual: Optional[float] = None
    t_amb_media: Optional[float] = None
    t_amb_sum, t_amb_n = 0.0, 0

    for ln in lineas[inicio_datos:]:
        cols = [c.strip() for c in ln.split(delim)]
        if not cols or not cols[0]:
            continue
        etiqueta = cols[0].strip(". ").lower()

        if _es_mes(etiqueta):
            mes = _MESES[etiqueta]
            valor_e = _safe_col(cols, idx_e_grid)
            if valor_e is not None:
                mensual_e[mes] = valor_e * factor_e
            valor_pr = _safe_col(cols, idx_pr)
            if valor_pr is not None:
                mensual_pr[mes] = _normalizar_pr(valor_pr)
            t = _safe_col(cols, idx_t_amb)
            if t is not None:
                t_amb_sum += t
                t_amb_n += 1
        elif etiqueta in _TOTAL_LABELS:
            anual_e_raw = _safe_col(cols, idx_e_grid)
            if anual_e_raw is not None:
                anual_e = anual_e_raw * factor_e
            anual_pr_raw = _safe_col(cols, idx_pr)
            if anual_pr_raw is not None:
                anual_pr = _normalizar_pr(anual_pr_raw)
            glob_inc_anual = _safe_col(cols, idx_glob_inc)

    if anual_e is None:
        if mensual_e:
            anual_e = sum(mensual_e.values())
        else:
            raise ValueError("No se pudieron extraer ni datos mensuales ni anuales.")

    if anual_pr is None and mensual_pr:
        # Promedio ponderado por kWh (no aritmético) — PR mensual del mes con
        # más generación pesa más en el PR anual.
        total_kwh = sum(mensual_e.values())
        if total_kwh > 0:
            anual_pr = sum(
                mensual_pr[m] * mensual_e[m] for m in mensual_pr if m in mensual_e
            ) / total_kwh

    if t_amb_n > 0:
        t_amb_media = t_amb_sum / t_amb_n

    return ResultadoPVSyst(
        energia_anual_kwh=anual_e,
        pr_anual=anual_pr,
        energia_mensual_kwh=[mensual_e.get(m, 0.0) for m in range(1, 13)],
        pr_mensual=[mensual_pr.get(m) for m in range(1, 13)],
        glob_inc_anual=glob_inc_anual,
        temperatura_media=t_amb_media,
        fuente=fuente,
    )


# ──────────────────────────────────────────────────────────────────────────────
# CROSS-CHECK
# ──────────────────────────────────────────────────────────────────────────────
def comparar(
    sizing,
    pvsyst: ResultadoPVSyst,
    umbral_warning_pct: float = 10.0,
) -> ComparacionPVSyst:
    """Compara generación estimada interna vs PVSyst. Warning si |delta|>umbral."""
    nuestra = float(sizing.generacion_anual_kwh)
    delta = (pvsyst.energia_anual_kwh - nuestra) / nuestra * 100 if nuestra else 0.0
    warning = None
    if abs(delta) > umbral_warning_pct:
        warning = (
            f"Δ {delta:+.1f}%: PVSyst da {pvsyst.energia_anual_kwh:,.0f} kWh "
            f"vs estimación interna {nuestra:,.0f} kWh. Revisar PR, irradiación o pérdidas."
        )
    return ComparacionPVSyst(
        nuestra_estimacion_kwh=nuestra,
        pvsyst_kwh=pvsyst.energia_anual_kwh,
        delta_pct=round(delta, 2),
        pr_pvsyst=pvsyst.pr_anual,
        warning=warning,
    )


# ──────────────────────────────────────────────────────────────────────────────
# EXPORT — memo para alimentar PVSyst manualmente
# ──────────────────────────────────────────────────────────────────────────────
def generar_memo(
    *,
    factura,
    sizing,
    ubicacion,
    irradiacion,
    inv_cfg,
    str_cfg,
    proyecto: str = "",
) -> str:
    """Texto estructurado que el diseñador copia para setear PVSyst.

    Cubre: site geográfico, orientación, módulo, inversor, configuración de
    strings, pérdidas sugeridas y resultados esperados. La idea es que
    PVSyst sea "transcripción guiada" en vez de re-cálculo desde cero.
    """
    from ..config import MODULO_REF

    sep = "═" * 72
    yield_kwh_kwp = (
        sizing.generacion_anual_kwh / sizing.kwp_real if sizing.kwp_real else 0
    )
    tilt = irradiacion.tilt_optimo or abs(round(ubicacion.lat))
    azimuth = irradiacion.azimuth_optimo or 0
    ok = "✓" if getattr(str_cfg, "dentro_ventana_mppt", True) else "✗"

    lines = [
        sep,
        f"PVSYST INPUT MEMO · RV Energía  ·  {proyecto or 'proyecto sin nombre'}",
        f"Cliente: {factura.titular or '—'}   ·   NIS: {factura.nis or '—'}",
        sep,
        "",
        "GEOGRAPHIC SITE",
        f"  Location:        {ubicacion.nombre or '—'}, Argentina",
        f"  Latitude:        {ubicacion.lat:.4f}°",
        f"  Longitude:       {ubicacion.lon:.4f}°",
        f"  Altitude:        {ubicacion.altitud_m if ubicacion.altitud_m is not None else '— (cargar de mapa)'}",
        f"  Meteo:           {irradiacion.fuente} · {irradiacion.hsp_anual:.2f} kWh/m²/día prom",
        "",
        "ORIENTATION",
        f"  Tilt:            {tilt}°",
        f"  Azimuth:         {azimuth}° (0=norte hemisferio sur)",
        "  Mounting:        Free standing (ajustar si es techo/coplanar)",
        "",
        "SYSTEM SIZING",
        f"  Total Pnom (DC): {sizing.kwp_real:.1f} kWp",
        f"  Inverters (AC):  {inv_cfg.cantidad} × {inv_cfg.inversor.descripcion} = {inv_cfg.p_ac_total_kw:.0f} kW",
        f"  DC/AC ratio:     {inv_cfg.ratio_dc_ac}",
        f"  Topología:       {sizing.topologia} — {sizing.topologia_descripcion}",
        "",
        "MODULE",
        f"  Manufacturer:    {MODULO_REF.marca}",
        f"  Model:           {MODULO_REF.sku}",
        f"  Type:            TOPCon Bifacial ({MODULO_REF.eficiencia*100:.1f}% efic.)",
        f"  Pnom:            {MODULO_REF.wp} Wp",
        f"  Voc / Isc:       {MODULO_REF.voc} V / {MODULO_REF.isc} A",
        f"  Vmpp / Impp:     {MODULO_REF.vmpp} V / {MODULO_REF.impp} A",
        f"  Total modules:   {sizing.n_paneles}",
        "",
        "INVERTER",
        "  Manufacturer:    GoodWe",
        f"  Model:           {inv_cfg.inversor.sku}",
        f"  Pnom AC:         {inv_cfg.inversor.p_ac_kw} kW ({inv_cfg.inversor.fase})",
        f"  Pmax DC:         {inv_cfg.inversor.p_dc_max_kw} kW",
        f"  MPPT range:      {inv_cfg.inversor.v_mppt_min} - {inv_cfg.inversor.v_mppt_max} V",
        f"  N° MPPTs:        {inv_cfg.inversor.n_mppt} × {inv_cfg.inversor.n_strings_por_mppt} strings",
        f"  Cantidad:        {inv_cfg.cantidad}",
        "",
        "STRING CONFIGURATION",
        f"  Modules/string:     {str_cfg.n_paneles_por_string}",
        f"  Total strings:      {str_cfg.n_strings}",
        f"  Strings/inverter:   {str_cfg.n_strings_por_inversor}",
        f"  Voc string (-5°C):  {str_cfg.voc_string} V (max inv {inv_cfg.inversor.v_mppt_max}) {ok}",
        f"  Vmpp string (+70°C):{str_cfg.vmpp_string} V (min inv {inv_cfg.inversor.v_mppt_min}) {ok}",
        "",
        "LOSSES (defaults — ajustar tras site survey)",
        "  Soiling:            2.5 %",
        "  Wiring DC:          1.5 %",
        "  Wiring AC:          0.5 %",
        "  Mismatch modules:   1.0 %",
        "  Mismatch strings:   0.1 %",
        "  Availability:       99.5 %",
        "  Target PR:          ~78 %",
        "",
        "EXPECTED RESULTS (estimación interna — validar en PVSyst)",
        f"  Yield específico:   {yield_kwh_kwp:.0f} kWh/kWp/año",
        f"  Generación anual:   {sizing.generacion_anual_kwh:,.0f} kWh",
        f"  Cobertura consumo:  {sizing.cobertura*100:.1f} %",
        "",
        "NEXT STEPS",
        "  1. Crear proyecto en PVSyst con met data PVGIS-SARAH3 del lat/lon arriba.",
        "  2. Cargar módulo TCL desde PAN file (vendor) o crear manual con specs.",
        "  3. Cargar inversor GoodWe desde OND file o crear manual con specs.",
        "  4. Configurar arrays: paneles/string + n° strings del bloque arriba.",
        "  5. Aplicar pérdidas y correr simulación.",
        "  6. Exportar 'Main results, per month' como CSV.",
        "  7. Re-correr pipeline: --pvsyst-report path/al/reporte.csv",
        "",
        sep,
    ]
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers internos
# ──────────────────────────────────────────────────────────────────────────────
def _detectar_delim(texto: str) -> str:
    head = "\n".join(texto.splitlines()[:30])
    if head.count(";") >= max(head.count(","), head.count("\t")):
        return ";"
    if head.count("\t") > head.count(","):
        return "\t"
    return ","


def _localizar_header(lineas: list[str], delim: str) -> Optional[int]:
    for i, ln in enumerate(lineas):
        if re.search(r"E[\s_]*Grid", ln, re.IGNORECASE):
            return i
    return None


def _buscar_col(cols: list[str], patrones: list[str]) -> Optional[int]:
    for i, c in enumerate(cols):
        for p in patrones:
            if re.search(p, c, re.IGNORECASE):
                return i
    return None


def _es_mes(s: str) -> bool:
    return s.strip(". ").lower() in _MESES


def _safe_col(cols: list[str], idx: Optional[int]) -> Optional[float]:
    if idx is None or idx >= len(cols):
        return None
    try:
        return _parse_num(cols[idx])
    except ValueError:
        return None


def _parse_num(s: str) -> float:
    """Parser numérico tolerante a formato EU vs US.

    Heurística:
      - "1.234,56" → 1234.56 (EU)
      - "1,234.56" → 1234.56 (US)
      - "1234,56"  → 1234.56 (EU sin miles)
      - "1234.56"  → 1234.56 (US sin miles)
      - "1234"     → 1234
    """
    s = s.strip().replace(" ", "")
    if not s:
        raise ValueError("empty")
    if "," in s and "." in s:
        # El último separador es el decimal
        if s.rindex(",") > s.rindex("."):
            return float(s.replace(".", "").replace(",", "."))
        return float(s.replace(",", ""))
    if "," in s:
        # Solo coma: decimal EU
        return float(s.replace(",", "."))
    return float(s)


def _normalizar_pr(valor: float) -> float:
    """PVSyst a veces exporta PR como fracción (0.78) y a veces como % (78)."""
    return valor / 100 if valor > 1.5 else valor
