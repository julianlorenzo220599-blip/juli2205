"""Extracción de texto plano de PDFs + heurísticas de escaneo."""
from __future__ import annotations

from pathlib import Path


def extraer_texto(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise RuntimeError(
            f"pypdf no disponible ({e}). Ejecutá: pip install pypdf"
        ) from e
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def parece_escaneado(texto: str, umbral_chars: int = 200) -> bool:
    """Heurística: PDFs escaneados extraen muy poco texto. Umbral conservador.

    Si está por debajo del umbral, el caller debería caer a OCR/Vision.
    """
    return len(texto.strip()) < umbral_chars
