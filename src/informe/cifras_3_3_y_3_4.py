"""Cifras de las secciones 3.3.4 y 3.4 del informe que no están guardadas en data/results.

Uso, desde la raíz del repositorio: python src/informe/cifras_3_3_y_3_4.py
Lee solo archivos del repositorio y no escribe nada. La cobertura a 40 km, la capacidad y la hipótesis
están en cifras_hipotesis.py.
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RES, CLEAN = ROOT / "data/results", ROOT / "data/clean"

# ---------- 3.3.4: métricas del modelo final (promedio ingenuo + LightGBM) ----------
pr = pd.read_csv(RES / "ML_Ce/predicciones_comparacion.csv", dtype={"cod_dane": str})
pr["final"] = (pr["naive"] + pr["lgbm"]) / 2

def met(g, m):
    e = (g[m] - g.real).abs(); en = (g.naive - g.real).abs(); ok = g.escala_mase > 0
    mase = (e[ok] / g.escala_mase[ok]).mean(); mn = (en[ok] / g.escala_mase[ok]).mean()
    w = e.sum() / g.real.abs().sum(); wn = en.sum() / g.real.abs().sum()
    return mase, w, 1 - mase / mn, 1 - w / wn

sin_cana = pr[pr.producto != "Caña de azúcar"]
print("3.3.4 Tabla 4")
for m in ["naive", "drift", "ets", "mean5", "lgbm", "final"]:
    a, b = met(pr, m), met(sin_cana, m)
    print(f"  {m:6s} MASE={a[0]:.3f} WAPE={a[1]:.1%} mejora MASE={a[2]:.2%} WAPE={a[3]:.2%} | sin caña WAPE={b[3]:.2%} MASE={b[2]:.2%}")
print("  participación de la caña en las toneladas reales:", f"{pr.loc[pr.producto=='Caña de azúcar','real'].sum()/pr.real.sum():.1%}")
gan = sum(1 for _, g in pr.groupby("producto") if met(g, "final")[2] > 0 and met(g, "final")[3] > 0)
print("  productos donde el modelo final mejora MASE y WAPE:", gan, "de", pr.producto.nunique())
for h, g in pr.groupby("horizonte"):
    print(f"  horizonte {h}: mejora MASE {met(g,'final')[2]:.2%}")

# ---------- 3.4.1: oferta y excedentes ----------
o = pd.read_csv(RES / "ML_Ce/oferta_escenarios_valor.csv", dtype={"cod_dane": str})
o = o[o.producto != "Caña de azúcar"]
print("\n3.4.1 oferta sin caña (t):"); print(o.groupby("año")[["oferta_bajo", "oferta_base", "oferta_alto"]].sum().round(0))
x = pd.read_csv(RES / "excedentes.csv", dtype={"cod_dane": str})
g = x[(x.anio == 2024) & (x.escenario_oferta == "base") & (x.escenario_consumo == "base")]
tot = g.oferta_t.sum()
print("  excedente 2024 base:", round(g.loc[g.consumo_pendiente == 0, "excedente_t"].sum()), f"({g.loc[g.consumo_pendiente==0,'excedente_t'].sum()/tot:.1%} de la oferta)")
print("  oferta sin consumo estimado por producto:"); print((g[g.consumo_pendiente == 1].groupby("producto").oferta_t.sum() / tot).sort_values(ascending=False).head(3).map("{:.1%}".format))

# ---------- 3.4.2: estabilidad de la central ----------
e = pd.read_csv(RES / "opt/estabilidad_escenarios.csv")
print("\n3.4.2 central en los 54 escenarios:"); print(e.central.value_counts())
print(pd.crosstab([e.anio, e.oferta], e.mezcla, values=e.central, aggfunc=lambda s: "/".join(sorted(set(s)))))
b = pd.read_csv(RES / "opt/frontera_pareto_base.csv")
print("  frontera (A+B):", dict(zip(b.central, b.costo_total_suma.round(0))))
base = e[e.es_base].iloc[0] if "es_base" in e else None
if base is not None: print("  peso de la distribución en el escenario base:", f"{base.B/(base.A+base.B):.1%}")

# ---------- 3.4.3: error en pesos ----------
pp = pd.read_csv(CLEAN / "precio_producto_anual.csv")
precio = pp[pp.anio.between(2021, 2023)].groupby("producto")["precio_cop_kg"].mean()
s = sin_cana.assign(p=sin_cana.producto.map(precio)).dropna(subset=["p"])
s = s.assign(ve=(s.final - s.real).abs() * 1000 * s.p, vr=s.real * 1000 * s.p, vs=(s.final - s.real) * 1000 * s.p)
print("\n3.4.3 error en pesos (sin caña)")
for h, gh in s.groupby("horizonte"):
    por_anio = gh.groupby("anio_objetivo").agg(ve=("ve", "sum"), vr=("vr", "sum"), vs=("vs", "sum"))
    print(f"  h{h}: errores por serie {gh.ve.sum()/gh.vr.sum():.1%} del valor, {por_anio.ve.mean()/1e9:,.0f} mil millones/año;"
          f" error del total departamental {por_anio.vs.abs().sum()/por_anio.vr.sum():.1%}")


# ---------- 3.4.3: comparación con la situación sin modelo (exposición logística, sin caña) ----------
# Mismo método de src/ML_C/10_metrica_negocio.py, pero sin la caña de azúcar, que no entra a la central:
# toneladas mal estimadas × minutos al acopio más cercano de la red del escenario base, a 250 COP por t·min
# (camión de 8 t a 120.000 COP por hora). Sin modelo = promedio de los últimos cinco años.
comp = pd.read_csv(RES / "opt/comparacion_libre_vs_zonas.csv")
fila = comp[comp.modo == "libre"].iloc[0]
red = {str(fila.central_cod)} | {x.strip() for x in str(fila.satelites_cods).split(";") if x.strip()}
mt = pd.read_csv(CLEAN / "matriz_tiempos.csv", dtype={"origen": str, "destino": str})
minutos = mt[mt.destino.isin(red)].groupby("origen").minutos.min()
h1 = sin_cana[sin_cana.horizonte == 1].assign(t_min=lambda d: d.cod_dane.map(minutos))
expo = {m: ((h1[m] - h1.real).abs() * h1.t_min).sum() for m in ("mean5", "naive", "final")}
anios = h1.anio_objetivo.nunique()
print(f"\n3.4.3 exposición a un año sin caña, {h1.anio_objetivo.min()}-{h1.anio_objetivo.max()} (red: {fila.central} y satélites)")
for m, nombre in (("mean5", "sin modelo (promedio 5 años)"), ("naive", "ingenuo"), ("final", "modelo final")):
    print(f"  {nombre:30s} {expo[m]/1e6:7.2f} M t·min  {expo[m]/expo['mean5']-1:+.1%} frente a sin modelo")
ahorro = (expo["mean5"] - expo["final"]) / anios
print("  diferencia anual del modelo final frente a sin modelo:",
      ", ".join(f"{c} COP/t·min: {ahorro * c / 1e6:,.0f} millones" for c in (100, 250, 600)))
