"""Cifras de la sección 3.2.3 del informe (análisis descriptivo e insights) que no están guardadas en data/results.

Uso, desde la raíz del repositorio: python src/informe/cifras_3_2_3.py
Lee archivos del repositorio y no escribe nada. Las subregiones son las del tablero central
(Ordenanza 513 de 2019), tomadas de src/dashboard/assets/tablero_central_acopio_valle.html.
"""
import json
import re
from pathlib import Path

import pandas as pd
from scipy.stats import spearmanr

RAIZ = Path(__file__).resolve().parents[2]
CLEAN, RES = RAIZ / "data/clean", RAIZ / "data/results/ML_Ce"

prod = pd.read_csv(CLEAN / "produccion_valle_clean.csv", dtype={"cod_dane": str})
html = (RAIZ / "src/dashboard/assets/tablero_central_acopio_valle.html").read_text(encoding="utf-8")
subregion = {m["id"]: m["s"] for m in json.loads(re.search(r"const D = (\{.*?\});\s*\n", html, re.S).group(1))["muns"]}
prod["subregion"] = prod.cod_dane.map(subregion)
pct = lambda x: f"{100 * x:.1f} %".replace(".", ",")
dec = lambda x, d=1: f"{x:.{d}f}".replace(".", ",")
mil = lambda x: f"{x:,.0f}".replace(",", ".")


def promedio_anual(df, por):
    """Promedio 2021-2023 de la suma anual (los años sin registro cuentan como cero)."""
    return df.groupby(por + ["anio"]).ha_sembradas.sum().groupby(por).sum() / 3


# ---------- Área sembrada (Figura 2) ----------
v = prod[prod.anio.between(2021, 2023)]
total_permanentes = v.ha_sembradas.sum() / 3
ft = v[v.familia.isin(["Frutales", "Cultivos Tropicales Tradicionales"])]
total_ft = ft.ha_sembradas.sum() / 3
cana = ft[ft.producto == "Caña de azúcar"]
print("Área sembrada, promedio 2021-2023")
print(f"  Frutales y cultivos tropicales tradicionales: {mil(total_ft)} ha, {pct(total_ft / total_permanentes)} de los cultivos permanentes")
print(f"  Caña de azúcar: {mil(cana.ha_sembradas.sum() / 3)} ha, {pct(cana.ha_sembradas.sum() / 3 / total_ft)}")
print(f"  Caña de azúcar en el sur: {pct(promedio_anual(cana, ['subregion'])['Sur'] / (cana.ha_sembradas.sum() / 3))}")
cafe = promedio_anual(ft[ft.producto == "Café"], ["subregion"])
fruta = promedio_anual(ft[ft.familia == "Frutales"], ["subregion"])
print(f"  Café en el centro y el norte: {pct(cafe[['Centro', 'Norte']].sum() / cafe.sum())}")
print(f"  Fruta y plátano en el centro y el norte: {pct(fruta[['Centro', 'Norte']].sum() / fruta.sum())}")

# ---------- Toneladas frente a valor (Figura 3) ----------
r = pd.read_csv(RES / "ranking_valor_vs_toneladas.csv")
r = r[r.producto != "Caña de azúcar"].set_index("producto")
t, val = r.produccion_t_2019_2023 / r.produccion_t_2019_2023.sum(), r.valor_cop_2019_2023 / r.valor_cop_2019_2023.sum()
print("\nParticipación sin caña de azúcar, 2019-2023 (toneladas / valor a precios SIPSA)")
for p in ("Café", "Caña panelera", "Aguacate"):
    print(f"  {p}: {pct(t[p])} / {pct(val[p])}")

# ---------- Concentración de la producción ----------
s = prod[prod.anio.between(2019, 2023) & (prod.producto != "Caña de azúcar")]
print("\nDiez productos con más toneladas sin caña, 2019-2023: municipios con producción y peso de los tres primeros")
for p in s.groupby("producto").produccion_t.sum().sort_values(ascending=False).head(10).index:
    m = s[s.producto == p].groupby("municipio").produccion_t.sum().sort_values(ascending=False)
    print(f"  {p:14s} {int((m > 0).sum()):2d} municipios, tres primeros {pct(m.head(3).sum() / m.sum())} ({', '.join(m.head(3).index)})")

# ---------- Tendencias 2014-2023 (Figura 4) ----------
ocho = s.groupby("producto").produccion_t.sum().sort_values(ascending=False).head(8).index
serie = prod[prod.anio.between(2014, 2023) & prod.producto.isin(ocho)].groupby(["producto", "anio"]).produccion_t.sum().unstack()
indice = (100 * serie[2023] / serie[2014]).round(0).astype(int).sort_values()
print("\nÍndice de producción 2023 (2014 = 100):", ", ".join(f"{p} {i}" for p, i in indice.items()))
crudo = next((RAIZ / "data/raw").glob("Consolidado_agr*permanentes*.csv"), None)
if crudo is not None:
    c = pd.read_csv(crudo, encoding="utf-8-sig", dtype=str)
    c = c[c.Cultivo == "Aguacate Hass"]
    hass = pd.to_numeric(c.Produccion_toneladas.str.replace(",", ""), errors="coerce").groupby(c["Año"].str.replace(",", "").astype(int)).sum()
    print(f"  Aguacate Hass (dato crudo): {mil(hass[2020])} t en 2020 y {mil(hass[2023])} t en 2023")

# ---------- Comprobaciones de correlación ----------
print("\nCorrelaciones (Spearman)")
ds = pd.read_csv(RES / "diagnostico_series.csv", dtype={"cod_dane": str})
pb = pd.read_csv(RES / "predicciones_baselines.csv", dtype={"cod_dane": str})
pb["error"] = (pb.naive - pb.real).abs()
w = pb.groupby(["producto", "cod_dane"]).agg(error=("error", "sum"), real=("real", "sum"))
w = w[w.real > 0]
w = (w.error / w.real).rename("wape").reset_index().merge(ds[["producto", "cod_dane", "pct_repetidos"]], on=["producto", "cod_dane"]).dropna()
rho = spearmanr(w.pct_repetidos, w.wape)
print(f"  % de valores repetidos frente al WAPE del ingenuo, por serie: {dec(rho.statistic, 2)} (p = {dec(rho.pvalue, 2)}, {len(w)} series)")
oni = pd.read_csv(CLEAN / "oni.csv").set_index("anio")["oni"]
anual = prod[prod.producto != "Caña de azúcar"].groupby("anio").produccion_t.sum().sort_index()
cambio = anual.pct_change().dropna()
mismo = spearmanr(oni.reindex(cambio.index).values, cambio.values)
rezago = spearmanr(oni.reindex(cambio.index - 1).values, cambio.values)
print(f"  ONI del año frente al cambio anual de la producción sin caña: {dec(mismo.statistic, 2)} (p = {dec(mismo.pvalue, 2)}, {len(cambio)} años)")
print(f"  ONI del año anterior frente al mismo cambio: {dec(rezago.statistic, 2)} (p = {dec(rezago.pvalue, 2)})")

# ---------- Rendimiento por subregión ----------
f = prod[(prod.familia == "Frutales") & prod.anio.between(2021, 2023)]
rend = lambda df: (df.groupby("subregion").produccion_t.sum() / df.groupby("subregion").ha_cosechadas.sum()).round(1)
pina = f[f.producto == "Piña"]
print("\nToneladas de fruta y plátano por hectárea cosechada, 2021-2023")
print("  Con piña:", ", ".join(f"{k} {dec(x)}" for k, x in rend(f).items()))
print("  Sin piña:", ", ".join(f"{k} {dec(x)}" for k, x in rend(f[f.producto != "Piña"]).items()))
print(f"  Piña: {dec(pina.produccion_t.sum() / pina.ha_cosechadas.sum())} t/ha en el departamento y {dec(rend(pina)['Sur'])} en el sur;"
      f" Dagua y La Cumbre producen {pct(pina[pina.municipio.isin(['Dagua', 'La Cumbre'])].produccion_t.sum() / pina.produccion_t.sum())} de la piña")
