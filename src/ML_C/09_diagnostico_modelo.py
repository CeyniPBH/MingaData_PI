"""Diagnóstico del modelo final por horizonte, producto, municipio y confianza.

El modelo desplegado es el ensamble (naive + LightGBM)/2 para productos
detallados y el ingenuo para simplificados. Este script no reentrena el modelo
final: usa las predicciones walk-forward ya generadas y produce tablas/figuras
para el informe.

Uso:
    python src/ML_C/09_diagnostico_modelo.py
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import CLEAN, RES, cargar_oni, cargar_panel

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import importlib  # noqa: E402

m6 = importlib.import_module("06_lgbm")

FIG = RES / "figuras"


def _metricas(g: pd.DataFrame) -> dict:
    ok = g["escala_mase"] > 0
    e = (g["modelo_final"] - g["real"]).abs()
    en = (g["naive"] - g["real"]).abs()
    mase = (e[ok] / g.loc[ok, "escala_mase"]).mean() if ok.any() else np.nan
    mase_n = (en[ok] / g.loc[ok, "escala_mase"]).mean() if ok.any() else np.nan
    wape = e.sum() / g["real"].abs().sum() if g["real"].abs().sum() else np.nan
    wape_n = en.sum() / g["real"].abs().sum() if g["real"].abs().sum() else np.nan
    err = g["modelo_final"] - g["real"]
    return {
        "n_obs": len(g),
        "n_series": g[["producto", "cod_dane"]].drop_duplicates().shape[0],
        "MASE": mase,
        "MASE_naive": mase_n,
        "WAPE": wape,
        "WAPE_naive": wape_n,
        "mejora_MASE_vs_naive": 1 - mase / mase_n if mase_n and mase_n > 0 else np.nan,
        "mejora_abs_vs_naive": 1 - e.sum() / en.sum() if en.sum() else np.nan,
        "sesgo_t": err.mean(),
        "error_abs_medio_t": e.mean(),
        "error_abs_total_t": e.sum(),
        "real_total_t": g["real"].sum(),
    }


def _por_segmento(df: pd.DataFrame, columna: str) -> pd.DataFrame:
    filas = []
    for valor, g in df.groupby(columna, dropna=False):
        fila = {columna: valor, **_metricas(g)}
        filas.append(fila)
    return pd.DataFrame(filas).sort_values("error_abs_total_t", ascending=False)


def _curva_aprendizaje(series, estado, oni) -> pd.DataFrame:
    """Error train vs validación al aumentar las iteraciones (origen 2022 → 2023)."""
    import lightgbm as lgb

    d = m6.construir_filas(series, estado, oni)
    cols = m6.features(d, oni)
    train = d[d["anio_objetivo"] <= 2022]
    test = d[d["T"] == 2022]
    params = dict(m6.PARAMS)
    params["n_estimators"] = 500
    modelo = lgb.LGBMRegressor(**params).fit(train[cols], train["target"])
    filas = []
    for n in (25, 50, 100, 200, 300, 500):
        p_tr = modelo.predict(train[cols], num_iteration=n)
        p_te = modelo.predict(test[cols], num_iteration=n)
        filas.append({
            "n_estimaciones": n,
            "rmse_train_log": float(np.sqrt(np.mean((p_tr - train["target"]) ** 2))),
            "rmse_validacion_log": float(np.sqrt(np.mean((p_te - test["target"]) ** 2))),
            "n_train": len(train),
            "n_validacion": len(test),
        })
    # La curva se calcula en espacio log-cambio para aislar sesgo/varianza.
    return pd.DataFrame(filas)


def _figuras(diag_h, diag_p, curva, pred):
    FIG.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"figure.dpi": 130, "font.size": 9})

    fig, ax = plt.subplots(figsize=(6, 3.5))
    ax.bar(diag_h["horizonte"].astype(str), diag_h["WAPE"] * 100, color="#2a7f62")
    ax.set_xlabel("Horizonte (años)")
    ax.set_ylabel("WAPE (%)")
    ax.set_title("El error crece con el horizonte, pero se mantiene bajo")
    for i, v in enumerate(diag_h["WAPE"] * 100):
        ax.text(i, v + 0.2, f"{v:.1f}%", ha="center", fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "error_por_horizonte.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 3.5))
    rel = (pred["modelo_final"] - pred["real"]) / pred["real"].replace(0, np.nan)
    datos = rel.replace([np.inf, -np.inf], np.nan).dropna()
    ax.hist(datos.clip(-1, 1), bins=50, color="#4c72b0", edgecolor="white")
    ax.axvline(0, color="black", linewidth=1)
    ax.set_xlabel("Error relativo (predicción − real) / real")
    ax.set_ylabel("Frecuencia")
    ax.set_title("Residuales con sesgo negativo en horizontes largos")
    fig.tight_layout()
    fig.savefig(FIG / "residuales_hist.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 3.5))
    ax.plot(curva["n_estimaciones"], curva["rmse_train_log"], marker="o", label="Entrenamiento")
    ax.plot(curva["n_estimaciones"], curva["rmse_validacion_log"], marker="s", label="Validación")
    ax.set_xlabel("Iteraciones de LightGBM")
    ax.set_ylabel("RMSE en log-cambio")
    ax.set_title("Brecha creciente entre entrenamiento y validación: sobreajuste leve")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG / "curva_aprendizaje.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4))
    top = diag_p.head(15).sort_values("error_abs_total_t")
    ax.barh(top["producto"], top["error_abs_total_t"] / 1e3, color="#c44e52")
    ax.set_xlabel("Error absoluto acumulado (miles de t)")
    ax.set_title("Quince productos concentran la mayor parte del error absoluto")
    fig.tight_layout()
    fig.savefig(FIG / "error_por_producto.png")
    plt.close(fig)


def main() -> int:
    pred = pd.read_csv(RES / "predicciones_comparacion.csv", dtype={"cod_dane": str})
    pred["modelo_final"] = np.where(pred["lgbm"].notna(),
                                    (pred["naive"] + pred["lgbm"]) / 2.0, pred["naive"])
    pred["error"] = pred["modelo_final"] - pred["real"]
    pred["error_abs"] = pred["error"].abs()

    diag_h = _por_segmento(pred, "horizonte").sort_values("horizonte")
    diag_p = _por_segmento(pred, "producto")

    pob = pd.read_csv(CLEAN / "poblacion_municipal.csv", dtype={"cod_dane": str})
    # Las proyecciones limpias empiezan en 2024; se usa el primer año como tamaño
    # estructural del municipio (la población cambia poco en el horizonte).
    pob = pob.sort_values("anio").groupby("cod_dane").head(1)
    pob = pob[["cod_dane", "poblacion_total"]]
    base_mun = pred.merge(pob, on="cod_dane", how="left")
    base_mun["tamano_municipio"] = pd.qcut(
        base_mun["poblacion_total"].rank(method="first"), 3,
        labels=["pequeño", "mediano", "grande"]
    )
    diag_m = _por_segmento(base_mun, "tamano_municipio")

    calidad = pd.read_csv(RES / "diagnostico_calidad.csv")
    base_conf = pred.merge(calidad[["producto", "confianza"]], on="producto", how="left")
    diag_c = _por_segmento(base_conf, "confianza")

    # Resumen global y residuales.
    resumen = {"ambito": "global", **_metricas(pred)}
    resumen.update({
        "residual_medio_t": pred["error"].mean(),
        "residual_mediano_t": pred["error"].median(),
        "residual_std_t": pred["error"].std(),
        "p5_t": pred["error"].quantile(0.05),
        "p95_t": pred["error"].quantile(0.95),
        "pct_sobreestima": (pred["error"] > 0).mean(),
        "pct_subestima": (pred["error"] < 0).mean(),
    })
    pd.DataFrame([resumen]).round(4).to_csv(RES / "residuales_resumen.csv", index=False,
                                            encoding="utf-8-sig")
    top = pred.reindex(pred["error_abs"].sort_values(ascending=False).index).head(20)
    top[["producto", "cod_dane", "anio_objetivo", "origen_anio", "horizonte", "real",
         "modelo_final", "error", "error_abs"]].round(2).to_csv(
        RES / "residuales_top.csv", index=False, encoding="utf-8-sig")

    diag_h.round(4).to_csv(RES / "diagnostico_horizonte.csv", index=False, encoding="utf-8-sig")
    diag_p.round(4).to_csv(RES / "diagnostico_producto.csv", index=False, encoding="utf-8-sig")
    diag_m.round(4).to_csv(RES / "diagnostico_municipio.csv", index=False, encoding="utf-8-sig")
    diag_c.round(4).to_csv(RES / "diagnostico_confianza.csv", index=False, encoding="utf-8-sig")

    series, lp = cargar_panel()
    estado = lp.set_index("producto")["estado"].to_dict()
    curva = _curva_aprendizaje(series, estado, cargar_oni())
    curva.round(6).to_csv(RES / "curva_aprendizaje.csv", index=False, encoding="utf-8-sig")
    _figuras(diag_h, diag_p, curva, pred)

    print("Diagnóstico del modelo final (ensamble naive + LightGBM)")
    print("\nPor horizonte:")
    print(diag_h[["horizonte", "n_obs", "MASE", "WAPE", "sesgo_t", "mejora_abs_vs_naive"]]
          .round(4).to_string(index=False))
    print("\nPor tamaño de municipio:")
    print(diag_m[["tamano_municipio", "n_obs", "MASE", "WAPE", "sesgo_t", "mejora_abs_vs_naive"]]
          .round(4).to_string(index=False))
    print("\nPor nivel de confianza de la serie:")
    print(diag_c[["confianza", "n_obs", "MASE", "WAPE", "sesgo_t", "mejora_abs_vs_naive"]]
          .round(4).to_string(index=False))
    print("\nCurva de aprendizaje:")
    print(curva.round(4).to_string(index=False))
    print(f"\nFiguras en {FIG.relative_to(RES.parents[1])}")
    print(f"Resumen: {RES / 'residuales_resumen.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
