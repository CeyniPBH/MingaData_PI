"""Pruebas de comportamiento de la pantalla "0. Resumen" con Streamlit AppTest.

Comprueban que el resumen responde la pregunta sin tocar controles, que cambiar la
sede no ejecuta el optimizador (no hay llamadas al solver en el camino del resumen),
que funciona aunque la API no responda y que conserva navegación y controles.

Ejecutar: pytest -q tests/dashboard/test_resumen_app.py
"""

import sys
from pathlib import Path
from unittest import mock

import pytest

RAIZ = Path(__file__).resolve().parents[2]
APP = str(RAIZ / "src" / "dashboard" / "app.py")

pytest.importorskip("streamlit.testing.v1")
from streamlit.testing.v1 import AppTest  # noqa: E402


TITULO_FIJO = "Selección de municipios y estimación de volumen para una central de acopio"


def _run():
    at = AppTest.from_file(APP, default_timeout=240)
    at.run()
    return at


def _hallazgo(at):
    """Línea secundaria con el hallazgo dinámico de la sede (encabezado ######)."""
    for m in at.markdown:
        if m.value.startswith("###### ") and "cubre" in m.value:
            return m.value
    return ""


def test_resumen_inicial_responde_sin_tocar_controles():
    at = _run()
    assert len(at.exception) == 0
    # El título principal es fijo y orientado al propósito.
    assert at.title[0].value == TITULO_FIJO
    # La sede por defecto no debe reemplazar el titulo principal.
    hallazgo = _hallazgo(at)
    assert "Bugalagrande" in hallazgo
    assert "52,1 %" in hallazgo
    etiquetas = [m.label for m in at.metric]
    assert any("Área cubierta a 40 km" in e for e in etiquetas)
    assert any("Puesto entre los 42 municipios" in e for e in etiquetas)
    assert any("Volumen anual captable" in e for e in etiquetas)
    assert any("Razón de volumen" in e for e in etiquetas)


def test_cambiar_sede_no_ejecuta_optimizador():
    # resolver_ubicacion / calcular_estabilidad no deben invocarse al pintar el resumen
    import importlib
    modelo_real = importlib.import_module("optimizacion.modelo_real")
    with mock.patch.object(modelo_real, "resolver_ubicacion") as m_res, \
         mock.patch.object(modelo_real, "calcular_estabilidad") as m_est, \
         mock.patch.object(modelo_real, "calcular_frontera_pareto") as m_par:
        at = AppTest.from_file(APP, default_timeout=240)
        at.run()
        sb = [s for s in at.sidebar.selectbox if s.label.startswith("Sede del resumen")]
        assert sb, "No se encontró el filtro de sede del resumen"
        sb[0].set_value("Vijes").run()
        assert len(at.exception) == 0
        assert at.title[0].value == TITULO_FIJO
        assert "Vijes" in _hallazgo(at)
        m_res.assert_not_called()
        m_est.assert_not_called()
        m_par.assert_not_called()


def test_resumen_funciona_si_falla_la_api():
    import importlib
    app_mod_name = "app"
    with mock.patch("requests.get", side_effect=OSError("API caída")), \
         mock.patch("requests.post", side_effect=OSError("API caída")):
        at = AppTest.from_file(APP, default_timeout=240)
        at.run()
        # El resumen sigue respondiendo la pregunta pese a la API inaccesible
        assert len(at.exception) == 0
        assert at.title[0].value == TITULO_FIJO
        assert "cubre" in _hallazgo(at)


def test_navegacion_conserva_pantallas():
    at = _run()
    radios = [r for r in at.sidebar.radio]
    assert radios, "No hay radio de navegación"
    opciones = radios[0].options
    for esperado in ["0. Resumen", "1. Oferta", "2. Zonas", "2b. Zonas de acopio",
                     "3. Ubicacion", "4. Cobertura y capacidad"]:
        assert esperado in opciones


def test_sede_fuera_top10_y_sin_selecciones():
    at = AppTest.from_file(APP, default_timeout=240)
    at.run()
    sb = [s for s in at.sidebar.selectbox if s.label.startswith("Sede del resumen")][0]
    sb.set_value("Cali").run()
    assert len(at.exception) == 0
    assert "Cali" in _hallazgo(at)
    # Vijes: sin selecciones en el optimizador; la respuesta no debe heredar otra sede
    sb.set_value("Vijes").run()
    assert len(at.exception) == 0
    textos = " ".join(i.value for i in at.info)
    assert "Vijes" in textos
