"""Figura 5 del informe (sección 3.3.3): esquema de la validación walk-forward (orígenes 2018-2022, horizontes 1-5).

La línea punteada separa los años que usó la búsqueda de hiperparámetros (objetivos hasta 2021) de los que
quedaron fuera de ella (2022 y 2023), según docs/ML_C/tuning.md.

Uso, desde la raíz del repositorio: python src/informe/figura_5_walk_forward.py
"""
from matplotlib.patches import FancyBboxPatch

from estilo import AZUL, GRIS_CLARO, TEXTO, TEXTO_2, plt, guardar

# Columnas: un bloque comprimido 2000-2017 (ancho 2) y luego un año por columna
cols = [("2000-2017", 0.0, 2.0)] + [(str(a), 2.0 + i, 1.0) for i, a in enumerate(range(2018, 2024))]
x_ini = {c[0]: c[1] for c in cols}
origenes = [2018, 2019, 2020, 2021, 2022]
alto, paso, gap = 0.62, 1.0, 0.06

fig, ax = plt.subplots(figsize=(6.1, 2.65), dpi=300)
for fila, O in enumerate(origenes):
    y = -fila * paso
    fin_ent = x_ini[str(O)] + 1.0                       # el entrenamiento llega hasta el año de origen
    ax.add_patch(FancyBboxPatch((0 + gap / 2, y - alto / 2), fin_ent - gap, alto,
                                boxstyle="round,pad=0,rounding_size=0.08", fc=GRIS_CLARO, ec="none"))
    if fila == 0:
        ax.text(fin_ent / 2, y, "Entrenamiento", ha="center", va="center", fontsize=8, color=TEXTO)
    for h, a in enumerate(range(O + 1, 2024), start=1):
        x0 = x_ini[str(a)]
        ax.add_patch(FancyBboxPatch((x0 + gap / 2, y - alto / 2), 1.0 - gap, alto,
                                    boxstyle="round,pad=0,rounding_size=0.08", fc=AZUL, ec="none"))
        ax.text(x0 + 0.5, y, f"h{h}", ha="center", va="center", fontsize=8, color="white", fontweight="bold")
    ax.text(-0.15, y, f"Origen {O}", ha="right", va="center", fontsize=8, color=TEXTO)

# Eje de años abajo
y_eje = -(len(origenes) - 1) * paso - alto / 2 - 0.25
for nombre, x0, w in cols:
    ax.text(x0 + w / 2, y_eje, nombre, ha="center", va="top", fontsize=7.5, color=TEXTO_2)
ax.text(8.0 + 0.05, 0, "Años evaluados\n(h = horizonte)", ha="left", va="center", fontsize=7.5, color=AZUL)

# Corte de la búsqueda de hiperparámetros: solo vio años objetivo hasta 2021.
x_corte = x_ini["2022"]
ax.plot([x_corte, x_corte], [y_eje + 0.12, 0.62], color=TEXTO_2, lw=0.8, ls=(0, (3, 2)), zorder=0)
ax.text(x_corte - 0.1, 0.78, "Búsqueda de hiperparámetros: años hasta 2021", ha="right", va="center",
        fontsize=7.5, color=TEXTO_2)
ax.text(x_corte + 0.1, 0.78, "Fuera de la búsqueda", ha="left", va="center", fontsize=7.5, color=TEXTO_2)

ax.set_xlim(-1.75, 9.6)
ax.set_ylim(y_eje - 0.45, 0.95)
ax.axis("off")
fig.tight_layout(pad=0.2)
guardar(fig, "figura_5_walk_forward.png", bbox_inches="tight")
print("ok")
