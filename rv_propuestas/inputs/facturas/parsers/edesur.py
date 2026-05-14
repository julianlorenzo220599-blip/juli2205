"""Parser EDESUR — grandes clientes T3 con tabla histórica de 6 meses.

Calibrado contra factura LSP A 9904-... (T3 MT, demanda convenida 50 kW).
Extrae: NIS (Nro de cliente), tarifa, tensión, potencia convenida, hasta
12 meses de energía total + demanda pico (DRP).
"""
from __future__ import annotations

import re
from typing import Optional

from ..modelo import ConsumoMensual, Factura
from ..registry import register
from ..util import parse_num_ar


@register("EDESUR", [
    r"\bEDESUR\b",
    r"Empresa\s+Distribuidora\s+Sur\s+S\.?A\.?",
    r"edesur\.com\.ar",
])
def parse(texto: str) -> Optional[Factura]:
    nis_match = re.search(
        r"(?:n[uú]mero\s+de\s+cliente\s+es|Nro\s+de\s+cliente\s+T?\d?[A-Z]*)\s+(\d{6,10})",
        texto, re.IGNORECASE,
    )

    cat_match = re.search(
        r"Tarifa\s+(T\d(?:\s*(?:MT|BT|AT|MD))?)", texto, re.IGNORECASE,
    )
    categoria = (
        cat_match.group(1).strip().replace(" ", "-").upper()
        if cat_match else "T?"
    )

    tension = "BT 380V"
    if re.search(r"T3\s*MT|\bMT\b\s*cliente", texto, re.IGNORECASE):
        tension = "MT 13.2 kV"
    elif re.search(r"T3\s*AT", texto, re.IGNORECASE):
        tension = "AT 33 kV"

    # Potencia convenida (CSC). En T3 también aparece "Adquirida" (CSR).
    pot_match = re.search(
        r"Convenida\s+([\d.,]+)", texto, re.IGNORECASE,
    )
    potencia = parse_num_ar(pot_match.group(1)) if pot_match else None

    consumos = _parse_tabla_meses(texto)

    if not consumos and not nis_match:
        return None

    return Factura(
        distribuidora="EDESUR",
        categoria_tarifaria=categoria,
        titular="",
        nis=nis_match.group(1) if nis_match else "",
        direccion="",
        tension_suministro=tension,
        potencia_contratada_kw=potencia,
        consumos=consumos,
        fuente="parser:EDESUR",
    )


def _parse_tabla_meses(texto: str) -> list[ConsumoMensual]:
    """Detecta el bloque tabular típico:

        Mes    03-25 04-25 05-25 06-25 07-25 08-25
        DRP    134   137   154   175   186   158
        DRFP   206   218   199   210   224   226
        E. Tot 59760 70800 67200 73920 87720 88920
    """
    meses_m = re.search(r"\bMes\b\s*((?:\d{2}-\d{2}\s*){2,12})", texto)
    if not meses_m:
        return []
    mes_tokens = re.findall(r"(\d{2})-(\d{2})", meses_m.group(1))
    if not mes_tokens:
        return []

    etot_m = re.search(r"E\.\s*Tot\s*((?:[\d.,]+\s*){2,12})", texto)
    if not etot_m:
        return []
    valores = re.findall(r"[\d.,]+", etot_m.group(1))[: len(mes_tokens)]

    drp_m = re.search(r"\bDRP\b\s*((?:[\d.,]+\s*){2,12})", texto)
    drps = (
        re.findall(r"[\d.,]+", drp_m.group(1))[: len(mes_tokens)] if drp_m else []
    )

    consumos: list[ConsumoMensual] = []
    for i, ((mm, yy), kwh_s) in enumerate(zip(mes_tokens, valores)):
        try:
            kwh = parse_num_ar(kwh_s)
        except ValueError:
            continue
        pico = None
        if i < len(drps):
            try:
                pico = parse_num_ar(drps[i])
            except ValueError:
                pico = None
        consumos.append(ConsumoMensual(
            mes=f"20{yy}-{mm}",
            kwh_total=kwh,
            potencia_pico_kw=pico,
        ))
    return consumos
