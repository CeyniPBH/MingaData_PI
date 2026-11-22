"""Cifras del tablero central: cobertura a 40 km, tamaño de la central y contraste de la hipótesis.

Uso, desde la raíz del repositorio: python src/informe/cifras_hipotesis.py
Hace el mismo cálculo del tablero (src/dashboard/tablero_central.py): hectáreas sembradas promedio 2021-2023 de fruta y
plátano, distancia en línea recta entre centroides y captación del 20 %. Respalda las secciones 3.4.3, 5 y 6 del informe
y la matriz de trazabilidad (docs/dashboard/matriz_trazabilidad.md). Lee archivos del repositorio y no escribe nada.
"""
import json
import math
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "src" / "dashboard"))
from tablero_central import PATRON_DATOS, generar_html_tablero  # noqa: E402

RADIO, CAPTACION = 40, 0.20
pct = lambda x: f"{100 * x:.1f} %".replace(".", ",")
mil = lambda x: f"{x:,.0f}".replace(",", ".")

prod = pd.read_csv(RAIZ / "data/clean/produccion_valle_clean.csv", dtype={"cod_dane": str})
html = generar_html_tablero(RAIZ / "src/dashboard/assets/tablero_central_acopio_valle.html", prod)
M = json.loads(PATRON_DATOS.search(html).group(1))["muns"]


def haversine(a, b):
    r = math.pi / 180
    h = (math.sin((b["lat"] - a["lat"]) * r / 2) ** 2
         + math.cos(a["lat"] * r) * math.cos(b["lat"] * r) * math.sin((b["lon"] - a["lon"]) * r / 2) ** 2)
    return 2 * 6371.0 * math.asin(math.sqrt(h))


DIST = [[haversine(a, b) for b in M] for a in M]
TOTAL = sum(sum(m["ha"]) for m in M)
cubiertos = lambda i, r: [j for j in range(len(M)) if DIST[i][j] <= r]
area = lambda i, r=RADIO: sum(sum(M[j]["ha"]) for j in cubiertos(i, r))
toneladas = lambda i, r=RADIO, k=1: CAPTACION * sum(M[j]["t"][k] for j in cubiertos(i, r))  # k: 0 bajo, 1 base, 2 alto
recuperable = lambda i, r=RADIO: sum(M[j].get("g", 0) for j in cubiertos(i, r))
centro_norte = [i for i, m in enumerate(M) if m["s"] in ("Centro", "Norte")]
sur = [i for i, m in enumerate(M) if m["s"] == "Sur"]

print(f"Fruta y plátano, promedio 2021-2023: {mil(TOTAL)} ha en {len(M)} municipios")
por_subregion = pd.Series({m["s"]: 0.0 for m in M})
for m in M:
    por_subregion[m["s"]] += sum(m["ha"])
print("  Por subregión:", ", ".join(f"{s} {pct(x / TOTAL)}" for s, x in por_subregion.sort_values(ascending=False).items()))
fr = prod[(prod.familia == "Frutales") & prod.anio.between(2013, 2023)].groupby("anio")[["produccion_t", "ha_cosechadas"]].sum()
print(f"  Producción 2013-2023: mínimo {mil(fr.produccion_t.min())} t ({fr.produccion_t.idxmin()}), máximo {mil(fr.produccion_t.max())} t"
      f" ({fr.produccion_t.idxmax()}); área cosechada {pct(fr.ha_cosechadas[2023] / fr.ha_cosechadas[2013] - 1)} entre 2013 y 2023")

print(f"\nPregunta 1. Sedes que más área alcanzan a {RADIO} km")
orden = sorted(range(len(M)), key=lambda i: -area(i))
for i in orden[:5]:
    print(f"  {M[i]['n']:14s} {M[i]['s']:7s} {len(cubiertos(i, RADIO)):2d} municipios, {mil(area(i))} ha, {pct(area(i) / TOTAL)}")
print("  Sensibilidad al radio (cinco mejores sedes, mejor sede del centro-norte y del sur):")
for r in (20, 30, 40, 50, 60, 70, 80):
    cinco = sorted(range(len(M)), key=lambda i: -area(i, r))[:5]
    i, j = max(centro_norte, key=lambda k: area(k, r)), max(sur, key=lambda k: area(k, r))
    todas_cn = all(M[k]["s"] in ("Centro", "Norte") for k in cinco)
    print(f"    {r} km: las cinco en centro o norte: {'sí' if todas_cn else 'no'}; primera {M[cinco[0]]['n']}"
          f" ({pct(area(i, r) / TOTAL)}); sur {M[j]['n']} ({pct(area(j, r) / TOTAL)})")

print(f"\nPregunta 2. Tamaño de la central con {pct(CAPTACION)} de captación")
sede = orden[0]
base, bajo, alto = toneladas(sede), toneladas(sede, k=0), toneladas(sede, k=2)
print(f"  {M[sede]['n']}: base {mil(base)} t/año, bajo {mil(bajo)}, alto {mil(alto)}")
print(f"  Una central de {mil(base)} t se usaría al {pct(bajo / base)} en el peor año y necesitaría {pct(alto / base - 1)} más"
      f" en el mejor ({mil(alto - base)} t)")

print("\nHipótesis")
mejor_cn, mejor_sur = max(centro_norte, key=area), max(sur, key=area)
print(f"  {M[mejor_cn]['n']}: {pct(area(mejor_cn) / TOTAL)} del área, {mil(toneladas(mejor_cn))} t/año")
print(f"  {M[mejor_sur]['n']}: {pct(area(mejor_sur) / TOTAL)} del área, {mil(toneladas(mejor_sur))} t/año")
razon = lambda x: f"{x:.2f}".replace(".", ",")
print(f"  Razón de área {razon(area(mejor_cn) / area(mejor_sur))}; razón de capacidad {razon(toneladas(mejor_cn) / toneladas(mejor_sur))}"
      " (la hipótesis pide más del 50 % del área y al menos el doble de capacidad)")

print("\nProducción por recuperar (brecha de rendimiento del tablero, valor de referencia que no se recalcula desde el CSV)")
for i in (mejor_cn, mejor_sur):
    print(f"  Zona de {M[i]['n']}: {mil(recuperable(i))} t/año; con captación del 20 % la central pasaría de {mil(toneladas(i))}"
          f" a {mil(toneladas(i) + CAPTACION * recuperable(i))} t")
