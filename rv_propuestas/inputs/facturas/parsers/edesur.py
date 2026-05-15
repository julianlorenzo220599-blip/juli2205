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
    r"\bEdesur\b",                # también en mayúsc/minúsc del cuerpo legal
])
def parse(texto: str) -> Optional[Factura]:
    # NIS: T3 grandes clientes ("Su número de cliente es 80515768") o
    # residencial ("Cliente: 04538667").
    nis_match = re.search(
        r"(?:n[uú]mero\s+de\s+cliente\s+es|Nro\s+de\s+cliente\s+T?\d?[A-Z]*)\s+(\d{6,10})",
        texto, re.IGNORECASE,
    )
    if not nis_match:
        nis_match = re.search(r"Cliente:\s*(\d{4,10})", texto, re.IGNORECASE)

    # Tarifa: T3 MT / T3 BT / T2 / T1-R / T1 R Residencial
    cat_match = re.search(
        r"Tarifa\s+(T\d(?:[\s\-]+R\d?)?(?:\s*(?:MT|BT|AT|MD))?)",
        texto, re.IGNORECASE,
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
    elif re.search(r"T1\s*R|Residencial", texto, re.IGNORECASE):
        tension = "BT 220V"

    # Potencia convenida (T3 grandes clientes). Residencial T1 no la declara.
    pot_match = re.search(
        r"Convenida\s+([\d.,]+)", texto, re.IGNORECASE,
    )
    potencia = parse_num_ar(pot_match.group(1)) if pot_match else None

    # Primero intentamos la tabla histórica T3 (6 meses); si no hay, caemos
    # al single-month residencial.
    consumos = _parse_tabla_meses(texto)
    if not consumos:
        consumos = _parse_residencial(texto)

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


def _parse_residencial(texto: str) -> list[ConsumoMensual]:
    """T1 residencial: 1 mes facturado a partir del 'Estado actual al DD/MM/YYYY'
    + 'Energía Consumida XXX kWh'.

    OJO: pdftotext glúa palabras en este layout ('Estadoactual', 'actualalal'),
    por eso el regex es lenient: buscamos la primera fecha cercana a 'actual'.
    """
    # Primer intento: con separación normal. Fallback: lenient (cualquier fecha
    # cercana a 'actual'). El regex lenient captura 3 grupos (DD, MM, YYYY).
    periodo_m = re.search(
        r"Estado\s*actual\s*al?\s*\d{1,2}/(\d{2})/(\d{4})",
        texto, re.IGNORECASE,
    )
    if periodo_m:
        mm, yyyy = periodo_m.group(1), periodo_m.group(2)
    else:
        lenient = re.search(
            r"actual[\s\S]{0,80}?\d{1,2}/(\d{2})/(\d{4})",
            texto, re.IGNORECASE,
        )
        if not lenient:
            return []
        mm, yyyy = lenient.group(1), lenient.group(2)
    # pdftotext desarma la columna "Energía Consumida XXX kWh" en líneas raras;
    # mejor usar la nota descriptiva "equivalente a XXX kWh en YY días".
    consumo_m = re.search(
        r"equivalente\s+a\s+([\d.,]+)\s*kWh\s+en\s+\d+", texto, re.IGNORECASE
    )
    if not consumo_m:
        consumo_m = re.search(
            r"Energ[ií]a\s+Consumida\s+([\d.,]+)\s*kWh", texto, re.IGNORECASE
        )
    if not consumo_m:
        return []
    try:
        kwh = parse_num_ar(consumo_m.group(1))
    except ValueError:
        return []
    return [ConsumoMensual(mes=f"{yyyy}-{mm}", kwh_total=kwh)]


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
