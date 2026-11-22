"""Métricas del modelo final del pronóstico: promedio del ingenuo y LightGBM en los productos detallados.

Usa las mismas filas del walk-forward que 06_lgbm.py (predicciones_comparacion.csv) y escribe
data/results/ML_Ce/metricas_modelo_final.csv con el ingenuo, LightGBM y el modelo final (naive_lgbm):
- alcance "todos", horizonte "todos": cada producto detallado y el TOTAL;
- alcance "sin_cana", horizonte "todos": TOTAL sin caña de azúcar, que es la mayor parte de las toneladas y domina el WAPE;
- alcance "todos", horizonte 1 a 5: TOTAL por horizonte.
No reentrena nada, así que no necesita lightgbm. Uso: python src/ML_C/06c_metricas_modelo_final.py
"""
from importlib import import_module
import pandas as pd
from common import RES

MODELOS = ("naive", "lgbm", "naive_lgbm")
CANA = "Caña de azúcar"


def main():
    comp = pd.read_csv(RES / "predicciones_comparacion.csv", dtype={"cod_dane": str})
    comp["naive_lgbm"] = (comp["naive"] + comp["lgbm"]) / 2          # modelo final de los detallados
    metricas = import_module("05_baselines").metricas
    partes = [metricas(comp, modelos=MODELOS).assign(alcance="todos", horizonte="todos"),
              metricas(comp[comp["producto"] != CANA], modelos=MODELOS).query("producto == 'TOTAL'")
              .assign(alcance="sin_cana", horizonte="todos")]
    for h, g in comp.groupby("horizonte"):
        partes.append(metricas(g, modelos=MODELOS).query("producto == 'TOTAL'").assign(alcance="todos", horizonte=str(h)))
    res = pd.concat(partes, ignore_index=True)
    res = res[["alcance", "horizonte"] + [c for c in res.columns if c not in ("alcance", "horizonte")]]
    res.round(4).to_csv(RES / "metricas_modelo_final.csv", index=False, encoding="utf-8-sig")

    final = res[res["modelo"] == "naive_lgbm"]
    print(final[final["producto"] == "TOTAL"][["alcance", "horizonte", "MASE", "WAPE",
                                              "mejora_MASE_vs_naive", "mejora_WAPE_vs_naive"]].to_string(index=False))
    pp = final[(final["producto"] != "TOTAL") & (final["horizonte"] == "todos")]
    gana = ((pp["mejora_MASE_vs_naive"] > 0) & (pp["mejora_WAPE_vs_naive"] > 0)).sum()
    print(f"El modelo final mejora MASE y WAPE a la vez en {gana} de {len(pp)} productos.")


if __name__ == "__main__":
    main()
