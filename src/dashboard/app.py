"""
Tablero interactivo con mapas - MingaData_PI
Autor: Samuel Gutierrez Jaramillo
Fecha: 17-21 nov 2026

Pantallas:
1. Oferta: selector producto/municipio, serie historica y pronostico bajo/base/alto
2. Zonas: mapa con municipios y oferta por producto/anio
3. Ubicacion: selector de escenario, mapa central+satelites, frontera de Pareto, tabla de estabilidad

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
    obtener_productos_disponibles,
    obtener_municipios_por_producto,
    obtener_serie_historica,
    obtener_pronostico_municipio,
)

from optimizacion.modelo_real import (
    cargar_datos_reales,
    construir_matriz_tiempos_dict,
    obtener_oferta_por_municipio,
    resolver_ubicacion,
    calcular_frontera_pareto,
    calcular_estabilidad,
)

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
    ["1. Oferta", "2. Zonas", "3. Ubicacion"],
    index=0,
)

st.sidebar.markdown("---")
st.sidebar.markdown("### Filtros globales")

anos_disponibles = sorted(oferta["año"].unique()) if not oferta.empty else [2024]
ano_seleccionado = st.sidebar.selectbox("Anio de pronostico:", anos_disponibles, index=0)

escenario = st.sidebar.selectbox("Escenario de oferta:", ["base", "bajo", "alto"], index=0)

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
# PANTALLA 3: UBICACION
# =============================================================================
def pantalla_ubicacion():
    st.title("📍 Pantalla 3 - Ubicacion de Central y Acopios Satelite")
    st.markdown("""
    Evalúa ubicaciones candidatas para la central de acopio y su red de satelites,
    considerando el costo de recoleccion y distribucion bajo diferentes escenarios.
    Usa datos reales del modelo de optimización con OR-Tools.
    """)

    # Cargar datos reales (cacheado)
    municipios, destinos, matriz_tiempos, oferta = cargar_datos_reales()
    tiempos = construir_matriz_tiempos_dict(matriz_tiempos, municipios, destinos)

    # Filtros: año y escenario (del sidebar global)
    ano_sel = ano_seleccionado
    esc_sel = escenario
    k_satelites = 4
    lam = 0.5

    # Resolver modelo con datos reales
    oferta_mun = obtener_oferta_por_municipio(oferta, ano=ano_sel, escenario=esc_sel)
    res = resolver_ubicacion(
        municipios, destinos, tiempos, oferta_mun,
        k=k_satelites, lam=lam, pct_nac=0.8, pct_exp=0.2
    )

    if res["status"] not in ("OPTIMAL", "FEASIBLE"):
        st.error("No se pudo resolver el modelo de optimización con los datos actuales.")
        return

    # Obtener nombres de central y satélites
    central_cod = res["central"]
    central_row = municipios[municipios["cod_dane"] == central_cod]
    central_nombre = central_row["municipio"].iloc[0] if not central_row.empty else central_cod
    central_lat = central_row["lat"].iloc[0] if not central_row.empty else 4.2
    central_lon = central_row["lon"].iloc[0] if not central_row.empty else -76.2

    satelites_cods = res["satelites"]
    satelites_info = []
    for s in satelites_cods:
        s_row = municipios[municipios["cod_dane"] == s]
        if not s_row.empty:
            satelites_info.append({
                "cod": s,
                "nombre": s_row["municipio"].iloc[0],
                "lat": s_row["lat"].iloc[0],
                "lon": s_row["lon"].iloc[0],
            })

    # Mapa de ubicación con datos reales
    st.markdown("### Mapa de Ubicacion")
    col1, col2 = st.columns([2, 1])

    with col1:
        centro_mapa = [central_lat, central_lon]
        m = folium.Map(location=centro_mapa, zoom_start=8, tiles="OpenStreetMap")

        # Agregar todos los municipios como puntos
        for _, row in municipios.iterrows():
            cod = row["cod_dane"]
            nom = row["municipio"]
            lat = row["lat"]
            lon = row["lon"]
            ofe = oferta_mun.get(cod, 0.0)

            es_central = (cod == central_cod)
            es_satelite = cod in satelites_cods

            if es_central:
                color = "red"
                radius = 12
                popup_txt = "<b>CENTRAL: {}</b> ({})<br>Oferta: {:,.0f} t".format(nom, cod, ofe)
            elif es_satelite:
                color = "orange"
                radius = 9
                popup_txt = "<b>SATELITE: {}</b> ({})<br>Oferta: {:,.0f} t".format(nom, cod, ofe)
            else:
                color = "blue"
                radius = 5
                popup_txt = "{} ({})<br>Oferta: {:,.0f} t".format(nom, cod, ofe)

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

        # Líneas de municipios a sus satélites (asignaciones del modelo)
        coord_map = {row["cod_dane"]: (row["lat"], row["lon"]) for _, row in municipios.iterrows()}
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
        st.metric("Codigo DANE", central_cod)
        st.metric("N° de Satelites", len(satelites_cods))

        st.markdown("**Acopios Satelite:**")
        for i, s_info in enumerate(satelites_info):
            st.write("{}. {} ({})".format(i+1, s_info["nombre"], s_info["cod"]))

        st.markdown("---")
        st.markdown("### Costos (toneladas × minutos)")
        st.metric("Costo Recoleccion", "{:,.0f}".format(res["costo_recoleccion"]))
        st.metric("Costo Distribucion", "{:,.0f}".format(res["costo_distribucion"]))
        st.metric("Costo Total Ponderado", "{:,.0f}".format(res["costo_total"]))

        st.markdown("---")
        st.markdown("**Parametros:**")
        st.write("Año: {}".format(ano_sel))
        st.write("Escenario: {}".format(esc_sel))
        st.write("k (satelites): {}".format(k_satelites))
        st.write("λ (peso recoleccion): {}".format(lam))

    st.markdown("---")

    # ===== Calcular costos para los 3 escenarios =====
    costos_escenarios = {}
    for esc in ["bajo", "base", "alto"]:
        oferta_esc = obtener_oferta_por_municipio(oferta, ano=ano_sel, escenario=esc)
        res_esc = resolver_ubicacion(
            municipios, destinos, tiempos, oferta_esc,
            k=k_satelites, lam=lam, pct_nac=0.8, pct_exp=0.2
        )
        if res_esc["status"] in ("OPTIMAL", "FEASIBLE"):
            costos_escenarios[esc] = res_esc["costo_total"]

    # ===== Frontera de Pareto real =====
    st.markdown("### Frontera de Pareto")
    st.markdown("""
    Variando el peso (λ) entre el costo de recoleccion y el costo de distribucion,
    se obtiene la frontera de soluciones no dominadas, calculada con OR-Tools sobre
    datos reales de oferta y tiempos de viaje.
    """)

    df_pareto = calcular_frontera_pareto(
        municipios, destinos, tiempos, oferta_mun,
        k=k_satelites,
        lambdas=[i / 10 for i in range(11)],
        pct_nac=0.8, pct_exp=0.2
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
    seleccionado como central por el modelo, calculado con datos reales.
    El escenario actualmente seleccionado en el filtro se marca con ✅.
    """)

    df_estab = calcular_estabilidad(
        municipios, destinos, tiempos, oferta,
        k=k_satelites, lam=lam, anos=[ano_sel],
        escenarios=["bajo", "base", "alto"]
    )

    # Marcar el escenario seleccionado con un icono
    def marcar_escenario(row):
        if row["escenario"] == esc_sel:
            return "✅ {}".format(row["escenario"])
        return row["escenario"]

    df_estab_display = df_estab.copy()
    df_estab_display["escenario"] = df_estab_display.apply(marcar_escenario, axis=1)
    df_estab_display["central_seleccionada"] = df_estab_display["central"].apply(
        lambda x: "{} ← central actual" if x == "{} ({})".format(central_nombre, central_cod) else x
    )

    st.dataframe(
        df_estab_display[["escenario", "central_seleccionada", "costo_total"]]
        .rename(columns={"central_seleccionada": "central"})
        .style.format({"costo_total": "{:,.0f}"}),
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

    if len(costos_escenarios) == 3:
        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            st.metric(
                "Escenario bajo",
                "{:,.0f} t·min".format(costos_escenarios.get("bajo", 0)),
                delta=None
            )
        with col_c2:
            delta_base = costos_escenarios.get("base", 0) - costos_escenarios.get("bajo", 0)
            st.metric(
                "Escenario base",
                "{:,.0f} t·min".format(costos_escenarios.get("base", 0)),
                delta="{:,.0f}".format(delta_base) if delta_base != 0 else None
            )
        with col_c3:
            delta_alto = costos_escenarios.get("alto", 0) - costos_escenarios.get("base", 0)
            st.metric(
                "Escenario alto",
                "{:,.0f} t·min".format(costos_escenarios.get("alto", 0)),
                delta="{:,.0f}".format(delta_alto) if delta_alto != 0 else None
            )

        # Rango de variación
        costo_min = min(costos_escenarios.values())
        costo_max = max(costos_escenarios.values())
        variacion_pct = ((costo_max - costo_min) / costo_min * 100) if costo_min > 0 else 0
        st.info("""
        **Variación de costos entre escenarios:** {:.1f}% (de {:,.0f} a {:,.0f} t·min)
        """.format(variacion_pct, costo_min, costo_max))


# =============================================================================
# RUTEO DE PANTALLAS
# =============================================================================
if pantalla == "1. Oferta":
    pantalla_oferta()
elif pantalla == "2. Zonas":
    pantalla_zonas()
elif pantalla == "3. Ubicacion":
    pantalla_ubicacion()

# =============================================================================
# PIE DE PAGINA
# =============================================================================
st.markdown("---")
st.markdown("""
**MingaData PI** - Central Inteligente de Acopio y Procesamiento de Productos Agricolas en el Valle del Cauca

Autores: Carlos Guillermo Zuniga Mendez, Ceyni Paola Beltran Hoyos, Samuel Gutierrez Jaramillo, Alejandro Rendon Corral | Proyecto Integrador 1 - 2026-2

Datos: Gobernación del Valle del Cauca, DANE (DIVIPOLA, SIPSA, poblacion), SIPSA, NOAA (ONI), FAOSTAT, OpenStreetMap.
""")
