"""Corre el módulo completo en orden. Uso: python src/ML_C/ejecutar_todo.py [--sin-modelos]

--sin-modelos corre solo datos (00-04) y el validador; útil si no se tiene lightgbm/statsmodels instalados.
"""
import subprocess, sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
PASOS = ["00_descargar_datos.py", "00b_validar_ingesta.py", "01_limpieza.py", "02_diagnostico.py", "03_geo_tiempos.py",
         "04_fuentes_externas.py", "05_baselines.py", "06_lgbm.py", "07_escenarios.py", "08_validar_entregas.py"]

if __name__ == "__main__":
    pasos = [p for p in PASOS if not ("--sin-modelos" in sys.argv and p[:2] in ("05", "06", "07"))]
    for p in pasos:
        print(f"\n===== {p} =====", flush=True)
        r = subprocess.run([sys.executable, str(AQUI / p)], cwd=AQUI.parents[1])
        if r.returncode != 0:
            sys.exit(f"Falló {p}; revisa el mensaje de arriba.")
