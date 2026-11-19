"""
CORRIDA PONDERADA POR VALOR (toneladas x precio SIPSA)
======================================================

Compara la ubicación óptima cuando el costo logístico se mide en toneladas x
minutos (modelo actual) contra una ponderación por valor, usando los precios
SIPSA de `data/results/ML_Ce/oferta_escenarios_valor.csv`.

Idea:
  - El modelo actual minimiza t·min: cada tonelada pesa igual.
  - La variante por valor reemplaza el excedente q_m por
        q_eq_m = Q * V_m / V_total
    donde V_m = suma_producto(excedente_t * 1000 * precio_cop_kg).
    Así, el modelo resuelve el MISMO problema de localización, pero cada
    municipio pesa según el valor de su producción. El total de q_eq se
    normaliza al total de toneladas para conservar la escala.
  - La red resultante se evalúa en las dos métricas:
        costo_toneladas = lambda*A + (1-lambda)*B          (t·min)
        costo_valor     = lambda*A_val + (1-lambda)*B_val  (COP·min)
    para responder si cambia la central y cuánto cuesta en toneladas.

No modifica `modelo_real.py`: usa `dataclasses.replace` para cambiar sólo el
excedente que ve el solver.

Uso:
    python src/optimizacion/corrida_valor.py
    python src/optimizacion/corrida_valor.py --anios 2024
    python src/optimizacion/corrida_valor.py --escenario 2024_Obase_Cbase_M50_50

Salida por defecto: `data/results/opt/`
    comparacion_toneladas_vs_valor.csv
    comparacion_toneladas_vs_valor_resumen.csv
    metadata_valor.json

Notas metodológicas:
  - Se usa `precio_cop_kg` (SIPSA), NO `valor_*_cop`, porque este último valora
    la oferta total y aquí interesa el excedente que realmente se transporta.
  - Los productos sin precio (Arazá, Chontaduro, Papachina, etc.) reciben el
    precio de referencia ponderado del escenario. Su participación se reporta
    en `cobertura_valor_pct`; en 2024/2028 es > 99 %.
  - Cuando hay empates, el solver puede devolver satélites alternativos con el
    mismo costo. La comparación relevante es la central y el costo, no el orden
    ni la identidad exacta de los satélites.
  - Cada solve tiene 120 s. Si queda FEASIBLE (sin certificado de optimalidad),
    se reintenta con 600 s para no reportar un artefacto del límite de tiempo.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import replace
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "src" / "optimizacion"))

from modelo_real import (  # noqa: E402
    cargar_datos_reales,
    construir_matriz_tiempos_dict,
    construir_pesos_destinos,
    listar_escenarios,
    preparar_para_solver,
    resolver_ubicacion,
)

SALIDA_DEFECTO = ROOT / "data" / "results" / "opt"
ESCENARIO_BASE = "2024_Obase_Cbase_M80_20"
ANIOS_DEFECTO = (2024, 2028)
EXCEDENTES = ROOT / "data" / "results" / "excedentes.csv"
VALOR = ROOT / "data" / "results" / "ML_Ce" / "oferta_escenarios_valor.csv"
ESTABILIDAD = SALIDA_DEFECTO / "estabilidad_escenarios.csv"

COLS_SALIDA = [
    "anio", "id_escenario",
    "central_ton", "central_cod_ton", "central_zona_ton",
    "central_valor", "central_cod_valor", "central_zona_valor",
    "misma_central",
    "satelites_ton", "satelites_valor", "mismos_satelites", "n_satelites",
    "obj_ton_red_ton", "obj_ton_red_valor",
    "obj_valor_red_ton", "obj_valor_red_valor",
    "delta_ton_pct", "delta_valor_pct",
    "A_ton_red_ton", "B_ton_red_ton",
    "A_valor_red_ton", "B_valor_red_ton",
    "A_ton_red_valor", "B_ton_red_valor",
    "A_valor_red_valor", "B_valor_red_valor",
    "volumen_total_t", "valor_total_cop", "precio_ref_cop_kg",
    "cobertura_valor_pct",
    "status_ton", "status_valor", "tiempo_s_valor", "gap_efectivo_valor",
]

COLS_RESUMEN = [
    "anio", "n_escenarios", "n_cambia_central", "n_cambia_satelites",
    "delta_ton_pct_promedio", "delta_ton_pct_max",
    "delta_valor_pct_promedio", "delta_valor_pct_min",
    "casos_cambio_central",
]


# =============================================================================
# UTILIDADES
# =============================================================================

def _sha256(ruta: Path) -> str:
    h = hashlib.sha256()
    with ruta.open("rb") as f:
        for bloque in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloque)
    return h.hexdigest()


def _ruta_legible(ruta: Path) -> str:
    try:
        return str(ruta.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(ruta)


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=str(ROOT), text=True,
            stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return None


def _leer_csv(ruta: Path, **kwargs) -> pd.DataFrame:
    return pd.read_csv(ruta, encoding="utf-8-sig", **kwargs)


def _cargar_precios() -> pd.DataFrame:
    """Precio SIPSA por producto, municipio y año."""
    val = _leer_csv(VALOR)
    # La columna de año viene con tilde; se renombra por posición para evitar
    # problemas de codificación entre Windows/PowerShell.
    val = val.rename(columns={val.columns[2]: "anio"})
    val["cod_dane"] = val["cod_dane"].astype(str).str.zfill(5)
    return val[["producto", "cod_dane", "anio", "precio_cop_kg"]].drop_duplicates()


def _cargar_excedentes() -> pd.DataFrame:
    return _leer_csv(EXCEDENTES, dtype={"cod_dane": str})


# =============================================================================
# PESOS POR VALOR
# =============================================================================

def construir_pesos_valor(paquete, precios: pd.DataFrame, excedentes: pd.DataFrame):
    """
    Devuelve un dict con:
      valor_municipio : COP por municipio (suma de excedente * precio)
      q_eq            : toneladas equivalentes de valor (misma escala que q)
      precio_ref      : COP/kg promedio ponderado por excedente
      cobertura_valor : % del excedente con precio SIPSA observado
      valor_total     : COP total del excedente
    """
    q = paquete.excedente_municipio.set_index("cod_dane")["excedente_t"].astype(float)
    q_index = q.index.tolist()

    sel = excedentes[
        (excedentes["anio"] == paquete.anio)
        & (excedentes["escenario_oferta"] == paquete.escenario_oferta)
        & (excedentes["escenario_consumo"] == paquete.escenario_consumo)
        & (excedentes["consumo_pendiente"] == 0)
    ].copy()
    sel = sel.merge(
        precios[precios["anio"] == paquete.anio],
        on=["producto", "cod_dane"], how="left",
    )

    con_precio = sel[sel["precio_cop_kg"].notna() & (sel["excedente_t"] > 0)]
    if con_precio.empty:
        raise ValueError(
            "No hay excedente con precio SIPSA para {}.".format(paquete.id_escenario))
    precio_ref = float(
        (con_precio["excedente_t"] * con_precio["precio_cop_kg"]).sum()
        / con_precio["excedente_t"].sum()
    )

    # Productos sin precio: se imputa el precio de referencia (ponderación
    # neutra). Su volumen se reporta en la cobertura.
    sel["precio_usado"] = sel["precio_cop_kg"].fillna(precio_ref)
    sel["valor_cop"] = sel["excedente_t"] * 1000.0 * sel["precio_usado"]

    valor_mun = sel.groupby("cod_dane")["valor_cop"].sum().reindex(q_index).fillna(0.0)
    sin_precio_t = float(
        sel.loc[sel["precio_cop_kg"].isna(), "excedente_t"].sum())
    q_total = float(q.sum())
    valor_total = float(valor_mun.sum())
    if valor_total <= 0:
        raise ValueError("Valor total no positivo en {}.".format(paquete.id_escenario))

    # q_eq = Q * V_m / V_total: conserva el total de toneladas y hace que el
    # objetivo del solver sea equivalente a valor * minutos (salvo constante).
    q_eq = (q_total * valor_mun / valor_total).reindex(q_index).fillna(0.0)
    cobertura_valor = 100.0 * (1.0 - sin_precio_t / q_total) if q_total else 0.0

    return {
        "valor_municipio": valor_mun,
        "q_eq": q_eq,
        "precio_ref": precio_ref,
        "cobertura_valor": cobertura_valor,
        "valor_total": valor_total,
        "excedente_sin_precio_t": sin_precio_t,
    }


def paquete_ponderado(paquete, pesos: dict):
    """Copia el paquete cambiando sólo el excedente que ve el solver."""
    q_eq = pesos["q_eq"]
    excedente = paquete.excedente_municipio.assign(
        excedente_t=paquete.excedente_municipio["cod_dane"].map(q_eq).fillna(0.0)
    )
    return replace(paquete, excedente_municipio=excedente)


# =============================================================================
# COSTOS DE UNA RED (toneladas y valor)
# =============================================================================

def costos_red(paquete, res, tiempos, pesos_dest, valor_municipio):
    """
    Calcula, para una red dada (central + satélites + asignaciones):
      - A1, A2, B y objetivo en t·min
      - A1, A2, B y objetivo en COP·min
    """
    q = paquete.excedente_municipio.set_index("cod_dane")["excedente_t"].astype(float)
    v = valor_municipio.reindex(q.index).fillna(0.0)
    central = res["central"]
    asignaciones = res["asignaciones_municipio_satelite"]

    # Toneladas
    a1_t = sum(q[m] * tiempos[(m, s)] for m, s in asignaciones)
    vol_sat = {}
    for m, s in asignaciones:
        vol_sat[s] = vol_sat.get(s, 0.0) + q[m]
    a2_t = sum(vol * tiempos[(s, central)] for s, vol in vol_sat.items())
    costo_unit = sum(p * tiempos[(central, d)] for d, p in pesos_dest.items())
    b_t = float(q.sum()) * costo_unit

    # Valor (misma red, pesos en COP)
    a1_v = sum(v[m] * tiempos[(m, s)] for m, s in asignaciones)
    val_sat = {}
    for m, s in asignaciones:
        val_sat[s] = val_sat.get(s, 0.0) + v[m]
    a2_v = sum(val * tiempos[(s, central)] for s, val in val_sat.items())
    b_v = float(v.sum()) * costo_unit

    return {
        "A1_ton": a1_t, "A2_ton": a2_t, "A_ton": a1_t + a2_t, "B_ton": b_t,
        "obj_ton": float(res["lambda"]) * (a1_t + a2_t) + (1 - float(res["lambda"])) * b_t,
        "A1_valor": a1_v, "A2_valor": a2_v, "A_valor": a1_v + a2_v, "B_valor": b_v,
        "obj_valor": float(res["lambda"]) * (a1_v + a2_v) + (1 - float(res["lambda"])) * b_v,
    }


def reconstruir_asignaciones(paquete, central: str, satelites: list[str], tiempos):
    """
    Para reutilizar la corrida por toneladas sin volver a resolver:
    cada municipio se asigna al satélite abierto que minimiza
    t[m,s] + t[s,central]. Es la regla del modelo (A1 + A2).
    """
    q_index = paquete.excedente_municipio["cod_dane"].tolist()
    asignaciones = []
    for m in q_index:
        s = min(satelites, key=lambda x: (tiempos[(m, x)] + tiempos[(x, central)], x))
        asignaciones.append((m, s))
    return asignaciones


def _resultado_toneladas_desde_csv(paquete, fila: pd.Series, tiempos):
    """Reconstruye un resultado mínimo desde estabilidad_escenarios.csv."""
    codigos = [s.strip() for s in str(fila["satelites_cods"]).split(";") if s.strip()]
    nombres = [s.strip() for s in str(fila["satelites"]).split(";") if s.strip()]
    satelites = [
        {"cod_dane": cod, "nombre": nombres[i] if i < len(nombres) else cod}
        for i, cod in enumerate(codigos)
    ]
    central = str(fila["central_cod"])
    return {
        "status": fila["status"],
        "central": central,
        "central_nombre": fila["central"],
        "central_zona": fila["central_zona"],
        "satelites": satelites,
        "asignaciones_municipio_satelite": reconstruir_asignaciones(
            paquete, central, codigos, tiempos),
        "lambda": None,
    }


# =============================================================================
# GENERACIÓN
# =============================================================================

def _resolver_con_reintento(paquete, municipios, destinos, tiempos, *,
                            k: int, lam: float, tiempo_limite: int, gap: float,
                            tiempo_reintento: int, etiqueta: str):
    """
    Resuelve una red y, si el solver no certifica optimalidad (FEASIBLE),
    reintenta con un límite mayor. En instancias con muchos empates SCIP puede
    agotar el límite corto y devolver una solución peor que la red de
    toneladas; el reintento evita reportar ese artefacto como resultado.
    """
    res = resolver_ubicacion(
        paquete, municipios, destinos, tiempos, k=k, lam=lam, modo="libre",
        tiempo_limite_s=tiempo_limite, gap_relativo=gap)
    if res.get("status") != "OPTIMAL" and tiempo_reintento > tiempo_limite:
        gap_previo = res.get("diagnostico", {}).get("gap_efectivo")
        print("\n    {}: {} (gap={}); reintentando con {} s ...".format(
            etiqueta, res.get("status"), gap_previo, tiempo_reintento),
            end=" ", flush=True)
        res = resolver_ubicacion(
            paquete, municipios, destinos, tiempos, k=k, lam=lam, modo="libre",
            tiempo_limite_s=tiempo_reintento, gap_relativo=gap)
    return res


def generar(escenarios: pd.DataFrame, k: int, lam: float, tiempo_limite: int,
            gap: float, salida: Path, reusar_toneladas: bool,
            tiempo_reintento: int = 600):
    precios = _cargar_precios()
    excedentes = _cargar_excedentes()
    municipios, destinos, matriz = cargar_datos_reales()
    tiempos = construir_matriz_tiempos_dict(matriz, municipios, destinos)

    est = None
    if reusar_toneladas and ESTABILIDAD.exists():
        est = _leer_csv(ESTABILIDAD, dtype={"central_cod": str, "satelites_cods": str})
        est = est[est["anio"].isin(escenarios["anio"].unique())]

    filas = []
    for i, esc in escenarios.reset_index(drop=True).iterrows():
        idesc, anio = esc["id_escenario"], int(esc["anio"])
        print("[{}/{}] {} ...".format(i + 1, len(escenarios), idesc),
              end=" ", flush=True)
        pkg = preparar_para_solver(idesc, anio)
        pesos = construir_pesos_valor(pkg, precios, excedentes)
        pesos_dest = construir_pesos_destinos(
            destinos, pkg.pct_nacional, pkg.pct_exportacion)
        pkg_val = paquete_ponderado(pkg, pesos)

        # Red por toneladas: reutilizar si está en la tabla de estabilidad.
        res_ton = None
        if est is not None:
            fila_est = est[est["id_escenario"] == idesc]
            if not fila_est.empty:
                res_ton = _resultado_toneladas_desde_csv(
                    pkg, fila_est.iloc[0], tiempos)
                res_ton["lambda"] = lam
                # Validar que la reconstrucción reproduzca el costo guardado.
                c = costos_red(pkg, res_ton, tiempos, pesos_dest,
                               pesos["valor_municipio"])
                guardado = float(fila_est.iloc[0]["costo_total"])
                if abs(c["obj_ton"] - guardado) > max(1.0, 1e-6 * abs(guardado)):
                    print("(reconstrucción no coincide, se resuelve) ", end="")
                    res_ton = None
        if res_ton is None:
            res_ton = _resolver_con_reintento(
                pkg, municipios, destinos, tiempos, k=k, lam=lam,
                tiempo_limite=tiempo_limite, gap=gap,
                tiempo_reintento=tiempo_reintento, etiqueta="toneladas")
            res_ton["lambda"] = lam

        res_val = _resolver_con_reintento(
            pkg_val, municipios, destinos, tiempos, k=k, lam=lam,
            tiempo_limite=tiempo_limite, gap=gap,
            tiempo_reintento=tiempo_reintento, etiqueta="valor")
        res_val["lambda"] = lam

        c_ton = costos_red(pkg, res_ton, tiempos, pesos_dest,
                           pesos["valor_municipio"])
        c_val = costos_red(pkg, res_val, tiempos, pesos_dest,
                           pesos["valor_municipio"])

        ok = (res_ton.get("status") in ("OPTIMAL", "FEASIBLE")
              and res_val.get("status") in ("OPTIMAL", "FEASIBLE")
              and res_ton.get("central") and res_val.get("central"))
        fila = {
            "anio": anio,
            "id_escenario": idesc,
            "central_ton": res_ton.get("central_nombre"),
            "central_cod_ton": res_ton.get("central"),
            "central_zona_ton": res_ton.get("central_zona"),
            "central_valor": res_val.get("central_nombre"),
            "central_cod_valor": res_val.get("central"),
            "central_zona_valor": res_val.get("central_zona"),
            "misma_central": res_ton.get("central") == res_val.get("central"),
            "satelites_ton": "; ".join(
                s.get("nombre", s.get("cod_dane", "")) for s in res_ton.get("satelites", [])),
            "satelites_valor": "; ".join(
                s.get("nombre", s.get("cod_dane", "")) for s in res_val.get("satelites", [])),
            "mismos_satelites": (
                {s.get("cod_dane") for s in res_ton.get("satelites", [])}
                == {s.get("cod_dane") for s in res_val.get("satelites", [])}
            ),
            "n_satelites": len(res_val.get("satelites", [])),
            "obj_ton_red_ton": c_ton["obj_ton"],
            "obj_ton_red_valor": c_ton["obj_valor"],
            "obj_valor_red_ton": c_val["obj_ton"],
            "obj_valor_red_valor": c_val["obj_valor"],
            "delta_ton_pct": 100.0 * (c_val["obj_ton"] / c_ton["obj_ton"] - 1.0)
            if c_ton["obj_ton"] else np.nan,
            "delta_valor_pct": 100.0 * (c_val["obj_valor"] / c_ton["obj_valor"] - 1.0)
            if c_ton["obj_valor"] else np.nan,
            "A_ton_red_ton": c_ton["A_ton"],
            "B_ton_red_ton": c_ton["B_ton"],
            "A_valor_red_ton": c_val["A_ton"],
            "B_valor_red_ton": c_val["B_ton"],
            "A_ton_red_valor": c_ton["A_valor"],
            "B_ton_red_valor": c_ton["B_valor"],
            "A_valor_red_valor": c_val["A_valor"],
            "B_valor_red_valor": c_val["B_valor"],
            "volumen_total_t": float(pkg.excedente_municipio["excedente_t"].sum()),
            "valor_total_cop": pesos["valor_total"],
            "precio_ref_cop_kg": pesos["precio_ref"],
            "cobertura_valor_pct": pesos["cobertura_valor"],
            "status_ton": res_ton.get("status"),
            "status_valor": res_val.get("status"),
            "tiempo_s_valor": res_val.get("diagnostico", {}).get("tiempo_s"),
            "gap_efectivo_valor": res_val.get("diagnostico", {}).get("gap_efectivo"),
        }
        filas.append(fila)
        print("{} | ton={} | valor={} | {}".format(
            "OK" if ok else "FALLO",
            res_ton.get("central_nombre", "-"),
            res_val.get("central_nombre", "-"),
            "CAMBIA" if not fila["misma_central"] else "igual"))

    return pd.DataFrame(filas)


def resumir(df: pd.DataFrame) -> pd.DataFrame:
    filas = []
    for anio, grupo in df.groupby("anio", sort=True):
        cambios = grupo[~grupo["misma_central"]]
        filas.append({
            "anio": anio,
            "n_escenarios": len(grupo),
            "n_cambia_central": int((~grupo["misma_central"]).sum()),
            "n_cambia_satelites": int((~grupo["mismos_satelites"]).sum()),
            "delta_ton_pct_promedio": float(cambios["delta_ton_pct"].mean())
            if not cambios.empty else 0.0,
            "delta_ton_pct_max": float(cambios["delta_ton_pct"].max())
            if not cambios.empty else 0.0,
            "delta_valor_pct_promedio": float(cambios["delta_valor_pct"].mean())
            if not cambios.empty else 0.0,
            "delta_valor_pct_min": float(cambios["delta_valor_pct"].min())
            if not cambios.empty else 0.0,
            "casos_cambio_central": "; ".join(
                "{}: {}->{}".format(r["id_escenario"], r["central_ton"], r["central_valor"])
                for _, r in cambios.iterrows()),
        })
    total = {
        "anio": "TOTAL",
        "n_escenarios": len(df),
        "n_cambia_central": int((~df["misma_central"]).sum()),
        "n_cambia_satelites": int((~df["mismos_satelites"]).sum()),
        "delta_ton_pct_promedio": float(df.loc[~df["misma_central"], "delta_ton_pct"].mean())
        if (~df["misma_central"]).any() else 0.0,
        "delta_ton_pct_max": float(df["delta_ton_pct"].max()),
        "delta_valor_pct_promedio": float(
            df.loc[~df["misma_central"], "delta_valor_pct"].mean())
        if (~df["misma_central"]).any() else 0.0,
        "delta_valor_pct_min": float(df["delta_valor_pct"].min()),
        "casos_cambio_central": "",
    }
    filas.append(total)
    return pd.DataFrame(filas)


def escribir_metadata(salida: Path, parametros: dict, df: pd.DataFrame) -> Path:
    entradas = [EXCEDENTES, VALOR, ESTABILIDAD]
    meta = {
        "generado": datetime.now().astimezone().isoformat(timespec="seconds"),
        "git_commit": _git_commit(),
        "python": sys.version,
        "parametros": parametros,
        "nota": (
            "q_eq = Q * V_m / V_total; el solver minimiza la misma formulación "
            "pero con excedente ponderado por valor. Los costos se reportan en "
            "t·min (red real) y COP·min (red ponderada)."
        ),
        "entradas": {
            str(p.relative_to(ROOT)).replace("\\", "/"): {
                "bytes": p.stat().st_size, "sha256": _sha256(p)
            } for p in entradas if p.exists()
        },
        "salidas": {
            "comparacion_toneladas_vs_valor.csv": {
                "filas": int(len(df)), "sha256": _sha256(salida / "comparacion_toneladas_vs_valor.csv")
            },
            "comparacion_toneladas_vs_valor_resumen.csv": {
                "sha256": _sha256(salida / "comparacion_toneladas_vs_valor_resumen.csv")
            },
        },
    }
    ruta = salida / "metadata_valor.json"
    ruta.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return ruta


# =============================================================================
# CLI
# =============================================================================

def parsear_args(argv=None):
    ap = argparse.ArgumentParser(
        description="Corrida ponderada por valor (SIPSA) vs toneladas.")
    ap.add_argument("--anios", type=int, nargs="+", default=list(ANIOS_DEFECTO),
                    help="Años a comparar (por defecto 2024 2028).")
    ap.add_argument("--escenario", default=None,
                    help="ID de un solo escenario; si se omite, corre todos los del año.")
    ap.add_argument("--k", type=int, default=5, help="Número de satélites (5).")
    ap.add_argument("--lam", type=float, default=0.5, help="Lambda (0.5).")
    ap.add_argument("--tiempo-limite", type=int, default=120,
                    help="Límite de tiempo por solve, en segundos.")
    ap.add_argument("--tiempo-reintento", type=int, default=600,
                    help="Límite si un solve queda FEASIBLE (600 s).")
    ap.add_argument("--gap", type=float, default=0.0,
                    help="Brecha relativa solicitada (0 = sin brecha).")
    ap.add_argument("--salida", type=Path, default=SALIDA_DEFECTO,
                    help="Carpeta de salida (data/results/opt).")
    ap.add_argument("--no-reusar-toneladas", action="store_true",
                    help="No reutilizar estabilidad_escenarios.csv; resolver ambas redes.")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    args = parsear_args(argv)
    if args.k < 1:
        raise SystemExit("--k debe ser >= 1.")
    if not (0.0 <= args.lam <= 1.0):
        raise SystemExit("--lam debe estar en [0, 1].")
    if args.gap < 0:
        raise SystemExit("--gap debe ser >= 0.")
    if args.tiempo_reintento < args.tiempo_limite:
        raise SystemExit("--tiempo-reintento debe ser >= --tiempo-limite.")

    salida = args.salida if args.salida.is_absolute() else (ROOT / args.salida)
    salida.mkdir(parents=True, exist_ok=True)

    if args.escenario:
        try:
            anio = int(str(args.escenario).split("_", 1)[0])
        except (ValueError, IndexError):
            raise SystemExit("No se pudo leer el año de --escenario: {}".format(args.escenario))
        escenarios = pd.DataFrame([{
            "id_escenario": args.escenario, "anio": anio,
            "oferta": None, "consumo": None,
        }])
    else:
        escenarios = listar_escenarios()
        escenarios = escenarios[escenarios["anio"].isin(args.anios)].sort_values(
            ["anio", "id_escenario"]).reset_index(drop=True)

    if escenarios.empty:
        raise SystemExit("No hay escenarios para los años indicados.")

    print("=" * 78)
    print("CORRIDA PONDERADA POR VALOR (SIPSA) vs TONELADAS")
    print("=" * 78)
    print("Escenarios: {} | k={} | lambda={} | gap={}".format(
        len(escenarios), args.k, args.lam, args.gap))
    print("Salida: {}".format(salida))

    df = generar(
        escenarios, args.k, args.lam, args.tiempo_limite, args.gap, salida,
        reusar_toneladas=not args.no_reusar_toneladas,
        tiempo_reintento=args.tiempo_reintento,
    )
    df = df.reindex(columns=COLS_SALIDA)
    ruta = salida / "comparacion_toneladas_vs_valor.csv"
    df.to_csv(ruta, index=False, encoding="utf-8-sig")

    resumen = resumir(df)
    ruta_res = salida / "comparacion_toneladas_vs_valor_resumen.csv"
    resumen.reindex(columns=COLS_RESUMEN).to_csv(ruta_res, index=False, encoding="utf-8-sig")

    meta = escribir_metadata(salida, {
        "escenarios": len(escenarios),
        "anios": sorted(escenarios["anio"].unique().tolist()),
        "k": args.k,
        "lambda": args.lam,
        "gap_relativo": args.gap,
        "tiempo_limite_s": args.tiempo_limite,
        "tiempo_reintento_s": args.tiempo_reintento,
        "reusar_toneladas": not args.no_reusar_toneladas,
    }, df)

    print("\n" + "=" * 78)
    print("RESUMEN")
    print("=" * 78)
    print(resumen[["anio", "n_escenarios", "n_cambia_central",
                   "n_cambia_satelites", "delta_ton_pct_promedio",
                   "delta_valor_pct_promedio"]].to_string(index=False))
    print("\nArchivos:")
    for p in (ruta, ruta_res, meta):
        print("  {} ({:,} bytes)".format(_ruta_legible(p), p.stat().st_size))

    fallos = df[~df["status_ton"].isin(["OPTIMAL", "FEASIBLE"])
                | ~df["status_valor"].isin(["OPTIMAL", "FEASIBLE"])]
    if not fallos.empty:
        print("\n[ATENCION] Escenarios sin solución OPTIMAL/FEASIBLE:")
        print(fallos[["id_escenario", "status_ton", "status_valor"]].to_string(index=False))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
