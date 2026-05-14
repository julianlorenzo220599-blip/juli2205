"""Motor de dimensionamiento: calcula kWp, n° de paneles, generación esperada.

Inputs:
  - Factura (consumo anual + potencia contratada)
  - IrradiacionAnual (kWh/kWp/año estimados)
  - PDI (límite de inyección, si existe)

Outputs: SizingResult con kWp recomendado y métricas técnicas.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from ..config import MODULO_REF, RatiosTecnicos, UMBRALES
from ..inputs.facturas import Factura
from ..inputs.pdi import PDI
from ..inputs.ubicacion import IrradiacionAnual


@dataclass
class SizingResult:
    kwp_recomendado: float
    n_paneles: int
    kwp_real: float                  # n_paneles * Wp_panel / 1000
    generacion_anual_kwh: float
    consumo_anual_kwh: float
    cobertura: float                 # generación / consumo
    cobertura_objetivo: float
    limitado_por_pdi: bool
    kwp_solicitado_sin_limite: float
    topologia: str                   # de config.UMBRALES
    topologia_descripcion: str
    notas: list[str]


def _seleccionar_topologia(kwp: float) -> tuple[str, str]:
    for umb in UMBRALES:
        if kwp <= umb.kwp_max:
            return umb.tipo, umb.descripcion
    return UMBRALES[-1].tipo, UMBRALES[-1].descripcion


def dimensionar(
    factura: Factura,
    irradiacion: IrradiacionAnual,
    pdi: PDI,
    ratios: RatiosTecnicos | None = None,
) -> SizingResult:
    ratios = ratios or RatiosTecnicos()
    notas: list[str] = []

    consumo_anual = factura.consumo_anual_kwh
    if consumo_anual <= 0:
        raise ValueError(
            "La factura no tiene consumo cargado. Cargá 12 meses con from_manual() o parse_pdf()."
        )

    gen_especifica = irradiacion.generacion_especifica_kwh_kwp or (
        irradiacion.hsp_anual * 365 * ratios.pr_default
    )

    # 1) kWp objetivo según cobertura deseada
    kwp_objetivo = (consumo_anual * ratios.cobertura_objetivo) / gen_especifica

    # 2) Tope por PDI
    kwp_max_pdi = pdi.kwp_maximo_por_pdi(ratio_dc_ac=ratios.ratio_dc_ac)
    limitado = False
    kwp_solicitado = kwp_objetivo
    if kwp_max_pdi is not None and kwp_objetivo > kwp_max_pdi:
        notas.append(
            f"kWp objetivo ({kwp_objetivo:.1f}) excede capacidad PDI "
            f"({pdi.capacidad_disponible_kw} kW × ratio DC/AC {ratios.ratio_dc_ac} = {kwp_max_pdi:.1f} kWp). "
            f"Se limita la planta."
        )
        kwp_objetivo = kwp_max_pdi
        limitado = True

    # 3) Cantidad de paneles
    wp_panel = MODULO_REF.wp
    n_paneles = math.ceil((kwp_objetivo * 1000) / wp_panel)
    kwp_real = n_paneles * wp_panel / 1000.0

    # 4) Generación esperada
    gen_anual = kwp_real * gen_especifica
    cobertura = gen_anual / consumo_anual if consumo_anual else 0.0

    # 5) Topología sugerida
    topo, topo_desc = _seleccionar_topologia(kwp_real)

    if pdi.es_baja_tension and kwp_real > 300:
        notas.append(
            "ATENCIÓN: kWp > 300 sobre BT. Verificar con distribuidora si admite o si requiere migrar a MT."
        )
    if pdi.es_media_tension and not pdi.requiere_trafo_elevador:
        notas.append("PDI en MT — confirmar si la planta inyecta directo en MT o requiere trafo.")
    if irradiacion.fuente == "offline-AR-typical":
        notas.append("Irradiación estimada offline. Validar con consulta PVGIS antes de cotizar firme.")

    return SizingResult(
        kwp_recomendado=round(kwp_real, 2),
        n_paneles=n_paneles,
        kwp_real=round(kwp_real, 3),
        generacion_anual_kwh=round(gen_anual, 0),
        consumo_anual_kwh=round(consumo_anual, 0),
        cobertura=round(cobertura, 3),
        cobertura_objetivo=ratios.cobertura_objetivo,
        limitado_por_pdi=limitado,
        kwp_solicitado_sin_limite=round(kwp_solicitado, 2),
        topologia=topo,
        topologia_descripcion=topo_desc,
        notas=notas,
    )
