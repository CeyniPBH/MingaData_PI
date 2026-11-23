"""Pruebas de cálculo y comportamiento de la pantalla "0. Resumen".

Verifican que las funciones de src/dashboard/cobertura.py reproducen las cifras del
informe (sin redondear y presentadas por separado), que la exposición sin caña
coincide con el método de src/informe/cifras_3_3_y_3_4.py, y los casos de borde que
pide el manual (Vijes, sede fuera del top 10, sede sin selecciones, denominadores
cero, coherencia entre tarjetas y descarga).

Ejecutar: pytest -q tests/dashboard/test_resumen.py
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "src" / "dashboard"))

import cobertura as cob  # noqa: E402
from utils import (  # noqa: E402
    fmt_pct, fmt_toneladas, fmt_entero, fmt_millones_cop, fmt_razon, fmt_puntos,
)

PROD = pd.read_csv(RAIZ / "data/clean/produccion_valle_clean.csv", dtype={"cod_dane": str})


@pytest.fixture(scope="module")
def modelo():
    muns = cob.cargar_municipios_tablero(PROD)
    return cob.ModeloCobertura(muns)


# --------------------------------------------------------------------------
# Cobertura y ranking de Bugalagrande
# --------------------------------------------------------------------------
def test_total_area(modelo):
    # 71.426 ha en 42 municipios (matriz de trazabilidad)
    assert round(modelo.total_ha) == 71426
    assert len(modelo.muns) == 42


def test_bugalagrande_cobertura(modelo):
    assert modelo.puesto("Bugalagrande") == 1
    assert modelo.pct_area("Bugalagrande") == pytest.approx(0.521, abs=0.001)
    assert round(modelo.area_cubierta("Bugalagrande")) == 37224
    assert modelo.n_municipios("Bugalagrande") == 14


def test_ranking_siguientes(modelo):
    rk = modelo.ranking_area()
    primeros = rk.head(3).set_index("sede")["pct_area"]
    assert primeros["Bugalagrande"] == pytest.approx(0.521, abs=0.001)
    assert primeros["Andalucia"] == pytest.approx(0.516, abs=0.001)
    assert primeros["Zarzal"] == pytest.approx(0.514, abs=0.001)


# --------------------------------------------------------------------------
# Volumen base y escenarios
# --------------------------------------------------------------------------
def test_volumen_base_y_escenarios(modelo):
    ve = cob.volumenes_escenarios(modelo, "Bugalagrande")
    base = ve.loc[ve["escenario"].str.startswith("Base"), "volumen_t"].iloc[0]
    bajo = ve.iloc[0]["volumen_t"]
    alto = ve.iloc[2]["volumen_t"]
    assert round(base) == 86348
    assert round(bajo) == 58211
    assert round(alto) == 112324
    # Utilización respecto al volumen base: 67,4 % bajo, 130,1 % alto
    assert ve.iloc[0]["pct_vs_base"] == pytest.approx(0.674, abs=0.001)
    assert ve.iloc[2]["pct_vs_base"] == pytest.approx(1.301, abs=0.001)


def test_base_define_100pct(modelo):
    ve = cob.volumenes_escenarios(modelo, "Bugalagrande")
    assert ve.loc[ve["escenario"].str.startswith("Base"), "pct_vs_base"].iloc[0] == 1.0


# --------------------------------------------------------------------------
# Razones frente al referente del sur (Vijes)
# --------------------------------------------------------------------------
def test_referente_sur_es_vijes(modelo):
    assert modelo.nombre(modelo.mejor_sede(("Sur",))) == "Vijes"


def test_razones_vs_vijes(modelo):
    buga = modelo.indice("Bugalagrande")
    vijes = modelo.indice("Vijes")
    razon_area = modelo.area_cubierta("Bugalagrande") / modelo.area_cubierta("Vijes")
    razon_vol = modelo.volumen_captable("Bugalagrande") / modelo.volumen_captable("Vijes")
    assert razon_area == pytest.approx(3.05, abs=0.02)   # ~3,0 veces
    assert razon_vol == pytest.approx(1.89, abs=0.02)    # ~1,9 veces, no alcanza el doble
    assert razon_vol < 2.0
    assert round(modelo.volumen_captable("Vijes")) == 45802


# --------------------------------------------------------------------------
# Participación de piña EN TONELADAS y t/ha sin piña
# --------------------------------------------------------------------------
def test_pina_en_toneladas(modelo):
    comp_vijes = cob.composicion_sede(PROD, modelo, "Vijes")
    comp_buga = cob.composicion_sede(PROD, modelo, "Bugalagrande")
    assert comp_vijes["pct_pina_toneladas"] == pytest.approx(0.518, abs=0.003)
    assert comp_buga["pct_pina_toneladas"] == pytest.approx(0.006, abs=0.002)


def test_t_por_ha_sin_pina(modelo):
    comp_vijes = cob.composicion_sede(PROD, modelo, "Vijes")
    comp_buga = cob.composicion_sede(PROD, modelo, "Bugalagrande")
    # 11,2 corresponde a Vijes, 11,6 a Bugalagrande
    assert comp_vijes["t_por_ha_sin_pina"] == pytest.approx(11.2, abs=0.2)
    assert comp_buga["t_por_ha_sin_pina"] == pytest.approx(11.6, abs=0.2)


# --------------------------------------------------------------------------
# Denominador y frecuencias reales de escenarios de optimización
# --------------------------------------------------------------------------
@pytest.fixture(scope="module")
def estabilidad():
    return pd.read_csv(RAIZ / "data/results/opt/estabilidad_escenarios.csv")


def test_frecuencias_optimizacion(estabilidad):
    frec = cob.frecuencia_centrales(estabilidad)
    assert frec["n_total"] == 54
    assert frec["n_resueltos"] == 54      # todos OPTIMAL
    assert frec["n_sin_solucion"] == 0
    assert frec["anios"] == [2024, 2028]
    f = frec["frecuencias"]
    assert f["Bugalagrande"] == 18
    assert f["Riofrío"] == 15
    assert f["Yotoco"] == 12
    assert f["Sevilla"] == 6
    assert f["Andalucia"] == 3
    assert int(f.sum()) == 54


def test_sede_sin_selecciones(estabilidad):
    frec = cob.frecuencia_centrales(estabilidad)
    # Vijes no aparece como central en ningún escenario
    assert int(frec["frecuencias"].get("Vijes", 0)) == 0


# --------------------------------------------------------------------------
# Exposición y anualización (método del informe)
# --------------------------------------------------------------------------
def test_exposicion_sin_cana_equivalencia():
    e = cob.exposicion_sin_cana()
    assert e["sin_modelo_millones"] == pytest.approx(100.08, abs=0.1)
    assert e["modelo_millones"] == pytest.approx(69.69, abs=0.1)
    assert e["reduccion_modelo_pct"] == pytest.approx(-0.304, abs=0.005)
    assert e["reduccion_ingenuo_pct"] == pytest.approx(-0.317, abs=0.01)  # ~32 % ingenuo
    assert e["anios"] == 5


def test_anualizacion_no_coincide_con_acumulado():
    e = cob.exposicion_sin_cana()
    # El acumulado de 5 años × 250 NO da ~1.500 millones; solo el anualizado lo da.
    assert e["valoracion_acumulada_5anios_cop"] / 1e6 == pytest.approx(7598, abs=50)
    assert e["valoracion_anual_cop"] / 1e6 == pytest.approx(1520, abs=30)
    # son claramente distintos
    assert e["valoracion_acumulada_5anios_cop"] > 4 * e["valoracion_anual_cop"]


# --------------------------------------------------------------------------
# Casos de borde: fuera del top 10 y denominadores
# --------------------------------------------------------------------------
def test_sede_fuera_top10(modelo):
    rk = modelo.ranking_area()
    cali = rk[rk["sede"] == "Cali"].iloc[0]
    assert cali["puesto"] > 10


def test_familia_frutales_incluye_platano():
    fr = PROD[PROD["familia"] == "Frutales"]
    assert "Plátano" in set(fr["producto"])
    assert "Piña" in set(fr["producto"])


def test_denominador_cero_no_rompe(modelo):
    # Una sede con composición: si no hubiera municipios cubiertos, no debe lanzar.
    # Forzamos un municipio sin cobertura usando un radio 0: solo él mismo queda cubierto.
    comp = cob.composicion_sede(PROD, modelo, "Buenaventura", radio_km=0)
    assert "pct_pina_toneladas" in comp  # devuelve dict sin romper


# --------------------------------------------------------------------------
# Coherencia entre tarjetas, descarga y formatos
# --------------------------------------------------------------------------
def test_coherencia_titulo_y_tarjetas(modelo):
    titulo = cob.titulo_resumen(modelo, modelo.cod_dane("Bugalagrande"))
    assert "52,1 %" in titulo
    assert "86.348 t" in titulo


def test_formatos_colombianos():
    assert fmt_pct(0.521) == "52,1 %"
    assert fmt_toneladas(86348) == "86.348 t"
    assert fmt_entero(86300) == "86.300"
    assert fmt_millones_cop(1_520_000_000) == "1.520 millones"
    assert fmt_razon(3.05, 1) == "3,0"
    assert fmt_puntos(0.345) == "+34,5 pp"
    assert fmt_pct(None) == "n.d."


def test_descarga_coincide_con_tarjetas(modelo):
    # El CSV de descarga debe reflejar los mismos valores que las tarjetas.
    sede_cod = modelo.cod_dane("Bugalagrande")
    sur_cod = modelo.mejor_sede(("Sur",))
    pct_tarjeta = round(100 * modelo.pct_area(sede_cod), 2)
    vol_tarjeta = round(modelo.volumen_captable(sede_cod))
    razon_tarjeta = round(modelo.volumen_captable(sede_cod) / modelo.volumen_captable(sur_cod), 2)
    assert pct_tarjeta == pytest.approx(52.12, abs=0.05)
    assert vol_tarjeta == 86348
    assert razon_tarjeta == pytest.approx(1.89, abs=0.01)
