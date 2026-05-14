"""Tests del subsistema de facturas con excerpts reales (texto extraído).

Cada excerpt es el texto plano que pypdf devuelve de una factura real,
recortado a las secciones que el parser necesita. Si EDESUR/EDESA/EDEN
cambian su layout, este test los detecta.
"""
from __future__ import annotations

from rv_propuestas.inputs.facturas import (
    Factura,
    distribuidoras_soportadas,
    from_manual,
    merge_facturas,
    validar,
)
from rv_propuestas.inputs.facturas.registry import detectar, get_parser
from rv_propuestas.inputs.facturas.util import parse_num_ar


# ──────────────────────────────────────────────────────────────────────────────
# EXCERPTS REALES (anonimizados — kWh y NIS auténticos para validar parsing)
# ──────────────────────────────────────────────────────────────────────────────
EXCERPT_EDESUR = """
Empresa Distribuidora Sur S.A. San José 140 - C1076AAD - CABA
Web edesur.com.ar Emergencias 24 hs
At. CLIENTE EJEMPLO SA
Su número de cliente es 80515768
LSP N° A 9904-02482839 17
Tarifa T3 MT cliente Privado Industrial
Potencias
 Convenida 50.00
 Adquirida 225.60
Mes 03-25 04-25 05-25 06-25 07-25 08-25
DRP 134 137 154 175 186 158
DRFP 206 218 199 210 224 226
E. Tot 59760 70800 67200 73920 87720 88920
"""

EXCERPT_EDESA = """
Edesa S.A.
Office Park II - Planta Baja, Circunvalación Oeste
edesa.com.ar
Usuario GONZALEZ MARCELO 3019711
NIS 3019711
Liq.Serv.Pub. 18(B) Nro. 0100-06315088
Identificación :3019711
Ref. de Pago : 0.3019711.02-08/01/2026
Tarifa: T1-R2-N1 - Pot. Cont (kW) : 2
Domicilio : PZTA CAMINO Nro. Tapa Medidor 2 CENTRO LA CALDERA
Período de Facturación 11/2025
Período de Consumo : 22/10/2025 - 20/11/2025
Tipo de Consumo  Lec. Ant.  Lec. Act.  Cte.  Consumo
Activa     56125     57205    1,00     1.080
Reactiva   23502     24037    1,00       535
"""

EXCERPT_EDEN = """
EMPRESA DISTRIBUIDORA DE ENERGÍA NORTE S.A.
Savio 703 (2900) San Nicolás
edensa.com.ar
NIS
0-1323067 - 01 - 14/11/2025
Periodo de Facturación 202512
Tipo de tarifa o categoría: T1RM - Res. Ing. Medios
Nro.Medidor Concepto Lect.Ant. Lect.actual Lect.por Consumo
704009 EA 64006 64180 1.000 174 R
"""

EXCERPT_EDENOR = """
EDENOR S.A.
Empresa Distribuidora y Comercializadora Norte
Tarifa T3-MD
NIS 12345678
Potencia Contratada: 150,00 kW
01/2025  Energía  35.000 kWh
02/2025  Energía  33.500 kWh
"""


# ──────────────────────────────────────────────────────────────────────────────
# DETECCIÓN
# ──────────────────────────────────────────────────────────────────────────────
def test_deteccion_edesur():
    assert detectar(EXCERPT_EDESUR) == "EDESUR"


def test_deteccion_edesa():
    assert detectar(EXCERPT_EDESA) == "EDESA"


def test_deteccion_eden():
    assert detectar(EXCERPT_EDEN) == "EDEN"


def test_deteccion_edenor():
    assert detectar(EXCERPT_EDENOR) == "EDENOR"


def test_deteccion_eden_no_confunde_edenor():
    """Un PDF de EDEN no debería ser detectado como EDENOR."""
    detectado = detectar(EXCERPT_EDEN)
    assert detectado == "EDEN", f"Esperado EDEN, obtuvo {detectado}"


def test_deteccion_desconocida():
    assert detectar("Esto no es una factura eléctrica") is None


# ──────────────────────────────────────────────────────────────────────────────
# PARSERS CONCRETOS
# ──────────────────────────────────────────────────────────────────────────────
def test_parser_edesur():
    fac = get_parser("EDESUR")(EXCERPT_EDESUR)
    assert fac is not None
    assert fac.distribuidora == "EDESUR"
    assert fac.nis == "80515768"
    assert fac.categoria_tarifaria == "T3-MT"
    assert fac.tension_suministro.startswith("MT")
    assert fac.potencia_contratada_kw == 50.0
    assert len(fac.consumos) == 6
    assert fac.consumos[0].mes == "2025-03"
    assert fac.consumos[-1].mes == "2025-08"
    assert fac.consumos[-1].kwh_total == 88920
    # Demanda pico (DRP) debería estar capturada
    assert fac.consumos[-1].potencia_pico_kw == 158
    assert fac.fuente == "parser:EDESUR"


def test_parser_edesa():
    fac = get_parser("EDESA")(EXCERPT_EDESA)
    assert fac is not None
    assert fac.distribuidora == "EDESA"
    assert fac.nis == "3019711"
    assert fac.categoria_tarifaria == "T1-R2-N1"
    assert fac.potencia_contratada_kw == 2.0
    assert len(fac.consumos) == 1
    assert fac.consumos[0].mes == "2025-11"
    assert fac.consumos[0].kwh_total == 1080
    assert fac.fuente == "parser:EDESA"


def test_parser_eden():
    fac = get_parser("EDEN")(EXCERPT_EDEN)
    assert fac is not None
    assert fac.distribuidora == "EDEN"
    assert fac.nis == "1323067"
    assert fac.categoria_tarifaria == "T1RM"
    assert len(fac.consumos) == 1
    assert fac.consumos[0].mes == "2025-12"
    assert fac.consumos[0].kwh_total == 174
    assert fac.fuente == "parser:EDEN"


def test_parser_edenor():
    fac = get_parser("EDENOR")(EXCERPT_EDENOR)
    assert fac is not None
    assert fac.distribuidora == "EDENOR"
    assert fac.nis == "12345678"
    assert fac.potencia_contratada_kw == 150.0
    assert len(fac.consumos) == 2
    assert fac.consumos[0].kwh_total == 35000


# ──────────────────────────────────────────────────────────────────────────────
# VALIDACIÓN
# ──────────────────────────────────────────────────────────────────────────────
def test_validacion_ok():
    fac = from_manual("EDENOR", [1000] * 12, potencia_contratada_kw=10)
    res = validar(fac)
    assert res.ok
    assert not res.errores


def test_validacion_kwh_negativo():
    fac = from_manual("EDENOR", [1000, -50] + [1000] * 10)
    res = validar(fac)
    assert not res.ok


def test_validacion_sin_consumos():
    fac = Factura(
        distribuidora="X", categoria_tarifaria="T?", titular="", nis="",
        direccion="", tension_suministro="BT", potencia_contratada_kw=None,
    )
    res = validar(fac)
    assert not res.ok
    assert "Sin consumos" in res.errores[0]


def test_validacion_pocos_meses_warning():
    fac = from_manual("EDENOR", [1000, 1000])  # solo 2 meses
    res = validar(fac)
    assert res.ok
    assert any("Solo 2 mes" in w for w in res.warnings)


# ──────────────────────────────────────────────────────────────────────────────
# UTILIDADES
# ──────────────────────────────────────────────────────────────────────────────
def test_parse_num_ar():
    assert parse_num_ar("1.080") == 1080.0
    assert parse_num_ar("1.080,50") == 1080.50
    assert parse_num_ar("1.234.567,89") == 1234567.89
    assert parse_num_ar("50.00") == 50.0          # un punto, 2 decimales
    assert parse_num_ar("88920") == 88920.0
    assert parse_num_ar("174") == 174.0


def test_distribuidoras_soportadas():
    soportadas = set(distribuidoras_soportadas())
    assert {"EDEN", "EDENOR", "EDESA", "EDESUR"}.issubset(soportadas)


def test_merge_facturas():
    f1 = from_manual("EDESA", [500], mes_inicial="2025-11", nis="X")
    f2 = from_manual("EDESA", [400], mes_inicial="2025-12", nis="X")
    f3 = from_manual("EDESA", [600], mes_inicial="2025-10", nis="X")
    combo = merge_facturas([f1, f2, f3])
    assert len(combo.consumos) == 3
    assert [c.mes for c in combo.consumos] == ["2025-10", "2025-11", "2025-12"]
    assert combo.consumo_anual_kwh == 1500
    assert combo.fuente == "merge:3"


if __name__ == "__main__":
    # Permite correr `python tests/test_facturas.py` sin pytest.
    import sys
    fns = [
        v for k, v in sorted(globals().items())
        if k.startswith("test_") and callable(v)
    ]
    fail = 0
    for fn in fns:
        try:
            fn()
            print(f"✓ {fn.__name__}")
        except AssertionError as e:
            print(f"✗ {fn.__name__}: {e}")
            fail += 1
        except Exception as e:
            print(f"✗ {fn.__name__}: {type(e).__name__}: {e}")
            fail += 1
    sys.exit(0 if fail == 0 else 1)
