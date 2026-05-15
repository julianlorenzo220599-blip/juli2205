"""Generador de template `.pptx` base con todos los placeholders del sistema.

El diseñador de RV abre el archivo generado en PowerPoint, restyla colores,
tipografías y logos, y lo usa como template productivo. Los placeholders
`{{...}}` y los marcadores `{{chart:...}}` ya están ubicados — el diseñador
solo se encarga de la identidad visual.

Uso:
    py -m rv_propuestas.cli crear-template-base --output ./template_rv.pptx
"""
from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Inches, Pt


# Paleta provisoria — el diseñador debería ajustar al identitario RV.
_AZUL = RGBColor(0x1F, 0x4E, 0x78)
_GRIS = RGBColor(0x59, 0x59, 0x59)
_NARANJA = RGBColor(0xED, 0x7D, 0x31)
_FONDO = RGBColor(0xF2, 0xF2, 0xF2)
_VERDE = RGBColor(0x4E, 0xA1, 0x4E)


def crear_template_base(output_path: str | Path) -> Path:
    """Genera un `.pptx` base con 7 slides y todos los placeholders cableados."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    prs = Presentation()
    prs.slide_width = Inches(13.33)
    prs.slide_height = Inches(7.5)
    blank = prs.slide_layouts[6] if len(prs.slide_layouts) > 6 else prs.slide_layouts[-1]

    _slide_portada(prs.slides.add_slide(blank))
    _slide_analisis_consumo(prs.slides.add_slide(blank))
    _slide_historico_consumo(prs.slides.add_slide(blank))
    _slide_solucion(prs.slides.add_slide(blank))
    _slide_generacion_vs_consumo(prs.slides.add_slide(blank))
    _slide_inversion(prs.slides.add_slide(blank))
    _slide_proximos_pasos(prs.slides.add_slide(blank))

    prs.save(str(output_path))
    return output_path


# ──────────────────────────────────────────────────────────────────────────────
# Slides
# ──────────────────────────────────────────────────────────────────────────────
def _slide_portada(slide):
    _add_text(slide, "RV ENERGÍA", left=0.5, top=0.4, width=12, size=14,
              bold=True, color=_GRIS)
    _add_text(slide, "Propuesta Técnico-Económica", left=0.5, top=2.0,
              width=12, size=36, bold=True, color=_AZUL)
    _add_text(slide, "Planta Solar Fotovoltaica", left=0.5, top=2.9,
              width=12, size=22, color=_GRIS)

    _add_text(slide, "{{kwp|kwp}}", left=0.5, top=3.8, width=12,
              size=48, bold=True, color=_NARANJA)
    _add_text(slide, "Cliente: {{cliente}}", left=0.5, top=5.0,
              width=12, size=20, color=_GRIS)
    _add_text(slide, "Proyecto: {{proyecto}}", left=0.5, top=5.5,
              width=12, size=20, color=_GRIS)
    _add_text(slide, "{{fecha}}", left=0.5, top=6.8, width=12,
              size=14, color=_GRIS)


def _slide_analisis_consumo(slide):
    _add_titulo(slide, "Análisis del consumo eléctrico")

    _add_kpi(slide, 0.5, 1.5, "Cliente",         "{{cliente}}", size_value=20)
    _add_kpi(slide, 4.0, 1.5, "Distribuidora",   "{{distribuidora}}", size_value=20)
    _add_kpi(slide, 7.5, 1.5, "Categoría",       "{{categoria_tarifaria}}", size_value=20)
    _add_kpi(slide, 11.0, 1.5, "NIS",            "{{nis}}", size_value=18)

    _add_kpi(slide, 0.5, 3.5, "Consumo anual",       "{{consumo_anual|kwh}}")
    _add_kpi(slide, 4.0, 3.5, "Promedio mensual",    "{{consumo_mensual_promedio|kwh}}")
    _add_kpi(slide, 7.5, 3.5, "Tensión",             "{{tension}}")
    _add_kpi(slide, 11.0, 3.5, "Pot. contratada",     "{{potencia_contratada|0}} kW")

    _add_text(slide, "Domicilio: {{direccion}}", left=0.5, top=5.8,
              width=12, size=14, color=_GRIS)


def _slide_historico_consumo(slide):
    _add_titulo(slide, "Histórico mensual de consumo")
    _add_text(slide,
              "Datos extraídos directamente de la factura eléctrica del cliente.",
              left=0.5, top=1.0, width=12, size=14, color=_GRIS)
    _add_chart_marker(slide, "consumo_mensual",
                      left=1.0, top=1.8, width=11.3, height=4.8)


def _slide_solucion(slide):
    _add_titulo(slide, "Solución propuesta")

    _add_kpi(slide, 0.5, 1.5, "Potencia DC",       "{{kwp|kwp}}", color=_NARANJA)
    _add_kpi(slide, 4.0, 1.5, "Generación anual",  "{{generacion_anual|kwh}}")
    _add_kpi(slide, 7.5, 1.5, "Cobertura",         "{{cobertura_pct|pct1}}")
    _add_kpi(slide, 11.0, 1.5, "Yield",            "{{yield_especifico|0}} kWh/kWp")

    _add_text(slide, "Equipamiento principal", left=0.5, top=3.6,
              width=12, size=18, bold=True, color=_AZUL)
    bullets = [
        "• Módulos: {{n_paneles}} × TCL TOPCon Bifacial {{wp_panel}} Wp",
        "• Inversor: {{n_inversores}} × {{inversor_descripcion}}",
        "• Smart meter trifásico, estructura, balance of system completo",
        "• Ingeniería, gestión ante {{distribuidora}}, puesta en marcha",
    ]
    for i, b in enumerate(bullets):
        _add_text(slide, b, left=0.7, top=4.2 + i * 0.45,
                  width=12, size=15, color=_GRIS)

    _add_text(slide,
              "Garantías: 15 años producto · 30 años performance lineal módulos · 10 años inversores",
              left=0.5, top=6.6, width=12, size=11, color=_GRIS)


def _slide_generacion_vs_consumo(slide):
    _add_titulo(slide, "Generación estimada vs consumo del cliente")
    _add_text(slide,
              "Cobertura de {{cobertura_pct|pct1}} del consumo anual ({{consumo_anual|kwh}}) "
              "con generación de {{generacion_anual|kwh}}.",
              left=0.5, top=1.0, width=12.5, size=14, color=_GRIS)
    _add_chart_marker(slide, "generacion_vs_consumo",
                      left=1.0, top=1.9, width=8.5, height=4.7)
    _add_chart_marker(slide, "cobertura",
                      left=9.8, top=1.9, width=3.3, height=4.7)


def _slide_inversion(slide):
    _add_titulo(slide, "Inversión llave en mano")

    _add_kpi(slide, 0.5, 1.5,  "Subtotal (sin IVA)", "{{neto_usd|usd}}")
    _add_kpi(slide, 4.0, 1.5,  "IVA diferencial",    "{{iva_usd|usd}}")
    _add_kpi(slide, 7.5, 1.5,  "TOTAL llave en mano", "{{total_usd|usd}}", color=_NARANJA)
    _add_kpi(slide, 11.0, 1.5, "USD por kWp",        "{{usd_kwp|0}}")

    _add_text(slide, "Condiciones comerciales", left=0.5, top=3.8,
              width=12, size=18, bold=True, color=_AZUL)
    condiciones = [
        "• Validez de oferta: 30 días corridos",
        "• Forma de pago: 50% anticipo · 40% acopio · 10% PEM (a convenir)",
        "• Plazo de ejecución: 60-90 días desde aprobación de proyecto",
        "• Incluye: ingeniería, materiales, instalación, gestión, puesta en marcha",
        "• Excluye: obra civil mayor y trámites municipales (cotizable aparte)",
    ]
    for i, c in enumerate(condiciones):
        _add_text(slide, c, left=0.7, top=4.4 + i * 0.40,
                  width=12, size=14, color=_GRIS)


def _slide_proximos_pasos(slide):
    _add_titulo(slide, "Próximos pasos")
    pasos = [
        ("1.", "Visita técnica al sitio y relevamiento del PDI"),
        ("2.", "Ingeniería de detalle + simulación PVSyst"),
        ("3.", "Gestión de habilitación ante {{distribuidora}}"),
        ("4.", "Provisión de equipos y montaje"),
        ("5.", "Puesta en marcha, capacitación y entrega final"),
    ]
    for i, (num, txt) in enumerate(pasos):
        _add_text(slide, num, left=0.7, top=1.6 + i * 0.75,
                  width=0.7, size=24, bold=True, color=_NARANJA)
        _add_text(slide, txt, left=1.5, top=1.7 + i * 0.75,
                  width=11, size=18, color=_GRIS)

    _add_text(slide, "Contacto", left=0.5, top=5.8, size=16,
              bold=True, color=_AZUL)
    _add_text(slide,
              "Julián Lorenzo  ·  Project Manager — Nuevos Negocios",
              left=0.5, top=6.2, width=12, size=13, color=_GRIS)
    _add_text(slide,
              "julian.lorenzo@radiovictoria.com.ar  ·  +54 11 4407-6575",
              left=0.5, top=6.5, width=12, size=13, color=_AZUL)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers visuales
# ──────────────────────────────────────────────────────────────────────────────
def _add_titulo(slide, texto: str):
    _add_text(slide, texto, left=0.5, top=0.3, width=12.5, size=28,
              bold=True, color=_AZUL)
    # Underline bar
    bar = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0.5), Inches(1.1), Inches(2.0), Inches(0.06),
    )
    bar.fill.solid()
    bar.fill.fore_color.rgb = _NARANJA
    bar.line.fill.background()


def _add_text(slide, texto: str, *, left: float, top: float,
              width: float = 6.0, height: float = 0.5, size: int = 14,
              bold: bool = False, color: RGBColor = _GRIS) -> None:
    box = slide.shapes.add_textbox(
        Inches(left), Inches(top), Inches(width), Inches(height),
    )
    tf = box.text_frame
    tf.word_wrap = True
    tf.text = texto
    p = tf.paragraphs[0]
    p.font.size = Pt(size)
    p.font.bold = bold
    p.font.color.rgb = color


def _add_kpi(slide, left: float, top: float, label: str, value: str,
             *, size_value: int = 22, color: RGBColor = _AZUL) -> None:
    """Caja con label arriba y valor abajo (estilo KPI tile)."""
    shape = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(left), Inches(top), Inches(3.0), Inches(1.7),
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = _FONDO
    shape.line.color.rgb = color

    tf = shape.text_frame
    tf.margin_left = Inches(0.2)
    tf.margin_top = Inches(0.2)
    tf.word_wrap = True

    tf.text = label
    p1 = tf.paragraphs[0]
    p1.font.size = Pt(11)
    p1.font.color.rgb = _GRIS
    p1.font.bold = True

    p2 = tf.add_paragraph()
    p2.text = value
    p2.font.size = Pt(size_value)
    p2.font.bold = True
    p2.font.color.rgb = color


def _add_chart_marker(slide, key: str, *, left: float, top: float,
                      width: float, height: float) -> None:
    """Inserta un placeholder visible para un chart.

    El marcador es un rectángulo de fondo claro con el texto `{{chart:KEY}}`
    centrado — el motor `insertar_charts()` lo detecta, captura su geometría
    y lo reemplaza por el chart real (column/pie/etc.) en la misma posición.
    """
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(left), Inches(top), Inches(width), Inches(height),
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = _FONDO
    shape.line.color.rgb = _GRIS

    tf = shape.text_frame
    tf.word_wrap = True
    tf.margin_top = Inches(height / 2 - 0.3)
    tf.text = "{{chart:" + key + "}}"
    p = tf.paragraphs[0]
    p.font.size = Pt(14)
    p.font.color.rgb = _GRIS
    p.font.bold = True
    from pptx.enum.text import PP_ALIGN
    p.alignment = PP_ALIGN.CENTER
