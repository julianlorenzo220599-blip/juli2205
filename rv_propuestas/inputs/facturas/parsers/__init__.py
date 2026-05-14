"""Auto-importa todos los parsers de distribuidoras para activar su registro.

Orden importa: el primer detector que matchee gana. Registrar primero los más
específicos (los que tienen identificadores únicos en el texto extraído).
"""
from . import edenor   # noqa: F401
from . import edesur   # noqa: F401
from . import edesa    # noqa: F401
from . import eden     # noqa: F401
