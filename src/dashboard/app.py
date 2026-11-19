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
from pathlib import Path

# Agregar src/ al path para importar modulos de optimizacion
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium

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
    obtener_productos_disponibles,
    obtener_municipios_por_producto,
    obtener_serie_historica,
    obtener_pronostico_municipio,
)

from tablero_central import generar_html_tablero

from optimizacion.modelo_real import (
    cargar_datos_reales,
    construir_matriz_tiempos_dict,
    resolver_ubicacion,
    calcular_frontera_pareto,
    calcular_estabilidad,
    comparar_configuraciones,
)

# Agregar src/ al path para importar el adaptador de Alejandro
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "arendonc2"))
from adaptador import preparar_para_solver, listar_escenarios

# =============================================================================
# CONFIGURACION DE LA PAGINA
# =============================================================================
st.set_page_config(
    page_title="MingaData - Central de Acopio Valle del Cauca",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

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
# SIDEBAR - NAVEGACION
# =============================================================================
st.sidebar.title("🌱 MingaData")
st.sidebar.markdown("**Central de Acopio y Procesamiento**")
st.sidebar.markdown("Valle del Cauca - Proyecto Integrador 1")

pantalla = st.sidebar.radio(
    "Seleccionar pantalla:",
    ["1. Oferta", "2. Zonas", "2b. Zonas de acopio", "3. Ubicacion", "4. Tablero central"],
    index=4,
)

anos_disponibles = sorted(oferta["año"].unique()) if not oferta.empty else [2024]

if pantalla != "4. Tablero central":
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Filtros globales")
    ano_seleccionado = st.sidebar.selectbox("Anio de pronostico:", anos_disponibles, index=0)
    escenario = st.sidebar.selectbox("Escenario de oferta:", ["base", "bajo", "alto"], index=0)
else:
    st.sidebar.markdown("---")
    st.sidebar.caption("Vista histórica 2021-2023. No usa los filtros de pronóstico.")
    ano_seleccionado = anos_disponibles[0]
    escenario = "base"

st.sidebar.markdown("---")
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
    st.title("🗺️ Pantalla 2 - Zonas de Acopio")
    st.markdown("""
    Mapa de los municipios del Valle del Cauca con su oferta pronosticada por producto y año.

    **Nota:** El agrupamiento en zonas de acopio (`zonas.csv`) depende de la tarea de Alejandro.
    Mientras tanto, se muestran los municipios individuales coloreados por su oferta base.
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
# PANTALLA 2b: ZONAS DE ACOPIO (Alejandro - tareas #2, #3, #4)
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
    st.title("🧭 Pantalla 2b - Zonas de Acopio (vecindad + agrupamiento espacial)")
    st.markdown("""
    Zonas de acopio espacialmente conexas (contigüidad Queen + Ward con restricción
    de conectividad). Los **centros de zona son referencias** (tiempos ponderados por
    oferta), no la ubicación óptima del modelo de optimización de Samuel.
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
    acopios satélite, usando los excedentes proyectados del adaptador de Alejandro y
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
        gap_relativo = cs1.number_input("Brecha relativa objetivo (0 = óptimo certificado):",
                                        min_value=0.0, max_value=0.2, value=0.0, step=0.005,
                                        format="%.3f", key="opt_gap")
        tiempo_limite_s = cs2.number_input("Límite de tiempo por solve (s):",
                                           min_value=10, max_value=600, value=120, step=10,
                                           key="opt_tlim")
        st.caption("El límite de tiempo NO se reduce por defecto para aparentar velocidad. "
                   "Con brecha > 0, la solución puede ser factible y no certificada óptima.")

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
if pantalla == "1. Oferta":
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
