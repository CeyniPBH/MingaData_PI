import warnings
import numpy as np, pandas as pd, lightgbm as lgb
from common import cargar_panel, objetivos, ORIGENES, RES, CLEAN, HORIZONTE_MAX, ANIO_FIN
from importlib import import_module

warnings.filterwarnings("ignore")
PARAMS = dict(objective="l1", n_estimators=300, learning_rate=0.03, num_leaves=15, min_child_samples=30,
              subsample=0.8, subsample_freq=1, colsample_bytree=0.8, reg_lambda=1.0, random_state=42, verbose=-1, n_jobs=1)

def cargar_oni():
    f = CLEAN / "oni.csv"
    if not f.exists(): return None
    o = pd.read_csv(f)           # columnas: anio, oni (promedio anual)
    return o.set_index("anio")["oni"]

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

def main():
    series, lp = cargar_panel()
    estado = lp.set_index("producto")["estado"].to_dict()
    oni = cargar_oni()
    print("ONI:", "usado" if oni is not None else "no disponible (el modelo corre sin ONI; agregar data/clean/oni.csv y volver a correr)")
    d = construir_filas(series, estado, oni)
    cols = features(d, oni)
    preds, imps = [], []
    for O in ORIGENES:
        tr = d[d.anio_objetivo <= O]                                  # sin fugas hacia adelante
        te = d[(d["T"] == O)]
        if te.empty: continue
        m = lgb.LGBMRegressor(**PARAMS).fit(tr[cols], tr["target"])
        te = te.copy()
        te["pred_log_cambio"] = m.predict(te[cols])
        te["lgbm"] = np.maximum(np.expm1(te["log_last"] + te["pred_log_cambio"]), 0)
        preds.append(te[["producto", "cod_dane", "horizonte", "anio_objetivo", "T", "lgbm", "pred_log_cambio"]].rename(columns={"T": "origen_anio"}))
        imps.append(pd.Series(m.booster_.feature_importance("gain"), index=cols, name=O))
    pl = pd.concat(preds)
    pl["producto"] = pl["producto"].astype(str); pl["cod_dane"] = pl["cod_dane"].astype(str)
    pl.to_csv(RES / "predicciones_lgbm.csv", index=False, encoding="utf-8-sig")
    imp = pd.concat(imps, axis=1)
    imp = (imp / imp.sum()).mean(axis=1).sort_values(ascending=False).rename("importancia_relativa").reset_index().rename(columns={"index": "variable"})
    imp.round(4).to_csv(RES / "importancia_variables.csv", index=False, encoding="utf-8-sig")

    # comparación con baselines sobre EXACTAMENTE las mismas filas
    base = pd.read_csv(RES / "predicciones_baselines.csv", dtype={"cod_dane": str})
    comp = base.merge(pl[["producto", "cod_dane", "origen_anio", "horizonte", "lgbm"]], on=["producto", "cod_dane", "origen_anio", "horizonte"], how="inner")
    b4 = import_module("04_baselines")
    met = b4.metricas(comp, modelos=("naive", "drift", "ets", "mean5", "lgbm"))
    met.round(4).to_csv(RES / "metricas_comparacion.csv", index=False, encoding="utf-8-sig")
    comp.to_csv(RES / "predicciones_comparacion.csv", index=False, encoding="utf-8-sig")
    print(met.query("producto=='TOTAL'").to_string(index=False))
    print(imp.head(8).to_string(index=False))

if __name__ == "__main__":
    main()
