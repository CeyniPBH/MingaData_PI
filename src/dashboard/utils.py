"""
Utilidades para cargar los datos del tablero Streamlit.
Todos los paths son relativos a la raiz del repo.

Las lecturas prefieren Parquet (artefacto derivado en data/clean o data/results)
y caen a CSV cuando el Parquet no existe. Asi el tablero funciona igual en un
clon recien descargado y aprovecha Parquet cuando se ejecuto
`python src/pipeline/exportar_parquet.py`.
"""

from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
DATA_CLEAN = ROOT / "data" / "clean"
DATA_RES = ROOT / "data" / "results" / "ML_Ce"
DATA_RES_ROOT = ROOT / "data" / "results"


def _leer(nombre_parquet, base, nombre_csv=None, particionado=False, dtype=None, **kwargs):
    """Lee Parquet si existe; si no, CSV. Devuelve un DataFrame vacio si no hay fuente."""
    nombre_csv = nombre_csv or nombre_parquet
    if particionado:
        carpeta = base / nombre_parquet
        if carpeta.exists():
            df = pd.read_parquet(carpeta)
            if "anio" in df.columns:
                df["anio"] = pd.to_numeric(df["anio"]).astype(int)
            if dtype:
                for col, tipo in dtype.items():
                    if col in df.columns:
                        df[col] = df[col].astype(tipo)
            return df
    parquet = base / f"{nombre_parquet}.parquet"
    if parquet.exists():
        df = pd.read_parquet(parquet)
        if dtype:
            for col, tipo in dtype.items():
                if col in df.columns:
                    df[col] = df[col].astype(tipo)
        return df
    csv = base / f"{nombre_csv}.csv"
    if csv.exists():
        return pd.read_csv(csv, encoding="utf-8-sig", dtype=dtype, **kwargs)
    return pd.DataFrame()


@st.cache_data
def cargar_oferta_escenarios():
    """Carga oferta_escenarios: producto, cod_dane, año, oferta_bajo/base/alto."""
    df = _leer("oferta_escenarios", DATA_RES, dtype={"cod_dane": str})
    if not df.empty and "cod_dane" in df.columns:
        df["cod_dane"] = df["cod_dane"].astype(str).str.zfill(5)
    return df


@st.cache_data
def cargar_oferta_departamento():
    """Carga oferta_departamento: producto, año, oferta_bajo/base/alto (suma de municipios)."""
    return _leer("oferta_departamento", DATA_RES)


@st.cache_data
def cargar_coherencia():
    """Carga coherencia_jerarquica."""
    return _leer("coherencia_jerarquica", DATA_RES)


@st.cache_data
def cargar_municipios_coordenadas():
    """Carga municipios_coordenadas: cod_dane, municipio, lat, lon."""
    return _leer("municipios_coordenadas", DATA_CLEAN, dtype={"cod_dane": str})


@st.cache_data
def cargar_destinos_coordenadas():
    """Carga destinos_coordenadas: id_destino, nombre, lat, lon."""
    return _leer("destinos_coordenadas", DATA_CLEAN, dtype={"id_destino": str})


@st.cache_data
def cargar_matriz_tiempos():
    """Carga matriz_tiempos: origen, destino, minutos, distancia_km, metodo."""
    return _leer("matriz_tiempos", DATA_CLEAN, dtype={"origen": str, "destino": str})


@st.cache_data
def cargar_produccion_limpia():
    """Carga produccion_valle_clean para la serie historica (Parquet particionado si existe)."""
    return _leer("produccion", DATA_CLEAN, "produccion_valle_clean",
                 particionado=True, dtype={"cod_dane": str})


@st.cache_data
def cargar_lista_productos():
    """Carga lista_productos: producto, familia, estado, ranking_toneladas."""
    return _leer("lista_productos", DATA_CLEAN)


@st.cache_data
def cargar_zonas():
    """Carga data/results/zonas.csv (tarea #2): cod_dane, municipio, zona, es_centro_zona."""
    return _leer("zonas", DATA_RES_ROOT, dtype={"cod_dane": str})


@st.cache_data
def cargar_zonas_geometrias():
    """Carga el GeoJSON de poligonos de zona (si geopandas esta disponible)."""
    path = DATA_RES_ROOT / "arendonc2" / "zonas_geometrias.geojson"
    if not path.exists():
        return None
    try:
        import geopandas as gpd

        return gpd.read_file(path)
    except Exception:
        return None


@st.cache_data
def cargar_escenarios_opt():
    """Carga data/results/escenarios.csv (tarea #4)."""
    return _leer("escenarios", DATA_RES_ROOT)


@st.cache_data
def cargar_excedentes():
    """Carga data/results/excedentes.csv (tarea #3)."""
    return _leer("excedentes", DATA_RES_ROOT, particionado=True, dtype={"cod_dane": str})


@st.cache_data
def cargar_metricas_comparacion():
    """Carga metricas_comparacion (MASE/WAPE por producto y modelo)."""
    return _leer("metricas_comparacion", DATA_RES)


@st.cache_data
def cargar_resumen_opt():
    """Carga el resumen libre vs zonas de OR-Tools, si ya se genero."""
    return _leer("comparacion_libre_vs_zonas_resumen", DATA_RES_ROOT / "opt")


@st.cache_data
def cargar_metrica_negocio():
    """Carga el resumen de impacto logistico (10_metrica_negocio.py), si existe."""
    return _leer("metrica_negocio_resumen", DATA_RES)


def obtener_productos_disponibles(df_oferta):
    """Devuelve lista ordenada de productos unicos."""
    if df_oferta.empty:
        return []
    return sorted(df_oferta["producto"].unique())


def obtener_municipios_por_producto(df_oferta, producto, ano=2024):
    """Devuelve municipios que tienen oferta para un producto y año dados."""
    if df_oferta.empty:
        return pd.DataFrame()
    sub = df_oferta[(df_oferta["producto"] == producto) & (df_oferta["año"] == ano)]
    return sub


def obtener_serie_historica(df_produccion, producto, cod_dane):
    """Devuelve serie historica de produccion (anio, produccion_t) para un producto-municipio."""
    if df_produccion.empty:
        return pd.DataFrame()
    sub = df_produccion[
        (df_produccion["producto"] == producto) & (df_produccion["cod_dane"] == cod_dane)
    ][["anio", "produccion_t"]].sort_values("anio")
    return sub


def obtener_pronostico_municipio(df_oferta, producto, cod_dane):
    """Devuelve pronostico 2024-2028 para un producto-municipio."""
    if df_oferta.empty:
        return pd.DataFrame()
    sub = df_oferta[
        (df_oferta["producto"] == producto) & (df_oferta["cod_dane"] == cod_dane)
    ][["año", "oferta_bajo", "oferta_base", "oferta_alto"]].sort_values("año")
    return sub
