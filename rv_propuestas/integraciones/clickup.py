"""Integración ClickUp — crea task automática al finalizar la pipeline.

Workspace por defecto: 90132555978 (configurable vía CLICKUP_WORKSPACE_ID).

Variables de entorno:
  CLICKUP_API_TOKEN   — Personal API Token (User Settings → Apps)
  CLICKUP_LIST_ID     — Lista donde crear las tasks (override con --clickup-list)
  CLICKUP_WORKSPACE_ID — opcional, default 90132555978

Si CLICKUP_API_TOKEN no está configurado, `crear_task_propuesta()` devuelve
None silenciosamente — la pipeline no falla por falta de token.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

API_BASE = "https://api.clickup.com/api/v2"


@dataclass
class ResultadoClickUp:
    task_id: str
    task_url: str
    attachments_subidos: int


def build_descripcion(
    *,
    factura,
    sizing,
    inv_cfg,
    costeo,
    ubicacion=None,
    proyecto: str = "",
) -> str:
    """Genera el body markdown de la task (mismo formato que ClickUp renderiza)."""
    lines = [
        f"## Propuesta solar fotovoltaica · {proyecto or 'sin nombre'}",
        "",
        f"**Cliente**: {factura.titular or '—'}",
        f"**NIS**: {factura.nis or '—'}",
        f"**Distribuidora**: {factura.distribuidora} · {factura.categoria_tarifaria}",
    ]
    if ubicacion is not None:
        lines.append(f"**Ubicación**: {ubicacion.nombre} (lat {ubicacion.lat:.4f}, lon {ubicacion.lon:.4f})")
    lines += [
        "",
        "### Sizing",
        f"- **Potencia**: {sizing.kwp_real:.1f} kWp DC",
        f"- **Paneles**: {sizing.n_paneles} × TCL TOPCon Bifacial 720 W",
        f"- **Inversores**: {inv_cfg.cantidad} × {inv_cfg.inversor.descripcion}",
        f"- **Generación anual**: {sizing.generacion_anual_kwh:,.0f} kWh",
        f"- **Cobertura consumo**: {sizing.cobertura*100:.1f}%",
        "",
        "### Inversión (vista cliente)",
        f"- Subtotal sin IVA: USD {costeo.neto_cliente:,.0f}",
        f"- IVA: USD {costeo.iva_total:,.0f}",
        f"- **TOTAL**: USD {costeo.total_cliente:,.0f}",
        f"- USD/kWp: {costeo.total_cliente/sizing.kwp_real:,.0f}" if sizing.kwp_real else "",
    ]
    if costeo.items_sin_precio:
        lines += [
            "",
            f"⚠ **{len(costeo.items_sin_precio)} SKUs sin precio** en catálogo "
            "(ver hoja 'Notas' del Excel).",
        ]
    if sizing.notas:
        lines += ["", "### Notas técnicas"]
        for n in sizing.notas:
            lines.append(f"- {n}")
    lines += [
        "",
        "---",
        "*Generado automáticamente por `rv_propuestas`*",
    ]
    return "\n".join(l for l in lines if l is not None)


def build_tags(*, sizing, factura) -> list[str]:
    """Tags útiles para filtrar en ClickUp."""
    tags = ["propuesta-auto"]
    if factura.distribuidora:
        tags.append(factura.distribuidora.lower())
    # Rango de tamaño
    kwp = sizing.kwp_real
    if kwp <= 50:
        tags.append("kwp-0-50")
    elif kwp <= 250:
        tags.append("kwp-50-250")
    elif kwp <= 1000:
        tags.append("kwp-250-1000")
    else:
        tags.append("kwp-1000+")
    if sizing.topologia.startswith("MT"):
        tags.append("media-tension")
    return tags


def build_payload(
    *,
    factura,
    sizing,
    inv_cfg,
    costeo,
    ubicacion=None,
    proyecto: str = "",
    cliente: str = "",
) -> dict:
    """Payload JSON para POST /list/{list_id}/task."""
    nombre = proyecto or (cliente or factura.titular or "Propuesta") or "Propuesta sin nombre"
    title = f"{nombre} · {sizing.kwp_real:.0f} kWp"
    return {
        "name": title[:128],
        "description": build_descripcion(
            factura=factura, sizing=sizing, inv_cfg=inv_cfg, costeo=costeo,
            ubicacion=ubicacion, proyecto=proyecto,
        ),
        "tags": build_tags(sizing=sizing, factura=factura),
        "priority": 3,                # Normal
        "notify_all": False,
    }


def crear_task_propuesta(
    *,
    factura,
    sizing,
    inv_cfg,
    costeo,
    ubicacion=None,
    proyecto: str = "",
    cliente: str = "",
    attachments: Optional[list[Path]] = None,
    list_id: Optional[str] = None,
    api_token: Optional[str] = None,
    http_post: Optional[Callable] = None,
) -> Optional[ResultadoClickUp]:
    """Crea una task en ClickUp con el resumen de la propuesta y attachments.

    Devuelve None si:
      - falta CLICKUP_API_TOKEN
      - falta lista (ni argumento ni env var)
      - `requests` no está instalado

    No lanza excepciones por errores HTTP transitorios — los loggea y sigue,
    para que un ClickUp down no rompa la generación de la propuesta.
    """
    token = api_token or os.environ.get("CLICKUP_API_TOKEN")
    if not token:
        print("⚠ CLICKUP_API_TOKEN no configurado — skip push a ClickUp")
        return None

    lista = list_id or os.environ.get("CLICKUP_LIST_ID")
    if not lista:
        print("⚠ Sin CLICKUP_LIST_ID (ni --clickup-list) — skip push a ClickUp")
        return None

    if http_post is None:
        try:
            import requests
            http_post = requests.post
        except ImportError:
            print("⚠ `requests` no instalado — skip push a ClickUp")
            return None

    payload = build_payload(
        factura=factura, sizing=sizing, inv_cfg=inv_cfg, costeo=costeo,
        ubicacion=ubicacion, proyecto=proyecto, cliente=cliente,
    )
    headers = {"Authorization": token, "Content-Type": "application/json"}

    try:
        resp = http_post(
            f"{API_BASE}/list/{lista}/task",
            headers=headers, json=payload, timeout=15,
        )
    except Exception as e:
        print(f"⚠ ClickUp HTTP error ({e}) — task NO creada")
        return None

    if not _ok(resp):
        print(f"⚠ ClickUp respondió {_status(resp)} — task NO creada")
        return None

    data = _json(resp)
    task_id = data.get("id", "")
    task_url = data.get("url", "")

    subidos = 0
    for path in attachments or []:
        if not path.exists():
            continue
        if _subir_attachment(task_id, path, token, http_post):
            subidos += 1

    return ResultadoClickUp(task_id=task_id, task_url=task_url, attachments_subidos=subidos)


def _subir_attachment(task_id: str, path: Path, token: str, http_post: Callable) -> bool:
    """POST /task/{task_id}/attachment con multipart/form-data."""
    try:
        with path.open("rb") as f:
            resp = http_post(
                f"{API_BASE}/task/{task_id}/attachment",
                headers={"Authorization": token},
                files={"attachment": (path.name, f)},
                timeout=60,
            )
    except Exception as e:
        print(f"⚠ Falló attachment {path.name}: {e}")
        return False
    if not _ok(resp):
        print(f"⚠ Attachment {path.name} → ClickUp respondió {_status(resp)}")
        return False
    return True


# Helpers para tolerar tanto requests.Response como mocks ──────────────────────
def _ok(resp) -> bool:
    code = _status(resp)
    return 200 <= code < 300


def _status(resp) -> int:
    return getattr(resp, "status_code", 0)


def _json(resp) -> dict:
    if callable(getattr(resp, "json", None)):
        try:
            return resp.json() or {}
        except Exception:
            return {}
    return getattr(resp, "_json", {}) or {}
