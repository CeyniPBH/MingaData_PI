"""Estilo común para las figuras de los notebooks."""
import matplotlib.pyplot as plt
from cycler import cycler

COLORES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
GRIS = "#52514e"


def estilo():
    plt.rcParams.update({
        "figure.figsize": (9, 4), "figure.dpi": 100, "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb",
        "axes.prop_cycle": cycler(color=COLORES), "axes.spines.top": False, "axes.spines.right": False,
        "axes.edgecolor": "#b5b4ad", "axes.grid": True, "grid.color": "#e6e5e0", "grid.linewidth": 0.6,
        "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlelocation": "left", "axes.labelcolor": GRIS,
        "xtick.color": GRIS, "ytick.color": GRIS, "lines.linewidth": 2, "legend.frameon": False, "font.size": 10,
    })
