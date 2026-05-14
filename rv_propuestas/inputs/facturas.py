"""Ingesta de facturas eléctricas — parser híbrido con fallback LLM.

Estrategia:
  1. Detectar distribuidora del PDF.
  2. Si hay parser específico → usarlo (rápido, sin costo).
  3. Si falla o no hay parser → fallback a Claude API (vision o texto).
  4. Manual: permitir construcción directa para casos sin PDF (datos tipeados).
"""
from __future__ import annotations

import re
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Import de pypdf es lazy: solo se carga al parsear un PDF real. Esto evita
# arrastrar la dependencia `cryptography` si el caller usa from_manual() o
# construye Factura directamente.


@dataclass
class ConsumoMensual:
    mes: str                # "2024-01", "2024-02", ...
    kwh_total: float
    kwh_pico: Optional[float] = None
    kwh_valle: Optional[float] = None
    kwh_resto: Optional[float] = None
    potencia_pico_kw: Optional[float] = None


@dataclass
class Factura:
    distribuidora: str
    categoria_tarifaria: str          # T1-R, T2, T3-MD, T3-BT, T3-MT, etc.
    titular: str
    nis: str                          # Número de identificación de suministro
    direccion: str
    tension_suministro: str           # "BT 380V" / "MT 13.2 kV"
    potencia_contratada_kw: Optional[float]
    consumos: list[ConsumoMensual] = field(default_factory=list)
    fuente: str = "unknown"           # "parser:edenor" / "llm" / "manual"

    @property
    def consumo_anual_kwh(self) -> float:
        return sum(c.kwh_total for c in self.consumos)

    @property
    def consumo_mensual_promedio(self) -> float:
        if not self.consumos:
            return 0.0
        return self.consumo_anual_kwh / len(self.consumos)

    @property
    def potencia_pico_max(self) -> Optional[float]:
        picos = [c.potencia_pico_kw for c in self.consumos if c.potencia_pico_kw]
        return max(picos) if picos else None


# ──────────────────────────────────────────────────────────────────────────────
# DETECCIÓN DE DISTRIBUIDORA
# ──────────────────────────────────────────────────────────────────────────────
DISTRIBUIDORAS_PATTERNS = {
    "EDENOR":  [r"\bEDENOR\b", r"Empresa Distribuidora.*Norte"],
    "EDESUR":  [r"\bEDESUR\b", r"Empresa Distribuidora.*Sur"],
    "EPEC":    [r"\bEPEC\b",   r"Empresa Provincial.*Energía Córdoba"],
    "EDEN":    [r"\bEDEN\s+S\.?A\.?\b", r"Empresa Distribuidora.*Norte.*BA"],
    "EDEA":    [r"\bEDEA\b",   r"Empresa Distribuidora.*Atlántica"],
    "EDESA":   [r"\bEDESA\b",  r"Empresa Distribuidora.*Salta"],
    "EDET":    [r"\bEDET\b",   r"Empresa Distribuidora.*Tucumán"],
    "EDEMSA":  [r"\bEDEMSA\b", r"Empresa Distribuidora.*Mendoza"],
    "EJESA":   [r"\bEJESA\b",  r"Empresa Jujeña"],
    "EDESE":   [r"\bEDESE\b",  r"Empresa Distribuidora.*Santiago"],
}


def detectar_distribuidora(texto: str) -> Optional[str]:
    for nombre, patterns in DISTRIBUIDORAS_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, texto, re.IGNORECASE):
                return nombre
    return None


def extraer_texto_pdf(path: Path) -> str:
    """Extrae texto plano de un PDF usando pypdf (import lazy)."""
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise RuntimeError(f"pypdf no disponible ({e}). Ejecutá: pip install pypdf") from e
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


# ──────────────────────────────────────────────────────────────────────────────
# PARSERS POR DISTRIBUIDORA (MVP: EDENOR + plantilla genérica)
# ──────────────────────────────────────────────────────────────────────────────
def _parse_edenor(texto: str) -> Optional[Factura]:
    """Parser para facturas EDENOR. Esqueleto: requiere ajuste contra PDFs reales."""
    nis_match = re.search(r"NIS\s*[:\-]?\s*(\d{6,10})", texto)
    cat_match = re.search(r"Tarifa[:\s]+(T[1-3][A-Z\-]*\d*)", texto, re.IGNORECASE)
    pot_match = re.search(r"Potencia\s+Contratada[:\s]+([\d.,]+)\s*kW", texto, re.IGNORECASE)

    consumos = []
    for m in re.finditer(
        r"(\d{2}/\d{4})\s+(?:.*?)\s+(\d{1,7}(?:[.,]\d{1,3})?)\s*kWh",
        texto,
    ):
        mes_raw = m.group(1)         # "01/2024"
        kwh = float(m.group(2).replace(".", "").replace(",", "."))
        mm, yyyy = mes_raw.split("/")
        consumos.append(ConsumoMensual(mes=f"{yyyy}-{mm}", kwh_total=kwh))

    if not nis_match and not consumos:
        return None

    return Factura(
        distribuidora="EDENOR",
        categoria_tarifaria=cat_match.group(1) if cat_match else "T?",
        titular="",
        nis=nis_match.group(1) if nis_match else "",
        direccion="",
        tension_suministro="BT 380V",
        potencia_contratada_kw=float(pot_match.group(1).replace(",", ".")) if pot_match else None,
        consumos=consumos,
        fuente="parser:edenor",
    )


PARSERS = {
    "EDENOR": _parse_edenor,
    # TODO: agregar EDESUR, EPEC, etc. a medida que tengamos PDFs de muestra
}


# ──────────────────────────────────────────────────────────────────────────────
# FALLBACK LLM (Claude API)
# ──────────────────────────────────────────────────────────────────────────────
def _parse_llm(texto: str, distribuidora_hint: Optional[str] = None) -> Optional[Factura]:
    """Fallback usando Claude API para parseo robusto de cualquier distribuidora.

    Requiere ANTHROPIC_API_KEY en el entorno. Si no está configurada o el
    SDK no está instalado, devuelve None y el caller debe pedir entrada manual.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        from anthropic import Anthropic
    except ImportError:
        return None

    prompt = f"""Extraé los datos de esta factura eléctrica argentina y devolvelos en JSON.

Schema esperado:
{{
  "distribuidora": "EDENOR|EDESUR|EPEC|...",
  "categoria_tarifaria": "T1-R|T2|T3-MD|T3-BT|T3-MT",
  "titular": "...",
  "nis": "...",
  "direccion": "...",
  "tension_suministro": "BT 380V|MT 13.2 kV|MT 33 kV",
  "potencia_contratada_kw": 30.0,
  "consumos": [
    {{"mes": "2024-01", "kwh_total": 12345, "kwh_pico": null, "kwh_valle": null, "potencia_pico_kw": null}}
  ]
}}

Hint de distribuidora: {distribuidora_hint or "desconocida"}

Factura:
---
{texto[:15000]}
---

Devolvé SOLO el JSON, sin explicación ni markdown."""

    client = Anthropic(api_key=api_key)
    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    content = resp.content[0].text.strip()
    # Limpiar fences de markdown si vinieran
    content = re.sub(r"^```(?:json)?\s*", "", content)
    content = re.sub(r"\s*```$", "", content)

    import json
    data = json.loads(content)
    return Factura(
        distribuidora=data.get("distribuidora", "?"),
        categoria_tarifaria=data.get("categoria_tarifaria", "?"),
        titular=data.get("titular", ""),
        nis=data.get("nis", ""),
        direccion=data.get("direccion", ""),
        tension_suministro=data.get("tension_suministro", "BT 380V"),
        potencia_contratada_kw=data.get("potencia_contratada_kw"),
        consumos=[ConsumoMensual(**c) for c in data.get("consumos", [])],
        fuente="llm",
    )


# ──────────────────────────────────────────────────────────────────────────────
# ENTRY POINT PÚBLICO
# ──────────────────────────────────────────────────────────────────────────────
def parse_pdf(path: str | Path) -> Factura:
    """Parsea una factura PDF: parser específico → fallback LLM → error."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)

    texto = extraer_texto_pdf(path)
    distrib = detectar_distribuidora(texto)

    if distrib and distrib in PARSERS:
        factura = PARSERS[distrib](texto)
        if factura:
            return factura

    factura = _parse_llm(texto, distribuidora_hint=distrib)
    if factura:
        return factura

    raise RuntimeError(
        f"No se pudo parsear la factura {path.name}. "
        f"Distribuidora detectada: {distrib or 'desconocida'}. "
        f"Configurá ANTHROPIC_API_KEY o cargá los datos manualmente con Factura(...)."
    )


def from_manual(
    distribuidora: str,
    consumos_kwh: list[float],
    potencia_contratada_kw: Optional[float] = None,
    tension_suministro: str = "BT 380V",
    categoria_tarifaria: str = "T3",
    mes_inicial: str = "2024-01",
    **kwargs,
) -> Factura:
    """Construye una Factura tipeando los kWh mensuales a mano (12 valores)."""
    import calendar
    yyyy, mm = mes_inicial.split("-")
    yyyy, mm = int(yyyy), int(mm)
    consumos = []
    for i, kwh in enumerate(consumos_kwh):
        m_idx = (mm - 1 + i) % 12 + 1
        y_idx = yyyy + (mm - 1 + i) // 12
        consumos.append(ConsumoMensual(mes=f"{y_idx:04d}-{m_idx:02d}", kwh_total=kwh))
    return Factura(
        distribuidora=distribuidora,
        categoria_tarifaria=categoria_tarifaria,
        titular=kwargs.get("titular", ""),
        nis=kwargs.get("nis", ""),
        direccion=kwargs.get("direccion", ""),
        tension_suministro=tension_suministro,
        potencia_contratada_kw=potencia_contratada_kw,
        consumos=consumos,
        fuente="manual",
    )
