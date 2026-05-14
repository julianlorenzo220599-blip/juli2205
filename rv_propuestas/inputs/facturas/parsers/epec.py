"""Parser EPEC (Empresa Provincial de Energía de Córdoba).

STUB inicial — calibrar contra PDF real cuando llegue. Patrones inferidos de
factura escaneada del cliente MOLINOS MARIMBO SAIC (Liq. Serv. Pub. A(17)
N° 00026-01266330, Media Tensión, período 03/2026).

Extrae: Cliente N°, Contrato, tensión, período, energía pico/valle/resto +
demanda contratada DP/DF.
"""
from __future__ import annotations

import re
from typing import Optional

from ..modelo import ConsumoMensual, Factura
from ..registry import register
from ..util import parse_num_ar


@register("EPEC", [
    r"\bEPEC\b",
    r"Empresa\s+Provincial\s+de\s+Energ[ií]a.*C[oó]rdoba",
    r"ERSeP",                          # ente regulador provincial
])
def parse(texto: str) -> Optional[Factura]:
    nis_match = re.search(
        r"CLIENTE\s*N[°º]\s*(\d{6,10})", texto, re.IGNORECASE,
    )
    contrato_match = re.search(
        r"CONTRATO\s*N[°º]\s*(\d{6,10}\s*[/\-]?\s*\d*)",
        texto, re.IGNORECASE,
    )

    # Período: "PERIODO LEIDO 28/02/2026 al 31/03/2026" o el label "03/2026"
    per_match = re.search(
        r"PERIODO\s+LEIDO[\s\S]{0,80}?al\s+\d{1,2}/(\d{2})/(\d{4})",
        texto, re.IGNORECASE,
    )
    if not per_match:
        per_match = re.search(
            r"Per[ií]odo\s+Facturado[\s\S]{0,40}?(\d{2})/(\d{4})\b",
            texto, re.IGNORECASE,
        )

    tension = "BT 380V"
    if re.search(r"Media\s+Tensi[oó]n", texto, re.IGNORECASE):
        tension = "MT 13.2 kV"
    elif re.search(r"Alta\s+Tensi[oó]n", texto, re.IGNORECASE):
        tension = "AT 33 kV"

    pico_m = re.search(
        r"Peaje\s+en\s+H\.\s*Pico\s+([\d.,]+)", texto, re.IGNORECASE,
    )
    valle_m = re.search(
        r"Peaje\s+en\s+H\.\s*Valle\s+([\d.,]+)", texto, re.IGNORECASE,
    )
    resto_m = re.search(
        r"Peaje\s+en\s+H\.\s*Resto\s+([\d.,]+)", texto, re.IGNORECASE,
    )
    dp_m = re.search(
        r"Cargo\s+Cap\.\s*Trans\.\s*DP\s+([\d.,]+)", texto, re.IGNORECASE,
    )

    pico = _safe_num(pico_m.group(1)) if pico_m else None
    valle = _safe_num(valle_m.group(1)) if valle_m else None
    resto = _safe_num(resto_m.group(1)) if resto_m else None
    pot_pico = _safe_num(dp_m.group(1)) if dp_m else None

    consumos: list[ConsumoMensual] = []
    if per_match:
        kwh_total = sum(v for v in (pico, valle, resto) if v is not None)
        if kwh_total > 0:
            consumos.append(ConsumoMensual(
                mes=f"{per_match.group(2)}-{per_match.group(1)}",
                kwh_total=kwh_total,
                kwh_pico=pico,
                kwh_valle=valle,
                kwh_resto=resto,
                potencia_pico_kw=pot_pico,
            ))

    if not nis_match and not consumos:
        return None

    categoria = "T3-MT" if "MT" in tension else "T3-BT" if "BT" in tension else "T?"

    return Factura(
        distribuidora="EPEC",
        categoria_tarifaria=categoria,
        titular="",
        nis=nis_match.group(1) if nis_match else "",
        direccion="",
        tension_suministro=tension,
        potencia_contratada_kw=pot_pico,
        consumos=consumos,
        fuente="parser:EPEC",
    )


def _safe_num(s: str) -> Optional[float]:
    try:
        return parse_num_ar(s)
    except ValueError:
        return None
