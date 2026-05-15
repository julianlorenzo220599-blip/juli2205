"""Parser ENERSA (Energía de Entre Ríos S.A.).

Calibrado contra factura real LSP A-17 N° 8811241 (FRIGORIFICO ARGENTINA
ALIMENTOS, Tarifa 3 GD BT, diciembre 2025). Cubre Gran Usuario en BT/MT
con tabla histórica de 13 meses + potencias punta y fuera-punta.
"""
from __future__ import annotations

import re
from typing import Optional

from ..modelo import ConsumoMensual, Factura
from ..registry import register
from ..util import parse_num_ar


@register("ENERSA", [
    r"\bENERSA\b",
    r"enersa\.com\.ar",
    r"enersagrandesclientes",
    r"Energ[ií]a\s+de\s+Entre\s+R[ií]os",
])
def parse(texto: str) -> Optional[Factura]:
    nis_m = re.search(r"N[°º]\s+de\s+ID:?\s+(\d{6,12})", texto, re.IGNORECASE)

    # Titular: línea después de "TITULAR:"
    tit_m = re.search(
        r"TITULAR:?\s+([A-ZÁÉÍÓÚÑ][A-Z0-9ÁÉÍÓÚÑ\.,\s&]+?)(?:\n|CUIT)",
        texto, re.IGNORECASE,
    )
    titular = tit_m.group(1).strip().rstrip(",") if tit_m else ""

    # Tarifa: "Tarifa 3 - G.D. Vinc. Inf. BT"
    cat_m = re.search(
        r"Tarifa\s+(\d+)\s*[-–]?\s*([A-Z][A-Z\.\s]*?(?:BT|MT|AT)?)",
        texto,
    )
    categoria = "T?"
    if cat_m:
        num = cat_m.group(1)
        sufijo = (cat_m.group(2) or "").strip()
        categoria = f"T{num}" + (f"-{sufijo.split()[-1]}" if sufijo else "")

    # Tensión: detecta BT/MT/AT explícitos
    tension = "BT 380V"
    if re.search(r"\bBT\b", texto):
        tension = "BT 380V"
    if re.search(r"\bMT\b\s+(?:industrial|grande|tarifa)", texto, re.IGNORECASE):
        tension = "MT 13.2 kV"

    # Tabla histórica:
    #   Período  Csmo(kWh)  Pot.Punta(kW)  Pot.FueraPunta(kW)
    #   12/24    700        11             98
    #   01/25    2.000      11             38
    consumos = _parse_tabla_mensual(texto)

    if not nis_m and not consumos:
        return None

    pot_max = max(
        (c.potencia_pico_kw for c in consumos if c.potencia_pico_kw is not None),
        default=None,
    )

    return Factura(
        distribuidora="ENERSA",
        categoria_tarifaria=categoria,
        titular=titular,
        nis=nis_m.group(1) if nis_m else "",
        direccion="",
        tension_suministro=tension,
        potencia_contratada_kw=pot_max,
        consumos=consumos,
        fuente="parser:ENERSA",
    )


def _parse_tabla_mensual(texto: str) -> list[ConsumoMensual]:
    """Lee filas tipo 'MM/YY  KWH  POT_PUNTA  POT_FUERA' o 'MM/YY  KWH'."""
    consumos: list[ConsumoMensual] = []
    visto: set[str] = set()
    # Sin anchor `$`: algunas filas tienen contenido extra al final ("Total
    # Factura ..." en la misma fila por layout multi-columna del PDF).
    for m in re.finditer(
        r"^\s*(\d{2})/(\d{2})\s+([\d.,]+)(?:\s+([\d.,]+)\s+([\d.,]+))?",
        texto, re.MULTILINE,
    ):
        mm, yy = m.group(1), m.group(2)
        mes = f"20{yy}-{mm}"
        if mes in visto:
            continue
        try:
            kwh = parse_num_ar(m.group(3))
        except ValueError:
            continue
        if kwh <= 0:
            continue
        pot_pico = None
        if m.group(4) and m.group(5):
            try:
                pot_punta = parse_num_ar(m.group(4))
                pot_fuera = parse_num_ar(m.group(5))
                pot_pico = max(pot_punta, pot_fuera)
            except ValueError:
                pot_pico = None
        consumos.append(ConsumoMensual(
            mes=mes, kwh_total=kwh, potencia_pico_kw=pot_pico,
        ))
        visto.add(mes)
    return consumos
