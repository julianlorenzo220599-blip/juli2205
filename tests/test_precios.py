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
