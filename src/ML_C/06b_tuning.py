"""Búsqueda pequeña de hiperparámetros de LightGBM sin tocar 2022/2023.

Diseño anti-fuga:
  - La selección usa walk-forward con orígenes 2018-2020 y objetivos <= 2021.
  - 2022 y 2023 NO participan en la selección. Solo se reportan al final como
    verificación de holdout, comparando la configuración actual con la mejor.
  - No se sobrescribe config/ML_C/parametros.yaml ni el modelo final.

Uso:
    python src/ML_C/06b_tuning.py
    python src/ML_C/06b_tuning.py --rapido   # menos candidatos
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from common import CFG, RES, cargar_oni, cargar_panel

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import importlib  # noqa: E402

m5 = importlib.import_module("05_baselines")
m6 = importlib.import_module("06_lgbm")

ACTUAL = {k: v for k, v in CFG["lightgbm"].items()}
ORIGENES_TUNING = [o for o in m6.ORIGENES if o <= 2020]       # objetivos <= 2021
ORIGENES_HOLDOUT = [o for o in m6.ORIGENES if o >= 2021]      # objetivos 2022-2023


def _candidatos(rapido: bool = False) -> list[dict]:
    base = dict(ACTUAL)
    variantes = [
        {},
        {"learning_rate": 0.02},
        {"learning_rate": 0.05},
        {"num_leaves": 7},
        {"num_leaves": 31},
        {"min_child_samples": 10},
        {"min_child_samples": 50},
        {"n_estimators": 500, "learning_rate": 0.02},
        {"n_estimators": 200, "learning_rate": 0.05},
        {"subsample": 0.7, "colsample_bytree": 0.7},
        {"subsample": 1.0, "colsample_bytree": 1.0},
        {"reg_lambda": 0.0},
        {"reg_lambda": 5.0},
        {"num_leaves": 31, "min_child_samples": 10, "learning_rate": 0.02, "n_estimators": 500},
    ]
    if rapido:
        variantes = variantes[:7]
    salida = []
    for i, cambio in enumerate(variantes):
        params = dict(base)
        params.update(cambio)
        params["n_jobs"] = 1
        params["random_state"] = 42
        salida.append({"candidato": i, "params": params,
                       "cambio": json.dumps(cambio, ensure_ascii=False)})
    return salida


def _entrenar(params: dict, train: pd.DataFrame, test: pd.DataFrame):
    import lightgbm as lgb

    cols = [c for c in m6.features(train, "oni_t" in train.columns) if c in train.columns]
    modelo = lgb.LGBMRegressor(**params).fit(train[cols], train["target"])
    pred = test.copy()
    pred["pred_log_cambio"] = modelo.predict(pred[cols])
    pred["lgbm"] = np.maximum(np.expm1(pred["log_last"] + pred["pred_log_cambio"]), 0.0)
    return pred


def _evaluar(series, estado, oni, params: dict, origenes: list[int],
             limite_objetivo: int | None = None) -> pd.DataFrame:
    """Devuelve filas con real, naive, escala_mase, lgbm y ensemble para los orígenes dados."""
    d = m6.construir_filas(series, estado, oni)
    base = pd.read_csv(RES / "predicciones_baselines.csv", dtype={"cod_dane": str})
    partes = []
    for O in origenes:
        train = d[d["anio_objetivo"] <= O]
        test = d[d["T"] == O].copy()
        if limite_objetivo is not None:
            test = test[test["anio_objetivo"] <= limite_objetivo]
        if test.empty:
            continue
        pred = _entrenar(params, train, test)
        cols = ["producto", "cod_dane", "T", "horizonte", "anio_objetivo", "lgbm"]
        p = pred[cols].rename(columns={"T": "origen_anio"})
        p["producto"] = p["producto"].astype(str)
        p["cod_dane"] = p["cod_dane"].astype(str)
        m = base.merge(p, on=["producto", "cod_dane", "origen_anio", "horizonte"], how="inner")
        if m.empty:
            continue
        m["ensemble"] = np.where(m["lgbm"].notna(), (m["naive"] + m["lgbm"]) / 2.0, m["naive"])
        partes.append(m)
    return pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()


def _metricas_totales(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"n_obs": 0, "MASE_lgbm": np.nan, "WAPE_lgbm": np.nan,
                "MASE_ensemble": np.nan, "WAPE_ensemble": np.nan}
    met = m5.metricas(df, modelos=("lgbm", "ensemble"))
    fila = met[met["producto"] == "TOTAL"].iloc[0]
    lg = met[(met["producto"] == "TOTAL")]
    return {
        "n_obs": int(fila["n_obs"]),
        "MASE_lgbm": float(lg[lg.modelo == "lgbm"]["MASE"].iloc[0]),
        "WAPE_lgbm": float(lg[lg.modelo == "lgbm"]["WAPE"].iloc[0]),
        "MASE_ensemble": float(lg[lg.modelo == "ensemble"]["MASE"].iloc[0]),
        "WAPE_ensemble": float(lg[lg.modelo == "ensemble"]["WAPE"].iloc[0]),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rapido", action="store_true", help="Evalúa solo 7 candidatos")
    args = ap.parse_args(argv)

    t0 = time.time()
    series, lp = cargar_panel()
    estado = lp.set_index("producto")["estado"].to_dict()
    oni = cargar_oni()
    candidatos = _candidatos(args.rapido)

    print(f"Tuning LightGBM | orígenes {ORIGENES_TUNING} | holdout {ORIGENES_HOLDOUT}")
    print(f"Candidatos: {len(candidatos)} | ONI: {'sí' if oni is not None else 'no'}")
    filas = []
    for cand in candidatos:
        t1 = time.time()
        val = _evaluar(series, estado, oni, cand["params"], ORIGENES_TUNING, limite_objetivo=2021)
        met = _metricas_totales(val)
        fila = {"candidato": cand["candidato"], "cambio": cand["cambio"],
                "params_json": json.dumps(cand["params"], sort_keys=True),
                **met, "segundos": round(time.time() - t1, 2)}
        filas.append(fila)
        print(f"  cand {cand['candidato']:02d} | n={met['n_obs']:5d} | "
              f"MASE ens={met['MASE_ensemble']:.4f} | WAPE ens={met['WAPE_ensemble']:.4f} | "
              f"{fila['segundos']:.1f}s | {cand['cambio']}")

    tabla = pd.DataFrame(filas).sort_values(["MASE_ensemble", "WAPE_ensemble"]).reset_index(drop=True)
    tabla["delta_MASE_vs_actual"] = tabla["MASE_ensemble"] - tabla.loc[
        tabla["candidato"] == 0, "MASE_ensemble"].iloc[0]
    tabla["delta_WAPE_vs_actual"] = tabla["WAPE_ensemble"] - tabla.loc[
        tabla["candidato"] == 0, "WAPE_ensemble"].iloc[0]
    tabla.round(6).to_csv(RES / "tuning_resultados.csv", index=False, encoding="utf-8-sig")

    mejor = tabla.iloc[0]
    mejor_params = json.loads(mejor["params_json"])
    (RES / "tuning_mejor_config.yaml").write_text(
        yaml.safe_dump({
            "seleccion": "menor MASE del ensamble (naive+LightGBM)/2",
            "origenes_tuning": ORIGENES_TUNING,
            "limite_objetivo": 2021,
            "candidato": int(mejor["candidato"]),
            "cambio": mejor["cambio"],
            "parametros": mejor_params,
            "metricas_tuning": {k: float(mejor[k]) for k in
                                ("MASE_lgbm", "WAPE_lgbm", "MASE_ensemble", "WAPE_ensemble")},
            "nota": "No se modificó config/ML_C/parametros.yaml; el modelo final sigue siendo el de 06/07.",
        }, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    # Holdout: solo reporte, no selección.
    print("\nEvaluación holdout 2022-2023 (no usada para seleccionar):")
    holdout = []
    for etiqueta, params in (("actual", ACTUAL), ("mejor", mejor_params)):
        for O in ORIGENES_HOLDOUT:
            val = _evaluar(series, estado, oni, params, [O])
            met = _metricas_totales(val)
            holdout.append({"configuracion": etiqueta, "origen": O, **met})
    hold = pd.DataFrame(holdout)
    hold.round(6).to_csv(RES / "tuning_holdout.csv", index=False, encoding="utf-8-sig")

    resumen = (hold.groupby("configuracion")[["MASE_lgbm", "WAPE_lgbm", "MASE_ensemble", "WAPE_ensemble"]]
               .mean().reset_index())
    resumen.round(6).to_csv(RES / "tuning_holdout_resumen.csv", index=False, encoding="utf-8-sig")
    print(resumen.round(4).to_string(index=False))
    print("\nMejor candidato:", mejor["candidato"], "|", mejor["cambio"])
    print(f"Tiempo total: {time.time() - t0:.1f}s")
    print(f"Salidas: {RES / 'tuning_resultados.csv'} y {RES / 'tuning_holdout_resumen.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
