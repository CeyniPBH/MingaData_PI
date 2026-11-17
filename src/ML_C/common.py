"""Utilidades compartidas: panel de series producto x municipio y esquema walk-forward."""
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CLEAN, RES = ROOT / "data/clean", ROOT / "data/results"
ANIO_FIN = 2023
ORIGENES = [2018, 2019, 2020, 2021, 2022]      # walk-forward: entrenar hasta O, pronosticar O+1..min(O+5, 2023)
HORIZONTE_MAX = 5

def cargar_panel():
    """Devuelve (series, lista). series: dict[(producto, cod_dane)] -> pd.Series indexada por año (anio_ini..2023).
    SUPUESTO: una serie existe desde su primer año con dato hasta 2023 y un año sin registro cuenta como 0 t."""
    d = pd.read_csv(CLEAN / "produccion_valle_clean.csv", dtype={"cod_dane": str})
    lp = pd.read_csv(CLEAN / "lista_productos.csv")
    d = d[d["producto"].isin(lp.loc[lp.estado != "excluido", "producto"])]
    act = d[d.anio.between(2019, 2023) & (d.produccion_t > 0)][["producto", "cod_dane"]].drop_duplicates()
    d = d.merge(act)
    series = {}
    for (p, c), s in d.groupby(["producto", "cod_dane"]):
        y = s.set_index("anio")["produccion_t"].reindex(range(int(s.anio.min()), ANIO_FIN + 1), fill_value=0.0)
        series[(p, c)] = y.astype(float)
    return series, lp

def objetivos(O):
    return list(range(1, min(HORIZONTE_MAX, ANIO_FIN - O) + 1))
