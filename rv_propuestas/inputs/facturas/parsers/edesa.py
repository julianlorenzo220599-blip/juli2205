"""Parser EDESA (Salta) — factura mensual T1/T2/T3.

Calibrado contra facturas 0100-06315088 / 0100-06315100 (T1-R2-N1, La Caldera).
Extrae el período facturado + consumo activo. Si el cliente manda varias
facturas mensuales del mismo NIS, combinarlas con `merge_facturas()`.
"""
from __future__ import annotations

import re
from typing import Optional

from ..modelo import ConsumoMensual, Factura
from ..registry import register
from ..util import parse_num_ar


@register("EDESA", [
    r"\bEDESA\s+SA\b",
    r"\bEdesa\s*S\.?A\.?\b",
    r"Empresa\s+Distribuidora\s+(?:de\s+)?Salta",
    r"edesa\.com\.ar",
])
def parse(texto: str) -> Optional[Factura]:
    nis_match = re.search(
        r"Identificaci[oó]n\s*:?\s*(\d{6,10})", texto, re.IGNORECASE
    )

    cat_match = re.search(
        r"Tarifa\s*:\s*(T\d[\-A-Z0-9]*)", texto, re.IGNORECASE
    )
    pot_match = re.search(
        r"Pot\.\s*Cont\.?\s*\(?kW\)?\s*:?\s*([\d.,]+)", texto, re.IGNORECASE
    )

    periodo = _extraer_periodo(texto)

    consumo: Optional[float] = None
    m_act = re.search(
        r"Activa\s+\d+\s+\d+\s+[\d.,]+\s+([\d.,]+)", texto, re.IGNORECASE
    )
    if m_act:
        try:
            consumo = parse_num_ar(m_act.group(1))
        except ValueError:
            consumo = None

    consumos: list[ConsumoMensual] = []
    if periodo and consumo is not None:
        consumos.append(ConsumoMensual(mes=periodo, kwh_total=consumo))

    if not nis_match and not consumos:
        return None

    return Factura(
        distribuidora="EDESA",
        categoria_tarifaria=cat_match.group(1) if cat_match else "T?",
        titular="",
        nis=nis_match.group(1) if nis_match else "",
        direccion="",
        tension_suministro="BT 380V",
        potencia_contratada_kw=parse_num_ar(pot_match.group(1)) if pot_match else None,
        consumos=consumos,
        fuente="parser:EDESA",
    )


def _extraer_periodo(texto: str) -> Optional[str]:
    """Devuelve YYYY-MM del período facturado (no de la emisión)."""
    m = re.search(
        r"Per[ií]odo\s+de\s+Facturaci[oó]n[\s\S]{0,40}?(\d{2})/(\d{4})",
        texto, re.IGNORECASE,
    )
    if not m:
        return None
    return f"{m.group(2)}-{m.group(1)}"
