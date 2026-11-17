"""Utilidades compartidas del módulo de pronóstico."""
from pathlib import Path
import yaml
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data/raw"
CLEAN = ROOT / "data/clean"
RES = ROOT / "data/results/ML_Ce"
CFG = yaml.safe_load((ROOT / "config/ML_C/parametros.yaml").read_text(encoding="utf-8"))
ANIO_FIN = int(CFG["pronostico"]["anio_fin"])
ORIGENES = list(CFG["pronostico"]["origenes_walk_forward"])  # walk-forward: entrenar hasta O, pronosticar O+1..min(O+5, 2023)
HORIZONTE_MAX = int(CFG["pronostico"]["horizonte_max"])


def cargar_panel():
    """Devuelve (series, lista). series: dict[(producto, cod_dane)] -> pd.Series indexada por año (anio_ini..2023).
    SUPUESTO: una serie existe desde su primer año con dato hasta 2023 y un año sin registro cuenta como 0 t."""
    d = pd.read_csv(CLEAN / "produccion_valle_clean.csv", dtype={"cod_dane": str})
    lp = pd.read_csv(CLEAN / "lista_productos.csv")
    d = d[d["producto"].isin(lp.loc[lp.estado != "excluido", "producto"])]
    act = d[d.anio.between(2019, ANIO_FIN) & (d.produccion_t > 0)][["producto", "cod_dane"]].drop_duplicates()
    d = d.merge(act)
    series = {}
    for (p, c), s in d.groupby(["producto", "cod_dane"]):
        y = s.set_index("anio")["produccion_t"].reindex(range(int(s.anio.min()), ANIO_FIN + 1), fill_value=0.0)
        series[(p, c)] = y.astype(float)
    return series, lp


def cargar_oni(forzar=False):
    """Devuelve un dict {anio: oni} si la tabla de ONI existe; `forzar` intenta regenerarla desde fuentes crudas cuando falta."""
    path = CLEAN / "oni.csv"
    if not path.exists():
        if not forzar:
            return None
        try:
            import importlib
            mod = importlib.import_module("04_fuentes_externas")
            mod.main()
        except Exception:
            return None
        if not path.exists():
            return None

    d = pd.read_csv(path)
    if d.empty or "anio" not in d.columns or "oni" not in d.columns:
        return None
    return d.set_index("anio")["oni"].astype(float).to_dict()


def objetivos(O):
    return list(range(1, min(HORIZONTE_MAX, ANIO_FIN - O) + 1))
