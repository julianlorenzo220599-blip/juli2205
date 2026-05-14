"""Subsistema de ingesta de facturas eléctricas.

Uso típico:
    from rv_propuestas.inputs.facturas import parse_pdf, from_manual, Factura

    factura = parse_pdf("factura_edesur.pdf")
    print(factura.distribuidora, factura.consumo_anual_kwh)

Para agregar una distribuidora nueva:
    1. Crear `rv_propuestas/inputs/facturas/parsers/<nombre>.py`
    2. Implementar `parse(texto: str) -> Optional[Factura]` decorado con
       `@register("NOMBRE", [patron1, patron2])` desde `..registry`.
    3. Importarlo en `parsers/__init__.py`.
"""
from .api import from_manual, merge_facturas, parse_pdf
from .modelo import ConsumoMensual, Factura
from .registry import distribuidoras_soportadas
from .validacion import validar

# Importa los parsers concretos (efecto colateral: se auto-registran).
from . import parsers  # noqa: F401, E402

__all__ = [
    "ConsumoMensual",
    "Factura",
    "parse_pdf",
    "from_manual",
    "merge_facturas",
    "distribuidoras_soportadas",
    "validar",
]
