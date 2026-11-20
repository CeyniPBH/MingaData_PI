"""Traduce el error de pronóstico a impacto logístico (t·min y COP).

Idea: si el decisor planea la recolección con una oferta estimada y la oferta
real difiere, la diferencia debe moverse igual. Se aproxima el impacto bruto
como |error de oferta| × minutos al nodo logístico más cercano (central o
satélite del escenario base de OR-Tools). No es un costo contable: es una
exposición física comparable entre alternativas.

Alternativas comparadas:
  - sin modelo: promedio de los últimos 5 años (mean5).
  - ingenuo: último año observado (naive).
  - modelo final: ensamble (naive + LightGBM)/2.
  - modelo con compuerta: usa el ensamble solo en productos donde superó al
    ingenuo en la validación 2022 y tienen volumen material; en el resto usa
    el ingenuo. Se evalúa en 2023, que no participó en la compuerta.

Uso:
    python src/ML_C/10_metrica_negocio.py
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from common import CLEAN, RES

warnings.filterwarnings("ignore")

# Supuestos de costo: camión de 8 t, operación de 120.000 COP/hora.
# 120.000 COP/h / 60 min = 2.000 COP/min por camión; / 8 t = 250 COP/(t·min).
SUPUESTOS = {
    "unidad_impacto": "t·min (toneladas × minutos)",
    "costo_camion_cop_hora": 120_000,
    "capacidad_camion_t": 8.0,
    "costo_tmin_cop_base": 250.0,
    "costo_tmin_cop_bajo": 100.0,
    "costo_tmin_cop_alto": 600.0,
    "red_logistica": "central + 5 satélites del escenario base libre de OR-Tools",
    "gate_mejora_minima": 0.05,
    "gate_volumen_minimo_t": 5_000,
    "gate_validacion": 2022,
    "gate_evaluacion": 2023,
    "nota": ("El impacto es una exposición bruta de planificación, no un costo contable. "
             "No incluye precio del producto, deterioro ni capacidad real de flota."),
}


def _red_logistica() -> list[str]:
    ruta = RES.parent / "opt" / "comparacion_libre_vs_zonas.csv"
    if ruta.exists():
        comp = pd.read_csv(ruta)
        libre = comp[comp["modo"] == "libre"]
        if not libre.empty:
            fila = libre.iloc[0]
            nodos = [str(fila["central_cod"])]
            nodos += [x.strip() for x in str(fila["satelites_cods"]).split(";") if x.strip()]
            return sorted(set(nodos))
    # Respaldo: la central de la corrida base.
    return ["76113"]


def _tiempos_a_red(pred: pd.DataFrame, red: list[str]) -> pd.Series:
    mt = pd.read_csv(CLEAN / "matriz_tiempos.csv", dtype={"origen": str, "destino": str})
    sub = mt[mt["destino"].isin(red)]
    tiempos = sub.groupby("origen")["minutos"].min()
    return pred["cod_dane"].map(tiempos)


def _impacto(df: pd.DataFrame, columna: str) -> pd.Series:
    return (df[columna] - df["real"]).abs() * df["t_min"]


def _resumen(df: pd.DataFrame, etiqueta: str) -> pd.DataFrame:
    filas = []
    base = _impacto(df, "mean5").sum()
    for nombre, col in (("sin_modelo", "mean5"), ("ingenuo", "naive"),
                        ("modelo_final", "ensemble"), ("modelo_compuerta", "gated")):
        if col not in df.columns:
            continue
        imp = _impacto(df, col)
        filas.append({
            "ambito": etiqueta,
            "alternativa": nombre,
            "n_obs": len(df),
            "error_abs_t": (df[col] - df["real"]).abs().sum(),
            "tmin": imp.sum(),
            "tmin_millones": imp.sum() / 1e6,
            "cop_base": imp.sum() * SUPUESTOS["costo_tmin_cop_base"],
            "cop_bajo": imp.sum() * SUPUESTOS["costo_tmin_cop_bajo"],
            "cop_alto": imp.sum() * SUPUESTOS["costo_tmin_cop_alto"],
            "delta_vs_sin_modelo_pct": (imp.sum() / base - 1) * 100 if base else np.nan,
        })
    return pd.DataFrame(filas)


def main() -> int:
    pred = pd.read_csv(RES / "predicciones_comparacion.csv", dtype={"cod_dane": str})
    pred["ensemble"] = np.where(pred["lgbm"].notna(),
                                (pred["naive"] + pred["lgbm"]) / 2.0, pred["naive"])
    red = _red_logistica()
    pred["t_min"] = _tiempos_a_red(pred, red)
    if pred["t_min"].isna().any():
        mediana = pred["t_min"].median()
        pred["t_min"] = pred["t_min"].fillna(mediana)
        print(f"AVISO: {int(pred['t_min'].isna().sum())} municipios sin tiempo; se usa {mediana:.1f} min")

    h1 = pred[pred["horizonte"] == 1].copy()
    val = h1[h1["anio_objetivo"] == SUPUESTOS["gate_validacion"]]
    test = h1[h1["anio_objetivo"] == SUPUESTOS["gate_evaluacion"]].copy()

    # Compuerta por producto entrenada en 2022 (no usa 2023).
    seleccion = []
    detalle_gate = []
    for prod, g in val.groupby("producto"):
        ens = (g["ensemble"] - g["real"]).abs().sum()
        nai = (g["naive"] - g["real"]).abs().sum()
        vol = g["real"].sum()
        mejora = 1 - ens / nai if nai else np.nan
        usa = bool(mejora >= SUPUESTOS["gate_mejora_minima"] and vol >= SUPUESTOS["gate_volumen_minimo_t"])
        detalle_gate.append({"producto": prod, "volumen_validacion_t": vol,
                             "mejora_abs_vs_naive": mejora, "usa_modelo": usa})
        if usa:
            seleccion.append(prod)
    test["gated"] = np.where(test["producto"].isin(seleccion), test["ensemble"], test["naive"])
    h1_gated = h1[h1["anio_objetivo"] == SUPUESTOS["gate_evaluacion"]].copy()
    h1_gated["gated"] = np.where(h1_gated["producto"].isin(seleccion),
                                 h1_gated["ensemble"], h1_gated["naive"])

    resumen = pd.concat([
        _resumen(h1, "h1_2019_2023"),
        _resumen(val, "h1_2022_validacion"),
        _resumen(h1_gated, "h1_2023_holdout"),
        _resumen(pred, "todos_los_horizontes"),
    ], ignore_index=True)
    resumen.round(3).to_csv(RES / "metrica_negocio_resumen.csv", index=False, encoding="utf-8-sig")

    # Por horizonte: impacto del modelo y del ingenuo.
    filas_h = []
    for h, g in pred.groupby("horizonte"):
        filas_h.append({
            "horizonte": h, "n_obs": len(g),
            "tmin_sin_modelo": _impacto(g, "mean5").sum(),
            "tmin_ingenuo": _impacto(g, "naive").sum(),
            "tmin_modelo": _impacto(g, "ensemble").sum(),
        })
    pd.DataFrame(filas_h).round(1).to_csv(RES / "metrica_negocio_horizonte.csv", index=False,
                                          encoding="utf-8-sig")

    # Por producto en el holdout 2023.
    filas_p = []
    for prod, g in test.groupby("producto"):
        filas_p.append({
            "producto": prod, "n_obs": len(g), "real_t": g["real"].sum(),
            "tmin_sin_modelo": _impacto(g, "mean5").sum(),
            "tmin_ingenuo": _impacto(g, "naive").sum(),
            "tmin_modelo": _impacto(g, "ensemble").sum(),
            "tmin_gated": _impacto(g, "gated").sum(),
            "usa_modelo": prod in seleccion,
        })
    producto = pd.DataFrame(filas_p).sort_values("tmin_ingenuo", ascending=False)
    producto["delta_modelo_vs_ingenuo_pct"] = (
        producto["tmin_modelo"] / producto["tmin_ingenuo"] - 1) * 100
    producto.round(2).to_csv(RES / "metrica_negocio_producto.csv", index=False, encoding="utf-8-sig")

    pd.DataFrame(detalle_gate).round(4).to_csv(RES / "metrica_negocio_gate.csv", index=False,
                                               encoding="utf-8-sig")
    (RES / "metrica_negocio_supuestos.yaml").write_text(
        yaml.safe_dump({**SUPUESTOS, "red_logistica_codigos": red,
                        "productos_gate": seleccion}, allow_unicode=True, sort_keys=False),
        encoding="utf-8")

    print("Métrica de negocio (impacto logístico bruto)")
    print(f"Red: {', '.join(red)} | costo base {SUPUESTOS['costo_tmin_cop_base']:.0f} COP/(t·min)")
    print("\nResumen:")
    print(resumen[["ambito", "alternativa", "n_obs", "tmin_millones", "cop_base",
                   "delta_vs_sin_modelo_pct"]].round(2).to_string(index=False))
    print(f"\nCompuerta 2022 → 2023: {len(seleccion)} productos usan el modelo")
    print(", ".join(seleccion) if seleccion else "(ninguno; se mantiene el ingenuo)")
    print("\nPor horizonte:")
    print(pd.DataFrame(filas_h).round(2).to_string(index=False))
    print(f"\nSalidas en {RES}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
