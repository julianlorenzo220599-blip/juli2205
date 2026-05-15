"""Tests de la integración ClickUp con HTTP mockeado.

No toca la API real: inyectamos un `http_post` fake que captura el payload
para verificación. Cubre payload builder, descripción markdown, tags,
attachments y skip silencioso cuando falta token o lista.
"""
from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from rv_propuestas.integraciones.clickup import (
    build_descripcion,
    build_payload,
    build_tags,
    crear_task_propuesta,
)


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures sintéticas
# ──────────────────────────────────────────────────────────────────────────────
def _factura():
    return SimpleNamespace(
        titular="ACME SA", distribuidora="EDESUR", categoria_tarifaria="T3-MT",
        tension_suministro="MT 13.2 kV", potencia_contratada_kw=200,
        consumo_anual_kwh=480000, consumo_mensual_promedio=40000,
        nis="80515768", direccion="—",
    )


def _sizing(kwp=304.6, topologia="MT_TRAFO"):
    return SimpleNamespace(
        kwp_real=kwp, n_paneles=423,
        generacion_anual_kwh=456840, cobertura=0.952,
        topologia=topologia, notas=["PDI en MT"],
    )


def _inv():
    return SimpleNamespace(
        cantidad=2, p_ac_total_kw=272, ratio_dc_ac=1.12,
        inversor=SimpleNamespace(sku="GW136K-HTH", descripcion="GoodWe HTH 136 kW 3F"),
    )


def _costeo(sin_precio=1):
    return SimpleNamespace(
        neto_cliente=120000, iva_total=25073, total_cliente=145073,
        items_sin_precio=["GW136K-HTH"] * sin_precio,
    )


def _ubic():
    return SimpleNamespace(nombre="Buenos Aires", lat=-34.6037, lon=-58.3816)


class _FakeResp:
    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self._json_data = json_data or {}

    def json(self):
        return self._json_data


# ──────────────────────────────────────────────────────────────────────────────
# Builders puros
# ──────────────────────────────────────────────────────────────────────────────
def test_build_tags_por_tamano():
    assert "kwp-0-50" in build_tags(sizing=_sizing(35), factura=_factura())
    assert "kwp-50-250" in build_tags(sizing=_sizing(150), factura=_factura())
    assert "kwp-250-1000" in build_tags(sizing=_sizing(500), factura=_factura())
    assert "kwp-1000+" in build_tags(sizing=_sizing(1500), factura=_factura())


def test_build_tags_incluye_distribuidora_y_tension():
    tags = build_tags(sizing=_sizing(), factura=_factura())
    assert "edesur" in tags
    assert "media-tension" in tags
    assert "propuesta-auto" in tags


def test_build_descripcion_contiene_secciones_clave():
    desc = build_descripcion(
        factura=_factura(), sizing=_sizing(), inv_cfg=_inv(), costeo=_costeo(),
        ubicacion=_ubic(), proyecto="Planta ACME",
    )
    for fragmento in [
        "## Propuesta solar fotovoltaica · Planta ACME",
        "ACME SA",
        "80515768",
        "EDESUR · T3-MT",
        "304.6 kWp",
        "423 ×",
        "GoodWe HTH 136 kW",
        "456,840 kWh",
        "95.2%",
        "USD 145,073",
        "1 SKUs sin precio",
    ]:
        assert fragmento in desc, f"Falta '{fragmento}' en la descripción"


def test_build_descripcion_sin_skus_sin_precio_oculta_warning():
    desc = build_descripcion(
        factura=_factura(), sizing=_sizing(), inv_cfg=_inv(),
        costeo=_costeo(sin_precio=0),
    )
    assert "sin precio" not in desc


def test_build_payload_completo():
    p = build_payload(
        factura=_factura(), sizing=_sizing(), inv_cfg=_inv(), costeo=_costeo(),
        ubicacion=_ubic(), proyecto="Planta ACME",
    )
    assert p["name"] == "Planta ACME · 305 kWp"
    assert isinstance(p["tags"], list) and len(p["tags"]) >= 3
    assert "ACME SA" in p["description"]
    assert p["notify_all"] is False


def test_build_payload_titulo_capped_a_128_chars():
    p = build_payload(
        factura=_factura(), sizing=_sizing(), inv_cfg=_inv(), costeo=_costeo(),
        proyecto="X" * 200,
    )
    assert len(p["name"]) <= 128


# ──────────────────────────────────────────────────────────────────────────────
# crear_task_propuesta con http_post mockeado
# ──────────────────────────────────────────────────────────────────────────────
def test_skip_sin_api_token():
    with patch.dict(os.environ, {"CLICKUP_API_TOKEN": ""}, clear=False):
        # Asegurar que NO está seteado
        os.environ.pop("CLICKUP_API_TOKEN", None)
        res = crear_task_propuesta(
            factura=_factura(), sizing=_sizing(), inv_cfg=_inv(),
            costeo=_costeo(), list_id="123",
        )
    assert res is None


def test_skip_sin_list_id():
    os.environ.pop("CLICKUP_LIST_ID", None)
    res = crear_task_propuesta(
        factura=_factura(), sizing=_sizing(), inv_cfg=_inv(), costeo=_costeo(),
        api_token="fake-token",
    )
    assert res is None


def test_crea_task_y_devuelve_url():
    capturado = {}

    def fake_post(url, **kwargs):
        capturado["url"] = url
        capturado["headers"] = kwargs.get("headers", {})
        capturado["json"] = kwargs.get("json")
        return _FakeResp(200, {"id": "abc123", "url": "https://app.clickup.com/t/abc123"})

    res = crear_task_propuesta(
        factura=_factura(), sizing=_sizing(), inv_cfg=_inv(), costeo=_costeo(),
        ubicacion=_ubic(), proyecto="Planta ACME",
        api_token="fake-token", list_id="LIST123",
        http_post=fake_post,
    )
    assert res is not None
    assert res.task_id == "abc123"
    assert "abc123" in res.task_url
    assert capturado["url"].endswith("/list/LIST123/task")
    assert capturado["headers"]["Authorization"] == "fake-token"
    assert capturado["json"]["name"].startswith("Planta ACME")


def test_falla_http_no_lanza():
    """Errores HTTP transitorios deben loggear y devolver None, no romper la pipeline."""
    def fake_post(url, **kwargs):
        raise ConnectionError("ClickUp down")

    res = crear_task_propuesta(
        factura=_factura(), sizing=_sizing(), inv_cfg=_inv(), costeo=_costeo(),
        api_token="fake-token", list_id="LIST123",
        http_post=fake_post,
    )
    assert res is None


def test_status_no_2xx_devuelve_none():
    def fake_post(url, **kwargs):
        return _FakeResp(401, {"error": "Unauthorized"})

    res = crear_task_propuesta(
        factura=_factura(), sizing=_sizing(), inv_cfg=_inv(), costeo=_costeo(),
        api_token="fake-token", list_id="LIST123",
        http_post=fake_post,
    )
    assert res is None


def test_sube_attachments(tmp_path: Path | None = None):
    """Verifica que tras crear la task se intenten subir los attachments."""
    import tempfile
    td = Path(tempfile.mkdtemp())
    excel = td / "REVISION.xlsx"
    excel.write_bytes(b"fake xlsx")
    ppt = td / "PROPUESTA.pptx"
    ppt.write_bytes(b"fake pptx")

    llamadas = []

    def fake_post(url, **kwargs):
        llamadas.append(url)
        if "/attachment" in url:
            return _FakeResp(200, {"id": "att-x"})
        return _FakeResp(200, {"id": "task-x", "url": "https://app.clickup.com/t/task-x"})

    res = crear_task_propuesta(
        factura=_factura(), sizing=_sizing(), inv_cfg=_inv(), costeo=_costeo(),
        api_token="fake-token", list_id="LIST123",
        attachments=[excel, ppt],
        http_post=fake_post,
    )
    assert res is not None
    assert res.attachments_subidos == 2
    assert any("/list/LIST123/task" in u for u in llamadas)
    assert sum("/attachment" in u for u in llamadas) == 2


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
