"""Sensibilidad del pronóstico al ONI: ¿qué cambia si se quita el ONI del modelo final?

1) Backtest por origen: repite el walk-forward de 06_lgbm.py con y sin ONI y compara el MASE del modelo final
   (promedio ingenuo + LightGBM) en cada origen 2018-2022.
2) Pronóstico 2024-2028: repite el paso 3 de 07_escenarios.py (modelo entrenado con toda la historia y origen 2023)
   con y sin ONI, y compara la oferta base sin ONI con la oferta base y la banda bajo-alto oficiales.
No modifica las salidas oficiales. Escribe data/results/ML_Ce/sensibilidad_oni.csv.
Uso: python src/ML_C/07b_sensibilidad_oni.py  (requiere lightgbm, como 06 y 07)
"""
import warnings
from importlib import import_module
import numpy as np, pandas as pd
from common import cargar_panel, cargar_oni, RES, ANIO_FIN, HORIZONTE_MAX

warnings.filterwarnings("ignore")
HORIZ = list(range(1, HORIZONTE_MAX + 1))
CANA = "Caña de azúcar"
LLAVE = ["producto", "cod_dane", "año"]


def oferta_base(series, estado, oni):
    """Oferta base 2024-2028 con el mismo cálculo del paso 3 de 07_escenarios.py."""
    import lightgbm as lgb
    m6 = import_module("06_lgbm")
    d = m6.construir_filas(series, estado, oni)
    cols = m6.features(d, oni)
    mdl = lgb.LGBMRegressor(**m6.PARAMS).fit(d[cols], d["target"])
    f = pd.DataFrame([r for (p, c), y in series.items() for r in m6.filas_origen(p, c, y, ANIO_FIN, oni, HORIZ, False)])
    f["estado"] = f["producto"].map(estado)
    cat_p, cat_c = d["producto"].cat.categories, d["cod_dane"].cat.categories
    det = (f.estado == "detallado") & (f["hist"] >= 3) & f["producto"].isin(cat_p) & f["cod_dane"].isin(cat_c)
    f["naive"] = np.expm1(f["log_last"])
    f["lgbm"] = np.nan
    g = f[det].copy()
    g["producto"] = pd.Categorical(g["producto"], categories=cat_p)
    g["cod_dane"] = pd.Categorical(g["cod_dane"], categories=cat_c)
    f.loc[det, "lgbm"] = np.maximum(np.expm1(g["log_last"] + mdl.predict(g[cols])), 0)
    f["oferta_base"] = np.where(f.lgbm.notna(), (f.naive + f.lgbm) / 2, f.naive)
    return f.rename(columns={"anio_objetivo": "año"})[LLAVE + ["oferta_base"]]


def backtest_por_origen(series, estado, oni_dict):
    """MASE del modelo final por origen, con y sin ONI, sobre las mismas filas del walk-forward."""
    m6, b5 = import_module("06_lgbm"), import_module("05_baselines")
    base = pd.read_csv(RES / "predicciones_baselines.csv", dtype={"cod_dane": str})
    filas = []
    for etiqueta, oni in [("con_oni", oni_dict), ("sin_oni", None)]:
        pl, _ = m6.walk_forward(series, estado, oni)
        comp = base.merge(pl[["producto", "cod_dane", "origen_anio", "horizonte", "lgbm"]],
                          on=["producto", "cod_dane", "origen_anio", "horizonte"])
        comp["naive_lgbm"] = (comp["naive"] + comp["lgbm"]) / 2
        for o, g in comp.groupby("origen_anio"):
            t = b5.metricas(g, modelos=("naive_lgbm",)).query("producto == 'TOTAL'").iloc[0]
            filas.append(dict(variante=etiqueta, origen=int(o), n_obs=int(t.n_obs), MASE=t.MASE, WAPE=t.WAPE))
    r = pd.DataFrame(filas).pivot(index="origen", columns="variante", values=["MASE", "WAPE"])
    r.columns = [f"{m}_{v}" for m, v in r.columns]
    return r.reset_index()


def comparar(x, nivel, por):
    g = x.groupby(por)[["oferta_bajo", "oferta_base", "oferta_alto", "base_sin_oni"]].sum().reset_index()
    g["dif_rel_sin_oni"] = g["base_sin_oni"] / g["oferta_base"] - 1
    g["bajo_rel"] = g["oferta_bajo"] / g["oferta_base"] - 1
    g["alto_rel"] = g["oferta_alto"] / g["oferta_base"] - 1
    return g.assign(nivel=nivel)


def main():
    series, lp = cargar_panel()
    estado = lp.set_index("producto")["estado"].to_dict()
    oni = cargar_oni(forzar=True)

    # 1) backtest por origen
    bt = backtest_por_origen(series, estado, oni)
    bt["dif_rel_MASE"] = bt["MASE_sin_oni"] / bt["MASE_con_oni"] - 1
    print("Backtest del modelo final por origen (MASE):")
    print(bt.round(4).to_string(index=False))
    print(f"Orígenes donde sin ONI tiene menor MASE: {int((bt.dif_rel_MASE < 0).sum())} de {len(bt)}\n")

    # 2) pronóstico 2024-2028
    of = pd.read_csv(RES / "oferta_escenarios.csv", dtype={"cod_dane": str})
    con = oferta_base(series, estado, oni).rename(columns={"oferta_base": "base_con_oni"})
    sin = oferta_base(series, estado, None).rename(columns={"oferta_base": "base_sin_oni"})
    x = of.merge(con, on=LLAVE).merge(sin, on=LLAVE)
    control = (x["base_con_oni"] - x["oferta_base"]).abs().max()
    print(f"Control: con ONI se reproduce oferta_escenarios.csv (diferencia máxima {control:.3f} t en {len(x)} filas)")
    dentro = ((x.base_sin_oni >= x.oferta_bajo - 0.01) & (x.base_sin_oni <= x.oferta_alto + 0.01)).mean()
    print(f"Filas producto-municipio-año con la base sin ONI dentro de la banda bajo-alto oficial: {dentro:.1%}")

    sc = x[x.producto != CANA]
    res = pd.concat([comparar(x, "departamento", ["año"]),
                     comparar(sc, "departamento_sin_cana", ["año"]),
                     comparar(x, "producto", ["producto", "año"]),
                     comparar(sc, "municipio_sin_cana", ["cod_dane", "año"])], ignore_index=True)
    res = res[["nivel", "producto", "cod_dane", "año", "oferta_bajo", "oferta_base", "oferta_alto",
               "base_sin_oni", "dif_rel_sin_oni", "bajo_rel", "alto_rel"]]
    bt_out = bt.assign(nivel="backtest_origen").rename(columns={"origen": "año"})
    pd.concat([res, bt_out], ignore_index=True).round(6).to_csv(RES / "sensibilidad_oni.csv", index=False, encoding="utf-8-sig")

    dep = res[res.nivel == "departamento_sin_cana"]
    print("\nOferta base departamental sin caña (t): oficial con ONI vs sin ONI, y banda oficial")
    print(dep[["año", "oferta_base", "base_sin_oni", "dif_rel_sin_oni", "bajo_rel", "alto_rel"]].round(4).to_string(index=False))
    for nivel, col in [("producto", "producto"), ("municipio_sin_cana", "cod_dane")]:
        r = res[res.nivel == nivel]
        i = r["dif_rel_sin_oni"].abs().idxmax()
        print(f"Mayor diferencia por {col}: {r.loc[i, col]} en {int(r.loc[i, 'año'])}: {r.loc[i, 'dif_rel_sin_oni']:+.2%}"
              f" (banda oficial {r.loc[i, 'bajo_rel']:+.0%} a {r.loc[i, 'alto_rel']:+.0%})")


if __name__ == "__main__":
    main()
