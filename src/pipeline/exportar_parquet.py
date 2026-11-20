"""Exporta las tablas clave del proyecto a Parquet y actualiza el catálogo.

El CSV sigue siendo la fuente de verdad versionada; el Parquet es un artefacto
derivado (zona *refined*) que acelera lecturas y conserva los tipos. El script
nunca borra ni sobrescribe los CSV.

Particionamiento:
  - data/clean/produccion/anio=YYYY/produccion.parquet
  - data/results/excedentes/anio=YYYY/excedentes.parquet

Uso:
    python src/pipeline/exportar_parquet.py
    python src/pipeline/exportar_parquet.py --sin-catalogo
"""
from __future__ import annotations

import argparse
import shutil
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
CLEAN = ROOT / "data" / "clean"
RES = ROOT / "data" / "results"
RES_ML = RES / "ML_Ce"
META = ROOT / "data" / "metadata"
CATALOGO = META / "catalogo.yaml"

# (origen CSV, destino Parquet, zona, partición, columnas de texto)
TABLAS = [
    ("data/clean/produccion_valle_clean.csv", "data/clean/produccion", "trusted", "anio",
     ("cod_dane",)),
    ("data/clean/lista_productos.csv", "data/clean/lista_productos.parquet", "trusted", None, ()),
    ("data/clean/municipios_coordenadas.csv", "data/clean/municipios_coordenadas.parquet", "trusted", None,
     ("cod_dane",)),
    ("data/clean/destinos_coordenadas.csv", "data/clean/destinos_coordenadas.parquet", "trusted", None,
     ("id_destino",)),
    ("data/clean/matriz_tiempos.csv", "data/clean/matriz_tiempos.parquet", "trusted", None,
     ("origen", "destino")),
    ("data/clean/precio_producto_anual.csv", "data/clean/precio_producto_anual.parquet", "trusted", None, ()),
    ("data/clean/valor_producto.csv", "data/clean/valor_producto.parquet", "trusted", None, ("cod_dane",)),
    ("data/clean/poblacion_municipal.csv", "data/clean/poblacion_municipal.parquet", "trusted", None,
     ("cod_dane",)),
    ("data/clean/consumo_percapita.csv", "data/clean/consumo_percapita.parquet", "trusted", None, ()),
    ("data/clean/comercio_ica_frontera.csv", "data/clean/comercio_ica_frontera.parquet", "trusted", None, ()),
    ("data/clean/produccion_promedio_municipio.csv", "data/clean/produccion_promedio_municipio.parquet",
     "trusted", None, ("cod_dane",)),
    ("data/clean/precios_sipsa_anual.csv", "data/clean/precios_sipsa_anual.parquet", "trusted", None, ()),
    ("data/results/ML_Ce/oferta_escenarios.csv", "data/results/ML_Ce/oferta_escenarios.parquet",
     "refined", None, ("cod_dane",)),
    ("data/results/ML_Ce/oferta_departamento.csv", "data/results/ML_Ce/oferta_departamento.parquet",
     "refined", None, ()),
    ("data/results/ML_Ce/predicciones_comparacion.csv",
     "data/results/ML_Ce/predicciones_comparacion.parquet", "refined", None, ("cod_dane",)),
    ("data/results/ML_Ce/metricas_comparacion.csv", "data/results/ML_Ce/metricas_comparacion.parquet",
     "refined", None, ()),
    ("data/results/ML_Ce/importancia_variables.csv", "data/results/ML_Ce/importancia_variables.parquet",
     "refined", None, ()),
    ("data/results/ML_Ce/cobertura_intervalos.csv", "data/results/ML_Ce/cobertura_intervalos.parquet",
     "refined", None, ()),
    ("data/results/ML_Ce/coherencia_jerarquica.csv", "data/results/ML_Ce/coherencia_jerarquica.parquet",
     "refined", None, ()),
    ("data/results/ML_Ce/tuning_resultados.csv", "data/results/ML_Ce/tuning_resultados.parquet",
     "refined", None, ()),
    ("data/results/ML_Ce/tuning_holdout_resumen.csv",
     "data/results/ML_Ce/tuning_holdout_resumen.parquet", "refined", None, ()),
    ("data/results/ML_Ce/diagnostico_horizonte.csv",
     "data/results/ML_Ce/diagnostico_horizonte.parquet", "refined", None, ()),
    ("data/results/ML_Ce/diagnostico_producto.csv",
     "data/results/ML_Ce/diagnostico_producto.parquet", "refined", None, ()),
    ("data/results/ML_Ce/diagnostico_municipio.csv",
     "data/results/ML_Ce/diagnostico_municipio.parquet", "refined", None, ()),
    ("data/results/ML_Ce/diagnostico_confianza.csv",
     "data/results/ML_Ce/diagnostico_confianza.parquet", "refined", None, ()),
    ("data/results/ML_Ce/residuales_resumen.csv",
     "data/results/ML_Ce/residuales_resumen.parquet", "refined", None, ()),
    ("data/results/ML_Ce/curva_aprendizaje.csv",
     "data/results/ML_Ce/curva_aprendizaje.parquet", "refined", None, ()),
    ("data/results/ML_Ce/metrica_negocio_resumen.csv",
     "data/results/ML_Ce/metrica_negocio_resumen.parquet", "refined", None, ()),
    ("data/results/ML_Ce/metrica_negocio_producto.csv",
     "data/results/ML_Ce/metrica_negocio_producto.parquet", "refined", None, ()),
    ("data/results/ML_Ce/metrica_negocio_horizonte.csv",
     "data/results/ML_Ce/metrica_negocio_horizonte.parquet", "refined", None, ()),
    ("data/results/excedentes.csv", "data/results/excedentes", "refined", "anio", ("cod_dane",)),
    ("data/results/escenarios.csv", "data/results/escenarios.parquet", "refined", None, ()),
    ("data/results/zonas.csv", "data/results/zonas.parquet", "refined", None, ("cod_dane",)),
    ("data/results/opt/frontera_pareto_base.csv", "data/results/opt/frontera_pareto_base.parquet",
     "refined", None, ("central_cod",)),
    ("data/results/opt/estabilidad_escenarios.csv", "data/results/opt/estabilidad_escenarios.parquet",
     "refined", None, ("central_cod",)),
    ("data/results/opt/comparacion_libre_vs_zonas.csv",
     "data/results/opt/comparacion_libre_vs_zonas.parquet", "refined", None, ("central_cod",)),
    ("data/results/opt/comparacion_toneladas_vs_valor.csv",
     "data/results/opt/comparacion_toneladas_vs_valor.parquet", "refined", None,
     ("central_cod_ton", "central_cod_valor")),
]

FUENTES = {
    "produccion_valle_clean": "Gobernación del Valle / EVA, consolidados permanentes y transitorios",
    "lista_productos": "Derivado de produccion_valle_clean",
    "municipios_coordenadas": "DANE DIVIPOLA + Gobernación del Valle",
    "destinos_coordenadas": "Mercados y puertos definidos en el proyecto",
    "matriz_tiempos": "OpenStreetMap/OSRM (o aproximación documentada)",
    "precio_producto_anual": "DANE SIPSA",
    "valor_producto": "Producción × precio SIPSA",
    "poblacion_municipal": "DANE Proyecciones municipales 2020-2035",
    "consumo_percapita": "FAOSTAT Food Balances",
    "comercio_ica_frontera": "ICA FRONTERA",
    "produccion_promedio_municipio": "Derivado de producción y precios",
    "precios_sipsa_anual": "DANE SIPSA",
    "oferta_escenarios": "Modelo de pronóstico ML_C (07_escenarios.py)",
    "oferta_departamento": "Agregación municipal de oferta_escenarios",
    "predicciones_comparacion": "Walk-forward de baselines + LightGBM (06_lgbm.py)",
    "metricas_comparacion": "Evaluación walk-forward (05_baselines.py)",
    "importancia_variables": "LightGBM global (06_lgbm.py)",
    "cobertura_intervalos": "Calibración de intervalos (07_escenarios.py)",
    "coherencia_jerarquica": "Validación municipios vs departamento (07_escenarios.py)",
    "excedentes": "Oferta menos consumo local (src/arendonc2/excedentes.py)",
    "escenarios": "Escenarios de optimización (src/arendonc2/escenarios.py)",
    "zonas": "Agrupamiento espacial de municipios (src/arendonc2/zonas_acopio.py)",
    "frontera_pareto_base": "OR-Tools, barrido de lambda (src/optimizacion/)",
    "estabilidad_escenarios": "OR-Tools, escenarios de oferta/consumo/mezcla",
    "comparacion_libre_vs_zonas": "OR-Tools, comparación territorial",
    "comparacion_toneladas_vs_valor": "OR-Tools, sensibilidad por valor SIPSA",
}


def _leer_csv(ruta: Path, columnas_texto: tuple[str, ...]) -> pd.DataFrame:
    dtype = {c: str for c in columnas_texto}
    return pd.read_csv(ruta, encoding="utf-8-sig", dtype=dtype or None)


def _normalizar(df: pd.DataFrame, columnas_texto: tuple[str, ...]) -> pd.DataFrame:
    df = df.copy()
    for c in columnas_texto:
        if c in df.columns:
            df[c] = df[c].astype(str).str.zfill(5) if c in ("cod_dane",) else df[c].astype(str)
    return df


def _escribir(df: pd.DataFrame, destino: Path, particion: str | None) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    if particion:
        if destino.exists():
            shutil.rmtree(destino)  # solo se borra un artefacto Parquet derivado
        df.to_parquet(destino, partition_cols=[particion], index=False, compression="snappy")
    else:
        df.to_parquet(destino, index=False, compression="snappy")


def _filas(df: pd.DataFrame, destino: Path, particion: str | None) -> int:
    if particion:
        return int(pd.read_parquet(destino).shape[0])
    return int(df.shape[0])


def exportar(sin_catalogo: bool = False) -> int:
    META.mkdir(parents=True, exist_ok=True)
    entradas, fallos = [], []
    total_bytes = 0
    print("Exportando tablas a Parquet...")
    for origen_rel, destino_rel, zona, particion, texto in TABLAS:
        origen, destino = ROOT / origen_rel, ROOT / destino_rel
        if not origen.exists():
            print(f"  OMITIDA {origen_rel} (no existe)")
            continue
        try:
            df = _normalizar(_leer_csv(origen, texto), texto)
            _escribir(df, destino, particion)
            filas = _filas(df, destino, particion)
            if particion:
                tam = sum(p.stat().st_size for p in destino.rglob("*.parquet"))
            else:
                tam = destino.stat().st_size
            total_bytes += tam
            nombre = origen.stem
            entradas.append({
                "dataset": nombre,
                "zona": zona,
                "ruta": destino_rel.replace("\\", "/"),
                "formato": "parquet",
                "particion": particion or "ninguna",
                "filas": filas,
                "columnas": list(map(str, df.columns)),
                "dtypes": {str(k): str(v) for k, v in df.dtypes.items()},
                "fuente": FUENTES.get(nombre, "Ver docs/ML_C/fuentes_caracterizacion.md"),
                "fecha_generacion": date.today().isoformat(),
            })
            print(f"  OK {destino_rel}: {filas:,} filas, {tam / 1024:.1f} KB")
        except Exception as exc:  # noqa: BLE001
            fallos.append((origen_rel, str(exc)))
            print(f"  FALLA {origen_rel}: {exc}")

    if not sin_catalogo:
        catalogo = {
            "version": 1,
            "fecha": date.today().isoformat(),
            "descripcion": "Catálogo de tablas del data lake ligero de MingaData_PI",
            "zonas": {
                "raw": "data/raw: fuentes originales inmutables",
                "trusted": "data/clean: tablas tipadas, armonizadas y validadas",
                "refined": "data/results: pronósticos, zonas, excedentes y optimización",
            },
            "tablas": entradas,
        }
        CATALOGO.write_text(
            yaml.safe_dump(catalogo, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        print(f"\nCatálogo actualizado: {CATALOGO.relative_to(ROOT)} ({len(entradas)} tablas)")

    print(f"Total Parquet: {total_bytes / 1024 / 1024:.2f} MB")
    if fallos:
        print("\nFALLOS:")
        for nombre, error in fallos:
            print(f"  - {nombre}: {error}")
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sin-catalogo", action="store_true", help="No reescribe data/metadata/catalogo.yaml")
    args = ap.parse_args(argv)
    return exportar(sin_catalogo=args.sin_catalogo)


if __name__ == "__main__":
    sys.exit(main())
