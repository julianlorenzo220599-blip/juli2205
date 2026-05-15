"""Parser EDENOR (Empresa Distribuidora y Comercializadora Norte).

Calibrado contra factura real LSP B 0027-32228380 (Cuenta 4 682 960 084,
T1-R1 residencial, mayo 2026). La cuenta de EDENOR viene formateada con
espacios cada 3 dígitos ("4 682 960 084"); el parser los strippea para
producir un NIS canónico.
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
    r"edenor(?:digital)?\.com",
])
def parse(texto: str) -> Optional[Factura]:
    # Cuenta: "Cuenta 4 682 960 084" (espacios cada 3 dígitos). También acepta
    # variantes T3 sin espacios.
    nis = ""
    m = re.search(r"Cuenta\s+(\d[\d\s]{6,15}\d)", texto)
    if m:
        nis = re.sub(r"\s", "", m.group(1))
    else:
        m_nis = re.search(r"\bNIS\s*[:\-]?\s*(\d{6,10})", texto)
        if m_nis:
            nis = m_nis.group(1)

    # Titular: pdftotext lineariza columnas y mete "TOTAL A PAGAR $..." entre
    # "Cuenta" y el nombre. Buscamos forward la primera línea que parezca
    # un nombre (todo mayúsculas, ≥2 palabras, sin $ ni keywords contables).
    titular = ""
    skip = ("$", "TOTAL", "VENCIMIENTO", "VTO", "S.E.", "Vencimiento", "EDENOR")
    m_cuenta = re.search(r"Cuenta\s+\d[\d\s]+\d", texto)
    if m_cuenta:
        for linea in texto[m_cuenta.end():m_cuenta.end() + 800].splitlines():
            ln = linea.strip()
            if not ln or any(kw in ln for kw in skip):
                continue
            if re.match(r"^[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s\.]{4,60}$", ln):
                titular = ln
                break

    # Tarifa: "TARIFA: T1-R1"  o  "Tarifa T3-BT"
    cat_m = re.search(r"TARIFA\s*:?\s*(T\d[\-A-Z0-9]*)", texto, re.IGNORECASE)
    categoria = cat_m.group(1) if cat_m else "T?"

    # Potencia contratada (T3): "Potencia Contratada: 150 kW"
    pot_m = re.search(
        r"Potencia\s+Contratada[:\s]+([\d.,]+)\s*kW", texto, re.IGNORECASE
    )
    potencia = parse_num_ar(pot_m.group(1)) if pot_m else None

    # Consumo y período mensual
    consumos: list[ConsumoMensual] = []
    consumo_m = re.search(
        r"Total\s+Consumo\s+([\d.,]+)\s*kWh\s+en\s+\d+", texto, re.IGNORECASE,
    )
    periodo_m = re.search(
        r"Per[ií]odo\s+de\s+consumo:?\s*\d{1,2}/\d{2}/\d{4}\s+AL?\s+"
        r"(\d{1,2})/(\d{2})/(\d{4})",
        texto, re.IGNORECASE,
    )
    if consumo_m and periodo_m:
        try:
            kwh = parse_num_ar(consumo_m.group(1))
        except ValueError:
            kwh = None
        if kwh is not None:
            consumos.append(ConsumoMensual(
                mes=f"{periodo_m.group(3)}-{periodo_m.group(2)}",
                kwh_total=kwh,
            ))

    if not nis and not consumos:
        return None

    # Tensión: T1 residencial es 220 V monofásico (CABA), T3 industrial es BT/MT.
    tension = "BT 220V" if categoria.startswith("T1") else "BT 380V"

    return Factura(
        distribuidora="EDENOR",
        categoria_tarifaria=categoria,
        titular=titular,
        nis=nis,
        direccion="",
        tension_suministro=tension,
        potencia_contratada_kw=potencia,
        consumos=consumos,
        fuente="parser:EDENOR",
    )
