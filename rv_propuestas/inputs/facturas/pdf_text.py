"""Extracción de texto plano de PDFs + heurísticas de escaneo.

Estrategia: probamos primero pdftotext (poppler) cuando está en PATH porque
preserva mejor el layout en facturas tabulares, y caemos a pypdf si no.
Si ninguno está disponible, ahí sí abortamos.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def _via_pdftotext(path: Path) -> str | None:
    if not shutil.which("pdftotext"):
        return None
    try:
        out = subprocess.run(
            ["pdftotext", "-layout", str(path), "-"],
            capture_output=True, timeout=30, check=True,
        )
        return out.stdout.decode("utf-8", errors="replace")
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        return None


def _via_pypdf(path: Path) -> str:
    from pypdf import PdfReader
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def extraer_texto(path: Path) -> str:
    texto = _via_pdftotext(path)
    if texto is not None and texto.strip():
        return texto
    try:
        return _via_pypdf(path)
    except ImportError as e:
        raise RuntimeError(
            f"Sin extractores de PDF disponibles ({e}). "
            "Instalá pypdf (pip install pypdf) o poppler-utils (apt install poppler-utils)."
        ) from e


def parece_escaneado(texto: str, umbral_chars: int = 200) -> bool:
    """Heurística: PDFs escaneados extraen muy poco texto. Umbral conservador.

    Si está por debajo del umbral, el caller debería caer a OCR/Vision.
    """
    return len(texto.strip()) < umbral_chars
