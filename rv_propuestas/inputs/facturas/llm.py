"""Fallback con Claude API: texto (rápido/barato) o vision (PDFs escaneados).

Cachea por hash SHA-256 del PDF en `~/.rv_cache/facturas/` para evitar
re-cobrar la API key cuando se procesa la misma factura más de una vez.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Optional

from .modelo import ConsumoMensual, Factura
from .pdf_text import parece_escaneado

CACHE_DIR = Path(os.environ.get("RV_CACHE_DIR", str(Path.home() / ".rv_cache" / "facturas")))
MODELO_DEFAULT = os.environ.get("RV_LLM_MODEL", "claude-haiku-4-5-20251001")

SCHEMA_PROMPT = """Extraé los datos de esta factura eléctrica argentina y devolvé EXCLUSIVAMENTE un JSON con este schema:

{
  "distribuidora": "EDENOR|EDESUR|EPEC|EDEN|EDEA|EDES|EDESA|EDET|EDEMSA|EJESA|EDESE|COOP_<slug>|OTRA",
  "categoria_tarifaria": "T1-R|T1-R2|T1-RM|T2|T3-MD|T3-BT|T3-MT|T3-AT",
  "titular": "...",
  "nis": "...",
  "direccion": "...",
  "tension_suministro": "BT 220V|BT 380V|MT 13.2 kV|MT 33 kV",
  "potencia_contratada_kw": 30.0,
  "consumos": [
    {"mes": "YYYY-MM", "kwh_total": 1234, "kwh_pico": null, "kwh_valle": null, "potencia_pico_kw": null}
  ]
}

Reglas:
- Si la factura es de un único período, devolvé un solo elemento en "consumos".
- Si tiene tabla histórica de varios meses, devolvélos todos.
- kwh_total es energía ACTIVA (no reactiva).
- "mes" en ISO YYYY-MM corresponde al período facturado, no a la fecha de emisión.
- Devolvé números, no strings con unidades.
- Campos sin dato: null. NUNCA inventes valores.
- Cooperativas locales → distribuidora = "COOP_<slug-en-minusculas>".

Devolvé SOLO el JSON, sin explicación ni bloques markdown."""


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def _cache_get(key: str) -> Optional[dict]:
    fp = CACHE_DIR / f"{key}.json"
    if not fp.exists():
        return None
    try:
        return json.loads(fp.read_text(encoding="utf-8"))
    except Exception:
        return None


def _cache_put(key: str, data: dict) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (CACHE_DIR / f"{key}.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _from_dict(data: dict, fuente: str) -> Factura:
    return Factura(
        distribuidora=data.get("distribuidora") or "?",
        categoria_tarifaria=data.get("categoria_tarifaria") or "?",
        titular=data.get("titular") or "",
        nis=str(data.get("nis") or ""),
        direccion=data.get("direccion") or "",
        tension_suministro=data.get("tension_suministro") or "BT 380V",
        potencia_contratada_kw=data.get("potencia_contratada_kw"),
        consumos=[ConsumoMensual(**c) for c in (data.get("consumos") or [])],
        fuente=fuente,
    )


def _limpiar(content: str) -> str:
    content = content.strip()
    content = re.sub(r"^```(?:json)?\s*", "", content)
    content = re.sub(r"\s*```$", "", content)
    return content


def parse_via_llm(
    pdf_path: Path,
    texto: str,
    distribuidora_hint: Optional[str] = None,
    modelo: str = MODELO_DEFAULT,
) -> Optional[Factura]:
    """Llama a Claude para parsear la factura. Devuelve None si no hay API key
    o el SDK no está instalado (el caller debe decidir qué hacer).
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        from anthropic import Anthropic
    except ImportError:
        return None

    cache_key = _sha256(pdf_path)
    cached = _cache_get(cache_key)
    if cached:
        return _from_dict(cached, fuente="llm:cache")

    client = Anthropic(api_key=api_key)
    hint = f"\n\nHint de distribuidora detectada: {distribuidora_hint or 'desconocida'}"

    if parece_escaneado(texto):
        pdf_b64 = base64.standard_b64encode(pdf_path.read_bytes()).decode("ascii")
        msg = client.messages.create(
            model=modelo,
            max_tokens=4000,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_b64,
                        },
                    },
                    {"type": "text", "text": SCHEMA_PROMPT + hint},
                ],
            }],
        )
    else:
        prompt = f"{SCHEMA_PROMPT}{hint}\n\nFactura (texto extraído):\n---\n{texto[:20000]}\n---"
        msg = client.messages.create(
            model=modelo,
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )

    raw = _limpiar(msg.content[0].text)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None

    _cache_put(cache_key, data)
    return _from_dict(data, fuente="llm")
