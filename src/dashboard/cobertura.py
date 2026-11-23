"""Cálculos de cobertura, volumen captable, composición y escenarios para el resumen.

Este módulo concentra las fórmulas que usa la pantalla "0. Resumen" para que no se
dupliquen entre tarjetas, gráficos, textos y descargas. Reutiliza:

- El mismo payload del tablero visual (pantalla 4): hectáreas sembradas promedio
  2021-2023 de fruta y plátano, producción anual 2014-2023 por municipio y el
  indicador de referencia "recuperable". Se extrae con
  `tablero_central.generar_html_tablero` y `PATRON_DATOS`, el mecanismo validado por
  `src/dashboard/test_tablero_central.py` y usado por `src/informe/cifras_hipotesis.py`.
- El mismo método de distancia (haversine entre centroides) y captación (20 %) de
  `cifras_hipotesis.py`.
- El método de exposición logística sin caña de `src/informe/cifras_3_3_y_3_4.py`
  (bloque "3.4.3 exposición"), reproducido en `exposicion_sin_cana`.

Ninguna función escribe datos ni modifica resultados. La distancia es geográfica en
línea recta entre centroides (haversine), NO distancia vial.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from tablero_central import CATEGORIAS, PATRON_DATOS, generar_html_tablero

RAIZ = Path(__file__).resolve().parents[2]
RUTA_HTML = RAIZ / "src" / "dashboard" / "assets" / "tablero_central_acopio_valle.html"

RADIO_KM = 40
CAPTACION = 0.20
RADIO_TIERRA_KM = 6371.0

# Índice de los escenarios del tablero dentro de m["t"] = [bajo, base, alto].
ESCENARIO_BAJO, ESCENARIO_BASE, ESCENARIO_ALTO = 0, 1, 2


# Carga del payload del tablero (fuente única de hectáreas y producción)
def cargar_municipios_tablero(
    produccion: pd.DataFrame, ruta_html: Path | str = RUTA_HTML
) -> list[dict[str, Any]]:
    """Devuelve la lista `muns` del tablero con hectáreas y producción recalculadas.

    Cada municipio trae: id, n (nombre), s (subregión), lat, lon, ha (5 categorías),
    t (bajo/base/alto) y g (recuperable, referencia que no se recalcula desde el CSV).
    """
    html = generar_html_tablero(ruta_html, produccion)
    coincidencia = PATRON_DATOS.search(html)
    if not coincidencia:
        raise ValueError("No se encontró el bloque de datos del tablero en {}".format(ruta_html))
    return json.loads(coincidencia.group(1))["muns"]


def _haversine(a: dict[str, Any], b: dict[str, Any]) -> float:
    r = math.pi / 180.0
    h = (
        math.sin((b["lat"] - a["lat"]) * r / 2) ** 2
        + math.cos(a["lat"] * r) * math.cos(b["lat"] * r) * math.sin((b["lon"] - a["lon"]) * r / 2) ** 2
    )
    return 2 * RADIO_TIERRA_KM * math.asin(math.sqrt(h))


# Modelo de cobertura por sede
@dataclass
class ModeloCobertura:
    """Cobertura de área y volumen captable de cada sede, con el método del tablero."""

    muns: list[dict[str, Any]]
    radio_km: int = RADIO_KM
    captacion: float = CAPTACION

    def __post_init__(self) -> None:
        self._dist = [[_haversine(a, b) for b in self.muns] for a in self.muns]
        self._idx = {m["id"]: i for i, m in enumerate(self.muns)}
        self._idx_nombre = {m["n"]: i for i, m in enumerate(self.muns)}
        self.total_ha = sum(sum(m["ha"]) for m in self.muns)

    # --- utilidades de índice ---
    def indice(self, sede: str) -> int:
        if sede in self._idx:
            return self._idx[sede]
        if sede in self._idx_nombre:
            return self._idx_nombre[sede]
        raise KeyError("Sede no encontrada: {}".format(sede))

    def nombre(self, sede: str) -> str:
        return self.muns[self.indice(sede)]["n"]

    def subregion(self, sede: str) -> str:
        return self.muns[self.indice(sede)]["s"]

    def cod_dane(self, sede: str) -> str:
        return self.muns[self.indice(sede)]["id"]

    # --- cobertura ---
    def cubiertos(self, sede: str, radio_km: float | None = None) -> list[int]:
        i = self.indice(sede)
        r = self.radio_km if radio_km is None else radio_km
        return [j for j in range(len(self.muns)) if self._dist[i][j] <= r]

    def area_cubierta(self, sede: str, radio_km: float | None = None) -> float:
        """Hectáreas de fruta y plátano a <= radio_km de la sede (promedio 2021-2023)."""
        return sum(sum(self.muns[j]["ha"]) for j in self.cubiertos(sede, radio_km))

    def pct_area(self, sede: str, radio_km: float | None = None) -> float:
        if self.total_ha <= 0:
            return 0.0
        return self.area_cubierta(sede, radio_km) / self.total_ha

    def volumen_captable(self, sede: str, escenario: int = ESCENARIO_BASE,
                         radio_km: float | None = None) -> float:
        """Toneladas/año captables = captación × suma de producción de municipios cubiertos.

        escenario: 0 bajo (peor año municipal 2014-2023), 1 base (promedio 2021-2023),
        2 alto (mejor año municipal 2014-2023).
        """
        return self.captacion * sum(
            self.muns[j]["t"][escenario] for j in self.cubiertos(sede, radio_km)
        )

    def recuperable(self, sede: str, radio_km: float | None = None) -> float:
        """Producción por recuperar (brecha de rendimiento). Referencia del análisis
        original: NO se recalcula desde el CSV."""
        return sum(self.muns[j].get("g", 0) for j in self.cubiertos(sede, radio_km))

    def n_municipios(self, sede: str, radio_km: float | None = None) -> int:
        return len(self.cubiertos(sede, radio_km))

    # --- ranking ---
    def ranking_area(self, radio_km: float | None = None) -> pd.DataFrame:
        """Ranking de las 42 sedes por área cubierta, de mayor a menor.

        Empates: se ordena por área descendente y, a igualdad exacta de área, por
        nombre ascendente (orden estable y reproducible). El puesto es denso: sedes
        con el mismo porcentaje redondeado comparten posición solo si su área es
        idéntica; en la práctica las diferencias son de hectáreas, no de empates.
        """
        filas = []
        for m in self.muns:
            filas.append({
                "cod_dane": m["id"],
                "sede": m["n"],
                "subregion": m["s"],
                "n_municipios": self.n_municipios(m["id"], radio_km),
                "area_ha": self.area_cubierta(m["id"], radio_km),
                "pct_area": self.pct_area(m["id"], radio_km),
                "volumen_base_t": self.volumen_captable(m["id"], ESCENARIO_BASE, radio_km),
            })
        df = pd.DataFrame(filas).sort_values(["area_ha", "sede"], ascending=[False, True])
        df = df.reset_index(drop=True)
        df.insert(0, "puesto", df["area_ha"].rank(method="min", ascending=False).astype(int))
        return df

    def mejor_sede(self, subregiones: tuple[str, ...] | None = None,
                   radio_km: float | None = None) -> str:
        """Devuelve el cod_dane de la sede con mayor área cubierta, opcionalmente
        restringida a un conjunto de subregiones (p. ej. la mejor del sur)."""
        candidatos = [
            m for m in self.muns
            if subregiones is None or m["s"] in subregiones
        ]
        mejor = max(candidatos, key=lambda m: (self.area_cubierta(m["id"], radio_km), -ord(m["n"][0])))
        return mejor["id"]

    def puesto(self, sede: str, radio_km: float | None = None) -> int:
        rk = self.ranking_area(radio_km)
        return int(rk[rk["cod_dane"] == self.cod_dane(sede)]["puesto"].iloc[0])


# Composición productiva por sede (toneladas, no área)
def composicion_sede(
    produccion: pd.DataFrame, modelo: ModeloCobertura, sede: str,
    radio_km: float | None = None,
) -> dict[str, Any]:
    """Composición productiva de los municipios cubiertos por una sede.

    Devuelve toneladas por cultivo (promedio anual 2021-2023), superficie sembrada,
    toneladas por hectárea sembrada (razón sobre área sembrada, no rendimiento
    agronómico) y la participación de piña EN TONELADAS. Reproducible para cualquier
    sede.
    """
    cods = {modelo.muns[j]["id"] for j in modelo.cubiertos(sede, radio_km)}
    fr = produccion[
        (produccion["familia"] == "Frutales") & produccion["anio"].between(2021, 2023)
    ]
    sub = fr[fr["cod_dane"].isin(cods)]
    if sub.empty:
        return {
            "sede": modelo.nombre(sede), "toneladas_por_cultivo": pd.Series(dtype=float),
            "total_t": 0.0, "ha_sembradas": 0.0, "t_por_ha_sembrada": float("nan"),
            "pct_pina_toneladas": float("nan"), "t_por_ha_sin_pina": float("nan"),
        }
    ton = sub.groupby(["producto", "anio"])["produccion_t"].sum().groupby("producto").mean()
    ha = sub.groupby(["producto", "anio"])["ha_sembradas"].sum().groupby("producto").mean()
    total_t = float(ton.sum())
    total_ha = float(ha.sum())
    pct_pina = (ton.get("Piña", 0.0) / total_t) if total_t else float("nan")
    ton_sp = float(ton.drop("Piña", errors="ignore").sum())
    ha_sp = float(ha.drop("Piña", errors="ignore").sum())
    return {
        "sede": modelo.nombre(sede),
        "toneladas_por_cultivo": ton.sort_values(ascending=False),
        "total_t": total_t,
        "ha_sembradas": total_ha,
        "t_por_ha_sembrada": (total_t / total_ha) if total_ha else float("nan"),
        "pct_pina_toneladas": pct_pina,
        "t_por_ha_sin_pina": (ton_sp / ha_sp) if ha_sp else float("nan"),
    }


def agrupar_composicion(ton_por_cultivo: pd.Series, destacar: str = "Piña",
                        tope: int = 6) -> pd.Series:
    """Agrupa la composición en categorías legibles: el cultivo destacado, los cultivos
    de mayor tonelada y 'Otros'. Mantiene una codificación consistente entre sedes."""
    serie = ton_por_cultivo.sort_values(ascending=False)
    principales = list(serie.index[:tope])
    if destacar in serie.index and destacar not in principales:
        principales = principales[: tope - 1] + [destacar]
    orden, resto = [], 0.0
    for cultivo, valor in serie.items():
        if cultivo in principales:
            orden.append((cultivo, valor))
        else:
            resto += valor
    resultado = dict(orden)
    if resto > 0:
        resultado["Otros frutales"] = resto
    return pd.Series(resultado)


# Escenarios históricos de volumen captable
def volumenes_escenarios(modelo: ModeloCobertura, sede: str,
                         radio_km: float | None = None) -> pd.DataFrame:
    """Volumen captable en los tres escenarios históricos de una sede.

    base = promedio 2021-2023 (define el 100 %). bajo/alto combinan el peor y el mejor
    año municipal de 2014-2023, que pueden corresponder a años diferentes; no son el
    peor ni el mejor año observado del conjunto, ni llevan probabilidad asociada.
    """
    base = modelo.volumen_captable(sede, ESCENARIO_BASE, radio_km)
    bajo = modelo.volumen_captable(sede, ESCENARIO_BAJO, radio_km)
    alto = modelo.volumen_captable(sede, ESCENARIO_ALTO, radio_km)
    filas = [
        {"escenario": "Bajo sintético", "volumen_t": bajo,
         "pct_vs_base": (bajo / base) if base else float("nan")},
        {"escenario": "Base (promedio 2021-2023)", "volumen_t": base,
         "pct_vs_base": 1.0 if base else float("nan")},
        {"escenario": "Alto sintético", "volumen_t": alto,
         "pct_vs_base": (alto / base) if base else float("nan")},
    ]
    return pd.DataFrame(filas)


# Frecuencia de sedes en los escenarios de optimización (pantalla 3)
def frecuencia_centrales(estabilidad: pd.DataFrame) -> dict[str, Any]:
    """Frecuencia de cada central entre los escenarios de optimización evaluados.

    Separa las ejecuciones resueltas (OPTIMAL/FEASIBLE) de las que no entregan una
    solución interpretable. Devuelve conteos, no probabilidades. El universo de
    escenarios es global: el filtro de sede del resumen solo cambia el resaltado,
    no recalcula estos resultados.
    """
    if estabilidad is None or estabilidad.empty:
        return {"frecuencias": pd.Series(dtype=int), "n_resueltos": 0, "n_sin_solucion": 0,
                "anios": [], "n_total": 0}
    resueltos = estabilidad[estabilidad["status"].isin(["OPTIMAL", "FEASIBLE"])]
    sin_sol = estabilidad[~estabilidad["status"].isin(["OPTIMAL", "FEASIBLE"])]
    freq = resueltos["central"].value_counts()
    return {
        "frecuencias": freq,
        "n_resueltos": int(len(resueltos)),
        "n_sin_solucion": int(len(sin_sol)),
        "anios": sorted(estabilidad["anio"].unique().tolist()),
        "n_total": int(len(estabilidad)),
    }


# Exposición logística sin caña (método de cifras_3_3_y_3_4.py, bloque 3.4.3)
def exposicion_sin_cana(raiz: Path | str = RAIZ) -> dict[str, Any]:
    """Reproduce el bloque "3.4.3 exposición" de src/informe/cifras_3_3_y_3_4.py.

    Exposición sin caña = Σ |predicción − real| × minutos al nodo más cercano de la
    red del escenario base (central + satélites), para el horizonte 1, excluyendo la
    caña de azúcar (que no entra a la central). Sin modelo = promedio de los últimos
    cinco años. La valoración en COP es una "valoración de exposición" anualizada,
    NO un ahorro financiero realizado.
    """
    raiz = Path(raiz)
    res = raiz / "data/results"
    clean = raiz / "data/clean"

    pr = pd.read_csv(res / "ML_Ce/predicciones_comparacion.csv", dtype={"cod_dane": str})
    pr["final"] = (pr["naive"] + pr["lgbm"]) / 2
    sin_cana = pr[pr["producto"] != "Caña de azúcar"]

    comp = pd.read_csv(res / "opt/comparacion_libre_vs_zonas.csv")
    fila = comp[comp["modo"] == "libre"].iloc[0]
    red = {str(fila["central_cod"])} | {
        x.strip() for x in str(fila["satelites_cods"]).split(";") if x.strip()
    }
    mt = pd.read_csv(clean / "matriz_tiempos.csv", dtype={"origen": str, "destino": str})
    minutos = mt[mt["destino"].isin(red)].groupby("origen")["minutos"].min()

    h1 = sin_cana[sin_cana["horizonte"] == 1].assign(t_min=lambda d: d["cod_dane"].map(minutos))
    expo = {m: float(((h1[m] - h1["real"]).abs() * h1["t_min"]).sum()) for m in ("mean5", "naive", "final")}
    anios = int(h1["anio_objetivo"].nunique())

    reduccion_final = (expo["final"] / expo["mean5"]) - 1  # negativo = reducción
    reduccion_naive = (expo["naive"] / expo["mean5"]) - 1
    diferencia_total = expo["mean5"] - expo["final"]
    diferencia_anual = diferencia_total / anios if anios else float("nan")
    cop_tmin = 250.0

    return {
        "sin_modelo_tmin": expo["mean5"],
        "ingenuo_tmin": expo["naive"],
        "modelo_tmin": expo["final"],
        "sin_modelo_millones": expo["mean5"] / 1e6,
        "ingenuo_millones": expo["naive"] / 1e6,
        "modelo_millones": expo["final"] / 1e6,
        "reduccion_modelo_pct": reduccion_final,   # p. ej. -0.304
        "reduccion_ingenuo_pct": reduccion_naive,  # p. ej. -0.317
        "anios": anios,
        "anio_min": int(h1["anio_objetivo"].min()),
        "anio_max": int(h1["anio_objetivo"].max()),
        "red": str(fila["central"]),
        "cop_tmin": cop_tmin,
        # Valoración de exposición anualizada (NO ahorro realizado):
        "valoracion_anual_cop": diferencia_anual * cop_tmin,
        "diferencia_total_tmin": diferencia_total,
        # Verificación de la advertencia del manual: el acumulado de 5 años por 250
        # COP NO equivale a la cifra anual; hay que anualizar.
        "valoracion_acumulada_5anios_cop": diferencia_total * cop_tmin,
    }


# Título dinámico del encabezado del resumen
def titulo_resumen(modelo: ModeloCobertura, sede: str) -> str:
    """'[Sede] cubre [X] % del área y presenta [Y] t/año captables al 20 %'."""
    from utils import fmt_pct, fmt_toneladas  # import local para evitar ciclo

    nombre = modelo.nombre(sede)
    pct = modelo.pct_area(sede)
    vol = modelo.volumen_captable(sede)
    return "{} cubre {} del área y presenta {} captables al 20 %".format(
        nombre, fmt_pct(pct), fmt_toneladas(vol)
    )
