"""Figura 1 del informe (sección 3.1.4): frontera entre el aprendizaje automático y la optimización.

Uso, desde la raíz del repositorio: python src/informe/figura_1_frontera.py
Esquema dibujado con matplotlib, sin datos. Los íconos son figuras geométricas simples.
"""
import numpy as np
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle, Wedge

from estilo import AZUL, FONDO, GRIS, GRIS_CLARO, TEXTO, TEXTO_2, guardar, plt

OSCURO = "#4B5563"
fig = plt.figure(figsize=(7.0, 3.9))
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 140)
ax.set_ylim(0, 78)
ax.set_aspect("equal")
ax.axis("off")


def panel(x0, y0, x1, y1, titulo):
    ax.add_patch(FancyBboxPatch((x0, y0), x1 - x0, y1 - y0, boxstyle="round,pad=0,rounding_size=2.2",
                                facecolor=FONDO, edgecolor=GRIS_CLARO, linewidth=0.8, zorder=0))
    ax.text(x0 + 2.2, y1 - 2.6, titulo, fontsize=6.8, color=TEXTO_2, va="top", ha="left")


def flecha(p, q, color=GRIS, estilo="-", texto=None, desplazamiento=(0, 0), rad=0.0):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=7, color=color, linewidth=0.9,
                                 linestyle=estilo, shrinkA=0, shrinkB=0, connectionstyle=f"arc3,rad={rad}",
                                 zorder=2))
    if texto:
        mx, my = (p[0] + q[0]) / 2 + desplazamiento[0], (p[1] + q[1]) / 2 + desplazamiento[1]
        ax.text(mx, my, texto, fontsize=6.3, color=TEXTO_2, ha="center", va="center", zorder=3,
                bbox=dict(facecolor=FONDO, edgecolor="none", pad=0.4))


def rotulo(x, y, titulo, detalle, color_titulo=TEXTO, tam=7.6):
    ax.text(x, y, titulo, fontsize=tam, fontweight="bold", color=color_titulo, ha="center", va="top", zorder=3)
    ax.text(x, y - 3.3, detalle, fontsize=6.3, color=TEXTO_2, ha="center", va="top", linespacing=1.25, zorder=3)


# ---------- Íconos ----------
def icono_pronostico(cx, cy, s=1.0):
    x0, y0, w, h = cx - 6 * s, cy - 4.5 * s, 12 * s, 9 * s
    ax.plot([x0, x0, x0 + w], [y0 + h, y0, y0], color=OSCURO, lw=1.0, solid_capstyle="round", zorder=3)
    hx = x0 + np.array([0.8, 2.6, 4.2, 5.6, 7.0]) * s
    hy = y0 + np.array([3.0, 4.6, 3.6, 5.2, 4.8]) * s
    ax.plot(hx, hy, color=OSCURO, lw=1.3, solid_capstyle="round", zorder=4)
    fx = np.array([hx[-1], x0 + 11.2 * s])
    ax.add_patch(Polygon([(fx[0], hy[-1]), (fx[1], y0 + 8.2 * s), (fx[1], y0 + 2.4 * s)], closed=True,
                         facecolor=GRIS_CLARO, edgecolor="none", zorder=3))
    ax.plot(fx, [hy[-1], y0 + 5.3 * s], color=OSCURO, lw=1.1, linestyle=(0, (2, 1.4)), zorder=4)


def icono_mapa(cx, cy, s=1.0):
    piezas = [
        [(-6, 3), (-1, 5), (0, 1), (-2, -1), (-6, -1)],
        [(-1, 5), (5, 4.5), (6, 0.5), (0, 1)],
        [(-6, -1), (-2, -1), (0, 1), (1, -4), (-5, -5)],
        [(0, 1), (6, 0.5), (5.5, -4.5), (1, -4)],
    ]
    tonos = ["#9CA3AF", "#C4C9D1", "#D1D5DB", "#B3B9C2"]
    for pieza, tono in zip(piezas, tonos):
        ax.add_patch(Polygon([(cx + x * s, cy + y * s) for x, y in pieza], closed=True, facecolor=tono,
                             edgecolor="white", linewidth=1.0, zorder=3))


def icono_excedente(cx, cy, s=1.0):
    base = cy - 4.5 * s
    ax.add_patch(Rectangle((cx - 4.5 * s, base), 3.6 * s, 9 * s, facecolor=OSCURO, edgecolor="none", zorder=3))
    ax.add_patch(Rectangle((cx + 0.9 * s, base), 3.6 * s, 4.2 * s, facecolor=GRIS, edgecolor="none", zorder=3))
    ax.plot([cx + 0.9 * s, cx + 4.5 * s], [base + 9 * s] * 2, color=OSCURO, lw=0.8, linestyle=(0, (1.5, 1)), zorder=3)
    ax.annotate("", xy=(cx + 2.7 * s, base + 4.4 * s), xytext=(cx + 2.7 * s, base + 8.8 * s),
                arrowprops=dict(arrowstyle="<->", color=AZUL, lw=0.9, shrinkA=0, shrinkB=0), zorder=4)


def icono_engranaje(cx, cy, r=5.0, dientes=8):
    pts = []
    for k in range(dientes * 2):
        ang0 = np.pi * k / dientes
        radio = r if k % 2 == 0 else r * 0.78
        for a in (ang0 - np.pi / (dientes * 2) * 0.55, ang0 + np.pi / (dientes * 2) * 0.55):
            pts.append((cx + radio * np.cos(a), cy + radio * np.sin(a)))
    ax.add_patch(Polygon(pts, closed=True, facecolor=OSCURO, edgecolor="none", zorder=3))
    ax.add_patch(Circle((cx, cy), r * 0.34, facecolor=FONDO, edgecolor="none", zorder=4))


def pin(x, y, s=1.0, color=OSCURO):
    ax.add_patch(Circle((x, y + 1.2 * s), 1.1 * s, facecolor=color, edgecolor="none", zorder=5))
    ax.add_patch(Polygon([(x - 0.95 * s, y + 0.75 * s), (x + 0.95 * s, y + 0.75 * s), (x, y - 0.9 * s)],
                         closed=True, facecolor=color, edgecolor="none", zorder=5))
    ax.add_patch(Circle((x, y + 1.2 * s), 0.42 * s, facecolor="white", edgecolor="none", zorder=6))


def icono_central(cx, cy, s=1.0):
    ax.add_patch(Rectangle((cx - 4 * s, cy - 4 * s), 8 * s, 5.2 * s, facecolor=OSCURO, edgecolor="none", zorder=3))
    ax.add_patch(Polygon([(cx - 5 * s, cy + 1.2 * s), (cx, cy + 4.6 * s), (cx + 5 * s, cy + 1.2 * s)], closed=True,
                         facecolor=OSCURO, edgecolor="none", zorder=3))
    ax.add_patch(Rectangle((cx - 1.4 * s, cy - 4 * s), 2.8 * s, 3.3 * s, facecolor=FONDO, edgecolor="none", zorder=4))
    for dx, dy in [(-9, 3), (-8.5, -4.5), (8.5, 4), (9, -3.5), (0.5, -9)]:
        pin(cx + dx * s, cy + dy * s, s=0.85)


def icono_camion(cx, cy, s=1.0):
    ax.add_patch(Rectangle((cx - 3.6 * s, cy - 1.2 * s), 4.6 * s, 3.0 * s, facecolor=GRIS, edgecolor="none", zorder=3))
    ax.add_patch(Polygon([(cx + 1.2 * s, cy - 1.2 * s), (cx + 1.2 * s, cy + 1.2 * s), (cx + 2.6 * s, cy + 1.2 * s),
                          (cx + 3.4 * s, cy), (cx + 3.4 * s, cy - 1.2 * s)], closed=True, facecolor=GRIS,
                         edgecolor="none", zorder=3))
    for wx in (cx - 2.3 * s, cx + 2.2 * s):
        ax.add_patch(Circle((wx, cy - 1.4 * s), 0.75 * s, facecolor=OSCURO, edgecolor="white", linewidth=0.6, zorder=4))


def icono_reloj(cx, cy, s=1.0):
    ax.add_patch(Circle((cx, cy), 2.0 * s, facecolor="white", edgecolor=GRIS, linewidth=1.0, zorder=3))
    ax.plot([cx, cx], [cy, cy + 1.3 * s], color=OSCURO, lw=0.9, zorder=4)
    ax.plot([cx, cx + 1.0 * s], [cy, cy - 0.4 * s], color=OSCURO, lw=0.9, zorder=4)


def tabla_frontera(cx, cy, titulo, detalle, h=8.4):
    w = 15.5
    ax.add_patch(FancyBboxPatch((cx - w / 2, cy - h / 2), w, h, boxstyle="round,pad=0,rounding_size=1.2",
                                facecolor=AZUL, edgecolor="none", zorder=4))
    ax.text(cx, cy + h / 2 - 2.4, titulo, fontsize=7.2, fontweight="bold", color="white", ha="center", va="center",
            zorder=5)
    ax.text(cx, cy + h / 2 - 4.6, detalle, fontsize=6.0, color="white", ha="center", va="top", linespacing=1.2,
            zorder=5)


def codo(puntos, color=AZUL):
    """Línea con quiebres que termina en flecha."""
    xs, ys = zip(*puntos[:-1])
    ax.plot(xs, ys, color=color, lw=0.9, zorder=2, solid_joinstyle="round")
    flecha(puntos[-2], puntos[-1], color=color)


# ---------- Composición ----------
panel(3, 3, 52, 75, "APRENDIZAJE AUTOMÁTICO")
panel(73, 18, 137, 75, "OPTIMIZACIÓN (OR-Tools)")

icono_pronostico(15, 47, s=0.95)
rotulo(15, 39.5, "Pronóstico", "LightGBM global\ny 4 modelos de referencia\n2024-2028 en escenarios\nbajo, base y alto")
icono_mapa(40, 60, s=0.95)
rotulo(40, 52.5, "Zonas de acopio", "Ward con vecindad\ntipo reina")
icono_excedente(40, 28, s=0.95)
rotulo(40, 20.5, "Excedentes", "oferta menos\nconsumo local")
flecha((22, 50), (32, 58), texto="valor", desplazamiento=(-2.4, 1.8))
flecha((22, 44), (32, 31), texto="toneladas", desplazamiento=(4.2, 0.6))

ax.plot([62.5, 62.5], [1, 76], color=AZUL, lw=1.0, linestyle=(0, (4, 2.5)), zorder=1)
ax.text(62.5, 77.2, "FRONTERA", fontsize=7.0, fontweight="bold", color=AZUL, ha="center", va="center")
tabla_frontera(62.5, 60, "Zonas", "municipio → zona")
tabla_frontera(62.5, 28, "Excedentes", "municipio × año\n9 escenarios", h=10.4)
flecha((47, 60), (54.6, 60), color=AZUL)
flecha((47, 28), (54.6, 28), color=AZUL)

icono_engranaje(88, 46, r=5.4)
rotulo(88, 38.5, "Modelo de localización", "minimiza λ·A + (1 − λ)·B\nA: recolección, B: distribución\nen toneladas × minutos", tam=7.2)
codo([(70.4, 60), (75.5, 60), (75.5, 46), (82.2, 46)])
codo([(70.4, 28), (75.5, 28), (75.5, 46), (82.2, 46)])
icono_central(121, 48, s=0.95)
rotulo(121, 38.5, "1 central y 5 satélites", "frontera de Pareto\ny estabilidad en\n27 escenarios por año", tam=7.2)
flecha((95, 46), (107, 46))

ax.add_patch(FancyBboxPatch((76, 3), 58, 11, boxstyle="round,pad=0,rounding_size=1.5", facecolor="white",
                            edgecolor=GRIS, linewidth=0.8, linestyle=(0, (3, 2)), zorder=1))
ax.text(78.5, 12.6, "SUPUESTOS EXTERNOS", fontsize=5.8, color=TEXTO_2, ha="left", va="top")
icono_camion(82.5, 7.2, s=0.95)
ax.text(87.5, 7.4, "Mezcla de mercados\n80/20, 50/50, 20/80", fontsize=6.2, color=TEXTO_2, va="center", ha="left")
icono_reloj(108.5, 7.2, s=1.0)
ax.text(112, 7.4, "Tiempos de viaje\n42 municipios, 5 destinos", fontsize=6.2, color=TEXTO_2, va="center", ha="left")
flecha((105, 14), (105, 18), color=GRIS, estilo=(0, (2.5, 2)))

guardar(fig, "figura_1_frontera_ml_optimizacion.png", bbox_inches="tight", pad_inches=0.04)
