"""Parser PAMPA — Pampa Energía S.A., Mercado a Término (Grandes Usuarios).

OJO: Pampa Energía NO es una distribuidora, es generador/comercializador en
el Mercado a Término (MATE). Esta factura representa la energía contratada
del Gran Usuario; para sizing solar conviene combinarla con la factura de
distribución local (EPEC en Córdoba, EDENOR en Bs As, etc.) y eventualmente
con CAMMESA, usando `merge_facturas()`.

Calibrado contra factura 1593-A00144687 (MOLINOS MARIMBO SAIC, La Carlota,
Córdoba, feb-2026). pdftotext -layout produce un layout con espacios anchos.
"""
from __future__ import annotations

import re
from typing import Optional

from ..modelo import ConsumoMensual, Factura
from ..registry import register
from ..util import parse_num_ar


@register("PAMPA", [
    r"Pampa\s+Energ[ií]a\s+S\.?A\.?",
    r"30-?52655265-?9",                       # CUIT Pampa Energía S.A.
    r"Central\s+T?\s*Loma\s+de\s+la\s+Lata",  # planta generadora
])
def parse(texto: str) -> Optional[Factura]:
    # Código de cliente Pampa: "CLIENTE   (10191)"
    nis_match = re.search(r"CLIENTE\s*\(\s*(\d+)\s*\)", texto)

    # Titular: línea siguiente a "CLIENTE (...)" (la línea CLIENTE tiene CUIT
    # del cliente al final; la razón social viene en el renglón siguiente).
    titular = ""
    tit_m = re.search(
        r"CLIENTE\s*\(\d+\)[^\n]*\n\s*([A-ZÁÉÍÓÚÑ][A-Z0-9ÁÉÍÓÚÑ\. &]+)",
        texto,
    )
    if tit_m:
        titular = tit_m.group(1).strip()

    # Período: "Suministro de EE del 1 al 28/02/2026"
    per_m = re.search(
        r"Suministro\s+de\s+EE\s+del\s+\d{1,2}\s+al\s+\d{1,2}/(\d{2})/(\d{4})",
        texto, re.IGNORECASE,
    )

    # Cantidad facturada: línea típica con MWH/kWh + Cantidad + Precio Unit + Total.
    # "...Fondo Nacional de EE.    MWH    443,520    2.029,00    899.902,08"
    cant_m = re.search(
        r"\b(MWh|MWH|kWh|KWH)\b\s+([\d.,]+)\s+[\d.,]+\s+[\d.,]+",
        texto,
    )

    consumos: list[ConsumoMensual] = []
    if per_m and cant_m:
        mm, yyyy = per_m.group(1), per_m.group(2)
        unit = cant_m.group(1).upper()
        try:
            cantidad = parse_num_ar(cant_m.group(2))
        except ValueError:
            cantidad = None
        if cantidad is not None:
            kwh = cantidad * 1000 if unit == "MWH" else cantidad
            consumos.append(ConsumoMensual(mes=f"{yyyy}-{mm}", kwh_total=kwh))

    # Dirección: "ARRASCAETA 88\n LA CARLOTA\n 2670 JUAREZ CELMAN Córdoba"
    dir_m = re.search(
        r"CLIENTE\s*\(\d+\)[\s\S]{0,400}?Ingresos\s+Brutos:[^\n]*\n\s*([^\n]+)\n\s*([^\n]+)",
        texto,
    )
    direccion = ""
    if dir_m:
        direccion = f"{dir_m.group(1).strip()}, {dir_m.group(2).strip()}"

    if not nis_match and not consumos:
        return None

    return Factura(
        distribuidora="PAMPA",
        categoria_tarifaria="MATE",                # Mercado a Término
        titular=titular,
        nis=nis_match.group(1) if nis_match else "",
        direccion=direccion,
        tension_suministro="MT",                   # GUs típicamente MT/AT
        potencia_contratada_kw=None,
        consumos=consumos,
        fuente="parser:PAMPA",
    )
