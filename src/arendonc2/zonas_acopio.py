"""
TAREA #2 — Zonas de acopio por vecindad Queen + Ward con restricción espacial.

Agrupa los 42 municipios del Valle del Cauca en zonas de acopio espacialmente
conexas, donde cada zona tiene sentido como área de recolección de un acopio
satélite.

Método:
  1. Carga polígonos municipales (GADM nivel 2, filtrado a Valle), los empareja
     por nombre con los códigos DANE, y valida geometrías.
  2. Construye la matriz de vecindad por contigüidad Queen (libpysal).
  3. Diagnostica islas y componentes conexas; NO inventa aristas para arreglar
     datos (los problemas se reportan).
  4. Agrupa con Ward bajo restricción de conectividad (AgglomerativeClustering con
     connectivity = grafo de vecindad). Alternativa justificada a SKATER.
  5. Evalúa k = 3..8 y publica métricas comparativas.
  6. Elige un centro de referencia por zona con tiempos ponderados por oferta.

Entradas:
  - data/raw/geo/gadm41_COL_2.json.zip  (polígonos; se descarga aparte)
  - data/clean/municipios_coordenadas.csv
  - data/results/ML_Ce/oferta_escenarios_valor.csv  (oferta valorizada)
  - data/clean/matriz_tiempos.csv

Salidas:
  - data/results/zonas.csv                 (cod_dane, municipio, zona, es_centro_zona)
  - data/results/arendonc2/zonas_geometrias.geojson
  - data/results/arendonc2/vecindad_queen.csv    (lista de adyacencia)
  - data/results/arendonc2/zonas_metricas_k.csv  (comparación de k)
  - data/results/arendonc2/zonas_diagnostico.json

Uso: python -m src.arendonc2.zonas_acopio
     (o)  python src/arendonc2/zonas_acopio.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Permitir ejecución como script directo (python src/arendonc2/zonas_acopio.py)
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
    from arendonc2 import common
else:
    from . import common

GADM_ZIP = common.DATA_GEO / "gadm41_COL_2.json.zip"


# --------------------------------------------------------------------------
# 1. Carga y validación de geometrías
# --------------------------------------------------------------------------

def cargar_geometrias(cfg: dict):
    """Carga polígonos de Valle (GADM) emparejados con cod_dane. Devuelve GeoDataFrame."""
    import geopandas as gpd

    if not GADM_ZIP.exists():
        raise FileNotFoundError(
            f"No se encontró {GADM_ZIP}. Descárgalo con:\n"
            "  python src/arendonc2/descargar_geometrias.py"
        )

    gdf = gpd.read_file(f"zip://{GADM_ZIP}")
    valle = gdf[gdf["NAME_1"] == "ValledelCauca"].copy()
    valle["nkey"] = valle["NAME_2"].map(common.norm_nombre)

    mun = common.leer_municipios_coordenadas()
    mun["nkey"] = mun["municipio"].map(common.clave_gadm)

    geo = mun.merge(valle[["nkey", "geometry"]], on="nkey", how="left")
    geo = gpd.GeoDataFrame(geo, geometry="geometry", crs=valle.crs)
    return geo


def validar_geometrias(geo, mun_esperados: int = 42) -> dict:
    """Valida municipios faltantes, duplicados, geometrías inválidas. Devuelve diagnóstico."""
    diag = {}
    diag["n_municipios"] = int(len(geo))
    diag["esperados"] = mun_esperados
    diag["geometrias_nulas"] = int(geo.geometry.isna().sum())
    diag["cod_dane_duplicados"] = (
        geo["cod_dane"].value_counts()[lambda s: s > 1].index.tolist()
    )
    invalidas = (~geo.geometry.is_valid).sum() if diag["geometrias_nulas"] == 0 else None
    diag["geometrias_invalidas"] = int(invalidas) if invalidas is not None else None
    diag["municipios_sin_poligono"] = (
        geo.loc[geo.geometry.isna(), "cod_dane"].tolist()
    )
    return diag


# --------------------------------------------------------------------------
# 2. Vecindad Queen
# --------------------------------------------------------------------------

def construir_vecindad(geo):
    """Construye la matriz de contigüidad Queen. Devuelve (w, lista_adyacencia_df)."""
    from libpysal.weights import Queen

    w = Queen.from_dataframe(geo, use_index=False)
    filas = []
    cods = geo["cod_dane"].tolist()
    noms = geo["municipio"].tolist()
    for i, vecinos in w.neighbors.items():
        for j in vecinos:
            filas.append(
                {
                    "cod_dane": cods[i],
                    "municipio": noms[i],
                    "cod_dane_vecino": cods[j],
                    "municipio_vecino": noms[j],
                }
            )
    ady = pd.DataFrame(filas).sort_values(["cod_dane", "cod_dane_vecino"]).reset_index(drop=True)
    return w, ady


def diagnosticar_vecindad(w, geo) -> dict:
    """Reporta islas y componentes conexas SIN modificar el grafo."""
    cods = geo["cod_dane"].tolist()
    noms = geo["municipio"].tolist()
    islas = [{"cod_dane": cods[i], "municipio": noms[i]} for i in w.islands]
    return {
        "n_componentes_conexas": int(w.n_components),
        "islas": islas,
        "min_vecinos": int(min(len(v) for v in w.neighbors.values())),
        "max_vecinos": int(max(len(v) for v in w.neighbors.values())),
        "promedio_vecinos": round(float(np.mean([len(v) for v in w.neighbors.values()])), 2),
    }


# --------------------------------------------------------------------------
# 3. Variables de agrupamiento
# --------------------------------------------------------------------------

def construir_features(geo, cfg: dict) -> pd.DataFrame:
    """
    Construye la tabla de features por municipio:
      - oferta valorizada (COP) del año/escenario base, excluyendo productos excluidos
      - lat, lon

    Transformaciones documentadas en config: log1p sobre oferta, z-score en todas.
    Devuelve DataFrame con columnas crudas + columnas '*_z' escaladas.
    """
    anio = cfg["zonas"]["anio_base"]
    esc = cfg["zonas"]["escenario_oferta"]
    excluidos = set(cfg["general"]["productos_excluidos"])

    valor = common.leer_oferta_valor()
    col_valor = f"valor_{esc}_cop"
    sub = valor[(valor["anio"] == anio) & (~valor["producto"].isin(excluidos))]
    oferta_val = sub.groupby("cod_dane")[col_valor].sum().rename("oferta_valor_cop")

    feats = geo[["cod_dane", "municipio", "lat", "lon"]].copy()
    feats = feats.merge(oferta_val, on="cod_dane", how="left")
    feats["oferta_valor_cop"] = feats["oferta_valor_cop"].fillna(0.0)

    conf = cfg["zonas"]["features"]

    def aplicar(col_src, spec):
        x = feats[col_src].astype(float).to_numpy()
        if spec["transform"] == "log1p":
            x = np.log1p(x)
        if spec["escala"] == "zscore":
            mu, sd = x.mean(), x.std(ddof=0)
            x = (x - mu) / sd if sd > 0 else x - mu
        return x

    feats["oferta_valor_z"] = aplicar("oferta_valor_cop", conf["oferta_valor"])
    feats["lat_z"] = aplicar("lat", conf["lat"])
    feats["lon_z"] = aplicar("lon", conf["lon"])
    return feats


# --------------------------------------------------------------------------
# 4. Agrupamiento Ward con restricción de conectividad
# --------------------------------------------------------------------------

def _connectivity_matrix(w, n):
    """Matriz de adyacencia dispersa (scipy) a partir de los vecinos Queen."""
    from scipy.sparse import lil_matrix

    A = lil_matrix((n, n), dtype=int)
    for i, vecinos in w.neighbors.items():
        for j in vecinos:
            A[i, j] = 1
            A[j, i] = 1
    return A.tocsr()


def agrupar(feats: pd.DataFrame, w, k: int):
    """
    Ward con restricción de conectividad (AgglomerativeClustering).
    Devuelve array de etiquetas de zona (0..k-1) alineado a feats.
    """
    from sklearn.cluster import AgglomerativeClustering

    X = feats[["oferta_valor_z", "lat_z", "lon_z"]].to_numpy()
    A = _connectivity_matrix(w, len(feats))
    modelo = AgglomerativeClustering(
        n_clusters=k, linkage="ward", connectivity=A
    )
    etiquetas = modelo.fit_predict(X)
    return etiquetas


# --------------------------------------------------------------------------
# 5. Métricas y selección de k
# --------------------------------------------------------------------------

def _tiempos_dict(matriz: pd.DataFrame) -> dict:
    return {(r.origen, r.destino): r.minutos for r in matriz.itertuples()}


def es_conexa(cods_zona, w, geo) -> bool:
    """Verifica conectividad de una zona en el grafo Queen (BFS sobre el subgrafo)."""
    idx = {c: i for i, c in enumerate(geo["cod_dane"].tolist())}
    nodos = set(idx[c] for c in cods_zona)
    if not nodos:
        return True
    inicio = next(iter(nodos))
    vistos = {inicio}
    pila = [inicio]
    while pila:
        u = pila.pop()
        for v in w.neighbors[u]:
            if v in nodos and v not in vistos:
                vistos.add(v)
                pila.append(v)
    return vistos == nodos


def elegir_centro_zona(cods_zona, feats, tiempos) -> str:
    """
    Centro de referencia: el municipio que minimiza el tiempo total ponderado por
    oferta hacia los demás municipios de la zona. Son referencias, no la ubicación
    óptima del modelo de Samuel.
    """
    oferta = feats.set_index("cod_dane")["oferta_valor_cop"].to_dict()
    mejor, mejor_costo = None, np.inf
    for c in cods_zona:
        costo = 0.0
        for m in cods_zona:
            if m == c:
                continue
            t = tiempos.get((m, c), tiempos.get((c, m)))
            if t is None:
                t = 0.0
            costo += oferta.get(m, 0.0) * t
        if costo < mejor_costo:
            mejor, mejor_costo = c, costo
    return mejor if mejor is not None else cods_zona[0]


def metricas_para_k(etiquetas, feats, w, geo, tiempos) -> dict:
    """Calcula métricas de calidad para un particionamiento dado."""
    df = feats.copy()
    df["zona"] = etiquetas
    X = df[["oferta_valor_z", "lat_z", "lon_z"]].to_numpy()

    # Homogeneidad: inercia intra-zona (menor es mejor), normalizada por n.
    inercia = 0.0
    tam = []
    oferta_zona = []
    tiempo_prom_centro = []
    todas_conexas = True

    for z, g in df.groupby("zona"):
        cods = g["cod_dane"].tolist()
        tam.append(len(cods))
        oferta_zona.append(float(g["oferta_valor_cop"].sum()))
        centro = g.iloc[g.index.get_indexer(g.index)]  # placeholder
        Xi = g[["oferta_valor_z", "lat_z", "lon_z"]].to_numpy()
        centro_feat = Xi.mean(axis=0)
        inercia += float(((Xi - centro_feat) ** 2).sum())
        if not es_conexa(cods, w, geo):
            todas_conexas = False
        # tiempo promedio de municipio a su centro de zona
        centro_cod = elegir_centro_zona(cods, feats, tiempos)
        ts = []
        for m in cods:
            if m == centro_cod:
                continue
            t = tiempos.get((m, centro_cod), tiempos.get((centro_cod, m)))
            if t is not None:
                ts.append(t)
        tiempo_prom_centro.append(float(np.mean(ts)) if ts else 0.0)

    try:
        from sklearn.metrics import silhouette_score

        sil = float(silhouette_score(X, etiquetas)) if len(set(etiquetas)) > 1 else np.nan
    except Exception:
        sil = np.nan

    return {
        "k": int(len(set(etiquetas))),
        "todas_conexas": bool(todas_conexas),
        "pct_zonas_conexas": 100.0 if todas_conexas else round(
            100.0 * sum(es_conexa(df[df.zona == z]["cod_dane"].tolist(), w, geo)
                        for z in df.zona.unique()) / len(df.zona.unique()), 1),
        "inercia_intra": round(inercia, 3),
        "silhouette": round(sil, 4) if not np.isnan(sil) else None,
        "tam_min": int(min(tam)),
        "tam_max": int(max(tam)),
        "oferta_min_cop": round(min(oferta_zona), 1),
        "oferta_max_cop": round(max(oferta_zona), 1),
        "oferta_cv": round(float(np.std(oferta_zona) / np.mean(oferta_zona)), 3) if np.mean(oferta_zona) else None,
        "tiempo_prom_centro_min": round(float(np.mean(tiempo_prom_centro)), 1),
        "tiempo_max_centro_min": round(float(np.max(tiempo_prom_centro)), 1),
    }


# --------------------------------------------------------------------------
# 6. Orquestación
# --------------------------------------------------------------------------

def ejecutar(cfg: dict | None = None, guardar: bool = True) -> dict:
    """Pipeline completo de la tarea #2. Devuelve dict con resultados principales."""
    import geopandas as gpd

    if cfg is None:
        cfg = common.cargar_config()
    common.asegurar_directorios()

    geo = cargar_geometrias(cfg)
    diag_geo = validar_geometrias(geo)
    if diag_geo["geometrias_nulas"] > 0:
        raise RuntimeError(
            f"Municipios sin polígono: {diag_geo['municipios_sin_poligono']}. "
            "No se inventan geometrías; corregir el emparejamiento de nombres."
        )

    w, ady = construir_vecindad(geo)
    diag_vec = diagnosticar_vecindad(w, geo)

    feats = construir_features(geo, cfg)
    matriz = common.leer_matriz_tiempos()
    tiempos = _tiempos_dict(matriz)

    # Evaluar k = k_min..k_max
    k_min, k_max = cfg["zonas"]["k_min"], cfg["zonas"]["k_max"]
    etiquetas_por_k = {}
    metricas = []
    for k in range(k_min, k_max + 1):
        et = agrupar(feats, w, k)
        etiquetas_por_k[k] = et
        metricas.append(metricas_para_k(et, feats, w, geo, tiempos))
    met_df = pd.DataFrame(metricas)

    # Selección final
    k_sel = cfg["zonas"]["k_seleccionado"]
    etiquetas = etiquetas_por_k[k_sel]

    zonas = feats[["cod_dane", "municipio"]].copy()
    zonas["zona"] = [f"Z{z + 1}" for z in etiquetas]

    # Centro por zona
    centros = {}
    for z, g in zonas.groupby("zona"):
        centros[z] = elegir_centro_zona(g["cod_dane"].tolist(), feats, tiempos)
    zonas["es_centro_zona"] = zonas.apply(
        lambda r: int(centros[r["zona"]] == r["cod_dane"]), axis=1
    )
    zonas = zonas.sort_values(["zona", "cod_dane"]).reset_index(drop=True)

    # Geometrías de zona (disolución de polígonos municipales)
    geo_z = geo.merge(zonas[["cod_dane", "zona", "es_centro_zona"]], on="cod_dane")
    zonas_geo = geo_z.dissolve(by="zona", as_index=False)[["zona", "geometry"]]

    resultado = {
        "diagnostico_geometrias": diag_geo,
        "diagnostico_vecindad": diag_vec,
        "metricas_k": met_df,
        "zonas": zonas,
        "k_seleccionado": k_sel,
        "centros": centros,
    }

    if guardar:
        zonas.to_csv(common.DATA_RES / "zonas.csv", index=False, encoding="utf-8-sig")
        ady.to_csv(common.DATA_RES_OUT / "vecindad_queen.csv", index=False, encoding="utf-8-sig")
        met_df.to_csv(common.DATA_RES_OUT / "zonas_metricas_k.csv", index=False, encoding="utf-8-sig")
        feats.to_csv(common.DATA_RES_OUT / "zonas_features.csv", index=False, encoding="utf-8-sig")
        zonas_geo.to_file(common.DATA_RES_OUT / "zonas_geometrias.geojson", driver="GeoJSON")
        geo_z[["cod_dane", "municipio", "zona", "geometry"]].to_file(
            common.DATA_RES_OUT / "municipios_zonas_geometrias.geojson", driver="GeoJSON"
        )
        with open(common.DATA_RES_OUT / "zonas_diagnostico.json", "w", encoding="utf-8") as fh:
            json.dump(
                {
                    "diagnostico_geometrias": diag_geo,
                    "diagnostico_vecindad": diag_vec,
                    "k_seleccionado": k_sel,
                    "centros": centros,
                    "metricas_k": met_df.to_dict(orient="records"),
                },
                fh, ensure_ascii=False, indent=2,
            )

    return resultado


def main():
    cfg = common.cargar_config()
    res = ejecutar(cfg, guardar=True)
    print("=" * 70)
    print("TAREA #2 — ZONAS DE ACOPIO")
    print("=" * 70)
    print("Diagnóstico geometrías:", json.dumps(res["diagnostico_geometrias"], ensure_ascii=False))
    print("Diagnóstico vecindad  :", json.dumps(res["diagnostico_vecindad"], ensure_ascii=False))
    print()
    print("Métricas por k:")
    print(res["metricas_k"].to_string(index=False))
    print()
    print(f"k seleccionado: {res['k_seleccionado']}")
    print("Centros de zona (referencia, NO ubicación óptima del modelo de Samuel):")
    zn = res["zonas"]
    for z, cod in res["centros"].items():
        nom = zn[zn.cod_dane == cod]["municipio"].iloc[0]
        n = (zn.zona == z).sum()
        print(f"  {z}: centro={nom} ({cod}) | {n} municipios")
    print()
    print("Archivos escritos:")
    print(f"  {common.DATA_RES / 'zonas.csv'}")
    print(f"  {common.DATA_RES_OUT / 'zonas_geometrias.geojson'}")
    print(f"  {common.DATA_RES_OUT / 'vecindad_queen.csv'}")
    print(f"  {common.DATA_RES_OUT / 'zonas_metricas_k.csv'}")
    print(f"  {common.DATA_RES_OUT / 'zonas_diagnostico.json'}")


if __name__ == "__main__":
    main()
