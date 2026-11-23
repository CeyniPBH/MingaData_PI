"""Figura 7 del informe (sección 3.4.4): oferta de fruta y plátano a 40 km de Bugalagrande, real, pronóstico a un año y escenarios.

La banda gris va del escenario bajo al base; el alto se anota porque, dibujado, aplastaría el resto del gráfico. La línea
punteada es el promedio 2021-2023, que es la base con la que el tablero dimensiona la central.

Uso, desde la raíz del repositorio: python src/informe/figura_7_caso_bugalagrande.py
"""
import json, math, sys
import numpy as np, pandas as pd

from estilo import RAIZ, AZUL, GRIS, GRIS_CLARO, TEXTO, TEXTO_2, plt, guardar, num

sys.path.insert(0, str(RAIZ / "src" / "dashboard")); sys.path.insert(0, str(RAIZ / "src" / "ML_C"))
from tablero_central import generar_html_tablero, PATRON_DATOS  # noqa: E402
from common import cargar_panel  # noqa: E402

prod = pd.read_csv(RAIZ / "data/clean/produccion_valle_clean.csv", dtype={"cod_dane": str})
D = json.loads(PATRON_DATOS.search(generar_html_tablero(RAIZ / "src/dashboard/assets/tablero_central_acopio_valle.html", prod)).group(1))
M = D["muns"]
def hav(a, b):
    R, r = 6371.0, math.pi / 180
    h = math.sin((b["lat"] - a["lat"]) * r / 2) ** 2 + math.cos(a["lat"] * r) * math.cos(b["lat"] * r) * math.sin((b["lon"] - a["lon"]) * r / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))
sede = next(m for m in M if m["n"] == "Bugalagrande")
area = {m["id"] for m in M if hav(sede, m) <= 40}

series, lp = cargar_panel()
lpi = lp.set_index("producto")
sel = [(p, c) for (p, c) in series if c in area and lpi.loc[p, "familia"] == "Frutales" and lpi.loc[p, "estado"] == "detallado"]
real = pd.concat([series[k] for k in sel], axis=1).fillna(0).sum(axis=1).loc[2014:2023] / 1000

pr = pd.read_csv(RAIZ / "data/results/ML_Ce/predicciones_comparacion.csv", dtype={"cod_dane": str})
pr = pr[pr.set_index(["producto", "cod_dane"]).index.isin(sel)]
pr["final"] = (pr.naive + pr.lgbm) / 2
h1 = pr[pr.horizonte == 1].groupby("anio_objetivo")[["final", "naive", "real"]].sum() / 1000

o = pd.read_csv(RAIZ / "data/results/ML_Ce/oferta_escenarios.csv", dtype={"cod_dane": str})
o = o[o.set_index(["producto", "cod_dane"]).index.isin(sel)]
fut = o.groupby("año")[["oferta_bajo", "oferta_base", "oferta_alto"]].sum() / 1000

fig, ax = plt.subplots(figsize=(6.3, 3.0), dpi=300)
anios_f = [2023] + list(fut.index)
base_f = [real.loc[2023]] + list(fut.oferta_base)
bajo_f = [real.loc[2023]] + list(fut.oferta_bajo)
ax.fill_between(anios_f, bajo_f, base_f, color="#E5E7EB", lw=0, zorder=1)
prom = real.loc[2021:2023].mean()
ax.hlines(prom, 2021, 2028, color=TEXTO_2, lw=0.8, ls=(0, (1, 2)), zorder=2)
ax.plot(real.index, real.values, color=AZUL, lw=2, zorder=3)
ax.plot(anios_f, base_f, color=AZUL, lw=2, ls=(0, (3, 2)), zorder=3)
ax.scatter(h1.index, h1["final"], s=28, color=GRIS, edgecolor="white", linewidth=1, zorder=4)
for a in h1.index:
    ax.plot([a, a], [h1.loc[a, "final"], real.loc[a]], color=GRIS_CLARO, lw=1, zorder=2)

# Etiqueta los escenarios 2024-2028 a la derecha.
ax.text(2014.1, real.loc[2014] + 25, "Real", color=AZUL, fontsize=8, fontweight="bold")
ax.text(2018.75, h1.loc[2019, "final"] + 22, "Pronóstico a un año", color=TEXTO_2, fontsize=7.5, ha="center")
ax.text(2028.25, fut.loc[2028, "oferta_base"] + 4, "Escenario base", color=AZUL, fontsize=7.5, va="center")
ax.text(2028.25, prom - 4, "Promedio 2021-2023", color=TEXTO_2, fontsize=7.5, va="center")
ax.text(2028.25, fut.loc[2028, "oferta_bajo"], "Escenario bajo", color=TEXTO_2, fontsize=7.5, va="center")
alto = fut.loc[2028, "oferta_alto"]
ax.annotate("", xy=(2028, 598), xytext=(2028, 512),
            arrowprops=dict(arrowstyle="-|>", color=GRIS, lw=0.8, mutation_scale=8))
ax.text(2027.8, 562, f"Escenario alto: {num(alto / 1000, 1)} millones\nen 2028, fuera de la escala", fontsize=7,
        color=TEXTO_2, ha="right", va="center")
ax.annotate("2022: +50 % con la misma\nárea sembrada", xy=(2022, real.loc[2022]), xytext=(2019.6, 470),
            fontsize=7.5, color=TEXTO, ha="center", va="center",
            arrowprops=dict(arrowstyle="-", color=TEXTO_2, lw=0.6, shrinkA=2, shrinkB=3))
err22 = round((h1.loc[2022, "final"] / real.loc[2022] - 1) * 100)
ax.annotate(f"{err22} %", xy=(2022, h1.loc[2022, "final"]),
            xytext=(2022.35, h1.loc[2022, "final"] - 10), fontsize=7.5, color=TEXTO_2, va="center")

ax.set_xlim(2013.6, 2031.4); ax.set_ylim(0, 600)
ax.set_xticks(range(2014, 2029, 2))
ax.set_ylabel("Miles de toneladas", fontsize=8, color=TEXTO_2)
ax.tick_params(labelsize=7.5, colors=TEXTO_2, length=0)
for lado in ("top", "right", "left"):
    ax.spines[lado].set_visible(False)
ax.spines["bottom"].set_color(GRIS_CLARO)
ax.spines["bottom"].set_bounds(2013.6, 2028.4)
ax.yaxis.grid(True, color="#F3F4F6", lw=0.8); ax.set_axisbelow(True)
fig.tight_layout(pad=0.3)
guardar(fig, "figura_7_caso_bugalagrande.png", bbox_inches="tight")

print("series:", len(sel), "municipios:", len(area))
print(real.round(1).to_dict())
print((h1.assign(err_final=h1.final / h1.real - 1, err_naive=h1.naive / h1.real - 1)).round(3))
print(fut.round(1))
print("promedio 2021-2023 (miles de t):", round(prom, 1), "| base 2024 sobre el promedio:", f"{fut.loc[2024, 'oferta_base'] / prom - 1:.1%}")
