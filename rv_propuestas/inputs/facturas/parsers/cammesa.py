"""Parser CAMMESA — Mercado Eléctrico Mayorista (Grandes Usuarios).

STUB inicial — calibrar contra PDF real cuando llegue. Patrones inferidos de
factura escaneada A-0057-00373700 (MOLINOS MARIMBO SAIC, suministro 23808
MOMALCXN, período 01/02/2026 al 28/02/2026).

OJO: CAMMESA factura cargos de potencia + comercialización, NO kWh. Para
sizing solar combinar con la factura de distribución local (EPEC, EDESUR,
etc.) usando `merge_facturas()`. Esta factura aporta la potencia contratada
y el período de referencia.
"""
from __future__ import annotations

import re
from typing import Optional

from ..modelo import ConsumoMensual, Factura
from ..registry import register
from ..util import parse_num_ar


@register("CAMMESA", [
    r"\bCAMMESA\b",
    r"30-?65537309-?4",   # CUIT CAMMESA
    r"Mercado\s+El[eé]ctrico\s+Mayorista",
])
def parse(texto: str) -> Optional[Factura]:
    # N° Suministro: "23808 MOMALCXN" o "N° de Suministro 23808"
    sum_match = re.search(
        r"(?:N[°º]\s+de\s+)?Suministro:?\s*(\d{4,8})",
        texto, re.IGNORECASE,
    )

    # Período Facturado: "01/02/2026 al 28/02/2026" — usar el mes del rango
    per_match = re.search(
        r"Per[ií]odo\s+Facturado:?\s*\d{1,2}/(\d{2})/(\d{4})",
        texto, re.IGNORECASE,
    )

    # Cargos de Potencia: "101.800 MW Cargos de Potencia"
    pot_match = re.search(
        r"([\d.,]+)\s*MW\s+Cargos?\s+de\s+Potencia",
        texto, re.IGNORECASE,
    )

    titular_match = re.search(
        r"Se[ñn]or\(?es\)?\s*:?\s*\n?\s*([A-ZÁÉÍÓÚÑ][A-Z0-9ÁÉÍÓÚÑ\. &]+)",
        texto,
    )

    pot_kw: Optional[float] = None
    if pot_match:
        try:
            pot_mw = parse_num_ar(pot_match.group(1))
            pot_kw = pot_mw * 1000   # MW → kW
        except ValueError:
            pot_kw = None

    # CAMMESA no detalla kWh, pero emitimos un registro de período con
    # potencia para que merge_facturas() lo consolide con otras facturas.
    consumos: list[ConsumoMensual] = []
    if per_match and pot_kw is not None:
        consumos.append(ConsumoMensual(
            mes=f"{per_match.group(2)}-{per_match.group(1)}",
            kwh_total=0.0,            # CAMMESA no factura kWh aquí
            potencia_pico_kw=pot_kw,
        ))

    if not sum_match and not consumos:
        return None

    return Factura(
        distribuidora="CAMMESA",
        categoria_tarifaria="GU-MEM",        # Gran Usuario MEM
        titular=titular_match.group(1).strip() if titular_match else "",
        nis=sum_match.group(1) if sum_match else "",
        direccion="",
        tension_suministro="MT/AT",
        potencia_contratada_kw=pot_kw,
        consumos=consumos,
        fuente="parser:CAMMESA",
    )
