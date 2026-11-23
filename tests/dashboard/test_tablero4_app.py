"""Pruebas de comportamiento de los controles de la pantalla 4 en la barra lateral.

Verifican que hay un único juego de controles (en la barra lateral de Streamlit), que la
configuración seleccionada es la que recibe el HTML, que cambiar un filtro conserva los
otros, que la selección persiste al navegar y volver, y que cambiar estos controles no
ejecuta el optimizador.

Ejecutar: pytest -q tests/dashboard/test_tablero4_app.py
"""

import sys
from pathlib import Path
from unittest import mock

import pytest

RAIZ = Path(__file__).resolve().parents[2]
APP = str(RAIZ / "src" / "dashboard" / "app.py")

pytest.importorskip("streamlit.testing.v1")
from streamlit.testing.v1 import AppTest  # noqa: E402


def _ir_a_tablero():
    at = AppTest.from_file(APP, default_timeout=240)
    at.run()
    at.sidebar.radio[0].set_value("4. Tablero central").run()
    return at


def test_controles_unicos_en_sidebar():
    at = _ir_a_tablero()
    assert len(at.exception) == 0
    etiquetas = [s.label for s in at.sidebar.selectbox]
    assert "Municipio sede" in etiquetas
    sliders = [s.label for s in at.sidebar.slider]
    assert "Radio de cobertura (km)" in sliders
    assert "Captación (%)" in sliders
    assert "Capacidad anual de referencia (t/año)" in sliders
    radios = [r.label for r in at.sidebar.radio]
    assert "Escenario de oferta" in radios
    # Default: la sede de mayor cobertura (Bugalagrande)
    sede = [s for s in at.sidebar.selectbox if s.label == "Municipio sede"][0]
    assert sede.value == "Bugalagrande"


def test_cambiar_un_filtro_conserva_los_demas():
    at = _ir_a_tablero()
    cap0 = at.session_state["t4_capacidad"]
    radio0 = at.session_state["t4_radio"]
    capt0 = at.session_state["t4_captacion"]
    esc0 = at.session_state["t4_escenario"]
    # Cambiar sede a Vijes
    sede = [s for s in at.sidebar.selectbox if s.label == "Municipio sede"][0]
    sede.set_value("Vijes").run()
    assert at.session_state["t4_sede"] == "Vijes"
    assert at.session_state["t4_capacidad"] == cap0   # capacidad intacta
    assert at.session_state["t4_radio"] == radio0
    assert at.session_state["t4_captacion"] == capt0
    assert at.session_state["t4_escenario"] == esc0
    # Cambiar escenario NO cambia la capacidad
    esc = [r for r in at.sidebar.radio if r.label == "Escenario de oferta"][0]
    esc.set_value("alto").run()
    assert at.session_state["t4_escenario"] == "alto"
    assert at.session_state["t4_capacidad"] == cap0


def test_persistencia_al_navegar():
    at = _ir_a_tablero()
    sede = [s for s in at.sidebar.selectbox if s.label == "Municipio sede"][0]
    sede.set_value("Vijes").run()
    cap = [s for s in at.sidebar.slider if s.label.startswith("Capacidad")][0]
    cap.set_value(60000).run()
    # Navegar a otra pantalla y volver
    at.sidebar.radio[0].set_value("1. Oferta").run()
    at.sidebar.radio[0].set_value("4. Tablero central").run()
    assert at.session_state["t4_sede"] == "Vijes"
    assert at.session_state["t4_capacidad"] == 60000


def test_config_coincide_con_session_state():
    """La configuración que el HTML recibe se deriva del estado de Streamlit: reconstruimos
    con las mismas funciones públicas y comprobamos que coincide con session_state y que
    la sede se resuelve a su cod_dane (no por posición)."""
    import cobertura as cob
    from tablero_central import construir_config

    at = _ir_a_tablero()
    sede = [s for s in at.sidebar.selectbox if s.label == "Municipio sede"][0]
    sede.set_value("Vijes").run()

    muns = cob.cargar_municipios_tablero(
        __import__("pandas").read_csv(RAIZ / "data/clean/produccion_valle_clean.csv", dtype={"cod_dane": str})
    )
    modelo = cob.ModeloCobertura(muns)
    por_nombre = dict(zip(modelo.ranking_area()["sede"], modelo.ranking_area()["cod_dane"]))
    cfg = construir_config(
        {"muns": muns},
        cod_dane=por_nombre[at.session_state["t4_sede"]],
        radio_km=at.session_state["t4_radio"],
        captacion_pct=at.session_state["t4_captacion"],
        capacidad_t=at.session_state["t4_capacidad"],
        escenario=at.session_state["t4_escenario"],
    )
    assert cfg["cod_dane"] == por_nombre["Vijes"]   # resuelto por DANE, no por índice
    assert cfg["radio_km"] == at.session_state["t4_radio"]
    assert cfg["captacion_pct"] == at.session_state["t4_captacion"]
    assert cfg["capacidad_t"] == at.session_state["t4_capacidad"]
    assert cfg["escenario"] == at.session_state["t4_escenario"]


def test_no_ejecuta_optimizador():
    import importlib
    modelo_real = importlib.import_module("optimizacion.modelo_real")
    with mock.patch.object(modelo_real, "resolver_ubicacion") as m_res, \
         mock.patch.object(modelo_real, "calcular_estabilidad") as m_est:
        at = AppTest.from_file(APP, default_timeout=240)
        at.run()
        at.sidebar.radio[0].set_value("4. Tablero central").run()
        sede = [s for s in at.sidebar.selectbox if s.label == "Municipio sede"][0]
        sede.set_value("Vijes").run()
        assert len(at.exception) == 0
        m_res.assert_not_called()
        m_est.assert_not_called()
