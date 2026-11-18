"""
Auditoría del mapeo FAOSTAT (punto 1 de la auditoría).

Genera una tabla por producto con: unidad de producción, ítem FAOSTAT y su unidad
de consumo, tipo de correspondencia, factor de conversión (si aplica), fuente/
justificación y estado (utilizable / pendiente). También verifica que ningún ítem
FAOSTAT se use en dos grupos distintos.

Salida: data/results/arendonc2/auditoria_mapeo_faostat.csv

Uso: python src/arendonc2/auditar_mapeo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import yaml

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
    from arendonc2 import common
else:
    from . import common

MAPEO_YAML = common.ROOT / "config" / "arendonc2" / "mapeo_faostat.yaml"

# Unidad física de la producción del Valle por producto (forma primaria en finca).
# Fuente: Gobernación del Valle / EVA; estados documentados en docs/ML_C.
UNIDAD_PRODUCCION = {
    "Café": "t café pergamino (grano con cascarilla)",
    "Caña panelera": "t caña (tallo)",
    "Cacao": "t grano de cacao",
    "Coco": "t coco fresco",
    "Macadamia": "t nuez con cáscara",
    "Sacha Inchi": "t semilla (oleaginosa)",
    "Stevia": "t hoja",
    "Té": "t hoja/té procesado",
    "Ají": "t ají fresco",
    "Cebolla Larga": "t cebolla larga (rama) fresca",
}
# El resto (frutas, raíces) es tonelada de producto fresco cosechado.
UNIDAD_PRODUCCION_DEFECTO = "t producto fresco cosechado"

UNIDAD_FAOSTAT = "kg/cápita/año (disponibilidad de alimento, FBS)"


def main():
    mapeo = yaml.safe_load(open(MAPEO_YAML, encoding="utf-8"))["mapeos"]
    cfg = common.cargar_config()
    excluidos = set(cfg["general"]["productos_excluidos"])
    lista = common.leer_lista_productos().set_index("producto")["produccion_t_2019_2023"].to_dict()

    filas = []
    for p, v in mapeo.items():
        if p in excluidos:
            continue
        up = UNIDAD_PRODUCCION.get(p, UNIDAD_PRODUCCION_DEFECTO)
        nota = " ".join(str(v.get("nota", "")).split())
        if v.get("pendiente"):
            # distinguir causa: no-alimentario vs conversión no respaldada
            tipo = "no_alimentario" if p in ("Flores y follajes", "Aromáticas", "Sábila") \
                else "conversion_no_respaldada"
            filas.append({
                "producto": p, "unidad_produccion": up,
                "item_faostat": "", "unidad_consumo_faostat": "",
                "tipo_correspondencia": tipo, "factor_conversion": "",
                "estado": "pendiente",
                "fuente_justificacion": nota,
                "prod_2019_2023_t": round(lista.get(p, 0.0), 1),
            })
        elif "items" in v:
            filas.append({
                "producto": p, "unidad_produccion": up,
                "item_faostat": " + ".join(v["items"]),
                "unidad_consumo_faostat": UNIDAD_FAOSTAT,
                "tipo_correspondencia": "directa",
                "factor_conversion": "1 (fresco vs fresco)",
                "estado": "utilizable",
                "fuente_justificacion": nota,
                "prod_2019_2023_t": round(lista.get(p, 0.0), 1),
            })
        elif "categoria_compartida" in v:
            filas.append({
                "producto": p, "unidad_produccion": up,
                "item_faostat": v["categoria_compartida"],
                "unidad_consumo_faostat": UNIDAD_FAOSTAT,
                "tipo_correspondencia": "reparto_categoria",
                "factor_conversion": "cuota por producción 2019-2023 (fresco vs fresco)",
                "estado": "utilizable",
                "fuente_justificacion": nota,
                "prod_2019_2023_t": round(lista.get(p, 0.0), 1),
            })

    df = pd.DataFrame(filas).sort_values(["estado", "producto"]).reset_index(drop=True)
    common.asegurar_directorios()
    out = common.DATA_RES_OUT / "auditoria_mapeo_faostat.csv"
    df.to_csv(out, index=False, encoding="utf-8-sig")

    # verificación de no reutilización de ítems entre grupos
    usados = {}
    problemas = []
    for p, v in mapeo.items():
        if p in excluidos or v.get("pendiente"):
            continue
        claves = v.get("items", []) + ([v["categoria_compartida"]] if "categoria_compartida" in v else [])
        for k in claves:
            usados.setdefault(k, []).append(p)
    # una categoría compartida puede tener varios productos (válido); un 'item' de
    # suma no puede estar en más de un producto, ni un nombre ser item y categoría.
    items_suma = [it for p, v in mapeo.items() if not v.get("pendiente") for it in v.get("items", [])]
    cats = [v["categoria_compartida"] for p, v in mapeo.items()
            if not v.get("pendiente") and "categoria_compartida" in v]
    for it in set(items_suma):
        if items_suma.count(it) > 1:
            problemas.append(f"item '{it}' en >1 producto (suma)")
    for it in set(items_suma) & set(cats):
        problemas.append(f"'{it}' usado como item y como categoría")

    print("=" * 70)
    print("AUDITORÍA DEL MAPEO FAOSTAT")
    print("=" * 70)
    print(f"Productos utilizables: {(df['estado'] == 'utilizable').sum()}")
    print(f"Productos pendientes : {(df['estado'] == 'pendiente').sum()}")
    print(f"  - conversión no respaldada: "
          f"{(df['tipo_correspondencia'] == 'conversion_no_respaldada').sum()}")
    print(f"  - no alimentario          : "
          f"{(df['tipo_correspondencia'] == 'no_alimentario').sum()}")
    print(f"Reutilización de ítems entre grupos: {problemas if problemas else 'ninguna'}")
    print(f"\nTabla escrita en {out}")
    print()
    print(df[["producto", "tipo_correspondencia", "estado"]].to_string(index=False))


if __name__ == "__main__":
    main()
