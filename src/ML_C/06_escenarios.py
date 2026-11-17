"""Tarea 6 (Ceyni): escenarios de oferta bajo/base/alto 2024-2028 y coherencia jerárquica.
Modelo base : 'detallado' -> promedio (ingenuo + LightGBM); 'simplificado' (y series cortas) -> ingenuo.
              Regla: el mejor modelo del walk-forward es un empate técnico con el ingenuo (ver docs/resumen_pronostico.md).
Escenarios  : base = pronóstico; bajo/alto = percentiles 10 y 90 del error logarítmico del walk-forward,
              por (producto, horizonte) si hay >= 30 observaciones; si no, por (estado, horizonte).
Cobertura   : se mide con calibración dejando un origen afuera (el error del origen evaluado NO calibra su intervalo).
Salidas     : data/results/oferta_escenarios.csv  (producto, cod_dane, año, oferta_bajo, oferta_base, oferta_alto)
              data/results/oferta_escenarios_detalle.csv (+ modelo, horizonte), oferta_departamento.csv,
              cobertura_intervalos.csv, coherencia_jerarquica.csv
"""
import warnings
import numpy as np, pandas as pd, lightgbm as lgb
from importlib import import_module
from common import cargar_panel, RES, ANIO_FIN, HORIZONTE_MAX
m5 = import_module("05_lgbm")
warnings.filterwarnings("ignore")
Q_BAJO, Q_ALTO, MIN_N = 0.10, 0.90, 30
HORIZ = list(range(1, HORIZONTE_MAX + 1))            # 2024..2028

H_CAL = 4   # el horizonte 5 solo tiene un origen (2018): se calibra con h=4 y se ensancha por raíz(h/4)

def tabla_q(cal):
    cal = cal[cal["horizonte"] <= H_CAL]
    tp = cal.groupby(["producto", "horizonte"])["e"].agg(n="size", q_lo=lambda s: s.quantile(Q_BAJO), q_hi=lambda s: s.quantile(Q_ALTO)).reset_index()
    te = cal.groupby(["estado", "horizonte"])["e"].agg(q_lo_e=lambda s: s.quantile(Q_BAJO), q_hi_e=lambda s: s.quantile(Q_ALTO)).reset_index()
    return tp, te

def aplicar_q(df, tp, te):
    x = df.copy(); x["h_cal"] = np.minimum(x["horizonte"], H_CAL)
    x = (x.merge(tp.rename(columns={"horizonte": "h_cal"}), on=["producto", "h_cal"], how="left")
          .merge(te.rename(columns={"horizonte": "h_cal"}), on=["estado", "h_cal"], how="left"))
    usa = x["n"].fillna(0) >= MIN_N
    ens = np.sqrt(x["horizonte"] / x["h_cal"])
    x["q_lo_f"] = np.where(usa, x["q_lo"], x["q_lo_e"]) * ens; x["q_hi_f"] = np.where(usa, x["q_hi"], x["q_hi_e"]) * ens
    return x

def main():
    series, lp = cargar_panel()
    estado = lp.set_index("producto")["estado"].to_dict()
    # ---- 1) errores del walk-forward del modelo base ----
    comp = pd.read_csv(RES / "predicciones_comparacion.csv", dtype={"cod_dane": str})
    bas = pd.read_csv(RES / "predicciones_baselines.csv", dtype={"cod_dane": str})
    wf = bas[["producto", "cod_dane", "estado", "origen_anio", "horizonte", "real", "naive"]].merge(
        comp[["producto", "cod_dane", "origen_anio", "horizonte", "lgbm"]], on=["producto", "cod_dane", "origen_anio", "horizonte"], how="left")
    wf["pred"] = np.where(wf["lgbm"].notna() & (wf["estado"] == "detallado"), (wf["naive"] + wf["lgbm"]) / 2, wf["naive"])
    wf["e"] = np.log1p(wf["real"]) - np.log1p(wf["pred"])

    # ---- 2) cobertura con calibración leave-one-origin-out ----
    cob = []
    for O in sorted(wf.origen_anio.unique()):
        tp, te = tabla_q(wf[wf.origen_anio != O])
        x = aplicar_q(wf[wf.origen_anio == O], tp, te)
        lo = np.expm1(np.log1p(x["pred"]) + x["q_lo_f"]); hi = np.expm1(np.log1p(x["pred"]) + x["q_hi_f"])
        x["dentro"] = ((x["real"] >= np.minimum(lo, x["pred"]) - 1e-9) & (x["real"] <= np.maximum(hi, x["pred"]) + 1e-9))
        cob.append(x[["producto", "estado", "origen_anio", "horizonte", "dentro"]])
    cob = pd.concat(cob)
    c_h = cob.groupby("horizonte")["dentro"].agg(n="size", cobertura="mean").reset_index().assign(grupo="todos")
    c_e = cob.groupby(["estado", "horizonte"])["dentro"].agg(n="size", cobertura="mean").reset_index().rename(columns={"estado": "grupo"})
    tot = pd.DataFrame([dict(grupo="todos", horizonte="todos", n=len(cob), cobertura=cob.dentro.mean())])
    out_cob = pd.concat([tot, c_h.assign(horizonte=c_h.horizonte.astype(str)), c_e.assign(horizonte=c_e.horizonte.astype(str))])
    out_cob["cobertura_nominal"] = Q_ALTO - Q_BAJO
    out_cob.round(3).to_csv(RES / "cobertura_intervalos.csv", index=False, encoding="utf-8-sig")

    # ---- 3) pronóstico final 2024-2028 (origen 2023) ----
    d = m5.construir_filas(series, estado, None)
    cols = m5.features(d, None)
    mdl = lgb.LGBMRegressor(**m5.PARAMS).fit(d[cols], d["target"])
    fin = []
    for (p, c), y in series.items():
        for r in m5.filas_origen(p, c, y, ANIO_FIN, None, HORIZ, False):
            fin.append(r)
    f = pd.DataFrame(fin)
    f["estado"] = f["producto"].map(estado)
    cat_p, cat_c = d["producto"].cat.categories, d["cod_dane"].cat.categories
    det_mask = (f.estado == "detallado") & (f["hist"] >= 3) & f["producto"].isin(cat_p) & f["cod_dane"].isin(cat_c)
    f["naive"] = np.expm1(f["log_last"])
    f["lgbm"] = np.nan
    if det_mask.any():
        g = f[det_mask].copy()
        g["producto"] = pd.Categorical(g["producto"], categories=cat_p); g["cod_dane"] = pd.Categorical(g["cod_dane"], categories=cat_c)
        f.loc[det_mask, "lgbm"] = np.maximum(np.expm1(g["log_last"] + mdl.predict(g[cols])), 0)
    f["oferta_base"] = np.where(f.lgbm.notna(), (f.naive + f.lgbm) / 2, f.naive)
    f["modelo"] = np.where(f.lgbm.notna(), "promedio_ingenuo_lgbm", "ingenuo")

    tp, te = tabla_q(wf)
    f = aplicar_q(f, tp, te)
    base_log = np.log1p(f["oferta_base"])
    f["oferta_bajo"] = np.minimum(np.expm1(base_log + f["q_lo_f"]), f["oferta_base"])
    f["oferta_alto"] = np.maximum(np.expm1(base_log + f["q_hi_f"]), f["oferta_base"])
    f["año"] = f["anio_objetivo"]
    cols_out = ["producto", "cod_dane", "año", "oferta_bajo", "oferta_base", "oferta_alto"]
    f = f.sort_values(["producto", "cod_dane", "año"])
    f[cols_out].round(2).to_csv(RES / "oferta_escenarios.csv", index=False, encoding="utf-8-sig")
    f[cols_out + ["modelo", "horizonte"]].round(2).to_csv(RES / "oferta_escenarios_detalle.csv", index=False, encoding="utf-8-sig")

    # ---- 4) coherencia jerárquica (bottom-up) ----
    dep = f.groupby(["producto", "año"])[["oferta_bajo", "oferta_base", "oferta_alto"]].sum().reset_index()
    dep.round(2).to_csv(RES / "oferta_departamento.csv", index=False, encoding="utf-8-sig")
    chk = f.groupby(["producto", "año"])["oferta_base"].sum().reset_index().merge(dep[["producto", "año", "oferta_base"]], on=["producto", "año"], suffixes=("_municipios", "_departamento"))
    chk["dif"] = (chk.oferta_base_municipios - chk.oferta_base_departamento).abs()
    chk.round(4).to_csv(RES / "coherencia_jerarquica.csv", index=False, encoding="utf-8-sig")
    print("filas escenarios:", len(f), "| series:", f[["producto", "cod_dane"]].drop_duplicates().shape[0], "| años", f["año"].min(), f["año"].max())
    print("max diferencia municipios vs departamento:", chk.dif.max())
    print("bajo<=base<=alto:", bool(((f.oferta_bajo <= f.oferta_base) & (f.oferta_base <= f.oferta_alto)).all()), "| nulos:", int(f[cols_out].isna().sum().sum()))
    print(out_cob.round(3).to_string(index=False))
    print(dep[dep["año"].isin([2024, 2028])].query("producto in ['Caña de azúcar','Plátano','Café']").round(0).to_string(index=False))

if __name__ == "__main__":
    main()
