"""Sanity checks sobre una Factura ya parseada.

Detecta: mes inválido, kWh negativos/extremos, meses duplicados, inconsistencia
entre potencia contratada y consumo mensual máximo.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .modelo import Factura

_RE_MES = re.compile(r"^\d{4}-\d{2}$")


@dataclass
class ResultadoValidacion:
    ok: bool
    errores: list[str]
    warnings: list[str]


def validar(factura: Factura) -> ResultadoValidacion:
    errores: list[str] = []
    warnings: list[str] = []

    if not factura.consumos:
        errores.append("Sin consumos parseados")
        return ResultadoValidacion(False, errores, warnings)

    meses_vistos: set[str] = set()
    for c in factura.consumos:
        if not c.mes or not _RE_MES.match(c.mes):
            errores.append(f"Mes inválido: {c.mes!r} (esperado YYYY-MM)")
            continue
        if c.mes in meses_vistos:
            warnings.append(f"Mes duplicado: {c.mes}")
        meses_vistos.add(c.mes)
        if c.kwh_total is None or c.kwh_total < 0:
            errores.append(f"kWh inválido para {c.mes}: {c.kwh_total}")
        elif c.kwh_total > 50_000_000:
            warnings.append(f"kWh sospechosamente alto en {c.mes}: {c.kwh_total:,.0f}")

    if len(factura.consumos) < 3:
        warnings.append(
            f"Solo {len(factura.consumos)} mes(es) parseados — "
            "para sizing robusto se recomienda ≥12 meses."
        )

    if factura.potencia_contratada_kw and factura.consumos:
        kwh_max = max(c.kwh_total for c in factura.consumos)
        # Tope físico mensual: 720 h * potencia * margen 1.5 (factor de uso alto + holgura).
        tope = 720 * factura.potencia_contratada_kw * 1.5
        if kwh_max > tope:
            warnings.append(
                f"Consumo mensual máximo ({kwh_max:,.0f} kWh) supera el tope físico "
                f"de la potencia contratada ({factura.potencia_contratada_kw} kW). "
                "Revisar si es factura T3 con potencia adquirida ≠ convenida."
            )

    return ResultadoValidacion(not errores, errores, warnings)
