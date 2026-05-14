"""Helpers numéricos compartidos entre parsers."""
from __future__ import annotations


def parse_num_ar(s: str) -> float:
    """Parsea número en formato AR: '1.234.567,89' → 1234567.89.

    Convenciones:
      - Coma decimal → '1.080,50' = 1080.50
      - Punto único como separador de miles → '1.080' = 1080
      - Múltiples puntos → todos miles
      - Sin coma ni punto → directo
    """
    s = s.strip()
    if not s:
        raise ValueError("cadena vacía")
    if "," in s:
        return float(s.replace(".", "").replace(",", "."))
    if s.count(".") == 1 and len(s.split(".")[1]) == 3:
        return float(s.replace(".", ""))
    if s.count(".") >= 2:
        return float(s.replace(".", ""))
    return float(s)
