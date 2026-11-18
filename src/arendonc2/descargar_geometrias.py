"""
Descarga los polígonos municipales de Colombia (GADM nivel 2) usados por la
tarea #2 para construir la vecindad Queen del Valle del Cauca.

Fuente: GADM 4.1 (https://gadm.org). Uso académico/no comercial permitido.
El archivo pesa ~1 MB y NO se versiona (va a data/raw/geo/, ignorado por git si
se desea). Se descarga una sola vez.

Uso: python src/arendonc2/descargar_geometrias.py
"""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
    from arendonc2 import common
else:
    from . import common

URL = "https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_COL_2.json.zip"
DESTINO = common.DATA_GEO / "gadm41_COL_2.json.zip"


def main():
    common.DATA_GEO.mkdir(parents=True, exist_ok=True)
    if DESTINO.exists():
        print(f"Ya existe: {DESTINO} ({DESTINO.stat().st_size:,} bytes)")
        return
    print(f"Descargando {URL} ...")
    urllib.request.urlretrieve(URL, DESTINO)
    print(f"Guardado en {DESTINO} ({DESTINO.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
