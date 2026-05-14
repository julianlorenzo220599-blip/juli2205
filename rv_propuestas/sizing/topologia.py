"""Selección de inversores y configuración de strings.

Algoritmo simple: dado kWp_DC y la lista de inversores disponibles,
elige la combinación que minimiza el sobredimensionamiento DC/AC sin pasarse
del límite permitido.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from ..config import INVERSORES_EPC, MODULO_REF, Inversor, RatiosTecnicos


@dataclass
class ConfiguracionInversores:
    inversor: Inversor
    cantidad: int
    p_ac_total_kw: float
    p_dc_total_kw: float
    ratio_dc_ac: float


@dataclass
class ConfiguracionStrings:
    n_paneles_por_string: int
    n_strings: int
    n_strings_por_inversor: float
    voc_string: float
    vmpp_string: float
    dentro_ventana_mppt: bool


def seleccionar_inversores(
    kwp_dc: float,
    ratios: RatiosTecnicos | None = None,
) -> ConfiguracionInversores:
    """Elige el modelo y cantidad de inversores para la planta."""
    ratios = ratios or RatiosTecnicos()
    p_ac_objetivo = kwp_dc / ratios.ratio_dc_ac

    mejor: ConfiguracionInversores | None = None
    for inv in INVERSORES_EPC:
        n = max(1, math.ceil(p_ac_objetivo / inv.p_ac_kw))
        p_ac_total = n * inv.p_ac_kw
        p_dc_max = n * inv.p_dc_max_kw
        if kwp_dc > p_dc_max:
            continue
        ratio = kwp_dc / p_ac_total
        if ratio > 1.30:  # nunca exceder 1.30 DC/AC
            continue
        cand = ConfiguracionInversores(
            inversor=inv, cantidad=n,
            p_ac_total_kw=p_ac_total,
            p_dc_total_kw=p_dc_max,
            ratio_dc_ac=round(ratio, 3),
        )
        # Preferimos menor cantidad de unidades; en empate, ratio más cercano al objetivo
        if mejor is None:
            mejor = cand
            continue
        if cand.cantidad < mejor.cantidad:
            mejor = cand
        elif cand.cantidad == mejor.cantidad and abs(cand.ratio_dc_ac - ratios.ratio_dc_ac) < abs(mejor.ratio_dc_ac - ratios.ratio_dc_ac):
            mejor = cand

    if mejor is None:
        # Fallback: el inversor más grande, calculando cuántos necesitamos
        inv = INVERSORES_EPC[-1]
        n = math.ceil(kwp_dc / inv.p_dc_max_kw)
        mejor = ConfiguracionInversores(
            inversor=inv, cantidad=n,
            p_ac_total_kw=n * inv.p_ac_kw,
            p_dc_total_kw=n * inv.p_dc_max_kw,
            ratio_dc_ac=round(kwp_dc / (n * inv.p_ac_kw), 3),
        )
    return mejor


def configurar_strings(
    n_paneles_total: int,
    inv_config: ConfiguracionInversores,
    temp_min_c: float = -5.0,
    temp_max_c: float = 70.0,
) -> ConfiguracionStrings:
    """Define paneles/string y cantidad de strings respetando ventana MPPT del inversor.

    Coef temperatura aproximados módulo TOPCon: Voc -0.25%/°C, Vmpp -0.30%/°C.
    """
    inv = inv_config.inversor
    voc_25 = MODULO_REF.voc
    vmpp_25 = MODULO_REF.vmpp

    # Voc a temperatura mínima (peor caso para superar V_max)
    voc_frio = voc_25 * (1 + 0.0025 * (25 - temp_min_c))
    # Vmpp a temperatura máxima (peor caso para caer bajo V_min)
    vmpp_caliente = vmpp_25 * (1 - 0.0030 * (temp_max_c - 25))

    n_max_por_voc = math.floor(inv.v_mppt_max / voc_frio)
    n_min_por_vmpp = math.ceil(inv.v_mppt_min / vmpp_caliente)

    n_por_string = min(n_max_por_voc, max(n_min_por_vmpp, 14))  # mínimo razonable AR
    # Buscar divisor de n_paneles_total cercano a n_por_string
    candidatos = [c for c in range(max(n_min_por_vmpp, 12), n_max_por_voc + 1) if n_paneles_total % c == 0]
    if candidatos:
        n_por_string = min(candidatos, key=lambda x: abs(x - n_por_string))

    n_strings = math.ceil(n_paneles_total / n_por_string)

    voc_string = n_por_string * voc_frio
    vmpp_string = n_por_string * vmpp_caliente
    ok = inv.v_mppt_min <= vmpp_string and voc_string <= inv.v_mppt_max

    return ConfiguracionStrings(
        n_paneles_por_string=n_por_string,
        n_strings=n_strings,
        n_strings_por_inversor=round(n_strings / inv_config.cantidad, 2),
        voc_string=round(voc_string, 1),
        vmpp_string=round(vmpp_string, 1),
        dentro_ventana_mppt=ok,
    )
