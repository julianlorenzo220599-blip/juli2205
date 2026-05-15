"""Tests del catálogo de precios — verifica integridad SKU/precio.

Asegura que:
  - precios.example.yaml es YAML válido y carga
  - SKUs del módulo de referencia y de inversores ≤125 kW tienen precio
  - SKUs >125 kW deliberadamente NO tienen precio (los lista en "Notas")
  - GMK330 (smart meter) tiene precio
  - MO-ELEC está en rango razonable USD/kWp
"""
from __future__ import annotations

from pathlib import Path

import yaml

from rv_propuestas.config import INVERSORES_EPC, MODULO_REF, SKU_IVA_REDUCIDO_PATTERNS


PRECIOS_PATH = Path(__file__).parent.parent / "data" / "precios.example.yaml"


def _cargar_precios() -> dict[str, float]:
    raw = yaml.safe_load(PRECIOS_PATH.read_text(encoding="utf-8"))
    out: dict[str, float] = {}
    for sku_map in raw.values():
        if isinstance(sku_map, dict):
            out.update({k: float(v) for k, v in sku_map.items()})
    return out


PRECIOS = _cargar_precios()


def test_precios_yaml_carga():
    assert isinstance(PRECIOS, dict)
    assert len(PRECIOS) > 0


def test_modulo_ref_tiene_precio():
    assert MODULO_REF.sku in PRECIOS, (
        f"{MODULO_REF.sku} debe estar en precios.example.yaml"
    )
    assert PRECIOS[MODULO_REF.sku] > 0


def test_inversores_catalogo_tienen_precio():
    """Inversores ≤125 kW son del catálogo retail RV y deben tener precio."""
    sin_precio = [
        inv.sku for inv in INVERSORES_EPC
        if inv.p_ac_kw <= 125 and inv.sku not in PRECIOS
    ]
    assert not sin_precio, (
        f"Inversores ≤125 kW sin precio en catálogo: {sin_precio}"
    )


def test_inversores_HTH_intencionalmente_sin_precio():
    """Inversores HTH >125 kW NO están en catálogo retail — deben aparecer en
    Notas como pendientes de cotización."""
    for inv in INVERSORES_EPC:
        if inv.p_ac_kw > 125:
            assert inv.sku not in PRECIOS, (
                f"{inv.sku} no debería tener precio (es 'cotizar'). "
                "Si RV lo agregó al catálogo, actualizar el test."
            )


def test_smart_meter_3f_disponible():
    """El BOM usa GMK330 — verificar que esté en el catálogo."""
    assert "GMK330" in PRECIOS
    assert PRECIOS["GMK330"] > 0


def test_iva_reducido_pattern_matchea_modulo():
    """MODULO_REF y GMK330 deben matchear los patrones de IVA reducido (Ley 27.191)."""
    assert MODULO_REF.sku.startswith(SKU_IVA_REDUCIDO_PATTERNS)
    assert "GMK330".startswith(SKU_IVA_REDUCIDO_PATTERNS)


def test_mo_elec_es_por_kwp():
    """MO-ELEC tiene unidad USD/kWp en el BOM — el valor debe estar entre
    10 y 200 USD/kWp para un EPC argentino."""
    assert "MO-ELEC" in PRECIOS
    assert 10 < PRECIOS["MO-ELEC"] < 200, (
        f"MO-ELEC = {PRECIOS['MO-ELEC']} fuera de rango razonable"
    )


def test_inversores_monofasicos_y_hibridos():
    """El catálogo D03.26 incluye 1F on-grid + híbridos (mono y trifásicos)."""
    esperados = [
        "GW3000-XS-30", "GW5000-MS-30", "GW6000-MS-30",
        "GW3000-ES-20", "GW5000-ES-20",
        "GW8000-ET-20", "GW10K-ET-20", "GW12K-ET-20", "GW15K-ET-20",
    ]
    faltantes = [s for s in esperados if s not in PRECIOS]
    assert not faltantes, f"Inversores faltantes: {faltantes}"


def test_baterias_litio_disponibles():
    """Baterías GoodWe Lynx D (HV apilable) y Lynx U (LV con fire suppression)."""
    assert PRECIOS["LX-D5.0-10"] > 0
    assert PRECIOS["LX-U5.0-30"] > 0


def test_cables_dc_slocable_nacionalizado():
    """Slocable 4mm² y 6mm² con costo nacionalizado debe estar disponible."""
    assert "CAB-DC-4-IMP" in PRECIOS
    assert "CAB-DC-6-IMP" in PRECIOS
    # 4mm² debe ser más barato que 6mm² (más cobre)
    assert PRECIOS["CAB-DC-4-IMP"] < PRECIOS["CAB-DC-6-IMP"]
    # Local debe ser más caro que nacionalizado (consistente con análisis)
    assert PRECIOS["CAB-DC-6-LOCAL"] > PRECIOS["CAB-DC-6-IMP"]


def test_abb_mt_componentes():
    """Componentes MT del proveedor ABB (parque 1.8 MWp ref)."""
    assert PRECIOS["TGBT-ABB"] > 100_000          # tablero general de gran porte
    assert PRECIOS["CELDA-MT-ABB"] > 30_000       # UNISEC 13.2 kV
    assert PRECIOS["SHELTER-ABB"] > 50_000


def test_kits_brief_2026():
    """Kits packaged del Brief Kit Solares 2026 v3 deben tener precio."""
    esperados_kits = {
        "EC-3K": 1099, "EC-5K": 1999, "EC-6K": 2299,
        "ECT-8K": 3380, "ECT-12K": 4599, "ECT-20K": 6399,
        "AC-3K": 3199, "AC-5K": 4399,
        "PS-8K": 6299, "PS-10K": 6899, "PS-12K": 9099, "PS-15K": 10499,
    }
    for sku, precio in esperados_kits.items():
        assert sku in PRECIOS, f"Kit {sku} faltante"
        assert PRECIOS[sku] == precio, (
            f"Kit {sku}: esperaba USD {precio}, encontré {PRECIOS[sku]}"
        )


def test_kits_escalado_monotono():
    """Dentro de cada familia, kits más grandes deben costar más."""
    # On-Grid 1F
    assert PRECIOS["EC-3K"] < PRECIOS["EC-5K"] < PRECIOS["EC-6K"]
    # On-Grid 3F
    assert PRECIOS["ECT-8K"] < PRECIOS["ECT-12K"] < PRECIOS["ECT-20K"]
    # Power Station 3F
    assert PRECIOS["PS-8K"] < PRECIOS["PS-10K"] < PRECIOS["PS-12K"] < PRECIOS["PS-15K"]


if __name__ == "__main__":
    import sys
    fns = [v for k, v in sorted(globals().items())
           if k.startswith("test_") and callable(v)]
    fail = 0
    for fn in fns:
        try:
            fn()
            print(f"✓ {fn.__name__}")
        except AssertionError as e:
            print(f"✗ {fn.__name__}: {e}")
            fail += 1
    sys.exit(0 if fail == 0 else 1)
