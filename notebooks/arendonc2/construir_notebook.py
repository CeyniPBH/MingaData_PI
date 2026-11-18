"""
Genera el notebook reproducible de las tareas #2, #3 y #4 (arendonc2).
Se versiona este generador; el .ipynb se produce con:
    python notebooks/arendonc2/construir_notebook.py
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "zonas_excedentes_escenarios.ipynb"


def md(src):
    return {"cell_type": "markdown", "metadata": {}, "source": src.splitlines(keepends=True)}


def code(src):
    return {"cell_type": "code", "metadata": {}, "execution_count": None,
            "outputs": [], "source": src.splitlines(keepends=True)}


cells = [
    md("""# Zonas, excedentes y escenarios — Valle del Cauca (arendonc2)

Notebook reproducible de las tareas **#2 (zonas)**, **#3 (excedentes)** y
**#4 (escenarios)** de Alejandro Rendón Correa.

Ejecuta de arriba a abajo. Requiere haber instalado `requirements.txt` y, la
primera vez, acceso a internet para descargar GADM y la población DANE.
"""),
    code("""import sys
from pathlib import Path
ROOT = Path.cwd()
while not (ROOT / "src" / "arendonc2").exists() and ROOT != ROOT.parent:
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT / "src"))
import pandas as pd
from arendonc2 import common, descargar_geometrias, poblacion, zonas_acopio, excedentes, escenarios
cfg = common.cargar_config()
print("Raíz del repo:", ROOT)"""),
    md("## 0. Insumos externos (GADM + población DANE)"),
    code("""descargar_geometrias.main()
poblacion.descargar()
pob = poblacion.generar(cfg["excedentes"]["anios"])
pob.head()"""),
    md("""## 1. Tarea #2 — Zonas de acopio

Vecindad Queen + Ward con restricción de conectividad. Se evalúan k = 3..8 y se
publica k = 5 (configurable)."""),
    code("""res_z = zonas_acopio.ejecutar(cfg, guardar=True)
print("Diagnóstico geometrías:", res_z["diagnostico_geometrias"])
print("Diagnóstico vecindad:", res_z["diagnostico_vecindad"])
res_z["metricas_k"]"""),
    code("""zonas = res_z["zonas"]
print("42 municipios únicos:", zonas["cod_dane"].nunique())
print("Un centro por zona:", (zonas.groupby("zona")["es_centro_zona"].sum() == 1).all())
zonas.groupby("zona")["municipio"].apply(list)"""),
    md("### Mapa de zonas"),
    code("""import geopandas as gpd
import matplotlib.pyplot as plt
mz = gpd.read_file(common.DATA_RES_OUT / "municipios_zonas_geometrias.geojson")
fig, ax = plt.subplots(figsize=(8, 10))
mz.plot(column="zona", ax=ax, legend=True, edgecolor="black", linewidth=0.4, cmap="tab10")
# centros de zona
mun = common.leer_municipios_coordenadas()
cent = zonas[zonas["es_centro_zona"] == 1].merge(mun, on="cod_dane", suffixes=("", "_c"))
ax.scatter(cent["lon"], cent["lat"], c="black", marker="*", s=200, label="Centro (referencia)")
for _, r in cent.iterrows():
    ax.annotate(r["municipio"], (r["lon"], r["lat"]), fontsize=8)
ax.set_title("Zonas de acopio del Valle del Cauca (k=5)\\nCentros = referencia, no ubicación óptima del solver")
ax.legend()
plt.tight_layout()
plt.savefig(common.DATA_RES_OUT / "mapa_zonas.png", dpi=120)
plt.show()"""),
    md("""## 2. Tarea #3 — Excedentes

9 combinaciones (oferta × consumo) por producto, municipio y año. Consumo desde
FAOSTAT (reparto por producción 2019–2023), población DANE (total municipal)."""),
    code("""res_e = excedentes.ejecutar(cfg, guardar=True)
exc = res_e["excedentes"]
print("Filas:", len(exc), "| Excedentes negativos:", (exc["excedente_t"] < 0).sum())
print("Pendientes:", res_e["pendientes"]["producto"].tolist())
res_e["cobertura"].head(9)"""),
    code("""# Cuotas de reparto (ejemplo Fruits, other)
cu = res_e["cuotas"]
cu[cu["item_o_categoria"] == "Fruits, other"].sort_values("cuota", ascending=False).head(10)"""),
    code("""# Excedente por zona (escenario base/base, 2024)
pz = res_e["por_zona"]
pz[(pz["anio"] == 2024) & (pz["escenario_oferta"] == "base") & (pz["escenario_consumo"] == "base")] \\
    .groupby("zona")["excedente_t"].sum()"""),
    md("""## 3. Tarea #4 — Escenarios para optimización

27 combinaciones por año (oferta × consumo × mezcla), filas por zona."""),
    code("""df_esc = escenarios.ejecutar(cfg, guardar=True)
print("Combinaciones por año:", df_esc.groupby("anio")["id_escenario"].nunique().unique())
df_esc["suma"] = df_esc["volumen_nacional"] + df_esc["volumen_exportacion"]
df_esc.head(10)"""),
    md("## 4. Adaptador para el solver de Samuel"),
    code("""from arendonc2.adaptador import preparar_para_solver, listar_escenarios
print(listar_escenarios(2024).head())
pkg = preparar_para_solver("2024_Obase_Cbase_M80_20", 2024)
print("Año:", pkg.anio, "| Cobertura:", pkg.cobertura_oferta_pct, "% | parcial:", pkg.cobertura_parcial)
print("Advertencias:", pkg.advertencias)
pkg.volumen_por_zona"""),
    md("""## 5. Lectura

- Las 5 zonas son contiguas (100 %) y agrupan los 42 municipios una sola vez.
- El excedente se concentra en las zonas productoras del norte y centro; Cali y los
  municipios urbanos aportan poco excedente porque su consumo local supera su oferta.
- Las mezclas nacional/exportación son **sensibilidad**, no participaciones
  observadas (ver `docs/arendonc2/escenarios_definicion.md`).
- Los centros de zona son referencias para recolección, **no** la ubicación óptima
  de la central: eso lo decide el modelo de Samuel.
"""),
]

nb = {
    "cells": cells,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.10"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

OUT.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
print("Escrito", OUT)
