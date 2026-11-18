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
    st.title("📍 Pantalla 3 - Ubicacion de Central y Acopios Satelite")
    st.markdown("""
    Evalúa ubicaciones candidatas para la central de acopio y su red de satelites,
    considerando el costo de recoleccion y distribucion bajo diferentes escenarios.
    Usa datos reales del modelo de optimización con OR-Tools y el adaptador de Alejandro.
    """)
    st.caption(
        "Esta pantalla minimiza el costo logístico (t·min) con OR-Tools. "
        "La sección '4. Tablero central' maximiza área cubierta; por eso la sede "
        "recomendada puede ser distinta."
    )

    # Cargar datos base (cacheado)
    municipios, destinos, matriz_tiempos = cargar_datos_reales()
    tiempos = construir_matriz_tiempos_dict(matriz_tiempos, municipios, destinos)

    # Filtros: año y escenario (del sidebar global)
    ano_sel = ano_seleccionado
    esc_sel = escenario
    k_satelites = 4
    lam = 0.5

    # Construir id_escenario para el adaptador de Alejandro
    # Formato: {anio}_O{oferta}_C{consumo}_M{pct_nac}{pct_exp}
    esc_map = {"bajo": "Obajo", "base": "Obase", "alto": "Oalto"}
    esc_sel_lower = esc_sel.lower()
    id_escenario = "{}_{}_Cbase_M80_20".format(ano_sel, esc_map.get(esc_sel_lower, "Obase"))

    # Cargar paquete de datos de Alejandro
    try:
        paquete = preparar_para_solver(id_escenario, ano_sel)
    except Exception as e:
        st.error("No se pudo cargar el paquete de datos de Alejandro: {}".format(e))
        st.info("Verifica que hayas corrido: python src/arendonc2/ejecutar_todo.py")
        return

    # Mostrar advertencia de cobertura parcial si aplica
    if paquete.cobertura_parcial:
        st.warning(
            "⚠️ **Cobertura parcial:** {:.2f}% de la oferta tiene consumo FAOSTAT definido. "
            "Productos sin equivalencia (caña, café, flores) quedan excluidos del excedente."
            .format(paquete.cobertura_oferta_pct)
        )

    # Mapear cod_dane -> zona para popups del mapa
    mun_a_zona = dict(zip(paquete.zonas["cod_dane"], paquete.zonas["zona"]))

    # Resolver modelo con datos reales de Alejandro
    res = resolver_ubicacion(
        paquete, municipios, destinos, tiempos,
        k=k_satelites, lam=lam,
        usar_zonas=False,
        usar_flujo=False,
        usar_satelite_central=True,
    )

    if res["status"] not in ("OPTIMAL", "FEASIBLE"):
        st.error("No se pudo resolver el modelo de optimización con los datos actuales.")
        return

    # Obtener nombres de central y satélites
    central_cod = res["central"]
    central_nombre = res["central_nombre"]
    central_zona = res["central_zona"]
    central_lat = municipios[municipios["cod_dane"] == central_cod]["lat"].iloc[0]
    central_lon = municipios[municipios["cod_dane"] == central_cod]["lon"].iloc[0]

    satelites_info = res["satelites"]  # lista de dicts con nombre, zona, es_centro

    # Mapa de ubicación con datos reales
    st.markdown("### Mapa de Ubicacion")
    col1, col2 = st.columns([2, 1])

    with col1:
        centro_mapa = [central_lat, central_lon]
        m = folium.Map(location=centro_mapa, zoom_start=8, tiles="OpenStreetMap")

        # Construir mapa de ofertas desde el paquete de Alejandro
        oferta_mun = {}
        for _, row in paquete.excedente_municipio.iterrows():
            oferta_mun[row["cod_dane"]] = float(row["excedente_t"])

        coord_map = {row["cod_dane"]: (row["lat"], row["lon"]) for _, row in municipios.iterrows()}

        # Agregar todos los municipios como puntos
        for _, row in municipios.iterrows():
            cod = row["cod_dane"]
            nom = row["municipio"]
            lat = row["lat"]
            lon = row["lon"]
            ofe = oferta_mun.get(cod, 0.0)

            es_central = (cod == central_cod)
            es_satelite = cod in [s["cod_dane"] for s in satelites_info]

            if es_central:
                color = "red"
                radius = 12
                popup_txt = "<b>CENTRAL: {}</b> ({})<br>Zona: {}<br>Excedente: {:,.0f} t".format(nom, cod, central_zona, ofe)
            elif es_satelite:
                color = "orange"
                radius = 9
                popup_txt = "<b>SATELITE: {}</b> ({})<br>Zona: {}<br>Excedente: {:,.0f} t".format(nom, cod, mun_a_zona.get(cod, "?"), ofe)
            else:
                color = "blue"
                radius = 5
                popup_txt = "{} ({})<br>Zona: {}<br>Excedente: {:,.0f} t".format(nom, cod, mun_a_zona.get(cod, "?"), ofe)

            folium.CircleMarker(
                location=[lat, lon],
                radius=radius,
                popup=folium.Popup(popup_txt, max_width=200),
                color="black",
                weight=1,
                fill=True,
                fillColor=color,
                fillOpacity=0.8,
            ).add_to(m)

        # Líneas de municipios a sus satélites
        for muni_cod, sat_cod in res["asignaciones_municipio_satelite"]:
            if muni_cod in coord_map and sat_cod in coord_map:
                folium.PolyLine(
                    locations=[coord_map[muni_cod], coord_map[sat_cod]],
                    color="gray",
                    weight=1,
                    opacity=0.3,
                ).add_to(m)

        # Líneas de satélites a central
        for sat_cod, cen_cod in res["asignaciones_satelite_central"]:
            if sat_cod in coord_map and cen_cod in coord_map:
                folium.PolyLine(
                    locations=[coord_map[sat_cod], coord_map[cen_cod]],
                    color="red",
                    weight=2,
                    opacity=0.7,
                ).add_to(m)

        # Destinos
        for _, drow in destinos.iterrows():
            folium.Marker(
                location=[drow["lat"], drow["lon"]],
                popup=folium.Popup("<b>{}</b><br>({})".format(drow["nombre"], drow["id_destino"]), max_width=200),
                icon=folium.Icon(color="blue", icon="info-sign"),
            ).add_to(m)

        st_folium(m, width=700, height=500, key="mapa_ubicacion")

    with col2:
        st.markdown("### Resultado del Modelo")
        st.metric("Central Seleccionada", central_nombre)
        st.metric("Zona de la Central", central_zona)
        st.metric("Código DANE", central_cod)
        st.metric("N° de Satelites", len(satelites_info))

        st.markdown("**Acopios Satelite:**")
        for i, s_info in enumerate(satelites_info):
            st.write("{}. {} (zona {}, {})".format(
                i+1, s_info["nombre"], s_info["zona"],
                "centro de zona" if s_info["es_centro"] else ""
            ))

        st.markdown("---")
        st.markdown("### Costos (toneladas × minutos)")
        st.metric("Costo Recoleccion (Z1)", "{:,.0f}".format(res["costo_recoleccion"]))
        st.metric("Costo Satelite->Central (Z2b)", "{:,.0f}".format(res["costo_satelite_central"]))
        st.metric("Costo Central->Destinos (Z2a)", "{:,.0f}".format(res["costo_central_destinos"]))
        st.metric("Costo Distribucion (Z2)", "{:,.0f}".format(res["costo_distribucion"]))
        st.metric("Costo Total Ponderado", "{:,.0f}".format(res["costo_total"]))

        st.markdown("---")
        st.markdown("**Parametros:**")
        st.write("Año: {}".format(ano_sel))
        st.write("Escenario: {} / {}".format(paquete.escenario_oferta, paquete.escenario_consumo))
        st.write("Mezcla Nacional/Exportacion: {:.0%} / {:.0%}".format(paquete.pct_nacional, paquete.pct_exportacion))
        st.write("k (satelites): {}".format(k_satelites))
        st.write("λ (peso recoleccion): {}".format(lam))
        st.write("Cobertura oferta: {:.2f}%".format(res["cobertura"]))

    st.markdown("---")

    # ===== Frontera de Pareto real (P4: filtrada por no-dominancia) =====
    st.markdown("### Frontera de Pareto")
    st.markdown("""
    Variando el peso (λ) entre el costo de recoleccion y el costo de distribucion,
    se obtiene la frontera de soluciones no dominadas, calculada con OR-Tools sobre
    datos reales de Alejandro (excedentes, zonas, escenarios).
    """)

    df_pareto = calcular_frontera_pareto(
        paquete, municipios, destinos, tiempos,
        k=k_satelites,
        lambdas=[i / 10 for i in range(11)],
        usar_zonas=False,
        usar_flujo=False,
        usar_satelite_central=True,
    )

    fig_pareto = go.Figure()
    fig_pareto.add_trace(go.Scatter(
        x=df_pareto["z1"],
        y=df_pareto["z2"],
        mode="lines+markers+text",
        text=df_pareto["lambda"].apply(lambda x: "λ={:.1f}".format(x)),
        textposition="top center",
        textfont=dict(size=10),
        marker=dict(size=10, color=df_pareto["lambda"], colorscale="Viridis", showscale=True),
        line=dict(color="gray", width=1),
        name="Frontera de Pareto",
    ))
    fig_pareto.update_layout(
        title="Frontera de Pareto: Costo Recoleccion vs Costo Distribucion",
        xaxis_title="Costo de Recoleccion (t·min)",
        yaxis_title="Costo de Distribucion (t·min)",
        template="plotly_white",
        height=400,
    )
    st.plotly_chart(fig_pareto, use_container_width=True)

    # ===== Tabla de Estabilidad real con escenario seleccionado marcado =====
    st.markdown("### Tabla de Estabilidad por Escenario")
    st.markdown("""
    Para cada escenario de oferta (bajo/base/alto), se muestra qué municipio es
    seleccionado como central por el modelo, calculado con datos reales de Alejandro.
    El escenario actualmente seleccionado en el filtro se marca con ✅.
    """)

    df_estab = calcular_estabilidad(
        paquete, municipios, destinos, tiempos,
        k=k_satelites, lam=lam,
        usar_zonas=False,
        usar_flujo=False,
        usar_satelite_central=True,
    )

    # Marcar el escenario seleccionado con un icono
    def marcar_escenario(row):
        if row["escenario"] == id_escenario:
            return "✅ {}".format(row["escenario"])
        return row["escenario"]

    df_estab_display = df_estab.copy()
    df_estab_display["escenario"] = df_estab_display.apply(marcar_escenario, axis=1)
    df_estab_display["central_seleccionada"] = df_estab_display["central"].apply(
        lambda x: "{} ← central actual" if x == "{} ({})".format(central_nombre, central_cod) else x
    )

    st.dataframe(
        df_estab_display[["escenario", "central_seleccionada", "costo_total", "cobertura"]]
        .rename(columns={"central_seleccionada": "central"})
        .style.format({"costo_total": "{:,.0f}", "cobertura": "{:.2f}%"}),
        use_container_width=True,
    )

    # ===== Indicador de estabilidad =====
    st.markdown("---")
    st.markdown("### Indicador de Estabilidad")

    centrales_unicas = df_estab["central"].nunique()

    if centrales_unicas == 1:
        st.success("""
        **Ubicación ESTABLE** — Todos los escenarios (bajo/base/alto) eligen la misma central: **{}**

        Esto significa que la ubicación óptima de la central no depende del nivel de oferta
        asumido; es una ubicación robusta frente a la incertidumbre del pronóstico.
        """.format(central_nombre))
    else:
        st.warning("""
        **Ubicación VARIABLE** — La central elegida cambia entre escenarios.

        Esto indica que la ubicación óptima depende del nivel de oferta asumido, y
        debería considerarse como un riesgo en la decisión de inversión.
        """)

    # ===== Comparación de costos =====
    st.markdown("### Comparación de Costos por Escenario")

    if len(df_estab) == 3:
        col_c1, col_c2, col_c3 = st.columns(3)
        df_estab_sorted = df_estab.sort_values("escenario")
        with col_c1:
            st.metric(
                "Escenario bajo",
                "{:,.0f} t·min".format(df_estab_sorted.iloc[0]["costo_total"]),
                delta=None
            )
        with col_c2:
            c_base = df_estab_sorted.iloc[1]["costo_total"]
            c_bajo = df_estab_sorted.iloc[0]["costo_total"]
            delta_base = c_base - c_bajo
            st.metric(
                "Escenario base",
                "{:,.0f} t·min".format(c_base),
                delta="{:,.0f}".format(delta_base) if delta_base != 0 else None
            )
        with col_c3:
            c_alto = df_estab_sorted.iloc[2]["costo_total"]
            delta_alto = c_alto - c_base
            st.metric(
                "Escenario alto",
                "{:,.0f} t·min".format(c_alto),
                delta="{:,.0f}".format(delta_alto) if delta_alto != 0 else None
            )

        costo_min = df_estab["costo_total"].min()
        costo_max = df_estab["costo_total"].max()
        variacion_pct = ((costo_max - costo_min) / costo_min * 100) if costo_min > 0 else 0
        st.info("""
        **Variación de costos entre escenarios:** {:.1f}% (de {:,.0f} a {:,.0f} t·min)
        """.format(variacion_pct, costo_min, costo_max))


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
