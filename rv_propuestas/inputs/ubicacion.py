"""Geolocalización + irradiación solar — query a PVGIS (JRC EU)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

try:
    import requests
except ImportError:
    requests = None  # type: ignore


@dataclass
class Ubicacion:
    nombre: str
    lat: float
    lon: float
    altitud_m: Optional[float] = None


@dataclass
class IrradiacionAnual:
    """Irradiación y generación específica estimadas por PVGIS."""

    ubicacion: Ubicacion
    hsp_anual: float                       # Horas sol pico promedio diarias (kWh/m²/día)
    hsp_mensual: list[float] = field(default_factory=list)  # 12 valores
    temperatura_media_anual: float = 0.0
    generacion_especifica_kwh_kwp: float = 0.0   # Output anual por kWp instalado
    pr_pvgis: float = 0.0
    tilt_optimo: int = 0
    azimuth_optimo: int = 0
    fuente: str = "PVGIS-SARAH3"


def query_pvgis(
    lat: float,
    lon: float,
    peakpower_kwp: float = 1.0,
    loss_pct: float = 14.0,
    tilt: Optional[int] = None,
    azimuth: int = 0,
    mounting: str = "free",
    timeout: int = 30,
) -> dict:
    """Llama a PVGIS v5.3 (JRC) — endpoint PVcalc.

    Si tilt es None, PVGIS busca el óptimo. azimuth=0 = norte en hemisferio sur
    (PVGIS usa convención S=0, ajustamos abajo). En AR: azimuth=180 (norte real).

    PVGIS convention: azimuth 0 = south. Para AR (sur) usar azimuth=180.
    """
    if requests is None:
        raise RuntimeError("requests no instalado. Ejecutá: pip install requests")

    url = "https://re.jrc.ec.europa.eu/api/v5_3/PVcalc"
    params = {
        "lat": lat,
        "lon": lon,
        "peakpower": peakpower_kwp,
        "loss": loss_pct,
        "outputformat": "json",
        "mountingplace": mounting,    # "free" (suelo) | "building" (techo)
        "pvtechchoice": "crystSi",
        "raddatabase": "PVGIS-SARAH3",
        "aspect": azimuth,
    }
    if tilt is None:
        params["optimalangles"] = 1
    else:
        params["angle"] = tilt

    resp = requests.get(url, params=params, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def get_irradiacion(ubic: Ubicacion, tilt: Optional[int] = None) -> IrradiacionAnual:
    """Devuelve la generación específica estimada (kWh/kWp/año) para la ubicación."""
    data = query_pvgis(ubic.lat, ubic.lon, peakpower_kwp=1.0, tilt=tilt, azimuth=180)
    outputs = data.get("outputs", {})
    monthly = outputs.get("monthly", {}).get("fixed", [])
    totals = outputs.get("totals", {}).get("fixed", {})
    inputs = data.get("inputs", {}).get("mounting_system", {}).get("fixed", {})

    gen_anual_kwh_por_kwp = totals.get("E_y", 0.0)
    hsp_anual = totals.get("H(i)_y", 0.0) / 365.0  # kWh/m²/día promedio
    pr = totals.get("PR", 0.0)

    hsp_mensual = [m.get("H(i)_m", 0.0) / 30.4 for m in monthly]  # promedio diario por mes

    return IrradiacionAnual(
        ubicacion=ubic,
        hsp_anual=hsp_anual,
        hsp_mensual=hsp_mensual,
        generacion_especifica_kwh_kwp=gen_anual_kwh_por_kwp,
        pr_pvgis=pr,
        tilt_optimo=int(inputs.get("slope", {}).get("value", tilt or 0)),
        azimuth_optimo=180,
        fuente="PVGIS-SARAH3",
    )


def estimar_offline(ubic: Ubicacion) -> IrradiacionAnual:
    """Estimación offline si no hay internet — usa HSP típico por latitud AR.

    Fuente: PVGIS valores promedio AR. Solo para sanity check; producción usa query_pvgis.
    """
    abs_lat = abs(ubic.lat)
    if abs_lat < 25:        # NOA, Misiones
        hsp = 5.4
        gen_kwh_kwp = 1750
    elif abs_lat < 32:      # Centro (Córdoba, Mendoza)
        hsp = 5.0
        gen_kwh_kwp = 1650
    elif abs_lat < 38:      # AMBA, BA
        hsp = 4.6
        gen_kwh_kwp = 1500
    elif abs_lat < 45:      # Sur BA, Río Negro
        hsp = 4.2
        gen_kwh_kwp = 1380
    else:                   # Patagonia
        hsp = 3.8
        gen_kwh_kwp = 1250

    return IrradiacionAnual(
        ubicacion=ubic,
        hsp_anual=hsp,
        hsp_mensual=[hsp] * 12,
        generacion_especifica_kwh_kwp=gen_kwh_kwp,
        pr_pvgis=0.78,
        tilt_optimo=int(abs_lat),
        azimuth_optimo=180,
        fuente="offline-AR-typical",
    )
