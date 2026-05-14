"""Smoke test del pipeline end-to-end con datos sintéticos (offline)."""
from __future__ import annotations

from pathlib import Path

from rv_propuestas.inputs.facturas import from_manual
from rv_propuestas.inputs.pdi import desde_factura_y_pdi
from rv_propuestas.inputs.ubicacion import Ubicacion
from rv_propuestas.pipeline import ejecutar_pipeline


def caso(nombre: str, kwh_anuales: float, lat: float, lon: float,
         tension_kv: float, capacidad_pdi: float | None) -> dict:
    factura = from_manual(
        distribuidora="EDENOR",
        consumos_kwh=[kwh_anuales / 12] * 12,
        potencia_contratada_kw=capacidad_pdi or 100.0,
        tension_suministro="BT 380V" if tension_kv <= 1 else f"MT {tension_kv} kV",
        categoria_tarifaria="T3-MD" if tension_kv <= 1 else "T3-MT",
        titular=nombre,
    )
    pdi = desde_factura_y_pdi(
        tension_kv=tension_kv,
        fases=3,
        capacidad_disponible_kw=capacidad_pdi,
        distancia_al_tablero_m=30.0,
    )
    return ejecutar_pipeline(
        factura=factura,
        ubicacion=Ubicacion(nombre=nombre, lat=lat, lon=lon),
        pdi=pdi,
        salida=Path("./output/smoke"),
        cliente_nombre=nombre,
        proyecto_nombre=nombre,
        usar_pvgis=False,                    # offline para CI
        precios_path="./data/precios.example.yaml",
    )


if __name__ == "__main__":
    print("\n── Caso 30 kW (BT, comercial chico) ──")
    caso("Demo_30kW", kwh_anuales=55_000, lat=-34.6, lon=-58.4, tension_kv=0.38, capacidad_pdi=30.0)

    print("\n── Caso 250 kW (BT industrial) ──")
    caso("Demo_250kW", kwh_anuales=420_000, lat=-31.4, lon=-64.2, tension_kv=0.38, capacidad_pdi=300.0)

    print("\n── Caso 1 MW (MT 13.2 kV) ──")
    caso("Demo_1MW", kwh_anuales=1_700_000, lat=-32.9, lon=-68.8, tension_kv=13.2, capacidad_pdi=1100.0)

    print("\n── Caso 3 MW (MT 33 kV) ──")
    caso("Demo_3MW", kwh_anuales=5_200_000, lat=-34.0, lon=-65.0, tension_kv=33.0, capacidad_pdi=3000.0)
