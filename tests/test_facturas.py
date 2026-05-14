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

# EPEC stub — excerpt simulado del layout de la factura escaneada
# A(17) 00026-01266330 (MOLINOS MARIMBO SAIC, MT, marzo 2026). Calibrar
# contra PDF real cuando llegue.
EXCERPT_EPEC = """
EPEC
LIQUIDACION DE SERVICIOS PUBLICOS A (17) N° 00026-01266330
MOLINOS MARIMBO SAIC
DEAN FUNES Y ARRASCAETA LA CARLOTA PCIA DE CORDOBA
2670 CORDOBA
CLIENTE N°  00160787
CONTRATO N° 00278648/01
TENSION   Media Tension
PERIODO LEIDO   28/02/2026 al 31/03/2026
03/2026
COSENO FI 0,9522

FACTURACION
DESCRIPCION                                    CANTIDAD     PRECIO UNIT.    IMPORTE
Cargo Cap.Trans.DP                                 1116    15632,877900    17.446.291,74
Cargo Cap.Trans.DF                                 1132    12093,762000    13.690.138,58
Peaje en H. Valle                                142020        4,974910       706.536,72
Peaje en H. Pico                                 109176        5,138280       560.976,86
Peaje en H. Resto                                305136        5,029990     1.534.831,03
"""

# CAMMESA stub — excerpt simulado del layout de factura A-0057-00373700
# (mismo cliente, suministro 23808, feb-2026). Calibrar con PDF real.
EXCERPT_CAMMESA = """
CAMMESA
Ruta 34 "S" Km. 3,5 (2121) PEREZ - Pcia. Santa Fe
C.U.I.T. N° 30-65537309-4
FACTURA N° 0057-00373700
Señor(es):
MOLINOS MARIMBO SAIC
ARRASCAETA 88
2670 - La Carlota - CORDOBA
Período Facturado: 01/02/2026 al 28/02/2026
Suministro 23808 MOMALCXN
Cantidad    Descripción                  Precio Medio    Importe
101,800 MW Cargos de Potencia              24.799,75    2.524.615,00
0,700      Cargo por Comercialización    385.992,86      270.195,00
"""

# Pampa Energía S.A. — Mercado a Término. Excerpt textual literal del PDF
# 1593-A00144687 (MOLINOS MARIMBO SAIC, feb-2026) extraído con `pdftotext -layout`.
EXCERPT_PAMPA = """
                    Pampa Energía S.A.
                    Maipú 1
                    C1084ABA Ciudad Autónoma de Buenos Aires
 Central T Loma de la Lata Base
                    C.U.I.T: 30-52655265-9

 CLIENTE          (10191)                              C.U.I.T.: 30-53758291-6
 MOLINOS MARIMBO SAIC
                                                       Ingresos Brutos: 30537582916
 ARRASCAETA 88
 LA CARLOTA
 2670 JUAREZ CELMAN Córdoba

 5502293   Fondo Nacional de EE.    MWH    443,520    2.029,00    899.902,08

 Suministro de EE del 1 al 28/02/2026
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


def test_deteccion_pampa():
    assert detectar(EXCERPT_PAMPA) == "PAMPA"


def test_deteccion_epec():
    assert detectar(EXCERPT_EPEC) == "EPEC"


def test_deteccion_cammesa():
    assert detectar(EXCERPT_CAMMESA) == "CAMMESA"


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


def test_parser_pampa():
    fac = get_parser("PAMPA")(EXCERPT_PAMPA)
    assert fac is not None
    assert fac.distribuidora == "PAMPA"
    assert fac.categoria_tarifaria == "MATE"
    assert fac.nis == "10191"
    assert fac.titular == "MOLINOS MARIMBO SAIC"
    assert "ARRASCAETA 88" in fac.direccion
    assert len(fac.consumos) == 1
    assert fac.consumos[0].mes == "2026-02"
    # 443,520 MWh (coma decimal AR) → 443.52 MWh → 443520 kWh
    assert fac.consumos[0].kwh_total == 443520.0
    assert fac.fuente == "parser:PAMPA"


def test_parser_epec():
    fac = get_parser("EPEC")(EXCERPT_EPEC)
    assert fac is not None
    assert fac.distribuidora == "EPEC"
    assert fac.nis == "00160787"
    assert fac.tension_suministro.startswith("MT")
    assert fac.categoria_tarifaria == "T3-MT"
    assert fac.potencia_contratada_kw == 1116
    assert len(fac.consumos) == 1
    assert fac.consumos[0].mes == "2026-03"
    # 142020 valle + 109176 pico + 305136 resto = 556332
    assert fac.consumos[0].kwh_total == 556332
    assert fac.consumos[0].kwh_pico == 109176
    assert fac.consumos[0].kwh_valle == 142020
    assert fac.consumos[0].kwh_resto == 305136
    assert fac.fuente == "parser:EPEC"


def test_parser_cammesa():
    fac = get_parser("CAMMESA")(EXCERPT_CAMMESA)
    assert fac is not None
    assert fac.distribuidora == "CAMMESA"
    assert fac.categoria_tarifaria == "GU-MEM"
    assert fac.nis == "23808"
    assert "MOLINOS" in fac.titular
    # 101,800 MW (coma decimal AR) → 101.8 MW → 101800 kW
    assert fac.potencia_contratada_kw == 101800
    assert len(fac.consumos) == 1
    assert fac.consumos[0].mes == "2026-02"
    # CAMMESA no factura kWh — emitido como 0 con potencia separada
    assert fac.consumos[0].kwh_total == 0
    assert fac.consumos[0].potencia_pico_kw == 101800


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
    assert {"EDEN", "EDENOR", "EDESA", "EDESUR", "PAMPA", "EPEC", "CAMMESA"}.issubset(soportadas)


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
