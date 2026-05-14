"""Reglas de negocio RV Energía — márgenes, IVA, ratios técnicos.

Fuente: RVEnergia_Contexto_ClaudeCode.md (§8).
Cambiar acá impacta toda la pipeline; no duplicar constantes en otros módulos.
"""
from dataclasses import dataclass, field

# ──────────────────────────────────────────────────────────────────────────────
# MÁRGENES POR CATEGORÍA (proyectos ON-GRID)
# ──────────────────────────────────────────────────────────────────────────────
MARGENES = {
    "equipos":     0.18,   # Equipos solares (módulos, inversores, baterías, estructura)
    "electrico":   0.25,   # Trabajos eléctricos (mano de obra, materiales BT/MT)
    "ingenieria":  0.30,   # Ingeniería / PEM / dirección de obra
    "logistica":   0.10,   # Flete federal
}

CONTINGENCIA   = 0.05   # +5% sobre subtotal con márgenes
COSTO_FINANCIERO = 0.04 # +4% sobre subtotal con márgenes

# ──────────────────────────────────────────────────────────────────────────────
# IVA (Argentina)
# ──────────────────────────────────────────────────────────────────────────────
# Ley 27.191: alícuota reducida para componentes de generación renovable.
IVA_REDUCIDO = 0.105   # Paneles + smart meter
IVA_GENERAL  = 0.21    # Resto de componentes y servicios

# SKU patterns que califican para IVA reducido
SKU_IVA_REDUCIDO_PATTERNS = ("TCL-", "GMK")  # Módulos TCL + smart meter GoodWe

# ──────────────────────────────────────────────────────────────────────────────
# RATIOS TÉCNICOS POR DEFECTO
# ──────────────────────────────────────────────────────────────────────────────
@dataclass
class RatiosTecnicos:
    """Coeficientes de diseño usados por el motor de sizing."""

    pr_default: float = 0.78          # Performance Ratio típico ON-GRID AR
    ratio_dc_ac: float = 1.20         # Sobredimensionamiento DC/AC permitido GoodWe
    coef_simultaneidad: float = 0.85  # Para sizing de inversor según potencia contratada
    cobertura_objetivo: float = 0.95  # % del consumo anual a cubrir (autoconsumo)
    degradacion_anual: float = 0.005  # 0.5% (TCL TOPCon performance lineal)
    vida_util_anios: int = 30

# ──────────────────────────────────────────────────────────────────────────────
# UMBRALES DE TOPOLOGÍA (basado en tensión del PDI y kWp)
# ──────────────────────────────────────────────────────────────────────────────
@dataclass
class UmbralTopologia:
    kwp_max: float
    tipo: str
    descripcion: str

UMBRALES = [
    UmbralTopologia(  30, "BT_KIT_INDUSTRIAL", "BT 380V, string inversores GoodWe MT/HT"),
    UmbralTopologia( 100, "BT_STRING_MULTI",   "BT 380V, múltiples string inversores + tablero AC compuesto"),
    UmbralTopologia( 300, "BT_LIMITE",         "BT 380V — verificar capacidad PDI, posible trafo dedicado"),
    UmbralTopologia(1000, "MT_TRAFO",          "MT 13.2 kV, trafo elevador, celdas MT, protecciones 51/27/59/81"),
    UmbralTopologia(3000, "MT_SET",            "MT 13.2/33 kV, SET propia, SCADA, multi-string o central inverter"),
]

# ──────────────────────────────────────────────────────────────────────────────
# MÓDULO DE REFERENCIA (TCL TOPCon Bifacial)
# ──────────────────────────────────────────────────────────────────────────────
@dataclass
class Modulo:
    sku: str
    marca: str
    descripcion: str
    wp: int           # Potencia nominal
    voc: float        # Tensión circuito abierto STC
    isc: float        # Corriente cortocircuito STC
    vmpp: float
    impp: float
    eficiencia: float
    largo_mm: int
    ancho_mm: int
    bifacial: bool = True

MODULO_REF = Modulo(
    sku="TCL-MI725DH210-66NT",
    marca="TCL SOLAR",
    descripcion="Módulo Fotovoltaico TOPCon Bifacial 725W G12-66P",
    wp=725,
    voc=46.8,
    isc=19.40,
    vmpp=39.2,
    impp=18.50,
    eficiencia=0.233,
    largo_mm=2382,
    ancho_mm=1134,
    bifacial=True,
)

# ──────────────────────────────────────────────────────────────────────────────
# CATÁLOGO DE INVERSORES GOODWE (rangos EPC)
# ──────────────────────────────────────────────────────────────────────────────
@dataclass
class Inversor:
    sku: str
    descripcion: str
    p_ac_kw: float
    p_dc_max_kw: float
    n_mppt: int
    n_strings_por_mppt: int
    v_mppt_min: int
    v_mppt_max: int
    fase: str  # "1F" / "3F"

INVERSORES_EPC = [
    Inversor("GW25K-MT",     "GoodWe MT 25 kW 3F",   25,  37.5, 3, 2, 200, 1000, "3F"),
    Inversor("GW50K-MT",     "GoodWe MT 50 kW 3F",   50,  75.0, 4, 2, 200, 1000, "3F"),
    Inversor("GW80K-HT",     "GoodWe HT 80 kW 3F",   80, 120.0, 8, 2, 200, 1100, "3F"),
    Inversor("GW100K-HT",    "GoodWe HT 100 kW 3F", 100, 150.0, 9, 2, 200, 1100, "3F"),
    Inversor("GW125K-HT",    "GoodWe HT 125 kW 3F", 125, 187.5, 10, 2, 200, 1100, "3F"),
    Inversor("GW136K-HTH",   "GoodWe HTH 136 kW 3F",136, 204.0, 12, 2, 200, 1500, "3F"),
    Inversor("GW225K-HTH",   "GoodWe HTH 225 kW 3F",225, 337.5, 18, 2, 200, 1500, "3F"),
    Inversor("GW250K-HTH",   "GoodWe HTH 250 kW 3F",250, 375.0, 20, 2, 200, 1500, "3F"),
]

# ──────────────────────────────────────────────────────────────────────────────
# FORMATO NUMÉRICO ARGENTINA
# ──────────────────────────────────────────────────────────────────────────────
def fmt_ar(value: float, decimales: int = 2) -> str:
    """Formato AR: coma decimal, punto miles. Ej: 1234567.89 → '1.234.567,89'."""
    if value is None:
        return ""
    s = f"{value:,.{decimales}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_usd(value: float) -> str:
    return f"USD {fmt_ar(value, 2)}"


def fmt_kwp(value: float) -> str:
    return f"{fmt_ar(value, 2)} kWp"
