"""Compara la ubicación de la central con y sin ONI, escenario por escenario.

Es la última prueba de la decisión de mantener el ONI (docs/ML_C/sensibilidad_oni.md). Necesita una corrida
completa sin ONI en una copia del proyecto: `usar_oni: false`, 06_lgbm.py, 07_escenarios.py, excedentes y
escenarios de arendonc2 y `generar_resultados.py --solo estabilidad`. Lee data/results/opt/estabilidad_escenarios.csv
de las dos carpetas y escribe data/results/ML_Ce/sensibilidad_oni_optimizacion.csv.
Uso: python src/ML_C/07c_comparar_oni_optimizacion.py --sin-oni ../MingaData_PI_sinONI
"""
import argparse
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / "data/results/ML_Ce"
LLAVE = ["anio", "id_escenario"]
INFO = ["oferta", "consumo", "mezcla", "es_base"]
COMPARA = ["central", "satelites", "cobertura", "A", "B", "costo_total_suma"]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sin-oni", required=True, type=Path, help="raíz de la copia del proyecto corrida con usar_oni: false")
    args = ap.parse_args()
    of = pd.read_csv(ROOT / "data/results/opt/estabilidad_escenarios.csv")
    sn = pd.read_csv(args.sin_oni / "data/results/opt/estabilidad_escenarios.csv")
    m = of[LLAVE + INFO + COMPARA].merge(sn[LLAVE + COMPARA], on=LLAVE, suffixes=("_oficial", "_sin_oni"))
    if len(m) != len(of):
        raise SystemExit(f"Las corridas no tienen los mismos escenarios ({len(of)} oficiales, {len(m)} en común).")
    m["misma_central"] = m["central_oficial"] == m["central_sin_oni"]
    m["mismos_satelites"] = m["satelites_oficial"] == m["satelites_sin_oni"]
    for c in ("A", "B", "costo_total_suma"):
        m[f"dif_rel_{c}"] = m[f"{c}_sin_oni"] / m[f"{c}_oficial"] - 1
    for v in ("oficial", "sin_oni"):
        m[f"participacion_distribucion_{v}"] = m[f"B_{v}"] / (m[f"A_{v}"] + m[f"B_{v}"])
    m.round(6).to_csv(RES / "sensibilidad_oni_optimizacion.csv", index=False, encoding="utf-8-sig")

    print(f"Escenarios: {len(m)} | misma central: {int(m.misma_central.sum())} | mismos satélites: {int(m.mismos_satelites.sum())}")
    print("Centrales oficiales:", of["central"].value_counts().to_dict())
    print("Centrales sin ONI:  ", sn["central"].value_counts().to_dict())
    d = m["dif_rel_costo_total_suma"]
    print(f"Costo físico total sin ONI frente al oficial: mínimo {d.min():+.1%}, mediana {d.median():+.1%}, máximo {d.max():+.1%}")
    b = m[m["es_base"].astype(str) == "True"]
    print(b[["anio", "central_oficial", "central_sin_oni", "participacion_distribucion_oficial",
             "participacion_distribucion_sin_oni", "cobertura_oficial", "cobertura_sin_oni"]].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
