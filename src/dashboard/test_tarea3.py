"""
Script de prueba automatizada para verificar que la Tarea 3 (Tablero Streamlit)
está completa al 100%.

Ejecuta: python src/dashboard/test_tarea3.py
"""

import os
import sys
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "dashboard"))

ERRORES = []
EXITOS = []


def check(condicion, mensaje):
    if condicion:
        EXITOS.append("  [OK] {}".format(mensaje))
    else:
        ERRORES.append("  [FAIL] {}".format(mensaje))


def main():
    print("=" * 70)
    print("VERIFICACION TAREA 3: Tablero con mapas (Streamlit)")
    print("=" * 70)
    print()

    # =========================================================================
    # 1. Verificar que existen los archivos del tablero
    # =========================================================================
    print("--- 1. Archivos del tablero ---")
    path_app = ROOT / "src" / "dashboard" / "app.py"
    path_utils = ROOT / "src" / "dashboard" / "utils.py"
    check(path_app.exists(), "src/dashboard/app.py existe")
    check(path_utils.exists(), "src/dashboard/utils.py existe")

    # =========================================================================
    # 2. Verificar requirements.txt tiene las dependencias
    # =========================================================================
    print("\n--- 2. Dependencias en requirements.txt ---")
    path_req = ROOT / "requirements.txt"
    if path_req.exists():
        req_contenido = path_req.read_text(encoding="utf-8")
        check("streamlit" in req_contenido, "streamlit en requirements.txt")
        check("folium" in req_contenido, "folium en requirements.txt")
        check("streamlit-folium" in req_contenido, "streamlit-folium en requirements.txt")
        check("plotly" in req_contenido, "plotly en requirements.txt")
    else:
        check(False, "requirements.txt no existe")

    # =========================================================================
    # 3. Verificar que el módulo app se puede importar
    # =========================================================================
    print("\n--- 3. Importacion del modulo app ---")
    try:
        spec = importlib.util.spec_from_file_location("app", path_app)
        # No ejecutamos el módulo completo porque llama a st.set_page_config
        # Solo verificamos que el archivo se puede compilar
        compile(path_app.read_text(encoding="utf-8"), str(path_app), "exec")
        check(True, "app.py compila sin errores de sintaxis")
    except Exception as e:
        check(False, "Error al compilar app.py: {}".format(e))

    # =========================================================================
    # 4. Verificar que utils se puede importar y cargar datos
    # =========================================================================
    print("\n--- 4. Carga de datos ---")
    try:
        sys.path.insert(0, str(ROOT / "src" / "dashboard"))
        from utils import (
            cargar_oferta_escenarios,
            cargar_municipios_coordenadas,
            cargar_produccion_limpia,
            cargar_destinos_coordenadas,
            obtener_productos_disponibles,
            obtener_municipios_por_producto,
            obtener_serie_historica,
            obtener_pronostico_municipio,
        )

        oferta = cargar_oferta_escenarios()
        municipios = cargar_municipios_coordenadas()
        produccion = cargar_produccion_limpia()
        destinos = cargar_destinos_coordenadas()

        check(not oferta.empty, "oferta_escenarios.csv carga correctamente ({} filas)".format(len(oferta)))
        check(not municipios.empty, "municipios_coordenadas.csv carga correctamente ({} municipios)".format(len(municipios)))
        check(not produccion.empty, "produccion_valle_clean.csv carga correctamente ({} filas)".format(len(produccion)))
        check(not destinos.empty, "destinos_coordenadas.csv carga correctamente ({} destinos)".format(len(destinos)))

        check(oferta["producto"].nunique() >= 10, "Hay al menos 10 productos en oferta ({})".format(oferta["producto"].nunique()))
        check(municipios["cod_dane"].nunique() == 42, "Hay 42 municipios con coordenadas")
        check(set(oferta["año"].unique()) == {2024, 2025, 2026, 2027, 2028}, "Horizonte de pronóstico 2024-2028")

        # Verificar columnas de oferta
        cols_esperadas = {"producto", "cod_dane", "año", "oferta_bajo", "oferta_base", "oferta_alto"}
        check(cols_esperadas.issubset(set(oferta.columns)), "oferta_escenarios.csv tiene columnas: producto, cod_dane, año, oferta_bajo/base/alto")

        # Verificar que bajo <= base <= alto
        if not oferta.empty:
            valido = ((oferta["oferta_bajo"] <= oferta["oferta_base"]) & (oferta["oferta_base"] <= oferta["oferta_alto"])).all()
            check(valido, "Todas las filas cumplen bajo <= base <= alto")

    except Exception as e:
        check(False, "Error al cargar datos: {}".format(e))

    # =========================================================================
    # 5. Verificar funciones de utilidad
    # =========================================================================
    print("\n--- 5. Funciones de utilidad ---")
    try:
        productos = obtener_productos_disponibles(oferta)
        check(len(productos) > 0, "obtener_productos_disponibles devuelve {} productos".format(len(productos)))

        mun = obtener_municipios_por_producto(oferta, productos[0], 2024)
        check(not mun.empty, "obtener_municipios_por_producto devuelve municipios para {}".format(productos[0]))

        ser = obtener_serie_historica(produccion, productos[0], mun["cod_dane"].iloc[0])
        check(not ser.empty, "obtener_serie_historica devuelve serie para {}-{}".format(productos[0], mun["cod_dane"].iloc[0]))

        pron = obtener_pronostico_municipio(oferta, productos[0], mun["cod_dane"].iloc[0])
        check(not pron.empty, "obtener_pronostico_municipio devuelve pronostico para {}-{}".format(productos[0], mun["cod_dane"].iloc[0]))
        check(len(pron) == 5, "Pronostico tiene 5 filas (2024-2028)")

    except Exception as e:
        check(False, "Error en funciones de utilidad: {}".format(e))

    # =========================================================================
    # 6. Verificar funciones de mapa (folium)
    # =========================================================================
    print("\n--- 6. Funciones de mapa (folium) ---")
    try:
        import folium
        from streamlit_folium import st_folium  # noqa: F401

        m = folium.Map(location=[4.2, -76.2], zoom_start=8)
        check(True, "folium.Map se crea correctamente")

        folium.Marker(
            location=[4.2, -76.2],
            popup="Prueba",
        ).add_to(m)
        check(True, "folium.Marker se agrega correctamente")

        folium.CircleMarker(
            location=[4.2, -76.2],
            radius=5,
            popup="Prueba",
        ).add_to(m)
        check(True, "folium.CircleMarker se agrega correctamente")

        folium.PolyLine(
            locations=[[4.2, -76.2], [3.8, -77.0]],
            color="red",
        ).add_to(m)
        check(True, "folium.PolyLine se agrega correctamente")

    except Exception as e:
        check(False, "Error en funciones de mapa: {}".format(e))

    # =========================================================================
    # 7. Verificar plotly para graficos
    # =========================================================================
    print("\n--- 7. Graficos con plotly ---")
    try:
        import plotly.graph_objects as go

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[1, 2, 3], y=[4, 5, 6], name="Prueba"))
        fig.update_layout(title="Test", xaxis_title="X", yaxis_title="Y")
        check(True, "plotly.graph_objects funciona correctamente")
    except Exception as e:
        check(False, "Error en plotly: {}".format(e))

    # =========================================================================
    # 8. Verificar que las 3 pantallas estén definidas
    # =========================================================================
    print("\n--- 8. Definicion de pantallas ---")
    app_code = path_app.read_text(encoding="utf-8")
    check("def pantalla_oferta()" in app_code, "Funcion pantalla_oferta() definida")
    check("def pantalla_zonas()" in app_code, "Funcion pantalla_zonas() definida")
    check("def pantalla_ubicacion()" in app_code, "Funcion pantalla_ubicacion() definida")
    check("Pantalla 1 - Oferta" in app_code, "Pantalla 1: Oferta por Producto y Municipio")
    check("Pantalla 2 - Zonas" in app_code, "Pantalla 2: Zonas de Acopio")
    check("Pantalla 3 - Ubicacion" in app_code, "Pantalla 3: Ubicacion de Central y Acopios Satelite")

    # =========================================================================
    # RESUMEN
    # =========================================================================
    print("\n" + "=" * 70)
    print("RESUMEN DE VERIFICACION")
    print("=" * 70)
    print("[OK] Exitos: {}".format(len(EXITOS)))
    print("[FAIL] Errores: {}".format(len(ERRORES)))
    print()

    if ERRORES:
        print("ERRORES ENCONTRADOS:")
        for e in ERRORES:
            print(e)
        print()
        print("LA TAREA 3 NO ESTA COMPLETA AL 100%. Corrige los errores arriba.")
        return 1
    else:
        print("TODAS LAS VERIFICACIONES PASARON.")
        print("La Tarea 3 está completa al 100% y lista para entregar.")
        print()
        print("Para ejecutar el tablero: streamlit run src/dashboard/app.py")
        return 0


if __name__ == "__main__":
    sys.exit(main())