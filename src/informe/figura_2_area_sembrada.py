"""Figura 2 del informe (sección 3.2.3): dónde está el área sembrada de caña de azúcar, café y fruta y plátano.

Uso, desde la raíz del repositorio: python src/informe/figura_2_area_sembrada.py
Lee data/clean/produccion_valle_clean.csv, las geometrías de data/results/arendonc2/municipios_zonas_geometrias.geojson
y las subregiones del Plan de Ordenamiento Territorial Departamental que usa el tablero central.
Un punto equivale a 500 hectáreas sembradas (promedio 2021-2023) y se ubica al azar dentro de su municipio, con una
semilla fija para que la figura salga igual en cada corrida.
"""
import json
import math
import re

import numpy as np
import pandas as pd
from matplotlib import patheffects
from matplotlib.collections import PolyCollection
from matplotlib.path import Path as Trazo

from estilo import RAIZ, AZUL, TEXTO, TEXTO_2, plt, guardar, num

HA_POR_PUNTO = 500
GRUPOS = {"Caña de azúcar": AZUL, "Fruta y plátano": "#E3A400", "Café": "#8C3A0F"}  # orden de las barras
TONOS = {"Norte": "#E8EAEE", "Centro": "#D6DAE0", "Sur": "#E8EAEE", "Pacífico": "#F4F5F7"}
KX = math.cos(math.radians(4.0))  # proyección equirectangular simple
rng = np.random.default_rng(2026)

# ---------- Datos ----------
prod = pd.read_csv(RAIZ / "data/clean/produccion_valle_clean.csv", dtype={"cod_dane": str})
v = prod[prod.anio.between(2021, 2023) & prod.familia.isin(["Frutales", "Cultivos Tropicales Tradicionales"])].copy()
v["grupo"] = np.select([v.producto == "Caña de azúcar", v.producto == "Café", v.familia == "Frutales"],
                       ["Caña de azúcar", "Café", "Fruta y plátano"], "Otros")
total = v.ha_sembradas.sum() / 3
por_grupo = v.groupby("grupo").ha_sembradas.sum() / 3
por_municipio = v[v.grupo != "Otros"].groupby(["cod_dane", "grupo"]).ha_sembradas.sum() / 3

html = (RAIZ / "src/dashboard/assets/tablero_central_acopio_valle.html").read_text(encoding="utf-8")
subregion = {m["id"]: m["s"] for m in json.loads(re.search(r"const D = (\{.*?\});\s*\n", html, re.S).group(1))["muns"]}
v["subregion"] = v.cod_dane.map(subregion)
participacion = lambda grupo, regiones: (v[(v.grupo == grupo) & v.subregion.isin(regiones)].ha_sembradas.sum()
                                         / v[v.grupo == grupo].ha_sembradas.sum())

# ---------- Geometrías ----------
geo = json.load(open(RAIZ / "data/results/arendonc2/municipios_zonas_geometrias.geojson", encoding="utf-8"))


def anillos(geom):
    poligonos = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    return [np.array([(lon * KX, lat) for lon, lat in p[0]]) for p in poligonos]


municipios = {f["properties"]["cod_dane"]: anillos(f["geometry"]) for f in geo["features"]}


def puntos_al_azar(anillos_mun, n):
    """n puntos uniformes dentro del municipio (muestreo por rechazo en su rectángulo envolvente)."""
    trazos = [Trazo(a) for a in anillos_mun]
    todos = np.vstack(anillos_mun)
    elegidos = []
    while len(elegidos) < n:
        candidatos = rng.uniform(todos.min(axis=0), todos.max(axis=0), size=(400, 2))
        dentro = np.zeros(len(candidatos), dtype=bool)
        for t in trazos:
            dentro |= t.contains_points(candidatos)
        elegidos.extend(candidatos[dentro][: n - len(elegidos)])
    return np.array(elegidos)


puntos = {g: [] for g in GRUPOS}
for (cod, grupo), ha in por_municipio.items():
    n = int(round(ha / HA_POR_PUNTO))
    if n:
        puntos[grupo].append(puntos_al_azar(municipios[cod], n))

# ---------- Mapa ----------
fig = plt.figure(figsize=(7.1, 4.3))
mapa = fig.add_axes([0.0, 0.02, 0.52, 0.96])
# Dibuja primero los bordes para conservar los límites entre subregiones.
for k, s in enumerate(["Pacífico", "Sur", "Centro", "Norte"]):
    anillos_s = [a for cod, lista in municipios.items() if subregion.get(cod) == s for a in lista]
    mapa.add_collection(PolyCollection(anillos_s, facecolor="none", edgecolor="#8A919C", linewidth=2.0, zorder=2 * k + 1))
    mapa.add_collection(PolyCollection(anillos_s, facecolor=TONOS[s], edgecolor="none", zorder=2 * k + 2))
todos_anillos = [a for lista in municipios.values() for a in lista]
mapa.add_collection(PolyCollection(todos_anillos, facecolor="none", edgecolor="white", linewidth=0.35, zorder=9))
for grupo in reversed(list(GRUPOS)):
    if puntos[grupo]:
        xy = np.vstack(puntos[grupo])
        mapa.scatter(xy[:, 0], xy[:, 1], s=9, color=GRUPOS[grupo], edgecolor="white", linewidth=0.3, zorder=10)
todos = np.vstack(todos_anillos)
mapa.set_xlim(todos[:, 0].min() - 0.01, todos[:, 0].max() + 0.01)
mapa.set_ylim(todos[:, 1].min() - 0.01, todos[:, 1].max() + 0.01)
mapa.set_aspect("equal")
mapa.axis("off")


def centro(s):
    """Centroide de la subregión, ponderado por el área de cada municipio."""
    pesos, xs, ys = [], [], []
    for c, lista in municipios.items():
        if subregion.get(c) != s:
            continue
        for a in lista:
            x, y = a[:, 0], a[:, 1]
            area = abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1))) / 2
            pesos.append(area); xs.append(x.mean()); ys.append(y.mean())
    return np.average(xs, weights=pesos), np.average(ys, weights=pesos)


halo = [patheffects.withStroke(linewidth=2.6, foreground="white")]
for s, (dx, dy) in {"Norte": (0.0, 0.05), "Centro": (-0.05, 0.0), "Sur": (0.02, -0.02), "Pacífico": (-0.05, -0.05)}.items():
    cx, cy = centro(s)
    mapa.text(cx + dx, cy + dy, s.upper(), fontsize=7.2, color=TEXTO, ha="center", va="center", zorder=12,
              fontweight="bold", path_effects=halo)
cn = participacion("Café", ["Centro", "Norte"]), participacion("Fruta y plátano", ["Centro", "Norte"])
sur = participacion("Caña de azúcar", ["Sur"])

# ---------- Barras ----------
fig.text(0.545, 0.885, "Área sembrada por cultivo", fontsize=12.5, fontweight="bold", color=TEXTO)
fig.text(0.545, 0.835, "Promedio anual 2021-2023", fontsize=9.5, color=TEXTO_2)
barras = fig.add_axes([0.70, 0.43, 0.27, 0.33])
ha = [por_grupo[g] for g in GRUPOS]
y = np.arange(len(GRUPOS))[::-1]
barras.barh(y, ha, height=0.6, color=list(GRUPOS.values()))
for yi, grupo, valor in zip(y, GRUPOS, ha):
    barras.text(-max(ha) * 0.03, yi, grupo, ha="right", va="center", fontsize=9.5, color=TEXTO)
    barras.text(valor + max(ha) * 0.03, yi, f"{num(valor / 1000, 1)} mil ha · {num(100 * valor / total)} %",
                ha="left", va="center", fontsize=9, color=TEXTO_2)
barras.set_xlim(0, max(ha) * 2.15)
barras.set_ylim(-0.6, len(GRUPOS) - 0.4)
barras.axis("off")
otros = por_grupo.get("Otros", 0)
fig.text(0.545, 0.375, f"Otros cultivos: {num(otros / 1000, 1)} mil ha · {num(100 * otros / total)} %", fontsize=8,
         color=TEXTO_2)
fig.text(0.545, 0.31, f"El {num(100 * sur)} % de la caña de azúcar está en el sur.\nEl centro y el norte tienen el "
         f"{num(100 * cn[0])} % del café\ny el {num(100 * cn[1])} % de la fruta y el plátano.", fontsize=8.6, color=TEXTO,
         va="top", linespacing=1.35)
fig.text(0.547, 0.135, "●", fontsize=8, color=TEXTO_2, va="center")
fig.text(0.57, 0.135, f"1 punto = {HA_POR_PUNTO} ha sembradas, ubicado al azar en su municipio", fontsize=7.6,
         color=TEXTO_2, va="center")
guardar(fig, "figura_2_area_sembrada_por_cultivo.png")
print(f"Área total: {num(total)} ha; " + ", ".join(f"{g} {num(por_grupo[g])} ha" for g in list(GRUPOS) + ["Otros"])
      + f"; sur {num(100 * sur, 1)} % de la caña; centro y norte {num(100 * cn[0], 1)} % del café y "
      f"{num(100 * cn[1], 1)} % de la fruta")
