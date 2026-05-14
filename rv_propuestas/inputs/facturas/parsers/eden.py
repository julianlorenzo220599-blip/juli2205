"""Parser EDEN (Empresa Distribuidora de Energía Norte SA, Pcia. Bs As).

Cubre Junín, San Nicolás y resto del territorio EDEN. Factura mensual con un
único período facturado y cuadro de barras histórico (no parseable de texto).

OJO: el nombre legal "Empresa Distribuidora de Energía Norte" se parece a
EDENOR pero son distintas empresas. La detección distingue por el dominio
edensa.com.ar y por la palabra "Energía" intercalada (EDENOR es
"Distribuidora y Comercializadora Norte", sin "Energía").
"""
from __future__ import annotations

import re
from typing import Optional

from ..modelo import ConsumoMensual, Factura
from ..registry import register
from ..util import parse_num_ar


@register("EDEN", [
    r"edensa\.com\.ar",
    r"EMPRESA\s+DISTRIBUIDORA\s+DE\s+ENERG[IÍ]A\s+NORTE",
    r"\bEDEN\s+S\.?A\.?\b",
])
def parse(texto: str) -> Optional[Factura]:
    # NIS: aparece como "NIS\n0-1323067 - 01" (con guiones y prefijo "0-").
    nis_match = re.search(
        r"NIS[\s\S]{0,30}?0?\s*-?\s*(\d{6,8})\s*-\s*\d{1,3}",
        texto, re.IGNORECASE,
    )

    cat_match = re.search(
        r"Tipo\s+de\s+tarifa\s+o\s+categor[ií]a\s*:?\s*(T\d[A-Z0-9]*)",
        texto, re.IGNORECASE,
    )

    periodo = _extraer_periodo_yyyymm(texto)

    consumo = _extraer_consumo(texto)

    consumos: list[ConsumoMensual] = []
    if periodo and consumo is not None:
        consumos.append(ConsumoMensual(mes=periodo, kwh_total=consumo))

    if not nis_match and not consumos:
        return None

    return Factura(
        distribuidora="EDEN",
        categoria_tarifaria=cat_match.group(1) if cat_match else "T?",
        titular="",
        nis=nis_match.group(1) if nis_match else "",
        direccion="",
        tension_suministro="BT 380V",
        potencia_contratada_kw=None,
        consumos=consumos,
        fuente="parser:EDEN",
    )


def _extraer_periodo_yyyymm(texto: str) -> Optional[str]:
    """EDEN imprime el período como YYYYMM concatenado (ej: '202512')."""
    m = re.search(
        r"Per[ií]odo\s+de\s+Facturaci[oó]n[\s\S]{0,40}?(\d{6})\b",
        texto, re.IGNORECASE,
    )
    if not m:
        return None
    s = m.group(1)
    return f"{s[:4]}-{s[4:]}"


def _extraer_consumo(texto: str) -> Optional[float]:
    """Línea típica: '704009 EA 64006 64180 1.000 174 R' — el penúltimo nº es kWh."""
    for m in re.finditer(
        r"(?:\bEA\b|Energ[ií]a\s+Activa)\s+\d+\s+\d+\s+[\d.,]+\s+([\d.,]+)\s*(?:R\b|kWh)?",
        texto, re.IGNORECASE,
    ):
        try:
            return parse_num_ar(m.group(1))
        except ValueError:
            continue
    return None
