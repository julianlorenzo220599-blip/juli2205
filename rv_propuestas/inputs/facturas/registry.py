"""Registro de parsers por distribuidora.

Cada parser se auto-registra al ser importado mediante el decorador `register`.
El registro es ordenado: los patrones se evalúan en orden de inserción, así que
parsers con detección más específica deben registrarse primero.
"""
from __future__ import annotations

import re
from typing import Callable, Optional

from .modelo import Factura

ParserFn = Callable[[str], Optional[Factura]]

_PARSERS: dict[str, ParserFn] = {}
_DETECTORES: dict[str, list[str]] = {}


def register(nombre: str, patterns: list[str]) -> Callable[[ParserFn], ParserFn]:
    """Registra un parser. Uso: `@register("EDESUR", [r"\\bEDESUR\\b", ...])`."""
    def wrap(fn: ParserFn) -> ParserFn:
        _PARSERS[nombre] = fn
        _DETECTORES[nombre] = patterns
        return fn
    return wrap


def detectar(texto: str) -> Optional[str]:
    for nombre, patterns in _DETECTORES.items():
        for pat in patterns:
            if re.search(pat, texto, re.IGNORECASE):
                return nombre
    return None


def get_parser(nombre: str) -> Optional[ParserFn]:
    return _PARSERS.get(nombre)


def distribuidoras_soportadas() -> list[str]:
    return sorted(_PARSERS.keys())
