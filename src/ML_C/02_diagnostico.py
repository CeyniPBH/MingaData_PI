from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CLEAN, RES = ROOT / "data/clean", ROOT / "data/results"

def main():
    d = pd.read_csv(CLEAN / "produccion_valle_clean.csv", dtype={"cod_dane": str})
    lp = pd.read_csv(CLEAN / "lista_productos.csv")
    d = d[d["producto"].isin(lp.loc[lp.estado != "excluido", "producto"])]
    out = []
    for (p, c), s in d.groupby(["producto", "cod_dane"]):
        s = s.sort_values("anio")
        y = s.set_index("anio")["produccion_t"]
        prev = y.shift(1); cons = pd.Series(y.index, index=y.index).diff() == 1
        ok = cons & (prev > 0)
        rep = int(((y == prev) & ok).sum()); n_tr = int(ok.sum())
        rel = ((y - prev) / prev)[ok]
        s100 = int((rel.abs() > 1).sum())
        s3 = 0
        if len(rel) >= 8 and rel.std() > 0:
            s3 = int((((rel - rel.mean()) / rel.std()).abs() > 3).sum())
        out.append(dict(producto=p, cod_dane=c, n_anios=len(y), anio_ini=int(y.index.min()), anio_fin=int(y.index.max()),
                        n_ceros=int((y == 0).sum()), n_transiciones=n_tr, n_repetidos=rep, n_saltos_100=s100, n_saltos_3sd=s3,
                        pct_repetidos=100 * rep / n_tr if n_tr else np.nan,
                        activo_2019_2023=bool(((y.index >= 2019) & (y > 0)).any())))
    ser = pd.DataFrame(out)
    ser.to_csv(RES / "diagnostico_series.csv", index=False, encoding="utf-8-sig")

    a = ser[ser.activo_2019_2023]
    prod = a.groupby("producto").agg(n_municipios=("cod_dane", "nunique"), anios_mediana=("n_anios", "median"),
                                    n_transiciones=("n_transiciones", "sum"), n_repetidos=("n_repetidos", "sum"),
                                    n_saltos_100=("n_saltos_100", "sum"), n_saltos_3sd=("n_saltos_3sd", "sum"),
                                    n_ceros=("n_ceros", "sum")).reset_index()
    prod["pct_repetidos"] = (100 * prod.n_repetidos / prod.n_transiciones).round(1)
    prod["pct_saltos_100"] = (100 * prod.n_saltos_100 / prod.n_transiciones).round(1)
    prod["pct_saltos_3sd"] = (100 * prod.n_saltos_3sd / prod.n_transiciones).round(1)
    def conf(r):
        if r.n_municipios < 3 or r.anios_mediana < 12 or r.pct_repetidos > 50: return "baja"
        if r.pct_repetidos > 30 or r.pct_saltos_100 > 15: return "media"
        return "alta"
    prod["confianza"] = prod.apply(conf, axis=1)
    prod = prod.merge(lp[["producto", "familia", "estado"]], on="producto").sort_values(["estado", "pct_repetidos"], ascending=[True, False])
    prod.to_csv(RES / "diagnostico_calidad.csv", index=False, encoding="utf-8-sig")
    tot_tr, tot_rep = prod.n_transiciones.sum(), prod.n_repetidos.sum()
    print(f"series activas {len(a)} | transiciones {tot_tr} | repetidas {tot_rep} ({100*tot_rep/tot_tr:.1f} %) | saltos>100% {prod.n_saltos_100.sum()} ({100*prod.n_saltos_100.sum()/tot_tr:.1f} %) | saltos 3sd {prod.n_saltos_3sd.sum()}")
    print(prod.confianza.value_counts().to_dict())
    print(prod[["producto", "estado", "n_municipios", "anios_mediana", "pct_repetidos", "pct_saltos_100", "confianza"]].to_string(index=False))

if __name__ == "__main__":
    main()
