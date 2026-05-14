"""Tests del bridge PVSyst — parser, memo generator y comparador.

Las fixtures imitan el formato CSV real que PVSyst exporta desde
"Main results, per month" del reporte de simulación.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from rv_propuestas.integraciones.pvsyst import (
    ResultadoPVSyst,
    comparar,
    generar_memo,
    parsear_reporte_csv,
    parsear_reporte_texto,
)
from rv_propuestas.integraciones.pvsyst import (
    _detectar_delim, _normalizar_pr, _parse_num
)


# ──────────────────────────────────────────────────────────────────────────────
# CSV de muestra — formato típico PVSyst con delimitador `;` y unidad MWh
# ──────────────────────────────────────────────────────────────────────────────
CSV_PVSYST_EU = """PVsyst V7.4 - Simulation results
Project: ACME Industrial
Variant: ACME_v1

Balances and main results:

;GlobHor;DiffHor;T_Amb;GlobInc;GlobEff;EArray;E_Grid;PR
;kWh/m²;kWh/m²;°C;kWh/m²;kWh/m²;MWh;MWh;
January;180,4;78,2;24,0;234,1;225,3;48,65;47,12;0,838
February;160,2;75,0;23,5;208,4;200,5;43,20;41,85;0,836
March;145,0;72,0;21,0;195,5;188,2;40,55;39,30;0,835
April;115,0;65,0;17,0;165,8;159,4;34,20;33,10;0,832
May;90,0;55,0;13,5;138,5;133,0;28,50;27,55;0,829
June;75,0;48,0;10,5;122,0;117,0;24,85;24,00;0,826
July;82,0;52,0;10,5;130,5;125,0;26,55;25,65;0,824
August;105,0;60,0;12,5;152,5;146,0;31,05;30,05;0,827
September;130,0;68,0;15,5;172,5;165,5;35,20;34,10;0,832
October;160,5;73,0;19,0;200,0;192,0;40,80;39,55;0,835
November;180,5;78,0;22,0;220,5;212,0;45,00;43,60;0,838
December;190,0;82,0;24,5;235,5;226,5;48,30;46,80;0,838
Year;1613,6;806,2;17,8;2375,8;2289,4;446,85;432,67;0,832
"""

# Formato US — coma como decimal local, sí; pero comas como separador de columna
CSV_PVSYST_US = """PVsyst V7.4 - Simulation
,GlobHor,DiffHor,T_Amb,GlobInc,GlobEff,EArray,E_Grid,PR
,kWh/m²,kWh/m²,°C,kWh/m²,kWh/m²,MWh,MWh,
Jan,180.4,78.2,24.0,234.1,225.3,48.65,47.12,0.838
Feb,160.2,75.0,23.5,208.4,200.5,43.20,41.85,0.836
Mar,145.0,72.0,21.0,195.5,188.2,40.55,39.30,0.835
Apr,115.0,65.0,17.0,165.8,159.4,34.20,33.10,0.832
May,90.0,55.0,13.5,138.5,133.0,28.50,27.55,0.829
Jun,75.0,48.0,10.5,122.0,117.0,24.85,24.00,0.826
Jul,82.0,52.0,10.5,130.5,125.0,26.55,25.65,0.824
Aug,105.0,60.0,12.5,152.5,146.0,31.05,30.05,0.827
Sep,130.0,68.0,15.5,172.5,165.5,35.20,34.10,0.832
Oct,160.5,73.0,19.0,200.0,192.0,40.80,39.55,0.835
Nov,180.5,78.0,22.0,220.5,212.0,45.00,43.60,0.838
Dec,190.0,82.0,24.5,235.5,226.5,48.30,46.80,0.838
Year,1613.6,806.2,17.8,2375.8,2289.4,446.85,432.67,0.832
"""

# Sin row Year — el parser debe sumar los 12 meses
CSV_SIN_YEAR = """;E_Grid
;MWh
Enero;47,12
Febrero;41,85
Marzo;39,30
Abril;33,10
Mayo;27,55
Junio;24,00
Julio;25,65
Agosto;30,05
Septiembre;34,10
Octubre;39,55
Noviembre;43,60
Diciembre;46,80
"""

# kWh en vez de MWh — el factor de conversión NO debe aplicarse
CSV_KWH = """;E_Grid;PR
;kWh;
Jan;47120;0.838
Feb;41850;0.836
Year;88970;0.837
"""


# ──────────────────────────────────────────────────────────────────────────────
# Helpers numéricos
# ──────────────────────────────────────────────────────────────────────────────
def test_parse_num_eu_y_us():
    assert _parse_num("1.234,56") == 1234.56
    assert _parse_num("1,234.56") == 1234.56
    assert _parse_num("1234,56") == 1234.56
    assert _parse_num("1234.56") == 1234.56
    assert _parse_num("1234") == 1234.0


def test_normalizar_pr():
    assert _normalizar_pr(0.838) == 0.838
    assert _normalizar_pr(83.8) == 0.838
    assert _normalizar_pr(0.5) == 0.5


def test_detectar_delim_punto_y_coma():
    assert _detectar_delim(CSV_PVSYST_EU) == ";"


def test_detectar_delim_coma():
    assert _detectar_delim(CSV_PVSYST_US) == ","


# ──────────────────────────────────────────────────────────────────────────────
# Parser
# ──────────────────────────────────────────────────────────────────────────────
def test_parsear_csv_eu_con_mwh():
    r = parsear_reporte_texto(CSV_PVSYST_EU)
    assert isinstance(r, ResultadoPVSyst)
    # Year row: 432.67 MWh × 1000 = 432670 kWh
    assert r.energia_anual_kwh == 432670.0
    assert r.pr_anual == 0.832
    assert len(r.energia_mensual_kwh) == 12
    # Ene = 47.12 MWh = 47120 kWh
    assert r.energia_mensual_kwh[0] == 47120.0
    assert r.energia_mensual_kwh[11] == 46800.0
    # PR mensual cargado
    assert r.pr_mensual[0] == 0.838
    # Temperatura media (promedio simple de los 12 meses)
    assert r.temperatura_media is not None
    assert 17 < r.temperatura_media < 19


def test_parsear_csv_us_idem():
    r = parsear_reporte_texto(CSV_PVSYST_US)
    assert r.energia_anual_kwh == 432670.0
    assert r.pr_anual == 0.832


def test_parsear_sin_year_suma_meses():
    r = parsear_reporte_texto(CSV_SIN_YEAR)
    suma_esperada = (47.12 + 41.85 + 39.30 + 33.10 + 27.55 + 24.00 +
                     25.65 + 30.05 + 34.10 + 39.55 + 43.60 + 46.80) * 1000
    assert abs(r.energia_anual_kwh - suma_esperada) < 1


def test_parsear_kwh_no_aplica_factor_1000():
    r = parsear_reporte_texto(CSV_KWH)
    # En kWh el factor es 1
    assert r.energia_anual_kwh == 88970.0
    assert r.energia_mensual_kwh[0] == 47120.0


def test_yield_especifico():
    r = ResultadoPVSyst(energia_anual_kwh=432670.0)
    assert r.yield_especifico(250) == 432670 / 250
    assert r.yield_especifico(0) is None


def test_parser_error_sin_e_grid():
    try:
        parsear_reporte_texto("PVsyst V7.4\nFoo;Bar\n1;2")
    except ValueError as e:
        assert "E_Grid" in str(e)
        return
    raise AssertionError("Debió lanzar ValueError")


def test_parsear_archivo_inexistente():
    try:
        parsear_reporte_csv("/no/existe.csv")
    except FileNotFoundError:
        return
    raise AssertionError("Debió lanzar FileNotFoundError")


# ──────────────────────────────────────────────────────────────────────────────
# Comparación
# ──────────────────────────────────────────────────────────────────────────────
def test_comparar_dentro_de_umbral():
    sizing = SimpleNamespace(generacion_anual_kwh=440000)
    pvsyst = ResultadoPVSyst(energia_anual_kwh=432670, pr_anual=0.832)
    comp = comparar(sizing, pvsyst)
    assert -2 < comp.delta_pct < 0
    assert comp.warning is None


def test_comparar_excede_umbral():
    sizing = SimpleNamespace(generacion_anual_kwh=500000)
    pvsyst = ResultadoPVSyst(energia_anual_kwh=400000, pr_anual=0.78)
    comp = comparar(sizing, pvsyst)
    assert abs(comp.delta_pct + 20) < 0.01  # -20%
    assert comp.warning is not None
    assert "Δ" in comp.warning


# ──────────────────────────────────────────────────────────────────────────────
# Memo generator
# ──────────────────────────────────────────────────────────────────────────────
def test_generar_memo_contiene_secciones_clave():
    factura = SimpleNamespace(titular="ACME SA", nis="12345")
    sizing = SimpleNamespace(
        kwp_real=304.6, n_paneles=423, generacion_anual_kwh=456750,
        cobertura=0.951, topologia="MT_TRAFO",
        topologia_descripcion="MT 13.2 kV trafo elevador",
    )
    ubic = SimpleNamespace(nombre="Buenos Aires", lat=-34.6, lon=-58.4, altitud_m=25)
    irrad = SimpleNamespace(
        fuente="PVGIS-SARAH3", hsp_anual=4.85,
        tilt_optimo=25, azimuth_optimo=0,
    )
    inv = SimpleNamespace(
        cantidad=2, p_ac_total_kw=272, ratio_dc_ac=1.12,
        inversor=SimpleNamespace(
            sku="GW136K-HTH", descripcion="GoodWe HTH 136 kW 3F",
            p_ac_kw=136, p_dc_max_kw=204,
            v_mppt_min=200, v_mppt_max=1500, fase="3F",
            n_mppt=12, n_strings_por_mppt=2,
        ),
    )
    strs = SimpleNamespace(
        n_paneles_por_string=18, n_strings=24,
        n_strings_por_inversor=12, voc_string=886, vmpp_string=622,
        dentro_ventana_mppt=True,
    )
    memo = generar_memo(
        factura=factura, sizing=sizing, ubicacion=ubic, irradiacion=irrad,
        inv_cfg=inv, str_cfg=strs, proyecto="Planta ACME 305 kW",
    )

    # Verificar secciones obligatorias
    for seccion in ["GEOGRAPHIC SITE", "ORIENTATION", "SYSTEM SIZING",
                    "MODULE", "INVERTER", "STRING CONFIGURATION", "LOSSES",
                    "EXPECTED RESULTS", "NEXT STEPS"]:
        assert seccion in memo, f"Falta sección {seccion}"

    # Datos numéricos clave
    assert "Planta ACME 305 kW" in memo
    assert "ACME SA" in memo
    assert "304.6 kWp" in memo
    assert "GW136K-HTH" in memo
    assert "TCL-MG720DT210-68NS" in memo
    assert "423" in memo                # n_paneles
    assert "18" in memo                 # paneles por string
    assert "24" in memo                 # n_strings
    assert "-34.6" in memo or "-34,6" in memo


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
        except Exception as e:
            print(f"✗ {fn.__name__}: {type(e).__name__}: {e}")
            fail += 1
    sys.exit(0 if fail == 0 else 1)
