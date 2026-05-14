"""Generador de BOM para proyectos EPC (30 kW – 3 MW).

Categorías del BOM (alineadas con las categorías de margen RV):
  - equipos:    paneles, inversores, estructura, baterías opcionales
  - electrico:  cables DC/AC, tableros, protecciones, malla tierra, trafo, celdas MT
  - ingenieria: PEM, dirección obra, gestión distribuidora, simulación PVSyst
  - logistica:  flete federal, descarga, izaje
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from ..config import MODULO_REF
from ..inputs.pdi import PDI
from ..sizing.engine import SizingResult
from ..sizing.topologia import ConfiguracionInversores, ConfiguracionStrings


@dataclass
class ItemBOM:
    categoria: str          # "equipos" | "electrico" | "ingenieria" | "logistica"
    sku: str
    descripcion: str
    cantidad: float
    unidad: str
    precio_unit_usd: Optional[float] = None  # llenado desde catálogo de precios
    iva_reducido: bool = False
    notas: str = ""

    @property
    def subtotal_usd(self) -> Optional[float]:
        if self.precio_unit_usd is None:
            return None
        return round(self.precio_unit_usd * self.cantidad, 2)


@dataclass
class BOM:
    items: list[ItemBOM] = field(default_factory=list)

    def add(self, item: ItemBOM) -> None:
        self.items.append(item)

    def por_categoria(self, categoria: str) -> list[ItemBOM]:
        return [i for i in self.items if i.categoria == categoria]

    def aplicar_precios(self, precios: dict[str, float]) -> list[str]:
        """Llena precio_unit_usd desde un dict SKU → USD. Devuelve SKUs sin precio."""
        faltantes = []
        for it in self.items:
            if it.sku in precios:
                it.precio_unit_usd = precios[it.sku]
            elif it.precio_unit_usd is None:
                faltantes.append(it.sku)
        return faltantes


# ──────────────────────────────────────────────────────────────────────────────
# GENERADOR
# ──────────────────────────────────────────────────────────────────────────────
def generar_bom(
    sizing: SizingResult,
    inv_cfg: ConfiguracionInversores,
    str_cfg: ConfiguracionStrings,
    pdi: PDI,
) -> BOM:
    bom = BOM()
    kwp = sizing.kwp_real

    # ── EQUIPOS ───────────────────────────────────────────────────────────────
    bom.add(ItemBOM(
        categoria="equipos",
        sku=MODULO_REF.sku,
        descripcion=MODULO_REF.descripcion,
        cantidad=sizing.n_paneles,
        unidad="u",
        iva_reducido=True,
    ))

    bom.add(ItemBOM(
        categoria="equipos",
        sku=inv_cfg.inversor.sku,
        descripcion=inv_cfg.inversor.descripcion,
        cantidad=inv_cfg.cantidad,
        unidad="u",
        notas=f"Ratio DC/AC: {inv_cfg.ratio_dc_ac}",
    ))

    # Estructura: m² aproximado (1 panel = 2.7 m² + factor de separación 1.4)
    m2_estructura = sizing.n_paneles * MODULO_REF.largo_mm * MODULO_REF.ancho_mm / 1_000_000 * 1.4
    bom.add(ItemBOM(
        categoria="equipos",
        sku="EST-EPC",
        descripcion="Estructura metálica EPC (suelo / techo industrial)",
        cantidad=round(m2_estructura, 1),
        unidad="m²",
    ))

    # Smart meter trifásico — IVA reducido (componente generación renovable Ley 27.191).
    bom.add(ItemBOM(
        categoria="equipos",
        sku="GMK330",
        descripcion="GoodWe Smart Meter trifásico GMK330",
        cantidad=1,
        unidad="u",
        iva_reducido=True,
    ))

    # ── ELÉCTRICO ─────────────────────────────────────────────────────────────
    # Cables DC: ~6 m promedio por panel (ida+vuelta string) + 4 mm² o 6 mm²
    metros_dc = sizing.n_paneles * 4
    bom.add(ItemBOM(
        categoria="electrico",
        sku="CAB-DC-6",
        descripcion="Cable DC 6 mm² solar (rojo + negro)",
        cantidad=metros_dc,
        unidad="m",
    ))

    # Conectores MC4
    bom.add(ItemBOM(
        categoria="electrico",
        sku="MC4-PAR",
        descripcion="Par de conectores MC4",
        cantidad=str_cfg.n_strings * 2,
        unidad="par",
    ))

    # Cable AC: dimensionado básico — m por kW (aproximación EPC) × distancia PDI
    metros_ac = max(50.0, pdi.distancia_al_tablero_m * inv_cfg.cantidad * 3)
    bom.add(ItemBOM(
        categoria="electrico",
        sku="CAB-AC",
        descripcion="Cable AC subterráneo armado (sección según corriente)",
        cantidad=round(metros_ac, 0),
        unidad="m",
    ))

    # Tableros de protección AC + DC
    bom.add(ItemBOM(
        categoria="electrico",
        sku="TAB-DC",
        descripcion="Tablero combinador DC (fusibles + descargadores)",
        cantidad=max(1, inv_cfg.cantidad // 4 + 1),
        unidad="u",
    ))
    bom.add(ItemBOM(
        categoria="electrico",
        sku="TAB-AC",
        descripcion="Tablero de protección AC (interruptor + descargador + medidor)",
        cantidad=1,
        unidad="u",
    ))

    # Puesta a tierra
    bom.add(ItemBOM(
        categoria="electrico",
        sku="PAT-MALLA",
        descripcion="Sistema de puesta a tierra (jabalinas + malla equipotencial)",
        cantidad=1,
        unidad="gl",
    ))

    # Trafo elevador y celdas MT si corresponde
    if pdi.requiere_trafo_elevador or sizing.topologia.startswith("MT"):
        # Dimensionar trafo: 1.1× P_AC (factor de carga)
        kva_trafo = math.ceil(inv_cfg.p_ac_total_kw * 1.1 / 50) * 50
        bom.add(ItemBOM(
            categoria="electrico",
            sku=f"TRAFO-{kva_trafo}",
            descripcion=f"Transformador elevador 0.4/{pdi.tension_kv:.1f} kV {kva_trafo} kVA",
            cantidad=1,
            unidad="u",
        ))
        bom.add(ItemBOM(
            categoria="electrico",
            sku="CELDA-MT",
            descripcion=f"Celdas MT {pdi.tension_kv:.1f} kV (entrada + medición + protección)",
            cantidad=1,
            unidad="gl",
        ))
        bom.add(ItemBOM(
            categoria="electrico",
            sku="PROT-MT-RELE",
            descripcion="Relé de protección 51/51N/27/59/81 + transductor",
            cantidad=1,
            unidad="u",
        ))

    # Mano de obra eléctrica — escala con kWp (precio en USD/kWp).
    bom.add(ItemBOM(
        categoria="electrico",
        sku="MO-ELEC",
        descripcion="Mano de obra eléctrica e instalación",
        cantidad=round(kwp, 1),
        unidad="kWp",
    ))

    # ── INGENIERÍA ────────────────────────────────────────────────────────────
    bom.add(ItemBOM(
        categoria="ingenieria",
        sku="ING-PEM",
        descripcion="Ingeniería de detalle + Proyecto Ejecutivo de Montaje (PEM)",
        cantidad=1,
        unidad="gl",
    ))
    bom.add(ItemBOM(
        categoria="ingenieria",
        sku="ING-PVSYST",
        descripcion="Simulación PVSyst V8 + memoria técnica",
        cantidad=1,
        unidad="gl",
    ))
    bom.add(ItemBOM(
        categoria="ingenieria",
        sku="ING-DIST",
        descripcion="Gestión de habilitación ante distribuidora",
        cantidad=1,
        unidad="gl",
    ))
    bom.add(ItemBOM(
        categoria="ingenieria",
        sku="ING-DIRECCION",
        descripcion="Dirección de obra + puesta en marcha",
        cantidad=1,
        unidad="gl",
    ))

    # ── LOGÍSTICA ─────────────────────────────────────────────────────────────
    bom.add(ItemBOM(
        categoria="logistica",
        sku="FLETE",
        descripcion="Flete federal (módulos + inversores + estructura)",
        cantidad=1,
        unidad="gl",
    ))
    if kwp > 200:
        bom.add(ItemBOM(
            categoria="logistica",
            sku="IZAJE",
            descripcion="Grúa / izaje para descarga y montaje",
            cantidad=1,
            unidad="gl",
        ))

    return bom
