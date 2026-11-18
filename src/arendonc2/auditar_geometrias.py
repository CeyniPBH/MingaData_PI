"""
Auditoría de geometrías (punto 2 de la auditoría).

Publica el emparejamiento completo entre el nombre GADM y el código DANE,
incluidos los alias, y comprueba que las 42 geometrías corresponden a los 42
municipios esperados sin emparejamientos ambiguos (1:1).

Salida: data/results/arendonc2/emparejamiento_gadm_dane.csv

Uso: python src/arendonc2/auditar_geometrias.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
    from arendonc2 import common
else:
    from . import common

GADM_ZIP = common.DATA_GEO / "gadm41_COL_2.json.zip"


def main():
    import geopandas as gpd

    if not GADM_ZIP.exists():
        raise FileNotFoundError(
            f"Falta {GADM_ZIP}. Corre: python src/arendonc2/descargar_geometrias.py"
        )

    gdf = gpd.read_file(f"zip://{GADM_ZIP}")
    valle = gdf[gdf["NAME_1"] == "ValledelCauca"].copy()
    valle["nkey"] = valle["NAME_2"].map(common.norm_nombre)

    mun = common.leer_municipios_coordenadas()
    mun["nkey_norm"] = mun["municipio"].map(common.norm_nombre)
    mun["nkey_match"] = mun["municipio"].map(common.clave_gadm)
    mun["alias_aplicado"] = mun["nkey_norm"] != mun["nkey_match"]

    gadm_por_key = valle.set_index("nkey")["NAME_2"].to_dict()

    filas = []
    for r in mun.itertuples():
        gadm_nombre = gadm_por_key.get(r.nkey_match, None)
        filas.append({
            "cod_dane": r.cod_dane,
            "municipio_repo": r.municipio,
            "clave_normalizada": r.nkey_norm,
            "clave_match_gadm": r.nkey_match,
            "alias_aplicado": "sí" if r.alias_aplicado else "no",
            "nombre_gadm_NAME_2": gadm_nombre,
            "emparejado": "sí" if gadm_nombre is not None else "NO",
        })
    df = pd.DataFrame(filas).sort_values("cod_dane").reset_index(drop=True)

    # Comprobaciones de ambigüedad
    n_esperado = 42
    sin_match = df[df["emparejado"] == "NO"]["cod_dane"].tolist()
    # ¿algún polígono GADM se usó más de una vez?
    uso = df[df["emparejado"] == "sí"]["clave_match_gadm"].value_counts()
    duplicados = uso[uso > 1].index.tolist()
    # ¿algún polígono GADM de Valle quedó sin emparejar?
    usados = set(df["clave_match_gadm"])
    gadm_no_usados = sorted(set(valle["nkey"]) - usados)

    common.asegurar_directorios()
    out = common.DATA_RES_OUT / "emparejamiento_gadm_dane.csv"
    df.to_csv(out, index=False, encoding="utf-8-sig")

    print("=" * 70)
    print("AUDITORÍA DE GEOMETRÍAS (GADM 4.1 nivel 2 -> DANE)")
    print("=" * 70)
    print(f"Municipios en el repo       : {len(mun)}")
    print(f"Polígonos GADM en Valle     : {len(valle)}")
    print(f"Emparejados 1:1             : {(df['emparejado'] == 'sí').sum()} / {n_esperado}")
    print(f"Sin emparejar               : {sin_match if sin_match else 'ninguno'}")
    print(f"Polígonos GADM usados >1 vez : {duplicados if duplicados else 'ninguno'}")
    print(f"Polígonos GADM sin usar      : {gadm_no_usados if gadm_no_usados else 'ninguno'}")
    print(f"Alias aplicados              : "
          f"{df[df['alias_aplicado'] == 'sí'][['municipio_repo', 'nombre_gadm_NAME_2']].to_dict('records')}")
    print(f"\nTabla escrita en {out}")

    if sin_match or duplicados or gadm_no_usados or len(df) != n_esperado:
        raise SystemExit("Emparejamiento con problemas: revisar.")


if __name__ == "__main__":
    main()
