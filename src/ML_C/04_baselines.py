import warnings, time
from importlib import import_module
import numpy as np, pandas as pd
from common import cargar_panel, objetivos, ORIGENES, RES

warnings.filterwarnings("ignore")

def f_naive(y, H):  return np.repeat(y.iloc[-1], H)
def f_mean5(y, H):  return np.repeat(y.iloc[-5:].mean(), H)
def f_drift(y, H):
    n = len(y) - 1
    sl = (y.iloc[-1] - y.iloc[0]) / n if n >= 2 else 0.0
    return np.maximum(y.iloc[-1] + sl * np.arange(1, H + 1), 0)
def f_ets(y, H):
    if len(y) < 8 or y.nunique() < 3:
        return f_naive(y, H)
    try:
        ExponentialSmoothing = import_module("statsmodels.tsa.holtwinters").ExponentialSmoothing
        m = ExponentialSmoothing(y.values, trend="add", damped_trend=True, initialization_method="estimated").fit()
        return np.maximum(m.forecast(H), 0)
    except Exception:
        return f_naive(y, H)

def main():
    series, lp = cargar_panel()
    estado = lp.set_index("producto")["estado"].to_dict()
    filas, t0 = [], time.time()
    for (p, c), y_all in series.items():
        det = estado[p] == "detallado"
        for O in ORIGENES:
            if y_all.index.min() > O: continue
            y = y_all.loc[:O]
            H = len(objetivos(O))
            preds = {"naive": f_naive(y, H), "mean5": f_mean5(y, H)}
            if det:
                preds["drift"] = f_drift(y, H); preds["ets"] = f_ets(y, H)
            scale = np.abs(np.diff(y.values)).mean() if len(y) > 1 else np.nan
            for h in range(1, H + 1):
                r = dict(producto=p, cod_dane=c, estado=estado[p], origen_anio=O, horizonte=h, anio_objetivo=O + h,
                         real=y_all.loc[O + h], escala_mase=scale)
                for k, v in preds.items(): r[k] = float(v[h - 1])
                filas.append(r)
    pr = pd.DataFrame(filas)
    pr.to_csv(RES / "predicciones_baselines.csv", index=False, encoding="utf-8-sig")
    print(f"predicciones: {len(pr)} filas, {time.time()-t0:.0f}s")
    print(metricas(pr).query("producto=='TOTAL'").to_string(index=False))

def metricas(pr, modelos=("naive", "mean5", "drift", "ets", "lgbm"), extra_cols=()):
    """MASE y WAPE por producto y TOTAL; mejora relativa vs ingenuo en las mismas filas."""
    out = []
    for p, g in list(pr.groupby("producto")) + [("TOTAL", pr)]:
        for m in modelos:
            if m not in g.columns: continue
            gg = g.dropna(subset=[m])
            if gg.empty: continue
            base = gg
            e = (gg[m] - gg["real"]).abs(); en = (gg["naive"] - gg["real"]).abs()
            ok = gg["escala_mase"] > 0
            mase = (e[ok] / gg.loc[ok, "escala_mase"]).mean() if ok.any() else np.nan
            mase_n = (en[ok] / gg.loc[ok, "escala_mase"]).mean() if ok.any() else np.nan
            wape = e.sum() / gg["real"].abs().sum() if gg["real"].abs().sum() > 0 else np.nan
            wape_n = en.sum() / gg["real"].abs().sum() if gg["real"].abs().sum() > 0 else np.nan
            out.append(dict(producto=p, modelo=m, n_obs=len(gg), n_series=gg[["producto", "cod_dane"]].drop_duplicates().shape[0],
                            pct_obs_escala0=round(100 * (~ok).mean(), 1), MASE=mase, WAPE=wape,
                            mejora_MASE_vs_naive=1 - mase / mase_n if mase_n and mase_n > 0 else np.nan,
                            mejora_WAPE_vs_naive=1 - wape / wape_n if wape_n and wape_n > 0 else np.nan))
    return pd.DataFrame(out)

if __name__ == "__main__":
    main()
    pr = pd.read_csv(RES / "predicciones_baselines.csv", dtype={"cod_dane": str})
    metricas(pr).round(4).to_csv(RES / "metricas_baselines.csv", index=False, encoding="utf-8-sig")
