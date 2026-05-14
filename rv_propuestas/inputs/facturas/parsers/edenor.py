"""Parser EDENOR — esqueleto basado en patrones genéricos T1/T3 BT.

Validar contra facturas reales cuando se reciban. Por ahora cubre los campos
mínimos para que el sizing arranque; cae a LLM si no logra extraer kWh.
"""
from __future__ import annotations

import re
from typing import Optional

from ..modelo import ConsumoMensual, Factura
from ..registry import register
from ..util import parse_num_ar


@register("EDENOR", [
    r"\bEDENOR\b",
    r"Empresa\s+Distribuidora\s+y\s+Comercializadora\s+Norte",
])
def parse(texto: str) -> Optional[Factura]:
    nis_match = re.search(r"NIS\s*[:\-]?\s*(\d{6,10})", texto, re.IGNORECASE)
    cat_match = re.search(r"Tarifa[:\s]+(T[1-3][A-Z0-9\-]*)", texto, re.IGNORECASE)
    pot_match = re.search(
        r"Potencia\s+Contratada[:\s]+([\d.,]+)\s*kW", texto, re.IGNORECASE
    )

    consumos: list[ConsumoMensual] = []
    for m in re.finditer(
        r"(\d{2})/(\d{4})\s+(?:.*?)\s+([\d.,]+)\s*kWh",
        texto,
    ):
        mm, yyyy, kwh_s = m.group(1), m.group(2), m.group(3)
        try:
            kwh = parse_num_ar(kwh_s)
        except ValueError:
            continue
        consumos.append(ConsumoMensual(mes=f"{yyyy}-{mm}", kwh_total=kwh))

    if not nis_match and not consumos:
        return None

    return Factura(
        distribuidora="EDENOR",
        categoria_tarifaria=cat_match.group(1) if cat_match else "T?",
        titular="",
        nis=nis_match.group(1) if nis_match else "",
        direccion="",
        tension_suministro="BT 380V",
        potencia_contratada_kw=(
            parse_num_ar(pot_match.group(1)) if pot_match else None
        ),
        consumos=consumos,
        fuente="parser:EDENOR",
    )
