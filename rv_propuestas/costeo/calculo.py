"""Cálculo de costo total con márgenes y IVA.

Pipeline:
  costo_neto (BOM)
    + margen por categoría (equipos 18%, eléctrico 25%, ingeniería 30%, logística 10%)
    = subtotal con margen
    + contingencia 5%
    + costo financiero 4%
    = neto cliente
    + IVA (10.5% paneles+smart, 21% resto)
    = total cliente

Devuelve ambos: vista interna (con desglose de márgenes) y vista cliente (final).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..bom.epc import BOM, ItemBOM
from ..config import (
    CONTINGENCIA, COSTO_FINANCIERO, IVA_GENERAL, IVA_REDUCIDO,
    MARGENES, SKU_IVA_REDUCIDO_PATTERNS,
)


@dataclass
class LineaCosteo:
    item: ItemBOM
    costo_neto: float
    margen_pct: float
    margen_usd: float
    precio_con_margen: float
    iva_pct: float
    iva_usd: float
    precio_final: float


@dataclass
class TotalesCategoria:
    categoria: str
    costo_neto: float
    margen_usd: float
    precio_con_margen: float


@dataclass
class CosteoResult:
    lineas: list[LineaCosteo] = field(default_factory=list)
    totales_categoria: list[TotalesCategoria] = field(default_factory=list)
    costo_neto_total: float = 0.0
    subtotal_con_margen: float = 0.0
    contingencia_usd: float = 0.0
    costo_financiero_usd: float = 0.0
    neto_cliente: float = 0.0
    iva_total: float = 0.0
    total_cliente: float = 0.0
    items_sin_precio: list[str] = field(default_factory=list)

    @property
    def precio_por_kwp(self) -> float:
        return 0.0  # se inyecta desde el caller con kWp real


def _es_iva_reducido(item: ItemBOM) -> bool:
    if item.iva_reducido:
        return True
    return any(item.sku.startswith(p) for p in SKU_IVA_REDUCIDO_PATTERNS)


def calcular(bom: BOM) -> CosteoResult:
    res = CosteoResult()
    cat_acum: dict[str, dict[str, float]] = {}

    for item in bom.items:
        if item.precio_unit_usd is None:
            res.items_sin_precio.append(item.sku)
            costo_neto = 0.0
        else:
            costo_neto = item.precio_unit_usd * item.cantidad

        margen_pct = MARGENES.get(item.categoria, 0.0)
        margen_usd = costo_neto * margen_pct
        precio_con_margen = costo_neto + margen_usd

        iva_pct = IVA_REDUCIDO if _es_iva_reducido(item) else IVA_GENERAL
        # IVA se aplica al precio final cliente, no acá; se calcula al final
        res.lineas.append(LineaCosteo(
            item=item,
            costo_neto=round(costo_neto, 2),
            margen_pct=margen_pct,
            margen_usd=round(margen_usd, 2),
            precio_con_margen=round(precio_con_margen, 2),
            iva_pct=iva_pct,
            iva_usd=0.0,            # se calcula abajo
            precio_final=0.0,
        ))

        acum = cat_acum.setdefault(item.categoria, {"neto": 0.0, "margen": 0.0, "con_margen": 0.0})
        acum["neto"] += costo_neto
        acum["margen"] += margen_usd
        acum["con_margen"] += precio_con_margen

    for cat, acum in cat_acum.items():
        res.totales_categoria.append(TotalesCategoria(
            categoria=cat,
            costo_neto=round(acum["neto"], 2),
            margen_usd=round(acum["margen"], 2),
            precio_con_margen=round(acum["con_margen"], 2),
        ))
        res.costo_neto_total += acum["neto"]
        res.subtotal_con_margen += acum["con_margen"]

    res.contingencia_usd = res.subtotal_con_margen * CONTINGENCIA
    res.costo_financiero_usd = (res.subtotal_con_margen + res.contingencia_usd) * COSTO_FINANCIERO
    res.neto_cliente = res.subtotal_con_margen + res.contingencia_usd + res.costo_financiero_usd

    # IVA: aplicar prorrateado por línea según precio_con_margen + share de
    # contingencia y financiero
    factor_overhead = (res.neto_cliente / res.subtotal_con_margen) if res.subtotal_con_margen else 1.0
    iva_total = 0.0
    for linea in res.lineas:
        base_iva = linea.precio_con_margen * factor_overhead
        linea.iva_usd = round(base_iva * linea.iva_pct, 2)
        linea.precio_final = round(base_iva + linea.iva_usd, 2)
        iva_total += linea.iva_usd

    res.iva_total = round(iva_total, 2)
    res.total_cliente = round(res.neto_cliente + res.iva_total, 2)

    # Redondeos finales
    res.costo_neto_total = round(res.costo_neto_total, 2)
    res.subtotal_con_margen = round(res.subtotal_con_margen, 2)
    res.contingencia_usd = round(res.contingencia_usd, 2)
    res.costo_financiero_usd = round(res.costo_financiero_usd, 2)
    res.neto_cliente = round(res.neto_cliente, 2)

    return res
