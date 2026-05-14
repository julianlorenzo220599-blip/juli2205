"""Orquestador end-to-end: factura + ubicación + PDI → archivos de salida."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from .bom.epc import generar_bom
from .costeo.calculo import calcular
from .inputs.facturas import Factura
from .inputs.pdi import PDI
from .inputs.ubicacion import Ubicacion, get_irradiacion, estimar_offline
from .render import propuesta_cliente, revision_interna
from .sizing.engine import dimensionar
from .sizing.topologia import configurar_strings, seleccionar_inversores


def _cargar_precios(path: str | Path | None) -> dict[str, float]:
    if path is None:
        return {}
    path = Path(path)
    if not path.exists():
        print(f"⚠ Archivo de precios no encontrado: {path}. Continuando sin precios.")
        return {}
    try:
        import yaml
    except ImportError:
        print("⚠ PyYAML no instalado. Instalá con: pip install pyyaml")
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    precios: dict[str, float] = {}
    for seccion, items in data.items():
        if isinstance(items, dict):
            for sku, precio in items.items():
                precios[sku] = float(precio)
    return precios


def ejecutar_pipeline(
    factura: Factura,
    ubicacion: Ubicacion,
    pdi: PDI,
    salida: Path,
    cliente_nombre: str = "",
    proyecto_nombre: str = "",
    usar_pvgis: bool = True,
    precios_path: Optional[str | Path] = None,
    template_ppt: Optional[str | Path] = None,
) -> dict[str, Path]:
    """Corre la pipeline completa y devuelve las rutas de los archivos generados."""
    salida = Path(salida)
    salida.mkdir(parents=True, exist_ok=True)

    # 1) Irradiación
    if usar_pvgis:
        try:
            irradiacion = get_irradiacion(ubicacion)
        except Exception as e:
            print(f"⚠ PVGIS falló ({e}). Cayendo a estimación offline.")
            irradiacion = estimar_offline(ubicacion)
    else:
        irradiacion = estimar_offline(ubicacion)

    # 2) Sizing
    sizing = dimensionar(factura, irradiacion, pdi)

    # 3) Topología (inversores + strings)
    inv_cfg = seleccionar_inversores(sizing.kwp_real)
    str_cfg = configurar_strings(sizing.n_paneles, inv_cfg)

    # 4) BOM
    bom = generar_bom(sizing, inv_cfg, str_cfg, pdi)

    # 5) Precios
    precios = _cargar_precios(precios_path)
    if precios:
        bom.aplicar_precios(precios)

    # 6) Costeo
    costeo = calcular(bom)

    # 7) Render
    slug = (proyecto_nombre or cliente_nombre or "proyecto").replace(" ", "_").replace("/", "-")[:40]
    out_excel = salida / f"REVISION_INTERNA_{slug}.xlsx"
    out_ppt = salida / f"PROPUESTA_{slug}.pptx"

    revision_interna.render(
        factura=factura, irradiacion=irradiacion, pdi=pdi, sizing=sizing,
        inv_cfg=inv_cfg, str_cfg=str_cfg, costeo=costeo,
        output_path=out_excel,
        cliente_nombre=cliente_nombre, proyecto_nombre=proyecto_nombre,
    )
    propuesta_cliente.render(
        factura=factura, irradiacion=irradiacion, sizing=sizing,
        inv_cfg=inv_cfg, costeo=costeo,
        output_path=out_ppt,
        cliente_nombre=cliente_nombre, proyecto_nombre=proyecto_nombre,
        template_path=template_ppt,
    )

    print()
    print(f"✓ {sizing.kwp_real:.1f} kWp · {sizing.n_paneles} paneles · {inv_cfg.cantidad}×{inv_cfg.inversor.sku}")
    print(f"✓ Cobertura: {sizing.cobertura*100:.1f}% · Generación: {sizing.generacion_anual_kwh:,.0f} kWh/año")
    print(f"✓ Total cliente: USD {costeo.total_cliente:,.0f} (USD/kWp: {costeo.total_cliente/sizing.kwp_real:,.0f})")
    if costeo.items_sin_precio:
        print(f"⚠ {len(costeo.items_sin_precio)} SKUs sin precio en catálogo (ver hoja 'Notas').")
    print(f"→ Revisión interna: {out_excel}")
    print(f"→ Propuesta cliente: {out_ppt}")

    return {"excel": out_excel, "ppt": out_ppt}
