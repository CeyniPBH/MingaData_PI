"""Modelo global LightGBM con el mismo walk-forward de los baselines."""
import sys, warnings
import numpy as np, pandas as pd, lightgbm as lgb
from importlib import import_module
from common import CFG, cargar_panel, cargar_oni, ORIGENES, RES, HORIZONTE_MAX, ANIO_FIN

warnings.filterwarnings("ignore")
PARAMS = dict(CFG["lightgbm"])

def filas_origen(p, c, y, T, oni, h_list, con_target):
    """Variables en el año T para una serie. y: Serie completa (anio -> t)."""
    ly = np.log1p(y.loc[:T].values)
    last = ly[-1]
    base = dict(producto=p, cod_dane=c, T=T, log_last=last,
                d1=last - ly[-2] if len(ly) > 1 else 0.0, d2=last - ly[-3] if len(ly) > 2 else 0.0,
                m3=ly[-3:].mean() - last, m5=ly[-5:].mean() - last,
                pct_ceros5=float((y.loc[:T].values[-5:] == 0).mean()), hist=len(ly),
                max_rel=last - ly.max())
    if oni is not None:
        base["oni_t"] = oni.get(T, np.nan); base["oni_t1"] = oni.get(T - 1, np.nan)
    out = []
    for h in h_list:
        r = dict(base, horizonte=h, anio_objetivo=T + h)
        if con_target: r["target"] = np.log1p(y.loc[T + h]) - last
        out.append(r)
    return out

def construir_filas(series, estado, oni):
    rows = []
    for (p, c), y in series.items():
        if estado[p] != "detallado": continue
        for T in range(int(y.index.min()) + 1, ANIO_FIN):          # al menos 2 puntos de historia
            hs = [h for h in range(1, HORIZONTE_MAX + 1) if T + h <= ANIO_FIN]
            rows += filas_origen(p, c, y, T, oni, hs, True)
    d = pd.DataFrame(rows)
    d["producto"] = d["producto"].astype("category"); d["cod_dane"] = d["cod_dane"].astype("category")
    return d

def features(d, oni):
    cols = ["log_last", "d1", "d2", "m3", "m5", "pct_ceros5", "hist", "max_rel", "horizonte", "T", "producto", "cod_dane"]
    return cols + (["oni_t", "oni_t1"] if oni is not None else [])

def walk_forward(series, estado, oni):
    """Entrena un modelo por origen y devuelve (predicciones, importancias)."""
    d = construir_filas(series, estado, oni)
    cols = features(d, oni)
    preds, imps = [], []
    for O in ORIGENES:
        tr = d[d.anio_objetivo <= O]                                  # sin fugas hacia adelante
        te = d[(d["T"] == O)].copy()
        if te.empty: continue
        m = lgb.LGBMRegressor(**PARAMS).fit(tr[cols], tr["target"])
        te["pred_log_cambio"] = m.predict(te[cols])
        te["lgbm"] = np.maximum(np.expm1(te["log_last"] + te["pred_log_cambio"]), 0)
        preds.append(te[["producto", "cod_dane", "horizonte", "anio_objetivo", "T", "lgbm", "pred_log_cambio"]].rename(columns={"T": "origen_anio"}))
        imps.append(pd.Series(m.booster_.feature_importance("gain"), index=cols, name=O))
    pl = pd.concat(preds)
    pl["producto"] = pl["producto"].astype(str); pl["cod_dane"] = pl["cod_dane"].astype(str)
    return pl, imps


def comparar_oni():
    """Experimento: LightGBM con y sin ONI sobre las mismas filas. Escribe metricas_oni.csv."""
    series, lp = cargar_panel()
    estado = lp.set_index("producto")["estado"].to_dict()
    base = pd.read_csv(RES / "predicciones_baselines.csv", dtype={"cod_dane": str})
    b5 = import_module("05_baselines")
    out = []
    for etiqueta, oni in [("sin_oni", None), ("con_oni", cargar_oni(forzar=True))]:
        pl, _ = walk_forward(series, estado, oni)
        comp = base.merge(pl[["producto", "cod_dane", "origen_anio", "horizonte", "lgbm"]], on=["producto", "cod_dane", "origen_anio", "horizonte"])
        out.append(b5.metricas(comp, modelos=("naive", "lgbm")).query("producto == 'TOTAL'").assign(variante=etiqueta))
    res = pd.concat(out)
    res.round(4).to_csv(RES / "metricas_oni.csv", index=False, encoding="utf-8-sig")
    print(res[["variante", "modelo", "MASE", "WAPE", "mejora_MASE_vs_naive", "mejora_WAPE_vs_naive"]].to_string(index=False))


def main():
    series, lp = cargar_panel()
    estado = lp.set_index("producto")["estado"].to_dict()
    oni = cargar_oni()
    print("ONI:", "usado" if oni is not None else "no usado (usar_oni: false en config/ML_C/parametros.yaml)")
    pl, imps = walk_forward(series, estado, oni)
    pl.to_csv(RES / "predicciones_lgbm.csv", index=False, encoding="utf-8-sig")
    imp = pd.concat(imps, axis=1)
    imp = (imp / imp.sum()).mean(axis=1).sort_values(ascending=False).rename("importancia_relativa").reset_index().rename(columns={"index": "variable"})
    imp.round(4).to_csv(RES / "importancia_variables.csv", index=False, encoding="utf-8-sig")

    # comparación con baselines sobre EXACTAMENTE las mismas filas
    base = pd.read_csv(RES / "predicciones_baselines.csv", dtype={"cod_dane": str})
    comp = base.merge(pl[["producto", "cod_dane", "origen_anio", "horizonte", "lgbm"]], on=["producto", "cod_dane", "origen_anio", "horizonte"], how="inner")
    b5 = import_module("05_baselines")
    met = b5.metricas(comp, modelos=("naive", "drift", "ets", "mean5", "lgbm"))
    met.round(4).to_csv(RES / "metricas_comparacion.csv", index=False, encoding="utf-8-sig")
    comp.to_csv(RES / "predicciones_comparacion.csv", index=False, encoding="utf-8-sig")
    print(met.query("producto=='TOTAL'").to_string(index=False))
    print(imp.head(8).to_string(index=False))

if __name__ == "__main__":
    comparar_oni() if "--comparar-oni" in sys.argv else main()
