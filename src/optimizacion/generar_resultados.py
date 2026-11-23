"""
GENERADOR DE RESULTADOS DE OPTIMIZACION PARA EL INFORME FINAL
==============================================================

Guarda en CSV los resultados que antes solo se veian en el tablero o en consola:

1. Barrido de lambda y frontera de Pareto del escenario base.
2. Estabilidad de la ubicacion en todos los escenarios de `data/results/escenarios.csv`
   para los anos indicados (por defecto 2024 y 2028; 27 escenarios por ano).
3. Comparacion entre ubicacion libre y ubicacion que respeta las zonas de Alejandro.

Salida por defecto: `data/results/opt/`

Uso:
    python src/optimizacion/generar_resultados.py
    python src/optimizacion/generar_resultados.py --anios 2024 2028
    python src/optimizacion/generar_resultados.py --anios 2024 2025 2026 2027 2028
    python src/optimizacion/generar_resultados.py --solo pareto
    python src/optimizacion/generar_resultados.py --solo estabilidad comparacion

Columnas de costos (todas en t·min, toneladas x minutos):
    costo_recoleccion        A1: municipio -> satelite
    costo_satelite_central   A2: satelite -> central
    costo_distribucion       B:  central -> destinos
    A                        A1 + A2
    B                        igual a costo_distribucion
    costo_total              objetivo del solver: lambda*A + (1-lambda)*B
    costo_total_suma         suma fisica de los tres tramos: A1 + A2 + B

El solver minimiza `costo_total` (objetivo ponderado); `costo_total_suma` sirve para
reportar el costo fisico total sin ponderacion. No se confunden a proposito.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "src" / "optimizacion"))

from modelo_real import (  # noqa: E402
    cargar_datos_reales,
    comparar_configuraciones,
    construir_matriz_tiempos_dict,
    filtrar_no_dominados,
    listar_escenarios,
    preparar_para_solver,
    resolver_ubicacion,
)

SALIDA_DEFECTO = ROOT / "data" / "results" / "opt"
ESCENARIO_BASE_DEFECTO = "2024_Obase_Cbase_M80_20"
ANIOS_DEFECTO = (2024, 2028)
LAMBDAS_DEFECTO = tuple(round(i / 10.0, 1) for i in range(11))

COLS_PARETO = [
    "lambda", "central", "central_cod", "central_zona", "satelites", "satelites_cods",
    "satelites_zonas", "n_satelites", "costo_recoleccion", "costo_satelite_central",
    "costo_distribucion", "costo_total", "costo_total_suma", "A", "B", "cobertura",
    "status", "gap_efectivo", "tiempo_s",
]

COLS_ESTABILIDAD = [
    "anio", "id_escenario", "oferta", "consumo", "mezcla", "pct_nacional",
    "pct_exportacion", "central", "central_cod", "central_zona", "satelites",
    "satelites_cods", "satelites_zonas", "n_satelites", "costo_recoleccion",
    "costo_satelite_central", "costo_distribucion", "costo_total",
    "costo_total_suma", "A", "B", "cobertura", "status", "gap_efectivo", "tiempo_s",
    "es_base", "cambia_central_vs_base", "cambia_satelites_vs_base",
]

COLS_COMPARACION = [
    "id_escenario", "anio", "lambda", "k", "modo", "central", "central_cod",
    "central_zona", "satelites", "satelites_cods", "satelites_zonas", "n_satelites",
    "costo_recoleccion", "costo_satelite_central", "costo_distribucion",
    "costo_total", "costo_total_suma", "A", "B", "cobertura", "status",
    "gap_efectivo", "tiempo_s", "delta_objetivo_vs_libre",
    "delta_objetivo_pct_vs_libre", "delta_costo_recoleccion_vs_libre",
    "delta_costo_distribucion_vs_libre", "delta_costo_total_suma_vs_libre",
    "misma_central_que_libre", "mismos_satelites_que_libre",
]

COLS_RESUMEN = [
    "id_escenario", "anio", "lambda", "k", "central_libre", "central_zonas",
    "misma_central", "satelites_libre", "satelites_zonas", "mismos_satelites",
    "objetivo_libre", "objetivo_zonas", "delta_objetivo", "delta_objetivo_pct",
    "costo_total_suma_libre", "costo_total_suma_zonas", "delta_costo_total_suma",
    "delta_costo_total_suma_pct", "status_libre", "status_zonas",
]

_SOLVER_VERSION = {"valor": None}


# UTILIDADES

def _sha256(ruta: Path) -> str:
    h = hashlib.sha256()
    with ruta.open("rb") as f:
        for bloque in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloque)
    return h.hexdigest()


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=str(ROOT), text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return None


def _mezcla(pct_nacional: float, pct_exportacion: float) -> str:
    return "{}_{}".format(int(round(pct_nacional * 100)), int(round(pct_exportacion * 100)))


def _conjunto_satelites(texto: object) -> set[str]:
    if texto is None or (isinstance(texto, float) and np.isnan(texto)):
        return set()
    return {t.strip() for t in str(texto).split(";") if t.strip()}


def _fila_resultado(res: dict, paquete) -> dict:
    """Aplana un resultado del solver con nombres de columna estables para CSV."""
    diag = res.get("diagnostico") or {}
    if diag.get("solver"):
        _SOLVER_VERSION["valor"] = diag["solver"]

    fila = {
        "central": None,
        "central_cod": None,
        "central_zona": None,
        "satelites": None,
        "satelites_cods": None,
        "satelites_zonas": None,
        "n_satelites": 0,
        "costo_recoleccion": np.nan,
        "costo_satelite_central": np.nan,
        "costo_distribucion": np.nan,
        "costo_total": np.nan,
        "costo_total_suma": np.nan,
        "A": np.nan,
        "B": np.nan,
        "cobertura": float(paquete.cobertura_oferta_pct) if paquete is not None else np.nan,
        "status": res.get("status"),
        "gap_efectivo": diag.get("gap_efectivo"),
        "tiempo_s": diag.get("tiempo_s"),
    }

    if res.get("status") in ("OPTIMAL", "FEASIBLE"):
        sats = res.get("satelites", [])
        fila.update({
            "central": res["central_nombre"],
            "central_cod": res["central"],
            "central_zona": res["central_zona"],
            "satelites": "; ".join(s["nombre"] for s in sats),
            "satelites_cods": "; ".join(s["cod_dane"] for s in sats),
            "satelites_zonas": "; ".join(s["zona"] for s in sats),
            "n_satelites": len(sats),
            "costo_recoleccion": float(res["costo_recoleccion"]),
            "costo_satelite_central": float(res["costo_satelite_central"]),
            "costo_distribucion": float(res["costo_central_destinos"]),
            "costo_total": float(res["costo_total"]),
            "costo_total_suma": float(res["A"] + res["B"]),
            "A": float(res["A"]),
            "B": float(res["B"]),
        })
    return fila


def _escribir_csv(df: pd.DataFrame, ruta: Path, columnas: list[str]) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    df = df.reindex(columns=columnas)
    df.to_csv(ruta, index=False, encoding="utf-8-sig")


def _resumen_archivo(ruta: Path) -> dict:
    with ruta.open(encoding="utf-8-sig") as f:
        filas = sum(1 for _ in f) - 1
    return {
        "filas": int(filas),
        "bytes": ruta.stat().st_size,
        "sha256": _sha256(ruta),
    }


# 1. BARRIDO DE LAMBDA Y FRONTERA DE PARETO (ESCENARIO BASE)

def generar_pareto(paquete, municipios, destinos, tiempos, k, lambdas,
                   tiempo_limite_s, gap_relativo, salida: Path):
    print("\n--- 1. Barrido de lambda y frontera de Pareto (escenario base) ---")
    filas = []
    for lam in lambdas:
        print("  lambda={:.1f} ...".format(lam), end=" ", flush=True)
        res = resolver_ubicacion(
            paquete, municipios, destinos, tiempos, k=k, lam=lam, modo="libre",
            tiempo_limite_s=tiempo_limite_s, gap_relativo=gap_relativo,
        )
        fila = {"lambda": float(lam), **_fila_resultado(res, paquete)}
        filas.append(fila)
        print("{} | central={} | A={:,.0f} | B={:,.0f}".format(
            res.get("status"), res.get("central_nombre", "-"),
            res.get("A", float("nan")), res.get("B", float("nan"))))

    barrido = pd.DataFrame(filas)
    _escribir_csv(barrido, salida / "barrido_lambda_base.csv", COLS_PARETO)

    validos = barrido[barrido["status"].isin(("OPTIMAL", "FEASIBLE"))].copy()
    frontera = filtrar_no_dominados(validos) if not validos.empty else validos
    if not frontera.empty:
        frontera = frontera.sort_values(["A", "B"]).reset_index(drop=True)
    _escribir_csv(frontera, salida / "frontera_pareto_base.csv", COLS_PARETO)

    print("  -> {} soluciones en el barrido; {} no dominadas".format(
        len(barrido), len(frontera)))
    return barrido, frontera


# 2. ESTABILIDAD EN TODOS LOS ESCENARIOS DE escenarios.csv

def generar_estabilidad(municipios, destinos, tiempos, anios, k, lam,
                        tiempo_limite_s, gap_relativo, salida: Path):
    print("\n--- 2. Estabilidad de la ubicacion en escenarios.csv ---")
    escenarios = listar_escenarios()
    faltantes_anio = [a for a in anios if a not in set(escenarios["anio"])]
    if faltantes_anio:
        raise ValueError("Anios sin escenarios en escenarios.csv: {}".format(faltantes_anio))

    seleccion = escenarios[escenarios["anio"].isin(anios)].sort_values(
        ["anio", "id_escenario"]).reset_index(drop=True)

    filas = []
    for i, esc in seleccion.iterrows():
        print("  [{}/{}] {} ...".format(i + 1, len(seleccion), esc["id_escenario"]),
              end=" ", flush=True)
        pkg = preparar_para_solver(esc["id_escenario"], int(esc["anio"]))
        res = resolver_ubicacion(
            pkg, municipios, destinos, tiempos, k=k, lam=lam, modo="libre",
            tiempo_limite_s=tiempo_limite_s, gap_relativo=gap_relativo,
        )
        fila = {
            "anio": int(esc["anio"]),
            "id_escenario": esc["id_escenario"],
            "oferta": esc["oferta"],
            "consumo": esc["consumo"],
            "mezcla": _mezcla(float(esc["pct_nacional"]), float(esc["pct_exportacion"])),
            "pct_nacional": float(esc["pct_nacional"]),
            "pct_exportacion": float(esc["pct_exportacion"]),
            **_fila_resultado(res, pkg),
        }
        filas.append(fila)
        print("{} | central={}".format(res.get("status"), res.get("central_nombre", "-")))

    df = pd.DataFrame(filas)
    df["es_base"] = df["id_escenario"].eq(
        df["anio"].astype(str) + "_Obase_Cbase_M80_20")
    df["cambia_central_vs_base"] = pd.NA
    df["cambia_satelites_vs_base"] = pd.NA

    for anio, grupo in df.groupby("anio", sort=True):
        base = grupo[grupo["es_base"]]
        if base.empty:
            continue
        b = base.iloc[0]
        if pd.isna(b["central_cod"]):
            continue
        base_sats = _conjunto_satelites(b["satelites_cods"])
        for idx, fila in grupo.iterrows():
            if pd.isna(fila["central_cod"]):
                continue
            df.loc[idx, "cambia_central_vs_base"] = (
                str(fila["central_cod"]) != str(b["central_cod"]))
            df.loc[idx, "cambia_satelites_vs_base"] = (
                _conjunto_satelites(fila["satelites_cods"]) != base_sats)

    _escribir_csv(df, salida / "estabilidad_escenarios.csv", COLS_ESTABILIDAD)

    print("  -> {} escenarios guardados ({} por anio)".format(
        len(df), ", ".join("{}: {}".format(a, int((df["anio"] == a).sum())) for a in anios)))
    return df


# 3. COMPARACION LIBRE vs ZONAS

def generar_comparacion(paquete, municipios, destinos, tiempos, k, lam,
                        tiempo_limite_s, gap_relativo, salida: Path):
    print("\n--- 3. Comparacion ubicacion libre vs zonas ---")
    comp = comparar_configuraciones(
        paquete, municipios, destinos, tiempos, k=k, lam=lam,
        tiempo_limite_s=tiempo_limite_s, gap_relativo=gap_relativo,
    )

    filas = []
    for modo in ("libre", "zonas"):
        res = comp[modo]
        print("  {} ... {}".format(modo, res.get("status")))
        filas.append({
            "id_escenario": paquete.id_escenario,
            "anio": int(paquete.anio),
            "lambda": float(lam),
            "k": int(k),
            "modo": modo,
            **_fila_resultado(res, paquete),
        })

    df = pd.DataFrame(filas)
    libre = df[df["modo"] == "libre"].iloc[0]

    for col in ("delta_objetivo_vs_libre", "delta_objetivo_pct_vs_libre",
                "delta_costo_recoleccion_vs_libre", "delta_costo_distribucion_vs_libre",
                "delta_costo_total_suma_vs_libre"):
        df[col] = np.nan
    df["misma_central_que_libre"] = pd.NA
    df["mismos_satelites_que_libre"] = pd.NA

    for idx, fila in df.iterrows():
        df.loc[idx, "delta_objetivo_vs_libre"] = fila["costo_total"] - libre["costo_total"]
        base_obj = abs(libre["costo_total"]) or 1.0
        df.loc[idx, "delta_objetivo_pct_vs_libre"] = (
            100.0 * (fila["costo_total"] - libre["costo_total"]) / base_obj)
        df.loc[idx, "delta_costo_recoleccion_vs_libre"] = (
            fila["costo_recoleccion"] - libre["costo_recoleccion"])
        df.loc[idx, "delta_costo_distribucion_vs_libre"] = (
            fila["costo_distribucion"] - libre["costo_distribucion"])
        df.loc[idx, "delta_costo_total_suma_vs_libre"] = (
            fila["costo_total_suma"] - libre["costo_total_suma"])
        df.loc[idx, "misma_central_que_libre"] = (
            str(fila["central_cod"]) == str(libre["central_cod"]))
        df.loc[idx, "mismos_satelites_que_libre"] = (
            _conjunto_satelites(fila["satelites_cods"])
            == _conjunto_satelites(libre["satelites_cods"]))

    _escribir_csv(df, salida / "comparacion_libre_vs_zonas.csv", COLS_COMPARACION)

    zonas = df[df["modo"] == "zonas"].iloc[0]
    resumen = pd.DataFrame([{
        "id_escenario": paquete.id_escenario,
        "anio": int(paquete.anio),
        "lambda": float(lam),
        "k": int(k),
        "central_libre": libre["central"],
        "central_zonas": zonas["central"],
        "misma_central": bool(zonas["misma_central_que_libre"]),
        "satelites_libre": libre["satelites"],
        "satelites_zonas": zonas["satelites"],
        "mismos_satelites": bool(zonas["mismos_satelites_que_libre"]),
        "objetivo_libre": libre["costo_total"],
        "objetivo_zonas": zonas["costo_total"],
        "delta_objetivo": zonas["costo_total"] - libre["costo_total"],
        "delta_objetivo_pct": 100.0 * (zonas["costo_total"] - libre["costo_total"])
        / (abs(libre["costo_total"]) or 1.0),
        "costo_total_suma_libre": libre["costo_total_suma"],
        "costo_total_suma_zonas": zonas["costo_total_suma"],
        "delta_costo_total_suma": zonas["costo_total_suma"] - libre["costo_total_suma"],
        "delta_costo_total_suma_pct": 100.0 * (
            zonas["costo_total_suma"] - libre["costo_total_suma"])
        / (abs(libre["costo_total_suma"]) or 1.0),
        "status_libre": libre["status"],
        "status_zonas": zonas["status"],
    }])
    _escribir_csv(resumen, salida / "comparacion_libre_vs_zonas_resumen.csv", COLS_RESUMEN)

    print("  -> libre: {} | zonas: {} | diferencia objetivo: {:.2f}%".format(
        libre["central"], zonas["central"], resumen.iloc[0]["delta_objetivo_pct"]))
    return df, resumen


# METADATOS

def escribir_metadata(salida: Path, parametros: dict) -> Path:
    entradas = [
        ROOT / "data" / "results" / "escenarios.csv",
        ROOT / "data" / "results" / "excedentes.csv",
        ROOT / "data" / "results" / "zonas.csv",
        ROOT / "data" / "clean" / "matriz_tiempos.csv",
        ROOT / "data" / "clean" / "municipios_coordenadas.csv",
        ROOT / "data" / "clean" / "destinos_coordenadas.csv",
    ]
    meta = {
        "generado": datetime.now().astimezone().isoformat(timespec="seconds"),
        "git_commit": _git_commit(),
        "python": sys.version,
        "solver": _SOLVER_VERSION["valor"],
        "parametros": parametros,
        "nota_columnas": {
            "costo_total": "lambda*A + (1-lambda)*B (objetivo que minimiza el solver)",
            "costo_total_suma": "A1 + A2 + B (suma fisica de los tres tramos)",
            "A": "A1 + A2 (recoleccion + satelite->central)",
            "B": "central->destinos (igual a costo_distribucion)",
            "cambia_central_vs_base": "comparacion contra el escenario base del mismo anio",
            "cambia_satelites_vs_base": "comparacion de conjuntos de satelites, sin importar el orden",
        },
        "entradas": {
            str(p.relative_to(ROOT)).replace("\\", "/"): {
                "bytes": p.stat().st_size, "sha256": _sha256(p)
            } for p in entradas if p.exists()
        },
        "salidas": {
            p.name: _resumen_archivo(p) for p in sorted(salida.glob("*.csv"))
        },
    }
    ruta = salida / "metadata.json"
    ruta.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return ruta


# CLI

def parsear_args(argv=None):
    ap = argparse.ArgumentParser(
        description="Genera los CSV de optimizacion para el informe final.")
    ap.add_argument("--anios", type=int, nargs="+", default=list(ANIOS_DEFECTO),
                    help="Anios de estabilidad (por defecto: 2024 2028).")
    ap.add_argument("--k", type=int, default=5, help="Numero de satelites (por defecto 5).")
    ap.add_argument("--lam", type=float, default=0.5, help="Lambda de estabilidad/comparacion.")
    ap.add_argument("--escenario-base", default=ESCENARIO_BASE_DEFECTO,
                    help="Escenario base para Pareto y comparacion.")
    ap.add_argument("--lambdas", type=float, nargs="+", default=list(LAMBDAS_DEFECTO),
                    help="Valores de lambda del barrido (por defecto 0.0 a 1.0 cada 0.1).")
    ap.add_argument("--tiempo-limite", type=int, default=120,
                    help="Limite de tiempo por solve, en segundos.")
    ap.add_argument("--gap", type=float, default=0.0,
                    help="Brecha relativa objetivo solicitada (0 = sin brecha).")
    ap.add_argument("--salida", type=Path, default=SALIDA_DEFECTO,
                    help="Carpeta de salida (por defecto data/results/opt).")
    ap.add_argument("--solo", nargs="+", choices=("pareto", "estabilidad", "comparacion"),
                    default=("pareto", "estabilidad", "comparacion"),
                    help="Generar solo una parte de los resultados.")
    ap.add_argument("--permitir-fallos", action="store_true",
                    help="No fallar si algun escenario queda sin solucion (se guarda igual).")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    args = parsear_args(argv)

    if not (0.0 <= args.lam <= 1.0):
        raise SystemExit("--lam debe estar en [0, 1].")
    if args.k < 1:
        raise SystemExit("--k debe ser >= 1.")
    if args.tiempo_limite <= 0:
        raise SystemExit("--tiempo-limite debe ser > 0.")
    if args.gap < 0:
        raise SystemExit("--gap debe ser >= 0.")

    salida = args.salida if args.salida.is_absolute() else (ROOT / args.salida)
    salida.mkdir(parents=True, exist_ok=True)

    print("=" * 74)
    print("GENERADOR DE RESULTADOS DE OPTIMIZACION")
    print("=" * 74)
    print("Salida: {}".format(salida))
    print("Escenario base: {}".format(args.escenario_base))
    print("Anios de estabilidad: {}".format(args.anios))
    print("k={} | lambda={} | gap={} | tiempo_limite={}s".format(
        args.k, args.lam, args.gap, args.tiempo_limite))

    municipios, destinos, matriz = cargar_datos_reales()
    tiempos = construir_matriz_tiempos_dict(matriz, municipios, destinos)

    paquete = preparar_para_solver(args.escenario_base, _anio_de(args.escenario_base))
    print("Volumen conocido del escenario base: {:,.1f} t | cobertura: {:.2f}%".format(
        paquete.excedente_municipio["excedente_t"].sum(), paquete.cobertura_oferta_pct))

    archivos = []
    if "pareto" in args.solo:
        barrido, frontera = generar_pareto(
            paquete, municipios, destinos, tiempos, args.k, args.lambdas,
            args.tiempo_limite, args.gap, salida)
        archivos += [salida / "barrido_lambda_base.csv", salida / "frontera_pareto_base.csv"]

    estabilidad = None
    if "estabilidad" in args.solo:
        estabilidad = generar_estabilidad(
            municipios, destinos, tiempos, args.anios, args.k, args.lam,
            args.tiempo_limite, args.gap, salida)
        archivos.append(salida / "estabilidad_escenarios.csv")

    comparacion = None
    resumen = None
    if "comparacion" in args.solo:
        if args.k != len(paquete.zonas["zona"].dropna().unique()):
            raise SystemExit(
                "El modo 'zonas' exige k = numero de zonas ({}), pero k={}. "
                "Ajusta --k o excluye 'comparacion'.".format(
                    len(paquete.zonas["zona"].dropna().unique()), args.k))
        comparacion, resumen = generar_comparacion(
            paquete, municipios, destinos, tiempos, args.k, args.lam,
            args.tiempo_limite, args.gap, salida)
        archivos += [salida / "comparacion_libre_vs_zonas.csv",
                     salida / "comparacion_libre_vs_zonas_resumen.csv"]

    parametros = {
        "escenario_base": args.escenario_base,
        "anios_estabilidad": args.anios,
        "k": args.k,
        "lambda": args.lam,
        "lambdas_pareto": args.lambdas,
        "gap_relativo": args.gap,
        "tiempo_limite_s": args.tiempo_limite,
        "partes_generadas": list(args.solo),
    }
    meta = escribir_metadata(salida, parametros)

    print("\n" + "=" * 74)
    print("ARCHIVOS GENERADOS")
    print("=" * 74)
    for p in archivos + [meta]:
        print("  {} ({:,} bytes)".format(p.relative_to(ROOT), p.stat().st_size))

    fallos = []
    if "pareto" in args.solo:
        fallos += barrido.loc[~barrido["status"].isin(("OPTIMAL", "FEASIBLE")), "lambda"] \
            .astype(str).map(lambda v: "pareto lambda={}".format(v)).tolist()
    if estabilidad is not None:
        fallos += estabilidad.loc[
            ~estabilidad["status"].isin(("OPTIMAL", "FEASIBLE")), "id_escenario"
        ].astype(str).map(lambda v: "estabilidad {}".format(v)).tolist()
    if comparacion is not None:
        fallos += comparacion.loc[
            ~comparacion["status"].isin(("OPTIMAL", "FEASIBLE")), "modo"
        ].astype(str).map(lambda v: "comparacion modo={}".format(v)).tolist()

    if fallos:
        print("\n[ATENCION] Configuraciones sin solucion OPTIMAL/FEASIBLE:")
        for f in fallos:
            print("  - {}".format(f))
        if not args.permitir_fallos:
            print("Se guardaron igual, pero el script termina con error. "
                  "Usa --permitir-fallos para aceptarlo.")
            return 1

    print("\nListo. Resultados en: {}".format(salida))
    return 0


def _anio_de(id_escenario: str) -> int:
    try:
        return int(str(id_escenario).split("_", 1)[0])
    except (ValueError, IndexError):
        raise SystemExit("No se pudo leer el anio de --escenario-base: {}".format(id_escenario))


if __name__ == "__main__":
    sys.exit(main())
