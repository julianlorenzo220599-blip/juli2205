"""Modelo de datos común al subsistema de facturas."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ConsumoMensual:
    mes: str                              # ISO "YYYY-MM"
    kwh_total: float
    kwh_pico: Optional[float] = None
    kwh_valle: Optional[float] = None
    kwh_resto: Optional[float] = None
    potencia_pico_kw: Optional[float] = None


@dataclass
class Factura:
    distribuidora: str
    categoria_tarifaria: str              # T1-R, T2, T3-MD, T3-BT, T3-MT, ...
    titular: str
    nis: str                              # Número de identificación de suministro
    direccion: str
    tension_suministro: str               # "BT 380V" / "MT 13.2 kV"
    potencia_contratada_kw: Optional[float]
    consumos: list[ConsumoMensual] = field(default_factory=list)
    fuente: str = "unknown"               # "parser:EDESUR" / "llm" / "llm:cache" / "manual"

    @property
    def consumo_anual_kwh(self) -> float:
        return sum(c.kwh_total for c in self.consumos)

    @property
    def consumo_mensual_promedio(self) -> float:
        return self.consumo_anual_kwh / len(self.consumos) if self.consumos else 0.0

    @property
    def potencia_pico_max(self) -> Optional[float]:
        picos = [c.potencia_pico_kw for c in self.consumos if c.potencia_pico_kw]
        return max(picos) if picos else None
