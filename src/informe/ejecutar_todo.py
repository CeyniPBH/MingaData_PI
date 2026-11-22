"""Genera las figuras del informe y muestra las cifras que no están guardadas en data/results.

Uso, desde la raíz del repositorio: python src/informe/ejecutar_todo.py
Las figuras 1 a 8 quedan en docs/informe/figuras/. Las figuras 9 y 10 son capturas del tablero y no se generan con
código (ver docs/informe/README.md).
"""
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
FIGURAS = ["figura_1_frontera.py", "figura_2_area_sembrada.py", "figura_3_4_valor_y_tendencias.py",
           "figura_5_walk_forward.py", "figura_6_centrales.py", "figura_7_caso_bugalagrande.py",
           "figura_8_arquitectura.py"]
CIFRAS = ["cifras_3_2_3.py", "cifras_3_3_y_3_4.py", "cifras_hipotesis.py"]


def correr(comando, nombre):
    print(f"\n===== {nombre} =====", flush=True)
    if subprocess.run(comando, cwd=RAIZ).returncode != 0:
        sys.exit(f"Falló {nombre}; revisa el mensaje de arriba.")


if __name__ == "__main__":
    for script in FIGURAS + CIFRAS:
        correr([sys.executable, str(AQUI / script)], script)
