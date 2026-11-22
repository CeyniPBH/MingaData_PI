"""Figura 6 del informe (sección 3.4.2): municipios donde cae la central en los 54 escenarios.

Uso, desde la raíz del repositorio: python src/informe/figura_6_centrales.py
Lee las geometrías de data/results/arendonc2/, las subregiones del Plan de Ordenamiento Territorial Departamental que
usa el tablero central, data/clean/destinos_coordenadas.csv y data/results/opt/estabilidad_escenarios.csv.
El sombreado marca la subregión Centro, que es la que nombra el título. Los destinos de la distribución se dibujan
porque el costo de distribución es cerca del 79 % del total y explica hacia dónde se mueve la central.
"""
import json
import math
import re

import pandas as pd
from matplotlib import patheffects
from matplotlib.collections import PolyCollection

from estilo import RAIZ, AZUL, GRIS, FONDO, TEXTO, TEXTO_2, plt, guardar

KX = math.cos(math.radians(4.0))  # proyección equirectangular simple, igual que en la Figura 2
TONO_CENTRO = "#D6DAE0"            # mismo tono de la subregión Centro en la Figura 2
BORDE_ZONA = "#8A919C"
halo = [patheffects.withStroke(linewidth=2.4, foreground="white")]


def xy(lon, lat):
    return lon * KX, lat


def anillos(geom):
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    return [[xy(lon, lat) for lon, lat in poly[0]] for poly in polys]


mun = json.load(open(RAIZ / "data/results/arendonc2/municipios_zonas_geometrias.geojson", encoding="utf-8"))
zon = json.load(open(RAIZ / "data/results/arendonc2/zonas_geometrias.geojson", encoding="utf-8"))
html = (RAIZ / "src/dashboard/assets/tablero_central_acopio_valle.html").read_text(encoding="utf-8")
subregion = {m["id"]: m["s"] for m in json.loads(re.search(r"const D = (\{.*?\});\s*\n", html, re.S).group(1))["muns"]}
coords = pd.read_csv(RAIZ / "data/clean/municipios_coordenadas.csv", dtype={"cod_dane": str}).set_index("cod_dane")
destinos = pd.read_csv(RAIZ / "data/clean/destinos_coordenadas.csv").set_index("id_destino")
est = pd.read_csv(RAIZ / "data/results/opt/estabilidad_escenarios.csv", dtype={"central_cod": str})
freq = est.groupby(["central", "central_cod"]).size().reset_index(name="n")
assert all(subregion.get(c) == "Centro" for c in freq.central_cod), "Alguna central quedó fuera de la subregión Centro"

fig, ax = plt.subplots(figsize=(5.2, 5.0), dpi=300)

# Fondo: municipios en gris claro y la subregión Centro un tono más oscuro.
for f in mun["features"]:
    cod = f["properties"]["cod_dane"]
    ax.add_collection(PolyCollection(anillos(f["geometry"]), facecolor=TONO_CENTRO if subregion.get(cod) == "Centro" else FONDO,
                                     edgecolor="white", linewidth=0.5, zorder=1))
# Zonas de acopio: solo el contorno.
zpolys = [r for f in zon["features"] for r in anillos(f["geometry"])]
ax.add_collection(PolyCollection(zpolys, facecolor="none", edgecolor=BORDE_ZONA, linewidth=0.9, zorder=2))


def centroide(r):
    a = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(r, r[1:] + r[:1]):
        c = x0 * y1 - x1 * y0
        a += c; cx += (x0 + x1) * c; cy += (y0 + y1) * c
    a *= 0.5
    return cx / (6 * a), cy / (6 * a), abs(a)


ajuste = {"Z1": (0.02, -0.30), "Z2": (0.05, 0.10), "Z3": (-0.24, 0.22), "Z4": (-0.07, -0.12), "Z5": (-0.02, 0.06)}
for f in zon["features"]:
    z = f["properties"]["zona"]
    cx, cy, _ = max((centroide(r) for r in anillos(f["geometry"])), key=lambda t: t[2])
    dx, dy = ajuste.get(z, (0, 0))
    ax.text(cx + dx, cy + dy, "Zona " + z[1:], ha="center", va="center", fontsize=7, color=TEXTO_2, zorder=3,
            path_effects=halo)
ax.text(*xy(-76.00, 3.95), "SUBREGIÓN CENTRO", fontsize=7, color=TEXTO, fontweight="bold", ha="center", va="center",
        zorder=3, path_effects=halo)

# Destinos de la distribución: tres dentro del mapa y dos fuera, con flecha.
for id_, etiqueta, dx, dy, ha in [("DEST_BUENAVENTURA", "Puerto de Buenaventura", 0.0, 0.08, "center"),
                                   ("DEST_AEROPUERTO_PALMIRA", "Aeropuerto de Palmira", 0.06, 0.0, "left"),
                                   ("DEST_CALI", "Cali", 0.06, 0.0, "left")]:
    x, y = xy(destinos.loc[id_, "lon"], destinos.loc[id_, "lat"])
    ax.scatter([x], [y], marker="s", s=20, color=GRIS, edgecolor="white", linewidth=0.8, zorder=4)
    ax.text(x + dx, y + dy, etiqueta, fontsize=7, color=TEXTO_2, ha=ha, va="center", zorder=4, path_effects=halo)
flecha = dict(arrowstyle="-|>", color=GRIS, lw=0.9, mutation_scale=8)
x_norte, y_norte = xy(-75.92, 5.06)
ax.annotate("", xy=(x_norte, y_norte + 0.13), xytext=(x_norte, y_norte + 0.02), arrowprops=flecha, zorder=4)
x_este, y_este = xy(-75.70, 4.55)
ax.annotate("", xy=(x_este + 0.17, y_este + 0.04), xytext=(x_este + 0.02, y_este), arrowprops=flecha, zorder=4)
ax.text(x_norte, y_norte + 0.15, "Medellín", fontsize=7, color=TEXTO_2, ha="center", va="bottom")
ax.text(x_este + 0.19, y_este + 0.05, "Bogotá", fontsize=7, color=TEXTO_2, ha="left", va="center")

# Centrales: área del círculo proporcional al número de escenarios.
etiquetas = {"Bugalagrande": (0.10, 0.27, "center"), "Andalucia": (0.20, -0.15, "left"), "Riofrío": (-0.22, 0.14, "right"),
             "Yotoco": (-0.20, -0.02, "right"), "Sevilla": (0.10, -0.12, "left")}
nombres = {"Andalucia": "Andalucía"}
for r in freq.sort_values("n", ascending=False).itertuples():
    x, y = xy(coords.loc[r.central_cod, "lon"], coords.loc[r.central_cod, "lat"])
    ax.scatter([x], [y], s=r.n * 13, color=AZUL, edgecolor="white", linewidth=1.1, zorder=5)
    dx, dy, ha = etiquetas[r.central]
    ax.annotate(f"{nombres.get(r.central, r.central)}: {r.n} de 54", xy=(x, y), xytext=(x + dx, y + dy),
                fontsize=7.5, color=TEXTO, fontweight="bold" if r.central == "Bugalagrande" else "normal",
                ha=ha, va="center", path_effects=halo, zorder=6,
                arrowprops=dict(arrowstyle="-", color=TEXTO_2, lw=0.5, shrinkA=0, shrinkB=4))

xs = [p[0] for f in mun["features"] for r in anillos(f["geometry"]) for p in r]
ys = [p[1] for f in mun["features"] for r in anillos(f["geometry"]) for p in r]
ax.set_xlim(min(xs) - 0.02, max(xs) + 0.36)
ax.set_ylim(min(ys) - 0.02, max(ys) + 0.24)
ax.set_aspect("equal")
ax.axis("off")
fig.tight_layout(pad=0.1)
guardar(fig, "figura_6_centrales_escenarios.png", bbox_inches="tight")
print(freq.to_string())
