"""
Tablero interactivo con mapas - MingaData_PI
Autor: Samuel Gutierrez Jaramillo
Fecha: 17-21 nov 2026

Pantallas:
1. Oferta: selector producto/municipio, serie historica y pronostico bajo/base/alto
2. Zonas: mapa con municipios y oferta por producto/anio
2b. Zonas de acopio: poligonos de zona, centros y volumenes por escenario
3. Ubicacion: selector de escenario, mapa central+satelites, frontera de Pareto, tabla de estabilidad
4. Tablero central: tablero visual de la central de acopio (mapa de puntos y respuestas)

Ejecutar: streamlit run src/dashboard/app.py
"""

import sys
import os
from pathlib import Path

# Agregar src/ al path para importar modulos de optimizacion
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

# st.set_page_config debe ser el PRIMER comando de Streamlit
st.set_page_config(
    page_title="MingaData - Central de Acopio Valle del Cauca",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

import pandas as pd
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium

# --- Leer secrets de Streamlit Cloud y establecer como variables de entorno ---
# utils.py y API_URL leen os.getenv; en Streamlit Cloud los valores vienen de st.secrets
try:
    for _key in [
        "MINGA_API_URL",
        "MINGA_DATA_BUCKET",
        "MINGA_DATA_REGION",
        "MINGA_DATA_PREFIX",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "MINGA_MODELO_S3_URL",
    ]:
        if _key in st.secrets:
            os.environ[_key] = str(st.secrets[_key])
except Exception:
    pass  # No estamos en Streamlit Cloud o no hay secrets configurados

from utils import (
    cargar_oferta_escenarios,
    cargar_oferta_departamento,
    cargar_coherencia,
    cargar_municipios_coordenadas,
    cargar_destinos_coordenadas,
    cargar_matriz_tiempos,
    cargar_produccion_limpia,
    cargar_lista_productos,
    cargar_zonas,
    cargar_zonas_geometrias,
    cargar_escenarios_opt,
    cargar_excedentes,
    cargar_metricas_comparacion,
    cargar_resumen_opt,
    cargar_metrica_negocio,
    obtener_productos_disponibles,
    obtener_municipios_por_producto,
    obtener_serie_historica,
    obtener_pronostico_municipio,
)

from tablero_central import generar_html_tablero
import cobertura as cob
from utils import (
    cargar_estabilidad_opt,
    fmt_pct,
    fmt_puntos,
    fmt_entero,
    fmt_toneladas,
    fmt_millones_cop,
    fmt_razon,
)

# Paleta del manual (sección 9)
AZUL = "#002855"       # protagonista: la sede seleccionada
GRIS_CTX = "#B8BEC8"   # contexto
GRIS_CLARO = "#D0D5DD"
REFERENCIA = "#18212D"  # referente del sur / líneas punteadas

from optimizacion.modelo_real import (
    cargar_datos_reales,
    construir_matriz_tiempos_dict,
    resolver_ubicacion,
    calcular_frontera_pareto,
    calcular_estabilidad,
    comparar_configuraciones,
)

# Agregar src/ al path para importar el adaptador de escenarios de optimización
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "arendonc2"))
from adaptador import preparar_para_solver, listar_escenarios

# Agregar src/ al path para importar módulos de despliegue y API
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    import requests
    _REQUESTS_DISPONIBLE = True
except Exception:
    _REQUESTS_DISPONIBLE = False

# URL de la API (variable de entorno o localhost por defecto)
API_URL = os.getenv("MINGA_API_URL", "http://localhost:8000").rstrip("/")

# =============================================================================
# CARGA DE DATOS
# =============================================================================
@st.cache_data
def cargar_todos_los_datos():
    oferta = cargar_oferta_escenarios()
    oferta_dep = cargar_oferta_departamento()
    coherencia = cargar_coherencia()
    municipios = cargar_municipios_coordenadas()
    destinos = cargar_destinos_coordenadas()
    matriz_tiempos = cargar_matriz_tiempos()
    produccion = cargar_produccion_limpia()
    lista_productos = cargar_lista_productos()
    return oferta, oferta_dep, coherencia, municipios, destinos, matriz_tiempos, produccion, lista_productos


oferta, oferta_dep, coherencia, municipios, destinos, matriz_tiempos, produccion, lista_productos = cargar_todos_los_datos()


# =============================================================================
# CACHÉ DE OPTIMIZACIÓN (pantalla 3)
# Se cachean SÓLO resultados serializables (dicts/DataFrames), nunca objetos del
# solver. Las claves incluyen escenario, año, modo, k, lambda, pesos de destinos,
# parámetros del solver y una huella de los datos de entrada, para invalidar la
# caché si cambian los datos o la configuración.
# =============================================================================
def _huella_datos():
    """Huella de los archivos de datos que alimentan la optimización (mtime+tamaño).
    Si cualquiera cambia, la clave de caché cambia y se recalcula."""
    import hashlib
    base = Path(__file__).resolve().parents[2]
    archivos = [
        base / "data" / "results" / "escenarios.csv",
        base / "data" / "results" / "excedentes.csv",
        base / "data" / "results" / "zonas.csv",
        base / "data" / "clean" / "matriz_tiempos.csv",
        base / "data" / "clean" / "municipios_coordenadas.csv",
        base / "data" / "clean" / "destinos_coordenadas.csv",
    ]
    h = hashlib.sha256()
    for a in archivos:
        try:
            st_ = a.stat()
            h.update("{}:{}:{}".format(a.name, int(st_.st_mtime), st_.st_size).encode())
        except FileNotFoundError:
            h.update("{}:missing".format(a.name).encode())
    return h.hexdigest()[:16]


@st.cache_data(show_spinner=False)
def opt_resolver_cache(id_escenario, anio, modo, k, lam,
                       pesos_nac, pesos_exp, tiempo_limite_s, gap_relativo, huella):
    """Resuelve una configuración y devuelve el dict (serializable) del resultado.
    `huella` entra en la clave para invalidar si cambian los datos."""
    municipios_, destinos_, matriz_ = cargar_datos_reales()
    tiempos_ = construir_matriz_tiempos_dict(matriz_, municipios_, destinos_)
    pkg = preparar_para_solver(id_escenario, anio)
    return resolver_ubicacion(
        pkg, municipios_, destinos_, tiempos_, k=k, lam=lam, modo=modo,
        pesos_internos_nac=pesos_nac, pesos_internos_exp=pesos_exp,
        tiempo_limite_s=tiempo_limite_s, gap_relativo=gap_relativo,
    )


@st.cache_data(show_spinner=False)
def opt_pareto_cache(id_escenario, anio, modo, k, tiempo_limite_s, gap_relativo, huella):
    """Barrido de lambda (bajo demanda). Devuelve un DataFrame (serializable)."""
    municipios_, destinos_, matriz_ = cargar_datos_reales()
    tiempos_ = construir_matriz_tiempos_dict(matriz_, municipios_, destinos_)
    pkg = preparar_para_solver(id_escenario, anio)
    return calcular_frontera_pareto(
        pkg, municipios_, destinos_, tiempos_, k=k,
        lambdas=[i / 10 for i in range(11)], modo=modo,
    )


@st.cache_data(show_spinner=False)
def opt_comparacion_cache(id_escenario, anio, k, lam, tiempo_limite_s, gap_relativo, huella):
    """Comparación libre vs zonas (bajo demanda). Devuelve dict de dicts serializables."""
    municipios_, destinos_, matriz_ = cargar_datos_reales()
    tiempos_ = construir_matriz_tiempos_dict(matriz_, municipios_, destinos_)
    pkg = preparar_para_solver(id_escenario, anio)
    return comparar_configuraciones(pkg, municipios_, destinos_, tiempos_, k=k, lam=lam)


@st.cache_data(show_spinner=False)
def opt_estabilidad_cache(anio, consumo, mezcla, modo, k, lam, tiempo_limite_s, gap_relativo, huella):
    """Estabilidad por nivel de oferta (bajo demanda). Devuelve DataFrame serializable
    más la lista de faltantes (en columnas), evitando usar .attrs no serializable."""
    municipios_, destinos_, matriz_ = cargar_datos_reales()
    tiempos_ = construir_matriz_tiempos_dict(matriz_, municipios_, destinos_)
    df = calcular_estabilidad(municipios_, destinos_, tiempos_, anio=anio,
                              consumo=consumo, mezcla=mezcla, modo=modo, k=k, lam=lam)
    faltantes = df.attrs.get("faltantes", [])
    return df.reset_index(drop=True), faltantes

# =============================================================================
# MODELO DE COBERTURA (compartido por el resumen y su selector de sede)
# =============================================================================
@st.cache_data(show_spinner=False)
def _modelo_cobertura():
    """Construye la lista de municipios del tablero una vez (reusa el payload del tablero)."""
    prod = cargar_produccion_limpia()
    return cob.cargar_municipios_tablero(prod)


def _resumen_opciones_sede():
    """Devuelve (lista de nombres de sede ordenada por cobertura, sede por defecto)."""
    muns = _modelo_cobertura()
    modelo = cob.ModeloCobertura(muns)
    rk = modelo.ranking_area()
    return list(rk["sede"]), rk.iloc[0]["sede"]


def _resumen_sede_sidebar():
    """Selector de sede del resumen, en la barra lateral, con el mismo key y default.
    Se renderiza inmediatamente debajo del selector de pantalla."""
    try:
        nombres, sede_default = _resumen_opciones_sede()
    except Exception:
        return
    st.sidebar.selectbox(
        "Sede del resumen (42 municipios):", nombres,
        index=nombres.index(sede_default), key="resumen_sede",
    )
    st.sidebar.caption("Selecciona una sede para actualizar los indicadores y gráficos")


# =============================================================================
# SIDEBAR - NAVEGACION
# =============================================================================
st.sidebar.title("🌱 MingaData")
st.sidebar.markdown("**Central de Acopio y Procesamiento**")
st.sidebar.markdown("Valle del Cauca - Proyecto Integrador 1")

# 1. Selector de pantalla (siempre primero)
pantalla = st.sidebar.radio(
    "Seleccionar pantalla:",
    ["0. Resumen", "1. Oferta", "2. Zonas", "2b. Zonas de acopio", "3. Ubicacion", "4. Tablero central"],
    index=0,
)

anos_disponibles = sorted(oferta["año"].unique()) if not oferta.empty else [2024]

# 2. Segmentadores y controles de la pantalla activa (antes de los bloques informativos)
if pantalla == "0. Resumen":
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Filtros de esta vista")
    _resumen_sede_sidebar()
    ano_seleccionado = anos_disponibles[0]
    escenario = "base"
elif pantalla == "4. Tablero central":
    ano_seleccionado = anos_disponibles[0]
    escenario = "base"
else:
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Filtros de esta vista")
    ano_seleccionado = st.sidebar.selectbox("Anio de pronostico:", anos_disponibles, index=0)
    escenario = st.sidebar.selectbox("Escenario de oferta:", ["base", "bajo", "alto"], index=0)

# 3. Información complementaria (estado de los datos, notas de la vista)
st.sidebar.markdown("---")
if pantalla in ("0. Resumen", "4. Tablero central"):
    st.sidebar.caption("Vista resumen o histórica 2021-2023. No usa los filtros de pronóstico.")
st.sidebar.markdown("### Estado de los datos")
st.sidebar.info(f"""
- Productos: {oferta['producto'].nunique() if not oferta.empty else 0}
- Municipios: {municipios['cod_dane'].nunique() if not municipios.empty else 0}
- Anos pronostico: {min(oferta['año'].unique()) if not oferta.empty else '-'} a {max(oferta['año'].unique()) if not oferta.empty else '-'}
""")

# =============================================================================
# FUNCIONES AUXILIARES PARA MAPAS
# =============================================================================
def crear_mapa_base(centro=None, zoom=8):
    if centro is None:
        centro = [4.2, -76.2]
    m = folium.Map(location=centro, zoom_start=zoom, tiles="OpenStreetMap")
    return m


def agregar_municipios_al_mapa(m, municipios_df, valores_df=None, columna_valor="oferta_base"):
    if municipios_df.empty:
        return m
    if valores_df is not None and not valores_df.empty:
        merge = municipios_df.merge(valores_df, on="cod_dane", how="left")
    else:
        merge = municipios_df.copy()
        merge[columna_valor] = 0

    vmin = merge[columna_valor].min()
    vmax = merge[columna_valor].max()
    if vmax == vmin:
        vmax = vmin + 1

    for _, row in merge.iterrows():
        lat, lon = row["lat"], row["lon"]
        nombre = row["municipio"]
        val = row[columna_valor] if pd.notna(row[columna_valor]) else 0
        if vmax > vmin:
            intensity = (val - vmin) / (vmax - vmin)
        else:
            intensity = 0.5
        r = int(255 * intensity)
        g = int(255 * (1 - intensity))
        b = 0
        color = "#{:02x}{:02x}{:02x}".format(r, g, b)
        popup_html = "<b>{}</b><br>Codigo DANE: {}<br>{}: {:,.0f} t".format(
            nombre, row['cod_dane'], columna_valor, val
        )
        folium.CircleMarker(
            location=[lat, lon],
            radius=6 + 8 * intensity,
            popup=folium.Popup(popup_html, max_width=200),
            color="black",
            weight=1,
            fill=True,
            fillColor=color,
            fillOpacity=0.7,
        ).add_to(m)
    return m


def agregar_destinos_al_mapa(m, destinos_df):
    if destinos_df.empty:
        return m
    for _, row in destinos_df.iterrows():
        folium.Marker(
            location=[row["lat"], row["lon"]],
            popup=folium.Popup("<b>{}</b><br>({})".format(row['nombre'], row['id_destino']), max_width=200),
            icon=folium.Icon(color="blue", icon="info-sign"),
        ).add_to(m)
    return m


# =============================================================================
# PANTALLA 0: RESUMEN (landing)
# =============================================================================
def pantalla_resumen():
    _pantalla_resumen_impl()


# =============================================================================
# PANTALLA 0: RESUMEN EJECUTIVO (rediseño conforme al manual)
# =============================================================================
def _barras_figura(fig, alto=320):
    fig.update_layout(
        template="plotly_white", height=alto,
        margin=dict(l=8, r=8, t=28, b=8),
        font=dict(size=12), showlegend=False,
    )
    return fig


def _visual_p1(modelo, sede_cod, sur_cod):
    """P1. ¿Qué sedes cubren más área a 40 km? Barras horizontales top 10 + sede + sur."""
    rk = modelo.ranking_area()
    top = rk.head(10).copy()
    extra = rk[rk["cod_dane"].isin([sede_cod, sur_cod]) & ~rk["cod_dane"].isin(top["cod_dane"])]
    vis = pd.concat([top, extra]).drop_duplicates("cod_dane")
    vis = vis.sort_values("pct_area")  # barras horizontales: mayor arriba
    colores, etiquetas = [], []
    for _, r in vis.iterrows():
        if r["cod_dane"] == sede_cod:
            colores.append(AZUL)
        elif r["cod_dane"] == sur_cod:
            colores.append(REFERENCIA)
        else:
            colores.append(GRIS_CTX)
        marca = ""
        if r["cod_dane"] == sede_cod:
            marca = " ◆ sede"
        elif r["cod_dane"] == sur_cod:
            marca = " ▲ ref. sur"
        etiquetas.append("{} (#{}){}".format(r["sede"], r["puesto"], marca))
    fig = go.Figure(go.Bar(
        x=vis["pct_area"] * 100, y=etiquetas, orientation="h",
        marker_color=colores,
        text=[fmt_pct(v) for v in vis["pct_area"]], textposition="outside",
        hovertemplate="%{y}<br>%{x:.1f} % del área<extra></extra>",
    ))
    fig.add_vline(x=50, line_dash="dot", line_color=REFERENCIA,
                  annotation_text="umbral de hipótesis 50 %", annotation_position="top")
    fig.update_xaxes(title="% del área de fruta y plátano a 40 km",
                     range=[0, max(60, vis["pct_area"].max() * 100 + 8)])
    return _barras_figura(fig, alto=360)


def _visual_p2(modelo, sede_cod):
    """P2. Volumen captable entre escenarios históricos (bajo/base/alto)."""
    ve = cob.volumenes_escenarios(modelo, sede_cod)
    colores = [GRIS_CTX, AZUL, GRIS_CTX]
    fig = go.Figure(go.Bar(
        x=ve["escenario"], y=ve["volumen_t"], marker_color=colores,
        text=["{}<br>{}".format(fmt_toneladas(v), fmt_pct(p)) for v, p in zip(ve["volumen_t"], ve["pct_vs_base"])],
        textposition="outside",
        hovertemplate="%{x}<br>%{y:,.0f} t/año<extra></extra>",
    ))
    base_val = ve.loc[ve["escenario"].str.startswith("Base"), "volumen_t"].iloc[0]
    fig.add_hline(y=base_val, line_dash="dot", line_color=REFERENCIA,
                  annotation_text="volumen base (100 %)", annotation_position="top left")
    fig.update_yaxes(title="t/año captables al 20 %")
    return _barras_figura(fig, alto=360)


def _visual_p3(produccion, modelo, sede_cod, sur_cod):
    """P3. Composición productiva de la sede frente al referente del sur (100 % apiladas)."""
    comp_sede = cob.composicion_sede(produccion, modelo, sede_cod)
    comp_sur = cob.composicion_sede(produccion, modelo, sur_cod)
    serie_sede = cob.agrupar_composicion(comp_sede["toneladas_por_cultivo"])
    serie_sur = cob.agrupar_composicion(comp_sur["toneladas_por_cultivo"])
    cultivos = list(dict.fromkeys(list(serie_sede.index) + list(serie_sur.index)))
    base_colores = [AZUL, "#2E5E8C", "#5B86AD", "#8FB0C9", GRIS_CTX, GRIS_CLARO, "#E4E7EC"]
    mapa_color, i = {}, 0
    for c in cultivos:
        if c == "Piña":
            mapa_color[c] = "#C44601"  # destaca piña con contraste y etiqueta propia
        else:
            mapa_color[c] = base_colores[i % len(base_colores)]
            i += 1
    etiquetas = [modelo.nombre(sede_cod), "{} (ref. sur)".format(modelo.nombre(sur_cod))]
    fig = go.Figure()
    for c in cultivos:
        tot_sede = serie_sede.sum() or 1
        tot_sur = serie_sur.sum() or 1
        vals = [100 * serie_sede.get(c, 0) / tot_sede, 100 * serie_sur.get(c, 0) / tot_sur]
        fig.add_trace(go.Bar(
            x=vals, y=etiquetas, orientation="h", name=c, marker_color=mapa_color[c],
            text=[c if v >= 8 else "" for v in vals], textposition="inside",
            hovertemplate="%{y}<br>" + c + ": %{x:.1f} %<extra></extra>",
        ))
    fig.update_layout(barmode="stack", template="plotly_white", height=300,
                      margin=dict(l=8, r=8, t=28, b=8), font=dict(size=12),
                      legend=dict(orientation="h", y=-0.2, font=dict(size=10)))
    fig.update_xaxes(title="% de toneladas por cultivo (promedio 2021-2023)", range=[0, 100])
    return fig, comp_sede, comp_sur


def _visual_p4(frec, sede_nombre):
    """P4. Frecuencia de sedes al variar escenarios de optimización."""
    freq = frec["frecuencias"]
    if freq.empty:
        return None
    df = freq.sort_values(ascending=True).reset_index()
    df.columns = ["central", "frecuencia"]
    colores = [AZUL if c == sede_nombre else GRIS_CTX for c in df["central"]]
    fig = go.Figure(go.Bar(
        x=df["frecuencia"], y=df["central"], orientation="h", marker_color=colores,
        text=df["frecuencia"], textposition="outside",
        hovertemplate="%{y}: %{x} de " + str(frec["n_resueltos"]) + " escenarios<extra></extra>",
    ))
    fig.update_xaxes(title="escenarios en que es central (de {} resueltos)".format(frec["n_resueltos"]))
    return _barras_figura(fig, alto=320)


def _pantalla_resumen_impl():
    produccion = cargar_produccion_limpia()
    if produccion.empty:
        st.error("No se pudo cargar produccion_valle_clean. Verifica data/clean/.")
        return
    try:
        muns = _modelo_cobertura()
    except Exception as e:
        st.error("No se pudo construir el modelo de cobertura: {}".format(e))
        return
    modelo = cob.ModeloCobertura(muns)

    # --- Filtro: sede entre los 42 municipios, por defecto la de mayor cobertura ---
    # El selector vive en la barra lateral (justo debajo del selector de pantalla); aquí
    # se lee su valor por su key, sin recrear el widget.
    rk = modelo.ranking_area()
    nombres = list(rk["sede"])
    cod_por_nombre = dict(zip(rk["sede"], rk["cod_dane"]))
    sede_default = rk.iloc[0]["sede"]  # mayor cobertura de área, calculada
    sede_sel = st.session_state.get("resumen_sede", sede_default)
    if sede_sel not in cod_por_nombre:
        sede_sel = sede_default
    sede_cod = cod_por_nombre[sede_sel]
    sur_cod = modelo.mejor_sede(("Sur",))
    sur_nombre = modelo.nombre(sur_cod)
    es_referente_sur = (sede_cod == sur_cod)

    pct_sede = modelo.pct_area(sede_cod)
    pct_sur = modelo.pct_area(sur_cod)
    vol_sede = modelo.volumen_captable(sede_cod)
    vol_sur = modelo.volumen_captable(sur_cod)
    puesto_sede = modelo.puesto(sede_cod)

    # --- Encabezado ---
    st.title(cob.titulo_resumen(modelo, sede_cod))
    st.markdown(
        "**¿Qué municipios conviene priorizar para estudiar una central de fruta y "
        "plátano, según el área cubierta a 40 km y el volumen captable estimado en "
        "2021-2023, frente a la mejor sede del sur?**"
    )
    st.caption("Base 2021-2023 · Radio 40 km · Captación supuesta 20 %")
    st.caption(
        "La distancia es geográfica en línea recta entre centroides (haversine), **no** "
        "distancia vial. En el resumen el radio y la captación están fijos; pueden "
        "explorarse en la pantalla 4. Tablero central."
    )
    st.caption(
        "Datos: consolidado agrícola de cultivos permanentes del Valle del Cauca "
        "(Gobernación del Valle), familia Frutales (incluye plátano). Fecha de los datos: "
        "cosechas 2014-2023. Fecha de cálculo: al abrir la pantalla. No hay un proceso de "
        "actualización automática anual; la frecuencia de actualización depende de nuevas "
        "publicaciones del consolidado."
    )
    if es_referente_sur:
        st.info("La sede seleccionada **es** el referente del sur ({}). Las comparaciones "
                "contra 'la mejor sede del sur' coinciden con ella misma.".format(sur_nombre))

    # --- Tarjetas: cuatro indicadores de decisión (base 2021-2023) ---
    st.markdown("### Indicadores de decisión (base 2021-2023)")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("1 · Área cubierta a 40 km", fmt_pct(pct_sede))
        st.caption("Diferencia frente al referente del sur ({}): {}".format(
            sur_nombre, fmt_puntos(pct_sede - pct_sur)))
    with c2:
        st.metric("2 · Puesto entre los 42 municipios", "#{}".format(puesto_sede))
        if puesto_sede == 1:
            seg = rk.iloc[1]
            st.caption("Ventaja sobre el 2.º ({}): {}".format(
                seg["sede"], fmt_puntos(pct_sede - seg["pct_area"])))
        else:
            lider = rk.iloc[0]
            st.caption("Distancia al líder ({}): {}".format(
                lider["sede"], fmt_puntos(pct_sede - lider["pct_area"])))
        st.caption("Empates: a igualdad exacta de área, orden alfabético; puesto por rango mínimo.")
    with c3:
        st.metric("3 · Volumen anual captable (20 %)", fmt_toneladas(vol_sede))
        st.caption("Referente del sur ({}): {}".format(sur_nombre, fmt_toneladas(vol_sur)))
    with c4:
        razon = (vol_sede / vol_sur) if vol_sur else float("nan")
        st.metric("4 · Razón de volumen vs. sur", "{} veces".format(fmt_razon(razon, 2)))
        st.caption("{}: {} · {}: {}".format(
            modelo.nombre(sede_cod), fmt_toneladas(vol_sede), sur_nombre, fmt_toneladas(vol_sur)))

    st.caption(
        "Estas son **métricas e indicadores de decisión**, no KPI: el proyecto no ha fijado "
        "meta, umbral ni responsable para ellas. El único umbral es el de la **hipótesis** "
        "(50 % del área, el doble de capacidad), señalado como tal. No se usan colores de "
        "estado ni flechas de tendencia: las comparaciones son entre sedes, no en el tiempo. "
        "Detalle en docs/dashboard/fichas_kpi.md."
    )

    # --- Cuatro visuales del resumen (cuadrícula 2x2) ---
    st.markdown("### Respuestas visuales")
    estab = cargar_estabilidad_opt()
    frec = cob.frecuencia_centrales(estab)

    fila1a, fila1b = st.columns(2)
    with fila1a:
        st.markdown("**P1. ¿Qué sedes cubren más área a 40 km?**")
        st.caption("% del área de fruta y plátano · base 2021-2023 · top 10 + sede + referente del sur")
        st.plotly_chart(_visual_p1(modelo, sede_cod, sur_cod), use_container_width=True)
        seg = rk.iloc[1]
        dif = abs(pct_sede - seg["pct_area"])
        if puesto_sede == 1 and dif < 0.02:
            resp_p1 = ("{} encabeza con {}, pero {} queda a {}: la diferencia es pequeña y "
                       "conviene tratar a las primeras como candidatas comparables, sin leer "
                       "significancia estadística.").format(
                sede_sel, fmt_pct(pct_sede), seg["sede"], fmt_puntos(seg["pct_area"] - pct_sede))
        else:
            resp_p1 = "{} ocupa el puesto #{} con {} del área a 40 km.".format(
                sede_sel, puesto_sede, fmt_pct(pct_sede))
        st.info(resp_p1)
    with fila1b:
        st.markdown("**P2. ¿Cómo cambia el volumen captable entre escenarios históricos?**")
        st.caption("t/año captables al 20 % · bajo/base/alto · base = 100 %")
        st.plotly_chart(_visual_p2(modelo, sede_cod), use_container_width=True)
        ve = cob.volumenes_escenarios(modelo, sede_cod)
        bajo_p = ve.iloc[0]["pct_vs_base"]; alto_p = ve.iloc[2]["pct_vs_base"]
        st.info(
            "Entre el bajo sintético ({}) y el alto sintético ({}) el volumen captable varía "
            "de forma amplia; conviene estudiar flexibilidad o desarrollo por etapas. El 100 % "
            "es la definición de la base 2021-2023, no evidencia de que una central opere al "
            "100 %. Bajo y alto combinan extremos municipales de 2014-2023, de años distintos y "
            "sin probabilidad asociada.".format(fmt_pct(bajo_p), fmt_pct(alto_p))
        )

    fila2a, fila2b = st.columns(2)
    with fila2a:
        st.markdown("**P3. ¿Cómo difiere la composición productiva frente al referente del sur?**")
        st.caption("% de toneladas por cultivo · promedio 2021-2023 · piña destacada")
        fig_p3, comp_sede, comp_sur = _visual_p3(produccion, modelo, sede_cod, sur_cod)
        st.plotly_chart(fig_p3, use_container_width=True)
        with st.expander("Producción, superficie y toneladas por hectárea sembrada"):
            tabla_p3 = pd.DataFrame({
                "": ["Producción total", "Superficie sembrada", "t por ha sembrada", "Piña (% toneladas)", "t por ha sin piña"],
                sede_sel: [fmt_toneladas(comp_sede["total_t"]), "{} ha".format(fmt_entero(comp_sede["ha_sembradas"])),
                           fmt_razon(comp_sede["t_por_ha_sembrada"], 2), fmt_pct(comp_sede["pct_pina_toneladas"]),
                           fmt_razon(comp_sede["t_por_ha_sin_pina"], 2)],
                sur_nombre: [fmt_toneladas(comp_sur["total_t"]), "{} ha".format(fmt_entero(comp_sur["ha_sembradas"])),
                             fmt_razon(comp_sur["t_por_ha_sembrada"], 2), fmt_pct(comp_sur["pct_pina_toneladas"]),
                             fmt_razon(comp_sur["t_por_ha_sin_pina"], 2)],
            })
            st.dataframe(tabla_p3, use_container_width=True, hide_index=True)
            st.caption("El % de piña es sobre **toneladas**, no área. 't por ha sembrada' es una "
                       "razón sobre área sembrada, descriptiva, no rendimiento agronómico.")
        if es_referente_sur:
            st.info("La sede coincide con el referente del sur: la composición mostrada es la "
                    "misma a ambos lados.")
        else:
            st.info(
                "La piña pesa {} de las toneladas en {} y {} en {}. Es una descripción de la "
                "mezcla de cultivos, no una relación causal.".format(
                    fmt_pct(comp_sede["pct_pina_toneladas"]), sede_sel,
                    fmt_pct(comp_sur["pct_pina_toneladas"]), sur_nombre)
            )
    with fila2b:
        st.markdown("**P4. ¿Qué sedes aparecen al variar los escenarios de optimización?**")
        st.caption("frecuencia por municipio · {} escenarios de {} · configuración k=5, λ=0,5".format(
            frec["n_total"], ", ".join(str(a) for a in frec["anios"])))
        fig_p4 = _visual_p4(frec, sede_sel)
        if fig_p4 is None:
            st.info("No hay escenarios de optimización disponibles (data/results/opt/).")
        else:
            st.plotly_chart(fig_p4, use_container_width=True)
            veces = int(frec["frecuencias"].get(sede_sel, 0))
            if veces > 0:
                resp_p4 = "{} aparece como central en {} de {} escenarios resueltos.".format(
                    sede_sel, veces, frec["n_resueltos"])
            else:
                resp_p4 = ("{} no aparece como central en ninguno de los {} escenarios resueltos; "
                           "no implica que sea inviable.").format(sede_sel, frec["n_resueltos"])
            st.info(
                resp_p4 + " Ejecuciones sin solución o no válidas: {}. Son **frecuencias**, no "
                "probabilidades. Este análisis usa excedentes con consumo (red de tiempos de "
                "viaje), un alcance distinto del histórico de área de fruta y plátano del resumen. "
                "El filtro de sede solo cambia el resaltado; no recalcula el universo de "
                "escenarios.".format(frec["n_sin_solucion"])
            )
            st.caption("Asociación mezcla de mercados ↔ sede: describir, no afirmar causa, salvo "
                       "comparar escenarios con año, oferta y consumo iguales (ver pantalla 3).")

    # --- Secciones complementarias plegadas ---
    _resumen_detalle_pronostico()
    _resumen_detalle_api(produccion, modelo)

    # --- Descarga del resumen con filtros, unidades, periodos y supuestos ---
    _resumen_descarga(modelo, sede_cod, sur_cod, frec)


def _resumen_detalle_pronostico():
    with st.expander("Pronóstico y exposición logística", expanded=False):
        try:
            e = cob.exposicion_sin_cana()
        except Exception as ex:
            st.info("No se pudo reproducir la exposición sin caña: {}".format(ex))
            return
        st.markdown(
            "**Alcance y horizonte:** error del pronóstico a un año (horizonte 1), años "
            "{}-{}, sin caña de azúcar (no entra a la central). Red del escenario base: "
            "{} y satélites.".format(e["anio_min"], e["anio_max"], e["red"])
        )
        cc1, cc2, cc3 = st.columns(3)
        cc1.metric("Exposición sin modelo", "{} M t·min".format(fmt_razon(e["sin_modelo_millones"], 2)))
        cc2.metric("Exposición con modelo", "{} M t·min".format(fmt_razon(e["modelo_millones"], 2)))
        cc3.metric("Reducción del modelo", fmt_pct(abs(e["reduccion_modelo_pct"])))
        st.markdown(
            "- Referencia ingenua: reducción de {} frente al promedio de cinco años.\n"
            "- Cobertura de intervalos observada ≈ 76 % frente al 80 % nominal "
            "(docs/ML_C/limitaciones_pronostico.md).\n"
            "- Error valorizado a un año sin caña ≈ 25 % por serie producto-municipio y "
            "≈ 7 % en el total departamental (src/informe/cifras_3_3_y_3_4.py)."
            .format(fmt_pct(abs(e["reduccion_ingenuo_pct"])))
        )
        st.markdown("**Valoración de exposición (reconciliada):**")
        st.caption(
            "La diferencia de exposición es un acumulado de cinco años ({} M t·min). "
            "A {} COP/(t·min), ese acumulado valdría {} COP; **anualizado** (÷ 5 años) da "
            "{} COP/año ≈ 1.500 millones. Es una **valoración de exposición** con un factor "
            "supuesto de 250 COP/(t·min), no un ahorro financiero realizado. Multiplicar "
            "100,08 − 69,69 por 250 sin anualizar NO produce los 1.500 millones.".format(
                fmt_razon(e["diferencia_total_tmin"] / 1e6, 2), fmt_entero(e["cop_tmin"]),
                fmt_millones_cop(e["valoracion_acumulada_5anios_cop"]),
                fmt_millones_cop(e["valoracion_anual_cop"]),
            )
        )


def _resumen_detalle_api(produccion, modelo):
    with st.expander("API y base de datos", expanded=False):
        col_api, col_db = st.columns(2)
        with col_api:
            st.markdown("**API REST (predicciones)**")
            if _REQUESTS_DISPONIBLE:
                try:
                    r = requests.get(f"{API_URL}/health", timeout=10)
                    if r.status_code == 200:
                        datos = r.json()
                        st.success("API en línea")
                        st.caption("Modelo cargado: {}".format(datos.get("modelo_cargado", False)))
                    else:
                        st.warning("API respondió {}".format(r.status_code))
                except Exception as ex:
                    st.warning("API no alcanzable en {}".format(API_URL))
                    st.caption("Los resultados locales siguen disponibles. Detalle: {}".format(type(ex).__name__))
            else:
                st.info("requests no instalado; se consultan solo los resultados locales.")
            st.caption("El endpoint /predict devuelve una predicción **LightGBM**; no es el "
                       "modelo final combinado (promedio ingenuo + LightGBM). Contrato de "
                       "/predict sin cambios en este PR.")
        with col_db:
            st.markdown("**Base de datos (DuckDB)**")
            if _REQUESTS_DISPONIBLE:
                try:
                    r = requests.get(f"{API_URL}/metricas", timeout=20)
                    if r.status_code == 200:
                        datos = r.json()
                        fuente = datos.get("fuente")
                        st.success("Fuente de métricas: {}".format(fuente or "n.d."))
                        st.caption("Métricas disponibles: {}".format(len(datos.get("metricas", []))))
                    else:
                        st.warning("API respondió {}".format(r.status_code))
                except Exception as ex:
                    st.warning("No se pudo consultar /metricas.")
                    st.caption("El resumen sigue funcionando con los datos locales. Detalle: {}".format(type(ex).__name__))
            else:
                st.info("requests no instalado; se consultan solo los resultados locales.")

        # Formulario de predicción existente (se conserva)
        st.markdown("**Probar predicción en vivo (LightGBM vía /predict)**")
        if not _REQUESTS_DISPONIBLE:
            st.info("requests no instalado; no se puede consultar la API.")
        elif produccion.empty:
            st.info("No hay datos históricos para poblar el formulario.")
        else:
            productos_api = sorted(produccion["producto"].dropna().unique())
            prod_default = "Caña de azúcar" if "Caña de azúcar" in productos_api else productos_api[0]
            fc1, fc2, fc3 = st.columns([2, 2, 1])
            prod_sel = fc1.selectbox("Producto", productos_api, index=productos_api.index(prod_default), key="api_producto")
            anio_hist = int(produccion.loc[produccion["producto"] == prod_sel, "anio"].max())
            hist = produccion[(produccion["producto"] == prod_sel) & (produccion["anio"] == anio_hist)]
            codigos = sorted(hist["cod_dane"].astype(str).unique())
            nombres_mun = dict(zip(municipios["cod_dane"].astype(str), municipios["municipio"])) if not municipios.empty else {}
            etiquetas = ["{} - {}".format(cod, nombres_mun.get(cod, "")).strip() for cod in codigos]
            if etiquetas:
                idx_m = next((i for i, cod in enumerate(codigos) if cod == "76113"), 0)
                mun_sel = fc2.selectbox("Municipio", etiquetas, index=idx_m, key="api_municipio")
                anio_sel = fc3.selectbox("Año", [2024, 2025, 2026, 2027, 2028], index=0, key="api_anio")
                if st.button("Predecir oferta", key="api_predecir"):
                    cod_sel = codigos[etiquetas.index(mun_sel)]
                    payload = {"producto": prod_sel, "cod_dane": cod_sel,
                               "horizonte": int(anio_sel) - 2023, "anio_objetivo": int(anio_sel)}
                    try:
                        with st.spinner("Consultando la API..."):
                            r = requests.post(f"{API_URL}/predict", json=payload, timeout=120)
                        if r.status_code == 200:
                            d = r.json()
                            st.metric("Oferta estimada (LightGBM)", fmt_toneladas(d.get("prediccion_t", 0)))
                            st.caption("Modelo {} · fuente {}".format(d.get("modelo_version", "n.d."), d.get("fuente", "n.d.")))
                        else:
                            st.error("API {}: {}".format(r.status_code, r.text[:200]))
                    except Exception as ex:
                        st.warning("No se pudo consultar la API: {}".format(type(ex).__name__))


def _resumen_descarga(modelo, sede_cod, sur_cod, frec):
    st.markdown("### Descargar resumen")
    sede = modelo.nombre(sede_cod); sur = modelo.nombre(sur_cod)
    ve = cob.volumenes_escenarios(modelo, sede_cod)
    filas = [
        {"indicador": "Sede seleccionada", "valor": sede, "unidad": "", "periodo": "", "supuesto": "filtro del usuario"},
        {"indicador": "Referente del sur", "valor": sur, "unidad": "", "periodo": "", "supuesto": "mayor área del sur"},
        {"indicador": "Área cubierta a 40 km", "valor": round(100 * modelo.pct_area(sede_cod), 2), "unidad": "% del área",
         "periodo": "2021-2023", "supuesto": "radio 40 km, distancia haversine entre centroides"},
        {"indicador": "Puesto entre 42 municipios", "valor": modelo.puesto(sede_cod), "unidad": "puesto",
         "periodo": "2021-2023", "supuesto": "orden por área; empates por nombre"},
        {"indicador": "Volumen captable base", "valor": round(modelo.volumen_captable(sede_cod)), "unidad": "t/año",
         "periodo": "2021-2023", "supuesto": "captación 20 %"},
        {"indicador": "Volumen captable bajo sintético", "valor": round(ve.iloc[0]["volumen_t"]), "unidad": "t/año",
         "periodo": "2014-2023", "supuesto": "peor año municipal, años distintos"},
        {"indicador": "Volumen captable alto sintético", "valor": round(ve.iloc[2]["volumen_t"]), "unidad": "t/año",
         "periodo": "2014-2023", "supuesto": "mejor año municipal, años distintos"},
        {"indicador": "Razón de volumen vs. sur", "valor": round(modelo.volumen_captable(sede_cod) / modelo.volumen_captable(sur_cod), 2),
         "unidad": "veces", "periodo": "2021-2023", "supuesto": "captación 20 %"},
        {"indicador": "Frecuencia como central (optimización)", "valor": int(frec["frecuencias"].get(sede, 0)),
         "unidad": "de {} escenarios resueltos".format(frec["n_resueltos"]), "periodo": ", ".join(str(a) for a in frec["anios"]),
         "supuesto": "k=5, λ=0,5; alcance distinto (excedentes con consumo)"},
    ]
    df = pd.DataFrame(filas)
    st.download_button(
        "⬇️ Descargar resumen de la sede (CSV)",
        data=df.to_csv(index=False).encode("utf-8-sig"),
        file_name="resumen_{}.csv".format(sede_cod),
        mime="text/csv",
    )


# =============================================================================
# PANTALLA 1: OFERTA
# =============================================================================
def pantalla_oferta():
    st.title("📊 Pantalla 1 - Oferta por Producto y Municipio")
    st.markdown("""
    Consulta el pronóstico de oferta agrícola por producto y municipio, con intervalos
    de confianza (bajo/base/alto) para el horizonte 2024-2028.
    """)

    if oferta.empty or municipios.empty:
        st.error("No se pudieron cargar los datos de oferta o municipios.")
        return

    col1, col2 = st.columns(2)

    with col1:
        productos = obtener_productos_disponibles(oferta)
        producto_sel = st.selectbox("Producto:", productos, index=0)

    with col2:
        mun_producto = obtener_municipios_por_producto(oferta, producto_sel, ano_seleccionado)
        if not mun_producto.empty:
            mun_opciones = sorted(mun_producto["cod_dane"].unique())
            mun_nombres = municipios.set_index("cod_dane")["municipio"].to_dict()
            mun_labels = ["{} - {}".format(c, mun_nombres.get(c, c)) for c in mun_opciones]
            mun_sel_label = st.selectbox("Municipio:", mun_labels, index=0)
            cod_dane_sel = mun_opciones[mun_labels.index(mun_sel_label)]
        else:
            st.warning("No hay datos de oferta para {} en el año {}".format(producto_sel, ano_seleccionado))
            return

    serie_hist = obtener_serie_historica(produccion, producto_sel, cod_dane_sel)
    pronostico = obtener_pronostico_municipio(oferta, producto_sel, cod_dane_sel)

    mun_nombre = municipios.set_index("cod_dane")["municipio"].get(cod_dane_sel, cod_dane_sel)

    st.markdown("### {} - {} ({})".format(producto_sel, mun_nombre, cod_dane_sel))

    fig = go.Figure()

    if not serie_hist.empty:
        fig.add_trace(go.Scatter(
            x=serie_hist["anio"],
            y=serie_hist["produccion_t"],
            mode="lines+markers",
            name="Historico (2000-2023)",
            line=dict(color="#1f77b4", width=2),
            marker=dict(size=6),
        ))

    if not pronostico.empty:
        fig.add_trace(go.Scatter(
            x=pronostico["año"],
            y=pronostico["oferta_base"],
            mode="lines+markers",
            name="Pronostico base",
            line=dict(color="#2ca02c", width=2, dash="dash"),
            marker=dict(size=6, symbol="diamond"),
        ))
        fig.add_trace(go.Scatter(
            x=pronostico["año"].tolist() + pronostico["año"].tolist()[::-1],
            y=pronostico["oferta_alto"].tolist() + pronostico["oferta_bajo"].tolist()[::-1],
            fill="toself",
            fillcolor="rgba(44, 160, 44, 0.2)",
            line=dict(color="rgba(255,255,255,0)"),
            showlegend=False,
            name="Intervalo bajo-alto",
        ))
        fig.add_trace(go.Scatter(
            x=pronostico["año"],
            y=pronostico["oferta_alto"],
            mode="lines",
            line=dict(color="rgba(255,255,255,0)"),
            showlegend=False,
        ))
        fig.add_trace(go.Scatter(
            x=pronostico["año"],
            y=pronostico["oferta_bajo"],
            mode="lines",
            line=dict(color="rgba(255,255,255,0)"),
            showlegend=False,
        ))

    fig.update_layout(
        title="Produccion y Pronostico - {} en {}".format(producto_sel, mun_nombre),
        xaxis_title="Anio",
        yaxis_title="Toneladas",
        hovermode="x unified",
        template="plotly_white",
        height=500,
    )
    st.plotly_chart(fig, use_container_width=True)

    if not pronostico.empty:
        st.markdown("### Tabla de Pronostico")
        st.dataframe(
            pronostico.style.format({"oferta_bajo": "{:,.0f}", "oferta_base": "{:,.0f}", "oferta_alto": "{:,.0f}"}),
            use_container_width=True,
        )

    if not serie_hist.empty:
        st.markdown("### Serie Historica Reciente (ultimos 10 anos)")
        st.dataframe(
            serie_hist.tail(10).style.format({"produccion_t": "{:,.0f}"}),
            use_container_width=True,
        )


# =============================================================================
# PANTALLA 2: ZONAS
# =============================================================================
def pantalla_zonas():
    st.title("🗺️ Pantalla 2 - Oferta municipal pronosticada (mapa)")
    st.markdown("""
    Mapa de los 42 municipios del Valle del Cauca coloreados por su **oferta pronosticada**
    por producto y año. El agrupamiento espacial en zonas de acopio está en la pantalla
    **2b. Zonas de acopio**.
    """)

    if oferta.empty or municipios.empty:
        st.error("No se pudieron cargar los datos.")
        return

    col1, col2 = st.columns(2)
    with col1:
        productos = obtener_productos_disponibles(oferta)
        producto_sel = st.selectbox("Producto:", productos, index=0, key="zonas_producto")
    with col2:
        ano_sel = st.selectbox("Anio:", anos_disponibles, index=0, key="zonas_ano")

    mun_oferta = obtener_municipios_por_producto(oferta, producto_sel, ano_sel)

    if mun_oferta.empty:
        st.warning("No hay datos para {} en {}".format(producto_sel, ano_sel))
        return

    valores_col = "oferta_{}".format(escenario)
    mapa_df = mun_oferta[["cod_dane", valores_col]].rename(columns={valores_col: "oferta_valor"})

    m = crear_mapa_base(centro=[4.2, -76.2], zoom=8)
    m = agregar_municipios_al_mapa(m, municipios, mapa_df, columna_valor="oferta_valor")
    m = agregar_destinos_al_mapa(m, destinos)

    st.markdown("### Oferta {} - {} - {}".format(escenario, producto_sel, ano_sel))
    st_folium(m, width=900, height=600, key="mapa_zonas")

    st.markdown("### Resumen por Municipio")
    resumen = municipios.merge(mapa_df, on="cod_dane", how="left")
    resumen = resumen[resumen["oferta_valor"].notna()].sort_values("oferta_valor", ascending=False)
    st.dataframe(
        resumen[["municipio", "cod_dane", "oferta_valor"]].style.format({"oferta_valor": "{:,.0f}"}),
        use_container_width=True,
    )

    total = resumen["oferta_valor"].sum()
    promedio = resumen["oferta_valor"].mean()
    col1, col2, col3 = st.columns(3)
    col1.metric("Oferta Total", "{:,.0f} t".format(total))
    col2.metric("Oferta Promedio por Municipio", "{:,.0f} t".format(promedio))
    col3.metric("Municipios con Produccion", "{}".format(len(resumen)))


# =============================================================================
# PANTALLA 2b: ZONAS DE ACOPIO (vecindad, agrupamiento y volúmenes por escenario)
# =============================================================================
def _color_zona(zona, zonas_lista):
    paleta = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
              "#8c564b", "#e377c2", "#7f7f7f"]
    try:
        i = sorted(zonas_lista).index(zona)
    except ValueError:
        i = 0
    return paleta[i % len(paleta)]


def pantalla_zonas_acopio():
    st.title("🧭 Pantalla 2b - Zonas de acopio por agrupamiento espacial")
    st.markdown("""
    Zonas de acopio espacialmente conexas (contigüidad Queen + Ward con restricción
    de conectividad). Los **centros de zona son referencias** (tiempos ponderados por
    oferta), no la ubicación óptima: esa la calcula la **optimización de la pantalla 3**.
    """)

    zonas_df = cargar_zonas()
    if zonas_df.empty or municipios.empty:
        st.error("No se encontró `data/results/zonas.csv`. Corre: python src/arendonc2/zonas_acopio.py")
        return

    zonas_geo = cargar_zonas_geometrias()
    escen = cargar_escenarios_opt()

    zonas_lista = sorted(zonas_df["zona"].unique())
    col1, col2, col3 = st.columns(3)
    with col1:
        anios_esc = sorted(escen["anio"].unique()) if not escen.empty else [ano_seleccionado]
        anio_z = st.selectbox("Año:", anios_esc, index=0, key="zacopio_anio")
    with col2:
        if not escen.empty:
            ids = sorted(escen[escen["anio"] == anio_z]["id_escenario"].unique())
            id_esc = st.selectbox("Escenario de optimización:", ids,
                                  index=ids.index(f"{anio_z}_Obase_Cbase_M80_20")
                                  if f"{anio_z}_Obase_Cbase_M80_20" in ids else 0,
                                  key="zacopio_id")
        else:
            id_esc = None
    with col3:
        st.metric("Zonas", len(zonas_lista))

    # Mapa de zonas
    mun_coord = municipios.merge(zonas_df, on="cod_dane", how="left", suffixes=("", "_z"))
    m = folium.Map(location=[4.2, -76.2], zoom_start=8, tiles="OpenStreetMap")

    if zonas_geo is not None:
        for _, row in zonas_geo.iterrows():
            color = _color_zona(row["zona"], zonas_lista)
            folium.GeoJson(
                row["geometry"].__geo_interface__,
                style_function=lambda x, c=color: {
                    "fillColor": c, "color": "black", "weight": 1, "fillOpacity": 0.35
                },
                tooltip=f"Zona {row['zona']}",
            ).add_to(m)

    for _, row in mun_coord.iterrows():
        color = _color_zona(row.get("zona"), zonas_lista)
        es_centro = int(row.get("es_centro_zona", 0) or 0) == 1
        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=10 if es_centro else 5,
            popup=folium.Popup(
                "<b>{}</b> ({})<br>Zona: {}<br>{}".format(
                    row["municipio"], row["cod_dane"], row.get("zona"),
                    "CENTRO de zona (referencia)" if es_centro else ""
                ), max_width=220),
            color="black", weight=2 if es_centro else 1,
            fill=True, fillColor=color,
            fillOpacity=0.95 if es_centro else 0.7,
        ).add_to(m)

    st_folium(m, width=900, height=560, key="mapa_zonas_acopio")

    # Volúmenes por zona del escenario seleccionado + advertencia de cobertura
    if id_esc is not None and not escen.empty:
        fila = escen[(escen["id_escenario"] == id_esc) & (escen["anio"] == anio_z)].copy()
        if not fila.empty:
            cobertura = float(fila["cobertura_oferta_pct"].min())
            if cobertura < 100.0:
                st.warning(
                    "⚠️ **Cobertura parcial de consumo:** {:.2f}% de la oferta tiene consumo "
                    "FAOSTAT definido. Los productos sin equivalencia de unidad (p. ej. café, "
                    "caña panelera, flores) quedan con excedente desconocido y NO aportan "
                    "volumen a la optimización; su oferta se conserva pero se excluye de estos volúmenes."
                    .format(cobertura)
                )
            fila["excedente_zona_t"] = fila["volumen_nacional"] + fila["volumen_exportacion"]
            st.markdown("### Volúmenes por zona — {}".format(id_esc))
            tabla = fila[["zona", "volumen_nacional", "volumen_exportacion",
                          "excedente_zona_t", "cobertura_oferta_pct"]].sort_values("zona")
            st.dataframe(
                tabla.style.format({
                    "volumen_nacional": "{:,.1f}", "volumen_exportacion": "{:,.1f}",
                    "excedente_zona_t": "{:,.1f}", "cobertura_oferta_pct": "{:.2f}%",
                }),
                use_container_width=True,
            )
            col_a, col_b = st.columns(2)
            col_a.metric("Excedente total (t)", "{:,.0f}".format(tabla["excedente_zona_t"].sum()))
            col_b.metric("Hacia exportación (t)", "{:,.0f}".format(tabla["volumen_exportacion"].sum()))

            st.download_button(
                "⬇️ Descargar volúmenes de este escenario (CSV)",
                data=tabla.to_csv(index=False).encode("utf-8-sig"),
                file_name="volumenes_{}.csv".format(id_esc),
                mime="text/csv",
            )

    st.markdown("### Asignación municipio → zona")
    tz = zonas_df.copy()
    tz["es_centro_zona"] = tz["es_centro_zona"].map({1: "centro (ref.)", 0: ""})
    st.dataframe(tz.sort_values(["zona", "municipio"]), use_container_width=True)
    st.download_button(
        "⬇️ Descargar zonas.csv",
        data=zonas_df.to_csv(index=False).encode("utf-8-sig"),
        file_name="zonas.csv", mime="text/csv",
    )


# =============================================================================
# PANTALLA 3: UBICACION
# =============================================================================
def pantalla_ubicacion():
    st.title("📍 Pantalla 3 - Ubicacion de Central y Acopios Satelite (logística)")
    st.markdown("""
    Minimiza el **costo logístico** (toneladas × minutos) de ubicar una central y sus
    acopios satélite, usando los excedentes proyectados del módulo de escenarios y
    OR-Tools con **flujo satélite→central explícito**.
    """)
    st.caption(
        "Optimización logística con el pronóstico seleccionado. Es distinta de la "
        "'4. Tablero central', que mide cobertura de área con estadísticas históricas; "
        "sus escenarios no son equivalentes."
    )

    municipios, destinos, matriz_tiempos = cargar_datos_reales()
    try:
        construir_matriz_tiempos_dict(matriz_tiempos, municipios, destinos)
    except ValueError as e:
        st.error("Matriz de tiempos inválida: {}".format(e))
        return

    # --- controles del escenario ---
    st.markdown("### Parámetros")
    c1, c2, c3 = st.columns(3)
    with c1:
        ano_sel = st.selectbox("Año:", anos_disponibles, index=0, key="opt_anio")
        oferta_sel = st.selectbox("Oferta:", ["base", "bajo", "alto"], index=0, key="opt_oferta")
    with c2:
        consumo_sel = st.selectbox("Consumo:", ["base", "bajo", "alto"], index=0, key="opt_consumo")
        mezcla_sel = st.selectbox("Mezcla nacional/exportación:", ["80_20", "50_50", "20_80"],
                                  index=0, key="opt_mezcla")
    with c3:
        modo_sel = st.selectbox("Configuración territorial:", ["libre", "zonas"],
                                index=0, key="opt_modo",
                                help="libre: 5 satélites sin restricción de zona. "
                                     "zonas: un satélite por cada una de las 5 zonas.")
        lam = st.slider("λ (peso de A = recolección+satélite-central):", 0.0, 1.0, 0.5, 0.1,
                        key="opt_lambda")

    with st.expander("Parámetros del solver (avanzado)"):
        cs1, cs2 = st.columns(2)
        gap_relativo = cs1.number_input("Brecha relativa objetivo (0 = sin brecha):",
                                        min_value=0.0, max_value=0.2, value=0.0, step=0.005,
                                        format="%.3f", key="opt_gap")
        tiempo_limite_s = cs2.number_input("Límite de tiempo por solve (s):",
                                           min_value=10, max_value=600, value=120, step=10,
                                           key="opt_tlim")
        st.caption("El límite de tiempo NO se reduce por defecto para aparentar velocidad. "
                   "Solicitar gap 0 exige buscar una solución sin brecha, pero el límite de "
                   "tiempo puede impedir alcanzarla; la calidad se informa con el estado del "
                   "solver, la mejor cota y la brecha efectiva.")

    k_satelites = 5
    id_escenario = "{}_O{}_C{}_M{}".format(ano_sel, oferta_sel, consumo_sel, mezcla_sel)
    st.caption("Capacidades: la versión base **no** impone capacidad mínima ni máxima por "
               "acopio (no hay valores respaldados). Se usan 5 satélites.")

    # paquete (barato, para mostrar cobertura y volumen sin resolver el MIP)
    try:
        paquete = preparar_para_solver(id_escenario, ano_sel)
    except Exception as e:
        st.error("No se pudo cargar el escenario {}: {}".format(id_escenario, e))
        st.info("Corre: python src/arendonc2/ejecutar_todo.py")
        return

    vol_conocido = float(paquete.excedente_municipio["excedente_t"].sum())
    mcol1, mcol2, mcol3 = st.columns(3)
    mcol1.metric("Volumen conocido (t)", "{:,.0f}".format(vol_conocido))
    mcol2.metric("Cobertura de consumo", "{:.2f}%".format(paquete.cobertura_oferta_pct))
    mcol3.metric("N° de satélites", k_satelites)
    if paquete.cobertura_parcial:
        st.warning(
            "⚠️ **Cobertura parcial:** {:.2f}% de la oferta tiene consumo FAOSTAT definido. "
            "Productos sin equivalencia de unidad (café, caña panelera, flores…) quedan con "
            "excedente desconocido y NO aportan volumen a la optimización."
            .format(paquete.cobertura_oferta_pct)
        )

    # --- botón explícito de cálculo ---
    st.markdown("### Cálculo")
    st.caption("La optimización se ejecuta sólo al pulsar el botón. Los resultados se "
               "cachean por escenario, año, modo, k, λ, pesos y parámetros del solver, "
               "y se invalidan si cambian los datos.")
    calcular = st.button("▶️ Calcular optimización", type="primary", key="opt_run")

    firma = (id_escenario, ano_sel, modo_sel, k_satelites, lam, gap_relativo, tiempo_limite_s)
    if calcular:
        st.session_state["opt_firma"] = firma
    if st.session_state.get("opt_firma") != firma:
        st.info("Ajusta los parámetros y pulsa **Calcular optimización** para resolver.")
        return

    huella = _huella_datos()
    mun_a_zona = dict(zip(paquete.zonas["cod_dane"], paquete.zonas["zona"]))

    # --- resolver (cacheado, sólo resultado serializable) ---
    try:
        with st.spinner("Resolviendo (modo {})…".format(modo_sel)):
            res = opt_resolver_cache(id_escenario, ano_sel, modo_sel, k_satelites, lam,
                                     None, None, int(tiempo_limite_s), float(gap_relativo), huella)
    except ValueError as e:
        st.error("Error en la configuración/solución: {}".format(e))
        return

    if res["status"] not in ("OPTIMAL", "FEASIBLE"):
        st.error("El solver no encontró solución (estado: {}).".format(res["status"]))
        diag = res.get("diagnostico", {})
        if diag:
            st.json(diag)
        return
    if res["status"] == "FEASIBLE":
        st.info("Solución **factible** (no certificada óptima dentro del límite/brecha). "
                "No se presenta como óptima.")

    # --- diagnóstico del solver ---
    diag = res["diagnostico"]
    with st.expander("Diagnóstico del solver", expanded=False):
        st.write({
            "solver": diag["solver"],
            "estado": diag["status"],
            "objetivo (t·min)": round(diag.get("objetivo", float("nan")), 2),
            "mejor_cota (t·min)": round(diag["mejor_cota"], 2) if diag.get("mejor_cota") is not None else None,
            "brecha_efectiva": diag.get("gap_efectivo"),
            "brecha_formula": diag.get("gap_efectivo_formula"),
            "tiempo_s": diag.get("tiempo_s"),
            "gap_solicitado": diag.get("gap_solicitado"),
            "gap_aceptado_por_solver": diag.get("gap_aceptado"),
            "detalle_gap": diag.get("gap_detalle"),
        })

    central_cod = res["central"]
    central_nombre = res["central_nombre"]
    central_zona = res["central_zona"]
    central_lat = municipios[municipios["cod_dane"] == central_cod]["lat"].iloc[0]
    central_lon = municipios[municipios["cod_dane"] == central_cod]["lon"].iloc[0]
    satelites_info = res["satelites"]

    st.markdown("### Mapa de ubicación (modo {}, estado {})".format(modo_sel, res["status"]))
    col1, col2 = st.columns([2, 1])
    with col1:
        m = folium.Map(location=[central_lat, central_lon], zoom_start=8, tiles="OpenStreetMap")
        oferta_mun = {r["cod_dane"]: float(r["excedente_t"])
                      for _, r in paquete.excedente_municipio.iterrows()}
        coord_map = {r["cod_dane"]: (r["lat"], r["lon"]) for _, r in municipios.iterrows()}
        sat_cods = [s["cod_dane"] for s in satelites_info]
        for _, row in municipios.iterrows():
            cod, nom = row["cod_dane"], row["municipio"]
            ofe = oferta_mun.get(cod, 0.0)
            if cod == central_cod:
                color, radius, tipo = "red", 12, "CENTRAL"
            elif cod in sat_cods:
                color, radius, tipo = "orange", 9, "SATÉLITE"
            else:
                color, radius, tipo = "blue", 5, ""
            popup = "<b>{} {}</b> ({})<br>Zona: {}<br>Excedente: {:,.0f} t".format(
                tipo, nom, cod, mun_a_zona.get(cod, "?"), ofe)
            folium.CircleMarker(location=[row["lat"], row["lon"]], radius=radius,
                                popup=folium.Popup(popup, max_width=220), color="black",
                                weight=1, fill=True, fillColor=color, fillOpacity=0.8).add_to(m)
        for muni_cod, sat_cod in res["asignaciones_municipio_satelite"]:
            if muni_cod in coord_map and sat_cod in coord_map:
                folium.PolyLine([coord_map[muni_cod], coord_map[sat_cod]],
                                color="gray", weight=1, opacity=0.3).add_to(m)
        for sat_cod, cen_cod in res["asignaciones_satelite_central"]:
            if sat_cod in coord_map and cen_cod in coord_map:
                folium.PolyLine([coord_map[sat_cod], coord_map[cen_cod]],
                                color="red", weight=2, opacity=0.7).add_to(m)
        for _, drow in destinos.iterrows():
            folium.Marker(location=[drow["lat"], drow["lon"]],
                          popup=folium.Popup("<b>{}</b><br>({})".format(drow["nombre"], drow["id_destino"]), max_width=200),
                          icon=folium.Icon(color="blue", icon="info-sign")).add_to(m)
        st_folium(m, width=700, height=500, key="mapa_ubicacion")

    with col2:
        st.markdown("### Resultado ({})".format(res["status"]))
        st.metric("Central", central_nombre)
        st.metric("Zona de la central", central_zona)
        st.metric("Código DANE", central_cod)
        st.markdown("**Satélites:**")
        for i, s in enumerate(satelites_info):
            st.write("{}. {} (zona {}{})".format(
                i + 1, s["nombre"], s["zona"], ", centro ref." if s["es_centro"] else ""))
        st.markdown("---")
        st.markdown("### Costos (t·min)")
        st.metric("A1 recolección (muni→sat)", "{:,.0f}".format(res["costo_recoleccion"]))
        st.metric("A2 satélite→central", "{:,.0f}".format(res["costo_satelite_central"]))
        st.metric("B central→destinos", "{:,.0f}".format(res["costo_central_destinos"]))
        st.markdown("—")
        st.metric("A = A1 + A2", "{:,.0f}".format(res["A"]))
        st.metric("B", "{:,.0f}".format(res["B"]))
        st.metric("Objetivo = λ·A + (1-λ)·B", "{:,.0f}".format(res["costo_total"]))
        st.caption("Objetivo del solver: {:,.0f}".format(res["objetivo_solver"]))
        st.markdown("---")
        st.write("Año: {} | Oferta: {} | Consumo: {}".format(ano_sel, oferta_sel, consumo_sel))
        st.write("Mezcla: {} ({:.0%}/{:.0%})".format(mezcla_sel, res["pct_nacional"], res["pct_exportacion"]))
        st.write("Modo: {} | k: {} | λ: {}".format(modo_sel, k_satelites, lam))

    st.markdown("---")

    # --- comparación libre vs zonas (bajo demanda, cacheada) ---
    st.markdown("### Comparación de configuraciones (mismas entradas)")
    st.markdown("Mismo año, oferta, consumo, mezcla, λ y k=5; libre vs un satélite por zona.")
    comp = opt_comparacion_cache(id_escenario, ano_sel, k_satelites, lam,
                                 int(tiempo_limite_s), float(gap_relativo), huella)
    filas_comp = []
    for modo, r in comp.items():
        if r["status"] in ("OPTIMAL", "FEASIBLE"):
            d = r.get("diagnostico", {})
            filas_comp.append({
                "modo": modo, "estado": r["status"],
                "central": "{} ({})".format(r["central_nombre"], r["central_zona"]),
                "A1 recolección": r["costo_recoleccion"], "A2 sat→central": r["costo_satelite_central"],
                "B central→dest": r["costo_central_destinos"], "A": r["A"], "B": r["B"],
                "objetivo": r["costo_total"],
                "brecha": d.get("gap_efectivo"), "tiempo_s": d.get("tiempo_s"),
            })
        else:
            filas_comp.append({"modo": modo, "estado": r["status"], "central": "-",
                               "A1 recolección": None, "A2 sat→central": None, "B central→dest": None,
                               "A": None, "B": None, "objetivo": None, "brecha": None, "tiempo_s": None})
    df_comp = pd.DataFrame(filas_comp)
    st.dataframe(
        df_comp.style.format({c: "{:,.0f}" for c in
                              ["A1 recolección", "A2 sat→central", "B central→dest", "A", "B", "objetivo"]},
                             na_rep="—"),
        use_container_width=True,
    )
    resueltos_comp = [r for r in comp.values() if r["status"] in ("OPTIMAL", "FEASIBLE")]
    if len(resueltos_comp) == 2:
        oa, ob = resueltos_comp[0]["costo_total"], resueltos_comp[1]["costo_total"]
        base_cmp = min(abs(oa), abs(ob)) or 1.0
        st.caption("Diferencia de objetivo entre configuraciones: {:.2f}% "
                   "(brecha efectiva de cada solución en la tabla).".format(100 * abs(oa - ob) / base_cmp))

    # --- Pareto (bajo demanda, cacheado) ---
    st.markdown("### Soluciones no dominadas encontradas (barrido de λ)")
    st.markdown("Ejes **A** (recolección + satélite→central) y **B** (central→destinos), "
                "coherentes con el objetivo; dominados y duplicados eliminados. No se "
                "afirma que el barrido recupere toda la frontera.")
    df_pareto = opt_pareto_cache(id_escenario, ano_sel, modo_sel, k_satelites,
                                 int(tiempo_limite_s), float(gap_relativo), huella)
    if df_pareto.empty:
        st.info("No se obtuvieron soluciones para el barrido de λ.")
    else:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_pareto["A"], y=df_pareto["B"], mode="lines+markers+text",
            text=df_pareto["lambda"].apply(lambda v: "λ={:.1f}".format(v)),
            textposition="top center",
            marker=dict(size=10, color=df_pareto["lambda"], colorscale="Viridis", showscale=True),
            line=dict(color="gray", width=1), name="No dominadas"))
        fig.update_layout(title="Soluciones no dominadas (A vs B)",
                          xaxis_title="A: recolección + satélite→central (t·min)",
                          yaxis_title="B: central→destinos (t·min)",
                          template="plotly_white", height=400)
        st.plotly_chart(fig, use_container_width=True)

    # --- estabilidad (bajo demanda, cacheada, año seleccionado) ---
    st.markdown("### Estabilidad por nivel de oferta (año {})".format(ano_sel))
    st.markdown("Compara oferta baja/base/alta para el **año seleccionado**, con el mismo "
                "consumo, mezcla, configuración, k y λ.")
    df_estab, faltantes = opt_estabilidad_cache(ano_sel, consumo_sel, mezcla_sel, modo_sel,
                                                k_satelites, lam, int(tiempo_limite_s),
                                                float(gap_relativo), huella)
    st.dataframe(
        df_estab[["escenario", "oferta", "central", "status", "A", "B", "costo_total", "cobertura"]]
        .style.format({"A": "{:,.0f}", "B": "{:,.0f}", "costo_total": "{:,.0f}",
                       "cobertura": "{:.2f}%"}, na_rep="—"),
        use_container_width=True,
    )
    sin_sol = df_estab[~df_estab["status"].isin(["OPTIMAL", "FEASIBLE"])]
    if faltantes or not sin_sol.empty:
        st.warning("Escenarios sin solución o no disponibles: {}".format(
            ", ".join(sorted(set(sin_sol["escenario"]).union(f["escenario"] for f in faltantes)))))
    resueltos = df_estab[df_estab["status"].isin(["OPTIMAL", "FEASIBLE"])]
    if not resueltos.empty:
        if resueltos["central"].nunique() == 1:
            st.success("Ubicación **estable**: la misma central en todos los niveles de oferta resueltos.")
        else:
            st.warning("Ubicación **variable**: la central cambia según el nivel de oferta.")


# =============================================================================
# PANTALLA 4 - TABLERO CENTRAL DE ACOPIO (HTML)
# =============================================================================
def pantalla_tablero_central():
    """Muestra el tablero visual de la central de acopio con sus propios controles."""
    ruta_html = Path(__file__).resolve().parent / "assets" / "tablero_central_acopio_valle.html"

    if not ruta_html.exists():
        st.error("No se encontro el tablero en {}".format(ruta_html))
        return

    try:
        html = generar_html_tablero(ruta_html, produccion)
    except Exception as e:
        st.error("No se pudo cargar el tablero central: {}".format(e))
        return

    st.caption(
        "Vista de cobertura: responde cuánta área y producción alcanza cada sede "
        "con datos históricos (promedio 2021-2023). No reemplaza la pantalla 3, "
        "que minimiza el costo logístico con el pronóstico seleccionado. "
        "El indicador 'recuperable' es una referencia del análisis original y no "
        "se recalcula desde el CSV."
    )
    st.iframe(html, height=1150)


# =============================================================================
# RUTEO DE PANTALLAS
# =============================================================================
if pantalla == "0. Resumen":
    pantalla_resumen()
elif pantalla == "1. Oferta":
    pantalla_oferta()
elif pantalla == "2. Zonas":
    pantalla_zonas()
elif pantalla == "2b. Zonas de acopio":
    pantalla_zonas_acopio()
elif pantalla == "3. Ubicacion":
    pantalla_ubicacion()
elif pantalla == "4. Tablero central":
    pantalla_tablero_central()

# =============================================================================
# PIE DE PAGINA
# =============================================================================
st.markdown("---")
st.markdown("""
**MingaData PI** - Central Inteligente de Acopio y Procesamiento de Productos Agricolas en el Valle del Cauca

Autores: Carlos Guillermo Zuniga Mendez, Ceyni Paola Beltran Hoyos, Samuel Gutierrez Jaramillo, Alejandro Rendon Corral | Proyecto Integrador 1 - 2026-2

Datos: Gobernación del Valle del Cauca, DANE (DIVIPOLA, SIPSA, poblacion), SIPSA, NOAA (ONI), FAOSTAT, OpenStreetMap.
""")
