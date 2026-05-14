"""Punto De Interconexión (PDI) — normalización de datos eléctricos del PDI.

El PDI define la frontera técnica entre la planta y la red. Sus parámetros
gobiernan: topología, BOM eléctrico, costos de obra y trámite ante la
distribuidora.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class PDI:
    """Datos relevantes del Punto De Interconexión."""

    tension_kv: float                       # 0.38 (BT) | 13.2 | 33
    fases: int                              # 1 | 3
    capacidad_disponible_kw: Optional[float] = None  # Límite de inyección autorizado
    distancia_al_tablero_m: float = 10.0    # Distancia desde inversores al PDI
    requiere_trafo_elevador: bool = False
    distribuidora: str = ""
    categoria_tarifaria: str = ""
    notas: str = ""

    @property
    def es_baja_tension(self) -> bool:
        return self.tension_kv <= 1.0

    @property
    def es_media_tension(self) -> bool:
        return 1.0 < self.tension_kv <= 36.0

    @property
    def descripcion(self) -> str:
        if self.es_baja_tension:
            return f"BT {int(self.tension_kv * 1000)}V {self.fases}F"
        return f"MT {self.tension_kv:.1f} kV"

    def kwp_maximo_por_pdi(self, ratio_dc_ac: float = 1.20) -> Optional[float]:
        """kWp máximo instalable limitado por la capacidad del PDI."""
        if self.capacidad_disponible_kw is None:
            return None
        return self.capacidad_disponible_kw * ratio_dc_ac


def desde_factura_y_pdi(
    tension_kv: float,
    fases: int,
    capacidad_disponible_kw: Optional[float] = None,
    **kwargs,
) -> PDI:
    """Constructor amigable. Determina si requiere trafo automáticamente."""
    pdi = PDI(
        tension_kv=tension_kv,
        fases=fases,
        capacidad_disponible_kw=capacidad_disponible_kw,
        **kwargs,
    )
    pdi.requiere_trafo_elevador = pdi.es_media_tension
    return pdi
