"""Figura 8 del informe (sección 4.1): arquitectura del pipeline de extremo a extremo.

Uso, desde la raíz del repositorio: python src/informe/figura_8_arquitectura.py
Carril de arriba: lo que está implementado. Las cajas azules corren en la nube (S3, Render y Streamlit Cloud) y las
grises en el computador del equipo. Carril de abajo, punteado: el despliegue hipotético en AWS para una implementación real, que no
está implementado. Las seis etapas son las que pide la rúbrica de SI7006: origen, ingesta, almacenamiento,
procesamiento, despliegue y consumo. El contenido sale de docs/arquitectura/ y docs/evaluacion/evidencia_despliegue.md.
"""
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from estilo import AZUL, FONDO, GRIS, TEXTO, TEXTO_2, plt, guardar

AZUL_CLARO = "#E6EAF0"  # fondo de las cajas que corren en la nube
etapas = ["Origen", "Ingesta", "Almacenamiento", "Procesamiento\ny modelos", "Despliegue", "Consumo"]
hoy = [  # (texto, corre en la nube)
    ("Fuentes públicas:\nGobernación,\nDANE, FAOSTAT,\nNOAA, ICA\ny GADM", False),
    ("Scripts y\ndescarga manual\nHuella SHA-256\nValidación antes\nde cada ejecución", False),
    ("raw, trusted\ny refined\nCSV y Parquet\npor año\nCatálogo de\n37 tablas", False),
    ("pandas en\nun solo nodo\nLightGBM, Ward\ny OR-Tools\nrun_all.py:\n9 etapas", False),
    ("S3: modelo\ncon versión\ny base DuckDB\nAPI FastAPI\nen Render", True),
    ("Tablero en\nStreamlit Cloud\nconsume la API\ny los Parquet", True),
]
escala = [
    "Mismas fuentes\nAPI de\ndatos.gov.co",
    "EventBridge\ny Lambda\ncada mes\nCuarentena y\naviso por SNS",
    "S3 por zonas\nParquet\npor año\nGlue Data\nCatalog",
    "Glue con\nPySpark\nSageMaker\nECS: escenarios\nen paralelo",
    "Modelo con\nversión en S3\nAPI Gateway\ny Lambda",
    "Athena y\nDynamoDB\nStreamlit en\nECS Express\nMode",
]

W, H = 100.0, 62.0
fig = plt.figure(figsize=(6.3, 3.91), dpi=300)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")

x0, ancho, sep = 7.6, 13.4, 2.34
xs = [x0 + i * (ancho + sep) for i in range(len(etapas))]
y_hoy, y_esc, alto = 34.4, 7.2, 19.0

for x, e in zip(xs, etapas):
    ax.text(x + ancho / 2, 58.6, e, ha="center", va="center", fontsize=7.0, fontweight="bold", color=TEXTO,
            linespacing=1.05)


def caja(x, y, texto, fc, ec, ls, color):
    ax.add_patch(FancyBboxPatch((x, y), ancho, alto, boxstyle="round,pad=0,rounding_size=1.1",
                                fc=fc, ec=ec, lw=0.9, ls=ls))
    ax.text(x + ancho / 2, y + alto / 2, texto, ha="center", va="center", fontsize=6.6, color=color, linespacing=1.2)


def flecha(x1, x2, y, color, ls="-"):
    ax.add_patch(FancyArrowPatch((x1 + 0.3, y), (x2 - 0.3, y), arrowstyle="-|>", mutation_scale=7, lw=0.9,
                                 color=color, linestyle=ls))


# Carril implementado
ax.text(3.3, y_hoy + alto / 2, "Implementado", rotation=90, ha="center", va="center", fontsize=7.4,
        fontweight="bold", color=TEXTO)
for i, (x, (texto, nube)) in enumerate(zip(xs, hoy)):
    caja(x, y_hoy, texto, AZUL_CLARO if nube else FONDO, AZUL if nube else GRIS, "-", TEXTO)
    if i < len(xs) - 1:
        flecha(x + ancho, xs[i + 1], y_hoy + alto / 2, AZUL if hoy[i + 1][1] else GRIS)
ax.text(xs[4] + ancho + sep / 2, y_hoy + alto + 1.4, "En la nube", ha="right", va="bottom", fontsize=6.6,
        color=AZUL, fontweight="bold")
ax.plot([xs[4] - 0.2, xs[5] + ancho + 0.2], [y_hoy + alto + 0.9] * 2, color=AZUL, lw=0.8)

# Carril de diseño a escala (no implementado)
ax.text(3.3, y_esc + alto / 2, "Despliegue\nhipotético en AWS", rotation=90, ha="center", va="center", fontsize=7.0,
        fontweight="bold", color=TEXTO_2, linespacing=1.1)
for i, (x, texto) in enumerate(zip(xs, escala)):
    caja(x, y_esc, texto, "white", GRIS, (0, (3, 2)), TEXTO_2)
    if i < len(xs) - 1:
        flecha(x + ancho, xs[i + 1], y_esc + alto / 2, GRIS)


def franja(y, texto, ec, ls, color):
    ax.add_patch(FancyBboxPatch((xs[0], y), xs[-1] + ancho - xs[0], 4.0, boxstyle="round,pad=0,rounding_size=1.0",
                                fc="white", ec=ec, lw=0.8, ls=ls))
    ax.text((xs[0] + xs[-1] + ancho) / 2, y + 2.0, texto, ha="center", va="center", fontsize=6.4, color=color)


franja(29.0, "GitHub versiona código, datos y resultados; las credenciales de AWS solo existen como variables de entorno en Render",
       GRIS, "-", TEXTO_2)
franja(2.0, "Step Functions orquestaría la cadena cada mes; IAM daría a cada servicio solo los permisos que necesita",
       GRIS, (0, (3, 2)), TEXTO_2)

guardar(fig, "figura_8_arquitectura.png", bbox_inches="tight", pad_inches=0.03)
