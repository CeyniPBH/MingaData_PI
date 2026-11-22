"""Figuras 3 y 4 del informe (sección 3.2.3): toneladas frente a valor, e índice de producción 2014 = 100.

Uso, desde la raíz del repositorio: python src/informe/figura_3_4_valor_y_tendencias.py
Lee data/clean/produccion_valle_clean.csv y data/results/ML_Ce/ranking_valor_vs_toneladas.csv.
"""
import pandas as pd

from estilo import RAIZ, AZUL, GRIS, GRIS_CLARO, TEXTO, TEXTO_2, plt, guardar

plt.rcParams.update({"font.size": 9, "axes.edgecolor": GRIS_CLARO,
                     "axes.labelcolor": TEXTO_2, "xtick.color": TEXTO_2, "ytick.color": TEXTO,
                     "savefig.dpi": 300, "savefig.bbox": "tight", "savefig.pad_inches": 0.06})
num = lambda x, d=0: f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")

# ---------- Figura 3: participación en toneladas frente a participación en valor ----------
r = pd.read_csv(RAIZ / "data/results/ML_Ce/ranking_valor_vs_toneladas.csv")
r = r[r.producto != "Caña de azúcar"].copy()
r["pct_t"] = 100 * r.produccion_t_2019_2023 / r.produccion_t_2019_2023.sum()
r["pct_v"] = 100 * r.valor_cop_2019_2023 / r.valor_cop_2019_2023.sum()
top = r.sort_values("pct_v", ascending=False).head(8).copy()
top["brecha"] = top.pct_v - top.pct_t
top = top.sort_values("brecha", ascending=False).reset_index(drop=True)
gana = top.brecha > 0
# Filas de arriba hacia abajo; los dos grupos quedan separados por un espacio.
top["y"] = [len(top) - 1 - i + (0.7 if g else 0) for i, g in enumerate(gana)]

fig, ax = plt.subplots(figsize=(6.3, 3.7))
for _, f in top.iterrows():
    ax.plot([f.pct_t, f.pct_v], [f.y, f.y], color=GRIS_CLARO, lw=2.2, zorder=1, solid_capstyle="round")
ax.scatter(top.pct_t, top.y, s=48, color=GRIS, zorder=2, edgecolor="white", linewidth=1.2)
ax.scatter(top.pct_v, top.y, s=48, color=AZUL, zorder=3, edgecolor="white", linewidth=1.2)
for _, f in top.iterrows():
    izq, der = sorted([(f.pct_t, GRIS), (f.pct_v, AZUL)], key=lambda v: v[0])
    ax.text(izq[0] - 0.7, f.y, num(izq[0], 1) + " %", ha="right", va="center", fontsize=8,
            color=TEXTO_2 if izq[1] == GRIS else AZUL)
    ax.text(der[0] + 0.7, f.y, num(der[0], 1) + " %", ha="left", va="center", fontsize=8,
            color=TEXTO_2 if der[1] == GRIS else AZUL)
# Leyenda directa sobre la primera fila
f0 = top.iloc[0]
ax.text(f0.pct_t, f0.y + 0.42, "toneladas", ha="center", va="bottom", fontsize=7.5, color=TEXTO_2)
ax.text(f0.pct_v, f0.y + 0.42, "valor", ha="center", va="bottom", fontsize=7.5, color=AZUL, fontweight="bold")
ax.set_yticks(top.y)
ax.set_yticklabels(top.producto)
for lab in ax.get_yticklabels():
    if lab.get_text() in ("Café", "Caña panelera"):
        lab.set_fontweight("bold")
y_corte = (top.y[gana].min() + top.y[~gana].max()) / 2
ax.axhline(y_corte, color="#E5E7EB", lw=0.8, zorder=0)
ax.text(31, top.y[gana].mean(), "Más peso en valor\nque en toneladas", ha="right", va="center", fontsize=7.5,
        color=AZUL, linespacing=1.15)
ax.text(31, top.y[~gana].mean(), "Más peso en toneladas\nque en valor", ha="right", va="center", fontsize=7.5,
        color=TEXTO_2, linespacing=1.15)
ax.set_xlim(-3, 31)
ax.set_ylim(top.y.min() - 0.6, top.y.max() + 1.0)
ax.set_xticks(range(0, 31, 5))
ax.set_xticklabels([f"{v} %" for v in range(0, 31, 5)])
ax.set_xlabel("Participación en el total sin caña de azúcar, 2019-2023")
ax.grid(axis="x", color="#EEF0F3", lw=0.8)
ax.set_axisbelow(True)
for lado in ["top", "right", "left"]:
    ax.spines[lado].set_visible(False)
ax.tick_params(axis="y", length=0)
ax.tick_params(axis="x", length=0)
guardar(fig, "figura_3_valor_vs_toneladas.png")
print(top[["producto", "pct_t", "pct_v", "brecha"]].round(1).to_string(index=False))

# ---------- Figura 4: índice de producción 2014 = 100, un panel por producto ----------
# Pequeños múltiplos en lugar de una sola gráfica de líneas: con ocho series, seis quedaban amontonadas
# entre 55 y 125. Cada panel resalta un producto y deja los otros siete en gris como referencia. El eje
# es logarítmico para que duplicarse y caer a la mitad queden a la misma distancia de la línea de 100.
from matplotlib.ticker import FixedLocator, NullLocator

c = pd.read_csv(RAIZ / "data/clean/produccion_valle_clean.csv")
s = c[(c.anio.between(2019, 2023)) & (c.producto != "Caña de azúcar")]
prods = list(s.groupby("producto").produccion_t.sum().sort_values(ascending=False).head(8).index)
t = c[c.anio.between(2014, 2023) & c.producto.isin(prods)].groupby(["producto", "anio"]).produccion_t.sum().unstack()
idx = t.div(t[2014], axis=0) * 100
orden = list(idx[2023].sort_values(ascending=False).index)  # del que más creció al que más cayó
anios = list(idx.columns)

fig, axes = plt.subplots(2, 4, figsize=(6.3, 3.25), sharex=True, sharey=True)
for ax, p in zip(axes.flat, orden):
    ax.hlines(100, 2014, 2023, color=GRIS, lw=0.7, ls=(0, (2, 2)), zorder=1)
    for q in orden:
        if q != p:
            ax.plot(anios, idx.loc[q], color="#E5E7EB", lw=0.9, zorder=2)
    ax.plot(anios, idx.loc[p], color=AZUL, lw=1.8, zorder=3, solid_capstyle="round")
    v = idx.loc[p, 2023]
    ax.scatter([2023], [v], s=10, color=AZUL, zorder=4)
    ax.text(2023.5, v, num(v), color=AZUL, fontsize=8, fontweight="bold", va="center", ha="left")
    ax.set_title(p, loc="left", fontsize=8.5, color=TEXTO, pad=3,
                 fontweight="bold" if p in ("Aguacate", "Café") else "normal")
    ax.set_yscale("log")
    ax.set_ylim(45, 560)
    ax.yaxis.set_major_locator(FixedLocator([50, 100, 200, 400]))
    ax.yaxis.set_minor_locator(NullLocator())
    ax.set_yticklabels(["50", "100", "200", "400"])
    ax.set_xlim(2013.6, 2026.2)
    ax.set_xticks([2014, 2023])
    ax.grid(axis="y", color="#EEF0F3", lw=0.6)
    ax.set_axisbelow(True)
    for lado in ["top", "right", "left", "bottom"]:
        ax.spines[lado].set_visible(False)
    ax.tick_params(length=0, labelsize=7.5)
# El pico del aguacate en 2022 lleva su valor, porque la caída de 2023 es parte de la historia.
ax0 = axes.flat[0]
pico = idx.loc[orden[0]].idxmax()
ax0.annotate(f"{num(idx.loc[orden[0], pico])} en {pico}", xy=(pico, idx.loc[orden[0], pico]),
             xytext=(2015.0, idx.loc[orden[0], pico]), fontsize=7, color=TEXTO_2, va="center",
             arrowprops=dict(arrowstyle="-", color=GRIS, lw=0.6))
fig.supylabel("Índice de producción (2014 = 100), escala logarítmica", fontsize=8, color=TEXTO_2, x=0.005)
fig.subplots_adjust(wspace=0.12, hspace=0.42)
guardar(fig, "figura_4_tendencias_2014_2023.png")
print("Productos de la Figura 4:", ", ".join(f"{p} {num(idx.loc[p, 2023])}" for p in orden))
