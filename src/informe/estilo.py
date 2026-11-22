"""Estilo común de las figuras del informe: paleta del curso de Visualización, tipografía y carpeta de salida.

Las figuras se guardan en docs/informe/figuras/ a 300 dpi. La tipografía es Liberation Sans en Linux y Arial en
macOS y Windows; las dos tienen las mismas medidas, así que la composición no cambia entre equipos.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
SALIDA = RAIZ / "docs" / "informe" / "figuras"

# Azul del curso para el dato que importa; grises para el contexto.
AZUL, GRIS, GRIS_CLARO, FONDO, TEXTO, TEXTO_2 = "#002855", "#9CA3AF", "#D1D5DB", "#F3F4F6", "#1F2937", "#6B7280"

plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Liberation Sans", "Arial", "Helvetica", "DejaVu Sans"]


def num(x, decimales=0):
    """Número con punto de miles y coma decimal: 86348.2 -> '86.348'."""
    return f"{x:,.{decimales}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def guardar(fig, nombre, **opciones):
    """Guarda la figura en docs/informe/figuras/<nombre> y devuelve la ruta."""
    SALIDA.mkdir(parents=True, exist_ok=True)
    ruta = SALIDA / nombre
    fig.savefig(ruta, dpi=300, facecolor="white", **opciones)
    plt.close(fig)
    print("Figura guardada en", ruta.relative_to(RAIZ))
    return ruta
