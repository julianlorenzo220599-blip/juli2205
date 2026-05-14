"""Fallback CSV editable cuando no hay parser ni API key disponibles.

Flujo:
  1. `crear_plantilla_csv("kwh.csv")` genera 12 filas con los últimos meses.
  2. El usuario completa la columna kwh_total a mano.
  3. `leer_csv("kwh.csv")` construye una Factura.
"""
from __future__ import annotations

import csv
import datetime
from pathlib import Path
from typing import Optional

from .modelo import ConsumoMensual, Factura


def crear_plantilla_csv(path: Path, meses: int = 12) -> None:
    """Crea un CSV con encabezado y `meses` filas para completar."""
    today = datetime.date.today()
    rows: list[list[str]] = []
    # Mes "actual - meses" hasta "actual - 1", en orden cronológico.
    for offset in range(meses, 0, -1):
        total = today.year * 12 + (today.month - 1) - offset
        y, m = divmod(total, 12)
        rows.append([f"{y:04d}-{m + 1:02d}", ""])
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["mes", "kwh_total"])
        w.writerows(rows)


def leer_csv(
    path: Path,
    distribuidora: str = "MANUAL",
    categoria_tarifaria: str = "T?",
    titular: str = "",
    nis: str = "",
    direccion: str = "",
    tension_suministro: str = "BT 380V",
    potencia_contratada_kw: Optional[float] = None,
) -> Factura:
    consumos: list[ConsumoMensual] = []
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            val = (row.get("kwh_total") or "").strip()
            if not val:
                continue
            consumos.append(ConsumoMensual(
                mes=row["mes"].strip(),
                kwh_total=float(val.replace(".", "").replace(",", ".")) if "," in val else float(val),
            ))
    return Factura(
        distribuidora=distribuidora,
        categoria_tarifaria=categoria_tarifaria,
        titular=titular,
        nis=nis,
        direccion=direccion,
        tension_suministro=tension_suministro,
        potencia_contratada_kw=potencia_contratada_kw,
        consumos=consumos,
        fuente="manual:csv",
    )
