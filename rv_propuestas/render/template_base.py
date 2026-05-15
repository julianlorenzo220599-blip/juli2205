"""Generador de template `.pptx` base — versión minimalista con identidad RV.

Diseño focal:
  - Fondo crema/marfil neutro (descansa la vista, lujoso, no satura).
  - Acentos cromáticos sólo de los colores del logo: verde lime + azul.
  - Líneas finas como separadores, KPIs sin caja, mucho espacio negativo.
  - Tipografía Outfit Light dominante; Bold sólo para enfatizar.

Paleta (Manual de Marca RV oct/2025):
  Crema                #FAF7F0  — fondo principal
  Blanco hueso         #FCFAF5  — fondo alterno (slides "respiro")
  Azul oscuro          #1A1F3A  — texto principal
  Gris cálido          #6E6A60  — body / bajadas
  Gris suave           #C8C2B5  — líneas separadoras
  Verde lime           #A6FF00  — acento (números, dots, underlines)
  Azul corporativo     #1B39CE  — títulos, énfasis, líneas activas

Los logos positivo y negativo del manual están en ./assets/. Como el fondo
crema es claro, usamos el logo positivo en todas las slides.
"""
from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt


# ──────────────────────────────────────────────────────────────────────────────
# PALETA — minimalista, fondo crema + acentos del logo
# ──────────────────────────────────────────────────────────────────────────────
CREMA = RGBColor(0xFA, 0xF7, 0xF0)
BLANCO_HUESO = RGBColor(0xFC, 0xFA, 0xF5)
AZUL_OSCURO = RGBColor(0x1A, 0x1F, 0x3A)          # texto principal
GRIS_CALIDO = RGBColor(0x6E, 0x6A, 0x60)          # bajadas
GRIS_SUAVE = RGBColor(0xC8, 0xC2, 0xB5)           # líneas separadoras
VERDE_LIME = RGBColor(0xA6, 0xFF, 0x00)           # acento logo
AZUL_LOGO = RGBColor(0x1B, 0x39, 0xCE)            # acento logo

FUENTE = "Outfit"

_ASSETS = Path(__file__).parent / "assets"
LOGO_POSITIVO = _ASSETS / "logo_rv_positivo.png"


def crear_template_base(output_path: str | Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    prs = Presentation()
    prs.slide_width = Inches(13.33)
    prs.slide_height = Inches(7.5)
    blank = prs.slide_layouts[6] if len(prs.slide_layouts) > 6 else prs.slide_layouts[-1]

    _slide_portada(prs.slides.add_slide(blank))
    _slide_contenidos(prs.slides.add_slide(blank))
    _slide_analisis_consumo(prs.slides.add_slide(blank))
    _slide_historico_consumo(prs.slides.add_slide(blank))
    _slide_solucion(prs.slides.add_slide(blank))
    _slide_generacion_vs_consumo(prs.slides.add_slide(blank))
    _slide_inversion(prs.slides.add_slide(blank))
    _slide_proximos_pasos(prs.slides.add_slide(blank))

    prs.save(str(output_path))
    return output_path


# ──────────────────────────────────────────────────────────────────────────────
# SLIDES
# ──────────────────────────────────────────────────────────────────────────────
def _slide_portada(slide):
    _fondo(slide, CREMA)
    _logo(slide, left=0.7, top=0.6, height=0.9)

    # Acento mínimo: línea fina verde lime arriba
    _linea(slide, left=0.7, top=2.0, width=1.2, color=VERDE_LIME, weight=2.5)

    _texto(slide, "PROPUESTA TÉCNICO-ECONÓMICA",
           left=0.7, top=2.3, width=12, size=12,
           color=GRIS_CALIDO, bold=True, letter_spacing=2)

    # Título grande Light + última palabra acento
    _titulo_dual(slide, "Planta solar", "fotovoltaica.",
                 left=0.7, top=2.9, size=64,
                 color1=AZUL_OSCURO, color2=AZUL_LOGO, bold2=False)

    # Datos clave en línea, separados por punto medio
    _texto(slide, "{{kwp|kwp}}    ·    {{cliente}}",
           left=0.7, top=5.2, width=12, size=24,
           color=AZUL_OSCURO, bold=False)
    _texto(slide, "{{proyecto}}",
           left=0.7, top=5.9, width=12, size=16, color=GRIS_CALIDO)

    # Línea fina inferior + fecha
    _linea(slide, left=0.7, top=6.85, width=2.0, color=AZUL_LOGO, weight=1)
    _texto(slide, "{{fecha}}",
           left=0.7, top=6.95, width=12, size=11, color=GRIS_CALIDO,
           letter_spacing=2)


def _slide_contenidos(slide):
    _fondo(slide, CREMA)
    _logo(slide, left=11.5, top=0.5, height=0.55)

    _texto(slide, "ÍNDICE",
           left=0.7, top=0.7, width=10, size=11,
           color=GRIS_CALIDO, bold=True, letter_spacing=3)
    _titulo_dual(slide, "Lo que vas a", "ver.",
                 left=0.7, top=1.1, size=48,
                 color1=AZUL_OSCURO, color2=AZUL_LOGO)

    items = [
        ("01", "Análisis del consumo"),
        ("02", "Solución técnica propuesta"),
        ("03", "Generación esperada"),
        ("04", "Inversión y condiciones"),
        ("05", "Próximos pasos"),
    ]
    for i, (num, txt) in enumerate(items):
        y = 2.9 + i * 0.75
        # Línea fina divisoria
        _linea(slide, left=0.7, top=y - 0.1, width=12.0,
               color=GRIS_SUAVE, weight=0.5)
        _texto(slide, num, left=0.7, top=y, width=1.0, size=18,
               bold=True, color=VERDE_LIME)
        _texto(slide, txt, left=2.0, top=y + 0.03, width=10, size=18,
               color=AZUL_OSCURO)


def _slide_analisis_consumo(slide):
    _fondo(slide, CREMA)
    _header(slide, "01", "Análisis del", "consumo.")

    _kpi_min(slide, 0.7, 2.3,  "Cliente",            "{{cliente}}",          size_value=18)
    _kpi_min(slide, 4.0, 2.3,  "Distribuidora",      "{{distribuidora}}",    size_value=18)
    _kpi_min(slide, 7.3, 2.3,  "Categoría tarifaria", "{{categoria_tarifaria}}", size_value=18)
    _kpi_min(slide, 10.6, 2.3, "NIS",                "{{nis}}",              size_value=16)

    _kpi_min(slide, 0.7, 4.3,  "Consumo anual",      "{{consumo_anual|kwh}}",
             accent=AZUL_LOGO, size_value=22)
    _kpi_min(slide, 4.0, 4.3,  "Promedio mensual",   "{{consumo_mensual_promedio|kwh}}",
             size_value=20)
    _kpi_min(slide, 7.3, 4.3,  "Tensión",            "{{tension}}",          size_value=20)
    _kpi_min(slide, 10.6, 4.3, "Pot. contratada",    "{{potencia_contratada|0}} kW",
             size_value=20)

    _texto(slide, "DOMICILIO DEL SUMINISTRO",
           left=0.7, top=6.3, width=12, size=10,
           color=GRIS_CALIDO, bold=True, letter_spacing=2)
    _texto(slide, "{{direccion}}",
           left=0.7, top=6.6, width=12, size=13, color=AZUL_OSCURO)


def _slide_historico_consumo(slide):
    _fondo(slide, BLANCO_HUESO)
    _header(slide, "02", "Histórico", "mensual.")
    _texto(slide,
           "Consumos extraídos de la factura del cliente — 12 meses.",
           left=0.7, top=2.2, width=12, size=13, color=GRIS_CALIDO)
    _chart_marker(slide, "consumo_mensual",
                  left=0.7, top=2.8, width=11.9, height=4.0)


def _slide_solucion(slide):
    _fondo(slide, CREMA)
    _header(slide, "03", "Solución técnica", "propuesta.")

    _kpi_min(slide, 0.7, 2.3,  "Potencia DC",       "{{kwp|kwp}}",
             accent=AZUL_LOGO, size_value=24)
    _kpi_min(slide, 4.0, 2.3,  "Generación anual",  "{{generacion_anual|kwh}}",
             accent=VERDE_LIME, size_value=22)
    _kpi_min(slide, 7.3, 2.3,  "Cobertura",         "{{cobertura_pct|pct1}}",
             size_value=22)
    _kpi_min(slide, 10.6, 2.3, "Yield específico",  "{{yield_especifico|0}} kWh/kWp",
             size_value=16)

    _texto(slide, "EQUIPAMIENTO PRINCIPAL",
           left=0.7, top=4.4, width=12, size=10,
           color=GRIS_CALIDO, bold=True, letter_spacing=2)
    _linea(slide, left=0.7, top=4.7, width=12.0, color=GRIS_SUAVE, weight=0.5)

    bullets = [
        "{{n_paneles}} × módulos TCL TOPCon Bifacial {{wp_panel}} Wp",
        "{{n_inversores}} × {{inversor_descripcion}}",
        "Smart meter GoodWe + estructura + balance of system completo",
        "Ingeniería, gestión ante {{distribuidora}}, puesta en marcha",
    ]
    for i, b in enumerate(bullets):
        y = 4.95 + i * 0.4
        _bullet_dot(slide, left=0.75, top=y + 0.07, color=VERDE_LIME)
        _texto(slide, b, left=1.05, top=y, width=12, size=14,
               color=AZUL_OSCURO)


def _slide_generacion_vs_consumo(slide):
    _fondo(slide, BLANCO_HUESO)
    _header(slide, "04", "Generación vs", "consumo.")
    _texto(slide,
           "Cobertura de {{cobertura_pct|pct1}} sobre un consumo anual de "
           "{{consumo_anual|kwh}}.",
           left=0.7, top=2.2, width=12.5, size=13, color=GRIS_CALIDO)
    _chart_marker(slide, "generacion_vs_consumo",
                  left=0.7, top=2.8, width=8.0, height=4.0)
    _chart_marker(slide, "cobertura",
                  left=9.0, top=2.8, width=3.6, height=4.0)


def _slide_inversion(slide):
    _fondo(slide, CREMA)
    _header(slide, "05", "Inversión", "llave en mano.")

    # TOTAL destacado a la izquierda, sin caja
    _texto(slide, "TOTAL DE LA INVERSIÓN",
           left=0.7, top=2.3, width=8, size=11,
           color=GRIS_CALIDO, bold=True, letter_spacing=2)
    _texto(slide, "{{total_usd|usd}}",
           left=0.7, top=2.7, width=8, size=64,
           color=AZUL_LOGO, bold=False, height=1.2)
    _linea(slide, left=0.7, top=3.95, width=4.0, color=VERDE_LIME, weight=3)
    _texto(slide, "{{usd_kwp|0}} USD por kWp instalado",
           left=0.7, top=4.1, width=8, size=14, color=GRIS_CALIDO)

    # Desglose a la derecha
    _texto(slide, "DESGLOSE",
           left=9.0, top=2.3, width=4, size=11,
           color=GRIS_CALIDO, bold=True, letter_spacing=2)
    _kpi_inline(slide, 9.0, 2.7,  "Subtotal sin IVA", "{{neto_usd|usd}}")
    _kpi_inline(slide, 9.0, 3.25, "IVA diferencial",   "{{iva_usd|usd}}")
    _kpi_inline(slide, 9.0, 3.8,  "USD/kWp",           "{{usd_kwp|0}}")

    # Condiciones al pie
    _texto(slide, "CONDICIONES COMERCIALES",
           left=0.7, top=5.1, width=12, size=10,
           color=GRIS_CALIDO, bold=True, letter_spacing=2)
    _linea(slide, left=0.7, top=5.4, width=12.0, color=GRIS_SUAVE, weight=0.5)
    cond = [
        "Validez de oferta: 30 días corridos",
        "Forma de pago: 50% anticipo · 40% acopio · 10% PEM",
        "Plazo de ejecución: 60-90 días desde aprobación",
        "Incluye ingeniería, materiales, instalación, gestión y puesta en marcha",
    ]
    for i, c in enumerate(cond):
        y = 5.6 + i * 0.34
        _bullet_dot(slide, left=0.75, top=y + 0.06, color=AZUL_LOGO)
        _texto(slide, c, left=1.05, top=y, width=12, size=12, color=AZUL_OSCURO)


def _slide_proximos_pasos(slide):
    _fondo(slide, CREMA)
    _logo(slide, left=11.5, top=0.5, height=0.55)
    _texto(slide, "CIERRE",
           left=0.7, top=0.7, width=10, size=11,
           color=GRIS_CALIDO, bold=True, letter_spacing=3)
    _titulo_dual(slide, "Próximos", "pasos.",
                 left=0.7, top=1.1, size=48,
                 color1=AZUL_OSCURO, color2=AZUL_LOGO)

    pasos = [
        ("01", "Visita técnica al sitio y relevamiento del PDI"),
        ("02", "Ingeniería de detalle + simulación PVSyst"),
        ("03", "Gestión de habilitación ante {{distribuidora}}"),
        ("04", "Provisión de equipos y montaje"),
        ("05", "Puesta en marcha, capacitación y entrega"),
    ]
    for i, (num, txt) in enumerate(pasos):
        y = 2.7 + i * 0.6
        _linea(slide, left=0.7, top=y - 0.08, width=12.0,
               color=GRIS_SUAVE, weight=0.5)
        _texto(slide, num, left=0.7, top=y, width=1.0, size=16,
               bold=True, color=VERDE_LIME)
        _texto(slide, txt, left=2.0, top=y + 0.03, width=11, size=15,
               color=AZUL_OSCURO)

    # Contacto al pie en una sola línea minimalista
    _linea(slide, left=0.7, top=6.7, width=2.0, color=VERDE_LIME, weight=2)
    _texto(slide, "Julián Lorenzo  ·  julian.lorenzo@radiovictoria.com.ar  ·  +54 11 4407-6575",
           left=0.7, top=6.85, width=12.5, size=11, color=GRIS_CALIDO)


# ──────────────────────────────────────────────────────────────────────────────
# COMPONENTES VISUALES
# ──────────────────────────────────────────────────────────────────────────────
def _header(slide, num: str, parte1: str, parte2: str) -> None:
    """Header común para slides de contenido: logo + número de sección + título dual."""
    _logo(slide, left=11.5, top=0.5, height=0.55)
    _texto(slide, num, left=0.7, top=0.7, width=1, size=11,
           bold=True, color=VERDE_LIME, letter_spacing=3)
    _texto(slide, "SECCIÓN", left=1.1, top=0.7, width=4, size=11,
           color=GRIS_CALIDO, bold=True, letter_spacing=3)
    _titulo_dual(slide, parte1, parte2,
                 left=0.7, top=1.1, size=42,
                 color1=AZUL_OSCURO, color2=AZUL_LOGO, bold2=False)
    # Línea fina horizontal al final del header
    _linea(slide, left=0.7, top=2.0, width=12.0, color=GRIS_SUAVE, weight=0.5)


def _fondo(slide, color: RGBColor) -> None:
    bg = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.33), Inches(7.5),
    )
    bg.fill.solid()
    bg.fill.fore_color.rgb = color
    bg.line.fill.background()
    spTree = bg._element.getparent()
    spTree.remove(bg._element)
    spTree.insert(2, bg._element)


def _logo(slide, *, left: float, top: float, height: float) -> None:
    if LOGO_POSITIVO.exists():
        slide.shapes.add_picture(
            str(LOGO_POSITIVO), Inches(left), Inches(top),
            height=Inches(height),
        )


def _linea(slide, *, left: float, top: float, width: float,
           color: RGBColor, weight: float = 1.0) -> None:
    line = slide.shapes.add_connector(
        1,  # straight line
        Inches(left), Inches(top),
        Inches(left + width), Inches(top),
    )
    line.line.color.rgb = color
    line.line.width = Pt(weight)


def _bullet_dot(slide, *, left: float, top: float,
                color: RGBColor, size: float = 0.13) -> None:
    dot = slide.shapes.add_shape(
        MSO_SHAPE.OVAL,
        Inches(left), Inches(top), Inches(size), Inches(size),
    )
    dot.fill.solid()
    dot.fill.fore_color.rgb = color
    dot.line.fill.background()


def _texto(slide, texto: str, *, left: float, top: float, width: float = 6.0,
           height: float = 0.5, size: int = 14, bold: bool = False,
           color: RGBColor = AZUL_OSCURO, letter_spacing: int = 0) -> None:
    box = slide.shapes.add_textbox(
        Inches(left), Inches(top), Inches(width), Inches(height),
    )
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0)
    tf.margin_top = Inches(0)
    p = tf.paragraphs[0]
    r = p.add_run()
    r.text = texto
    _aplicar_fuente(r, size=size, color=color, bold=bold,
                    letter_spacing=letter_spacing)


def _titulo_dual(slide, parte1: str, parte2: str, *, left: float, top: float,
                 size: int = 48, color1: RGBColor = AZUL_OSCURO,
                 color2: RGBColor = AZUL_LOGO, bold2: bool = False) -> None:
    """Título 'Light + Light' o 'Light + Bold' con palabra acento al final."""
    box = slide.shapes.add_textbox(
        Inches(left), Inches(top), Inches(12.5), Inches(size * 0.022 + 0.4),
    )
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0)
    p = tf.paragraphs[0]
    r1 = p.add_run()
    r1.text = parte1 + " "
    _aplicar_fuente(r1, size=size, color=color1, bold=False)
    r2 = p.add_run()
    r2.text = parte2
    _aplicar_fuente(r2, size=size, color=color2, bold=bold2)


def _kpi_min(slide, left: float, top: float, label: str, value: str,
             *, size_value: int = 22, accent: RGBColor = AZUL_OSCURO) -> None:
    """KPI minimalista: label tiny en gris + valor grande Light + underline color accent."""
    # Label en uppercase, tracking amplio
    _texto(slide, label.upper(),
           left=left, top=top, width=3.2, size=9,
           color=GRIS_CALIDO, bold=True, letter_spacing=2)
    # Underline fina
    _linea(slide, left=left, top=top + 0.32,
           width=0.5, color=GRIS_SUAVE, weight=0.5)
    # Valor grande Light
    _texto(slide, value,
           left=left, top=top + 0.45, width=3.2, size=size_value,
           color=accent, bold=False, height=0.8)


def _kpi_inline(slide, left: float, top: float, label: str, value: str) -> None:
    """KPI inline (label izq + valor der) para el desglose de inversión."""
    _texto(slide, label, left=left, top=top, width=2.5, size=12,
           color=GRIS_CALIDO)
    _texto(slide, value, left=left + 1.8, top=top, width=2.5, size=14,
           color=AZUL_OSCURO, bold=True)


def _chart_marker(slide, key: str, *, left: float, top: float,
                  width: float, height: float) -> None:
    """Placeholder minimalista para chart — solo línea fina superior + texto centrado."""
    # Línea fina arriba
    _linea(slide, left=left, top=top, width=width,
           color=GRIS_SUAVE, weight=0.5)
    # Texto del marker centrado
    box = slide.shapes.add_textbox(
        Inches(left), Inches(top + height / 2 - 0.2),
        Inches(width), Inches(0.4),
    )
    tf = box.text_frame
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = "{{chart:" + key + "}}"
    _aplicar_fuente(r, size=12, color=GRIS_SUAVE, bold=True)
    # Línea fina abajo
    _linea(slide, left=left, top=top + height, width=width,
           color=GRIS_SUAVE, weight=0.5)


def _aplicar_fuente(run, *, size: int, color: RGBColor, bold: bool,
                    letter_spacing: int = 0) -> None:
    run.font.name = FUENTE
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    if letter_spacing:
        from pptx.oxml.ns import qn
        rPr = run._r.get_or_add_rPr()
        rPr.set("spc", str(letter_spacing * 100))
