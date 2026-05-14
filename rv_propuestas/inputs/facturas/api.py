"""Entry point del subsistema de facturas: parse_pdf, from_manual, merge_facturas."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from .llm import parse_via_llm
from .modelo import ConsumoMensual, Factura
from .pdf_text import extraer_texto
from .registry import detectar, distribuidoras_soportadas, get_parser
from .validacion import validar


def parse_pdf(
    path: str | Path,
    forzar_llm: bool = False,
    validar_salida: bool = True,
    silencioso: bool = False,
) -> Factura:
    """Parsea una factura PDF.

    Estrategia:
      1. Extraer texto.
      2. Detectar distribuidora por patrones registrados.
      3. Si hay parser específico → ejecutarlo (gratis).
      4. Si falla o no hay parser → fallback Claude API (con caché).
      5. Validar consistencia antes de devolver.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)

    texto = extraer_texto(path)
    distrib = detectar(texto)
    factura: Optional[Factura] = None

    if not forzar_llm and distrib:
        parser = get_parser(distrib)
        if parser:
            try:
                factura = parser(texto)
            except Exception as e:
                if not silencioso:
                    print(f"⚠ Parser {distrib} falló ({e}). Cayendo a LLM.")

    if factura is None:
        factura = parse_via_llm(path, texto, distribuidora_hint=distrib)

    if factura is None:
        raise RuntimeError(
            f"No se pudo parsear {path.name}. "
            f"Distribuidora detectada: {distrib or 'desconocida'}. "
            f"Parsers disponibles: {distribuidoras_soportadas()}. "
            "Configurá ANTHROPIC_API_KEY o usá from_manual() / interactivo.leer_csv()."
        )

    if validar_salida:
        res = validar(factura)
        if not res.ok:
            raise RuntimeError(
                f"Factura parseada inválida: {'; '.join(res.errores)}"
            )
        if not silencioso:
            for w in res.warnings:
                print(f"⚠ {w}")

    return factura


def from_manual(
    distribuidora: str,
    consumos_kwh: list[float],
    potencia_contratada_kw: Optional[float] = None,
    tension_suministro: str = "BT 380V",
    categoria_tarifaria: str = "T3",
    mes_inicial: str = "2024-01",
    **kwargs,
) -> Factura:
    """Construye una Factura tipeando los kWh mensuales (N valores)."""
    yyyy_s, mm_s = mes_inicial.split("-")
    yyyy, mm = int(yyyy_s), int(mm_s)
    consumos: list[ConsumoMensual] = []
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


def merge_facturas(facturas: list[Factura]) -> Factura:
    """Combina facturas del mismo suministro consolidando consumos por mes.

    Útil cuando el cliente manda 12 PDFs (uno por mes) en lugar de una factura
    T3 con histórico. Toma metadatos de la primera factura como referencia.
    """
    if not facturas:
        raise ValueError("Sin facturas para combinar")

    base = facturas[0]
    consumos_por_mes: dict[str, ConsumoMensual] = {}
    for f in facturas:
        for c in f.consumos:
            consumos_por_mes.setdefault(c.mes, c)

    ordenados = [consumos_por_mes[m] for m in sorted(consumos_por_mes.keys())]
    return Factura(
        distribuidora=base.distribuidora,
        categoria_tarifaria=base.categoria_tarifaria,
        titular=base.titular,
        nis=base.nis,
        direccion=base.direccion,
        tension_suministro=base.tension_suministro,
        potencia_contratada_kw=base.potencia_contratada_kw,
        consumos=ordenados,
        fuente=f"merge:{len(facturas)}",
    )
