"""Pruebas de comportamiento de la pantalla 3 (Ubicación) tras el rediseño de UX.

Verifican que los parámetros técnicos del solver no están en la interfaz, que los
controles de negocio viven en la barra lateral con sus valores iniciales, que cambiar
un control no dispara el cálculo, que la configuración obsoleta no se atribuye a un
resultado nuevo, y que la prioridad conserva su significado. No se cambian fórmulas.

Ejecutar: pytest -q tests/dashboard/test_ubicacion_app.py
"""

import sys
from pathlib import Path
from unittest import mock

import pytest

RAIZ = Path(__file__).resolve().parents[2]
APP = str(RAIZ / "src" / "dashboard" / "app.py")
sys.path.insert(0, str(RAIZ / "src" / "dashboard"))

pytest.importorskip("streamlit.testing.v1")
from streamlit.testing.v1 import AppTest  # noqa: E402


def _ir():
    at = AppTest.from_file(APP, default_timeout=120)
    at.run()
    at.sidebar.radio[0].set_value("3. Ubicacion").run()
    return at


def test_sin_controles_tecnicos_del_solver():
    at = _ir()
    assert len(at.exception) == 0
    etiquetas = " ".join(
        [s.label for s in at.sidebar.selectbox] + [s.label for s in at.sidebar.slider] +
        [s.label for s in at.sidebar.select_slider] + [r.label for r in at.sidebar.radio] +
        [m.value for m in at.markdown]
    ).lower()
    for prohibido in ["límite de tiempo", "brecha", "solver", "tolerancia", "motor", "gap", "lambda", "λ"]:
        assert prohibido not in etiquetas, "aparece control/term técnico: {}".format(prohibido)
    # No existe sección 'Parámetros del solver'
    assert not any("parámetros del solver" in m.value.lower() for m in at.markdown)


def test_controles_negocio_y_defaults():
    at = _ir()
    labels_sel = [s.label for s in at.sidebar.selectbox]
    assert "Año del análisis" in labels_sel
    assert "Escenario de producción" in labels_sel
    assert "Escenario de consumo local" in labels_sel
    assert "Distribución entre mercado nacional y exportación" in labels_sel
    assert "Organización de los acopios" in [r.label for r in at.sidebar.radio]
    assert "Prioridad del transporte" in [s.label for s in at.sidebar.select_slider]
    # Valores iniciales conservados
    assert at.session_state["opt_oferta"] == "base"
    assert at.session_state["opt_consumo"] == "base"
    assert at.session_state["opt_mezcla"] == "80_20"
    assert at.session_state["opt_modo"] == "libre"
    assert at.session_state["opt_k_libre"] == 5
    assert at.session_state["opt_lambda"] == 0.5


def test_numero_acopios_solo_en_libre():
    at = _ir()
    assert "Número de acopios" in [s.label for s in at.sidebar.slider]
    modo = [r for r in at.sidebar.radio if r.label == "Organización de los acopios"][0]
    modo.set_value("zonas").run()
    assert "Número de acopios" not in [s.label for s in at.sidebar.slider]


def test_cambiar_control_no_ejecuta_optimizador():
    import importlib
    modelo_real = importlib.import_module("optimizacion.modelo_real")
    with mock.patch.object(modelo_real, "resolver_ubicacion") as m_res:
        at = AppTest.from_file(APP, default_timeout=120)
        at.run()
        at.sidebar.radio[0].set_value("3. Ubicacion").run()
        sel = [s for s in at.sidebar.selectbox if s.label == "Escenario de producción"][0]
        sel.set_value("alto").run()
        assert len(at.exception) == 0
        m_res.assert_not_called()  # sin pulsar "Calcular ubicación" no se resuelve


def test_prioridad_conserva_significado():
    """El select_slider ofrece el rango/paso/valor inicial actuales (0..1 paso 0,1, 0,5) y
    el valor que recibe el modelo (lam) no se invierte: el objetivo sigue siendo λ·A+(1−λ)·B,
    con λ=1 priorizando A (recolección y traslado a la central) y λ=0 priorizando destinos."""
    at = _ir()
    sl = [s for s in at.sidebar.select_slider if s.label == "Prioridad del transporte"][0]
    assert at.session_state["opt_lambda"] == 0.5
    # Mover a cada extremo y comprobar que el estado guarda el valor sin invertir.
    sl.set_value(1.0).run()
    assert at.session_state["opt_lambda"] == 1.0
    sl.set_value(0.0).run()
    assert at.session_state["opt_lambda"] == 0.0


def test_estados_en_lenguaje_claro_definidos():
    """Las traducciones de estado a lenguaje claro existen y no alteran el significado.
    (El flujo de INFEASIBLE/sin solución/error retorna antes de mostrar central o métricas;
    ver _pantalla_ubicacion_impl.)"""
    from app import _ESTADO_TITULO, _ESTADO_AYUDA
    assert _ESTADO_TITULO["OPTIMAL"] == "Solución óptima del modelo"
    assert _ESTADO_TITULO["FEASIBLE"] == "Solución válida; podría existir una mejor"
    assert "No existe una solución" in _ESTADO_TITULO["INFEASIBLE"]
    assert "óptima" in _ESTADO_AYUDA["OPTIMAL"]


def test_config_obsoleta_no_se_atribuye(monkeypatch):
    at = _ir()
    btn = [b for b in at.button if b.label == "Calcular ubicación"][0]
    btn.click().run()
    assert len(at.exception) == 0
    # Hay un resultado (central en un H2)
    assert any(m.value.startswith("## ") for m in at.markdown)
    # Cambiar un control: debe pedir recálculo y no mostrar central nueva
    sel = [s for s in at.sidebar.selectbox if s.label == "Escenario de producción"][0]
    sel.set_value("alto").run()
    assert any("La configuración cambió" in w.value for w in at.warning)
    assert not any(m.value.startswith("## ") for m in at.markdown)
