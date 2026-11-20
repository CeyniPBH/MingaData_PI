"""Orquestador raíz del pipeline MingaData.

Ejecuta, en orden:
  1. Validación de ingesta (00b).
  2. Módulo de pronóstico ML_C (00-08).
  3. Zonas, excedentes y escenarios (arendonc2), si hay insumos o se fuerza.
  4. Diagnóstico del modelo (09) y métrica de negocio (10).
  5. Tuning opcional (06b) con --con-tuning.
  6. Optimización OR-Tools (Pareto, estabilidad, libre vs zonas).
  7. Exportación a Parquet y catálogo.
  8. Pruebas automatizadas con pytest.

Uso:
    python src/pipeline/run_all.py
    python src/pipeline/run_all.py --rapido              # sin tuning ni optimización
    python src/pipeline/run_all.py --skip pruebas ml
    python src/pipeline/run_all.py --con-tuning --con-arendonc2
    python src/pipeline/run_all.py --dry-run

El log queda en data/logs/pipeline_YYYYMMDD_HHMMSS.log.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOGS = ROOT / "data" / "logs"
PY = sys.executable


@dataclass
class Etapa:
    nombre: str
    comando: list[str]
    descripcion: str


def _existe(*rutas: str) -> bool:
    return all((ROOT / r).exists() for r in rutas)


def _etapas(args) -> tuple[list[Etapa], list[str]]:
    saltar = set(args.skip or [])
    avisos: list[str] = []

    etapas = [
        Etapa("validar", [PY, "src/ML_C/00b_validar_ingesta.py"],
              "Validación de las fuentes crudas"),
        Etapa("ml", [PY, "src/ML_C/ejecutar_todo.py"],
              "Pronóstico: limpieza, baselines, LightGBM y escenarios"),
        Etapa("arendonc2", [PY, "src/arendonc2/ejecutar_todo.py"],
              "Zonas, excedentes y escenarios de optimización"),
        Etapa("diagnostico", [PY, "src/ML_C/09_diagnostico_modelo.py"],
              "Diagnóstico por horizonte, producto, municipio y confianza"),
        Etapa("metrica", [PY, "src/ML_C/10_metrica_negocio.py"],
              "Impacto logístico en t·min y COP"),
        Etapa("opt", [PY, "src/optimizacion/generar_resultados.py"],
              "Pareto, estabilidad y comparación libre vs zonas"),
        Etapa("parquet", [PY, "src/pipeline/exportar_parquet.py"],
              "Exportación a Parquet y catálogo"),
        Etapa("pruebas", [PY, "-m", "pytest", "-q"],
              "Pruebas automatizadas"),
    ]

    # Tuning: solo si se pide; es un experimento, no parte del modelo final.
    if args.con_tuning and "tuning" not in saltar:
        etapas.insert(5, Etapa("tuning", [PY, "src/ML_C/06b_tuning.py"],
                               "Búsqueda de hiperparámetros (experimento)"))

    if args.rapido:
        saltar.update({"tuning", "opt"})

    # arendonc2: si los insumos crudos descargables no están, se reutilizan salidas.
    if "arendonc2" not in saltar and "arendonc2" not in (args.skip or []):
        salidas = ("data/results/zonas.csv", "data/results/excedentes.csv",
                   "data/results/escenarios.csv")
        geo = _existe("data/raw/geo/gadm41_COL_2.json.zip")
        pob = bool(list((ROOT / "data/raw/poblacion").glob("*.xlsx")))
        if _existe(*salidas) and not (geo and pob) and not args.con_arendonc2:
            saltar.add("arendonc2")
            avisos.append(
                "arendonc2 se omite: ya existen zonas.csv, excedentes.csv y escenarios.csv "
                "y faltan insumos crudos descargables. Usa --con-arendonc2 para forzarlo."
            )

    # Validación y pruebas no se omiten por --rapido.
    etapas = [e for e in etapas if e.nombre not in saltar]
    return etapas, avisos


def _ejecutar(etapa: Etapa, log) -> tuple[int, float]:
    inicio = time.time()
    linea = f"\n===== {etapa.nombre.upper()} | {etapa.descripcion} ====="
    print(linea, flush=True)
    log.write(linea + "\n")
    log.write(" ".join(etapa.comando) + "\n")
    log.flush()
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    with subprocess.Popen(
        etapa.comando, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace", env=env,
    ) as proceso:
        assert proceso.stdout is not None
        for salida in proceso.stdout:
            print(salida, end="", flush=True)
            log.write(salida)
            log.flush()
        codigo = proceso.wait()
    segundos = time.time() - inicio
    estado = "OK" if codigo == 0 else f"FALLA (código {codigo})"
    print(f"----- {etapa.nombre}: {estado} en {segundos:.1f}s -----\n", flush=True)
    log.write(f"----- {etapa.nombre}: {estado} en {segundos:.1f}s -----\n")
    log.flush()
    return codigo, segundos


def main(argv: list[str] | None = None) -> int:
    etapas_posibles = ["validar", "ml", "arendonc2", "diagnostico", "metrica",
                       "tuning", "opt", "parquet", "pruebas"]
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip", nargs="+", choices=etapas_posibles, default=[],
                    help="Etapas a omitir")
    ap.add_argument("--rapido", action="store_true",
                    help="Omite tuning y optimización (mantiene validación, ML, diagnóstico y pruebas)")
    ap.add_argument("--con-tuning", action="store_true", help="Incluye 06b_tuning.py")
    ap.add_argument("--con-arendonc2", action="store_true",
                    help="Fuerza arendonc2 aunque falten insumos crudos")
    ap.add_argument("--continuar", action="store_true",
                    help="Continúa tras una etapa fallida")
    ap.add_argument("--dry-run", action="store_true", help="Solo muestra las etapas")
    args = ap.parse_args(argv)

    etapas, avisos = _etapas(args)
    if not etapas:
        print("No hay etapas para ejecutar.")
        return 0

    LOGS.mkdir(parents=True, exist_ok=True)
    ruta_log = LOGS / f"pipeline_{datetime.now():%Y%m%d_%H%M%S}.log"
    print("=" * 78)
    print("PIPELINE MINGADATA")
    print("=" * 78)
    for aviso in avisos:
        print(f"AVISO: {aviso}")
    print("Etapas:")
    for e in etapas:
        print(f"  - {e.nombre:12s} {e.descripcion}")
    print(f"Log: {ruta_log.relative_to(ROOT)}")
    if args.dry_run:
        for e in etapas:
            print("  " + " ".join(e.comando))
        return 0

    resultados = []
    with open(ruta_log, "w", encoding="utf-8") as log:
        log.write(f"Pipeline MingaData | {datetime.now():%Y-%m-%d %H:%M:%S}\n")
        log.write(f"Python: {PY}\n")
        for aviso in avisos:
            log.write(f"AVISO: {aviso}\n")
        for etapa in etapas:
            codigo, segundos = _ejecutar(etapa, log)
            resultados.append((etapa.nombre, codigo, segundos))
            if codigo != 0 and not args.continuar:
                print(f"Se detiene el pipeline: falló {etapa.nombre}. "
                      "Usa --continuar para ignorar el fallo.", file=sys.stderr)
                break

    print("\n" + "=" * 78)
    print("RESUMEN DEL PIPELINE")
    print("=" * 78)
    for nombre, codigo, segundos in resultados:
        estado = "OK" if codigo == 0 else f"FALLA ({codigo})"
        print(f"  {nombre:12s} {estado:14s} {segundos:7.1f}s")
    print(f"Log completo: {ruta_log.relative_to(ROOT)}")
    fallas = [r for r in resultados if r[1] != 0]
    if fallas:
        print(f"\n{len(fallas)} etapa(s) fallaron.", file=sys.stderr)
        return 1
    print("\nPipeline completado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
