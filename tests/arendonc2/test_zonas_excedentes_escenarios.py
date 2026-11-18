"""
Pruebas de las tareas #2 (zonas), #3 (excedentes), #4 (escenarios) y del
adaptador de integración con Samuel.

Validan las propiedades exigidas en el alcance:
  - 42 municipios asignados una vez; cada zona conexa.
  - Sin duplicados en las claves de resultados.
  - Repartos de consumo no duplican categorías (cuotas suman 1).
  - Consumos desconocidos permanecen identificados (no sustituidos por 0 silencioso).
  - Excedentes no negativos; totales municipales == zonales.
  - 27 combinaciones por año; nacional+exportación conservan el total.
  - El adaptador selecciona exactamente el año solicitado.
  - La cobertura parcial aparece en los archivos.

Ejecutar: python -m pytest tests/arendonc2 -q
(los resultados deben existir: correr antes src/arendonc2/ejecutar_todo.py)
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from arendonc2 import common  # noqa: E402

RES = common.DATA_RES
OUT = common.DATA_RES_OUT

requiere_resultados = pytest.mark.skipif(
    not (RES / "zonas.csv").exists()
    or not (RES / "excedentes.csv").exists()
    or not (RES / "escenarios.csv").exists(),
    reason="Faltan resultados; correr src/arendonc2/ejecutar_todo.py primero.",
)


@pytest.fixture(scope="module")
def zonas():
    return pd.read_csv(RES / "zonas.csv", dtype={"cod_dane": str})


@pytest.fixture(scope="module")
def excedentes():
    return pd.read_csv(RES / "excedentes.csv", dtype={"cod_dane": str})


@pytest.fixture(scope="module")
def escenarios():
    return pd.read_csv(RES / "escenarios.csv")


# ----------------------------- TAREA #2 -----------------------------------

@requiere_resultados
def test_42_municipios_una_vez(zonas):
    assert len(zonas) == 42
    assert zonas["cod_dane"].nunique() == 42
    assert zonas["cod_dane"].duplicated().sum() == 0


@requiere_resultados
def test_un_centro_por_zona(zonas):
    por_zona = zonas.groupby("zona")["es_centro_zona"].sum()
    assert (por_zona == 1).all(), por_zona.to_dict()


@requiere_resultados
def test_zonas_conexas():
    """Cada zona debe ser espacialmente conexa en el grafo Queen."""
    from arendonc2 import zonas_acopio as za

    cfg = common.cargar_config()
    geo = za.cargar_geometrias(cfg)
    w, _ = za.construir_vecindad(geo)
    zonas_df = pd.read_csv(RES / "zonas.csv", dtype={"cod_dane": str})
    for z, g in zonas_df.groupby("zona"):
        assert za.es_conexa(g["cod_dane"].tolist(), w, geo), f"Zona {z} no es conexa"


@requiere_resultados
def test_metricas_k_todas_conexas():
    met = pd.read_csv(OUT / "zonas_metricas_k.csv")
    assert (met["pct_zonas_conexas"] == 100.0).all()
    assert set(met["k"]) >= set(range(3, 9))


# ----------------------------- TAREA #3 -----------------------------------

@requiere_resultados
def test_cuotas_reparto_suman_uno():
    cu = pd.read_csv(OUT / "faostat_mapeo_cuotas.csv")
    rep = cu[cu["tipo_mapeo"] == "reparto_categoria"]
    sumas = rep.groupby("item_o_categoria")["cuota"].sum()
    assert ((sumas - 1.0).abs() < 1e-6).all(), sumas.to_dict()


@requiere_resultados
def test_excedentes_no_negativos(excedentes):
    assert (excedentes["excedente_t"] >= 0).all()


@requiere_resultados
def test_claves_excedentes_sin_duplicados(excedentes):
    k = ["producto", "cod_dane", "anio", "escenario_oferta", "escenario_consumo"]
    assert excedentes.duplicated(k).sum() == 0


@requiere_resultados
def test_9_combinaciones_por_anio(excedentes):
    comb = excedentes.groupby("anio").apply(
        lambda g: g[["escenario_oferta", "escenario_consumo"]].drop_duplicates().shape[0]
    )
    assert (comb == 9).all(), comb.to_dict()


@requiere_resultados
def test_consumos_desconocidos_identificados(excedentes):
    """Productos pendientes: consumo 0 PERO marcados; no desaparecen."""
    pend = pd.read_csv(OUT / "excedentes_pendientes.csv")
    assert len(pend) >= 1
    marcados = excedentes[excedentes["consumo_pendiente"] == 1]
    assert set(pend["producto"]) <= set(marcados["producto"].unique())
    # ninguno con consumo > 0
    assert (marcados["consumo_local_t"] == 0).all()


@requiere_resultados
def test_totales_municipales_igual_zonales(excedentes):
    z = pd.read_csv(OUT / "excedentes_por_zona.csv")
    keys = ["zona", "producto", "anio", "escenario_oferta", "escenario_consumo"]
    mun = excedentes.groupby(keys, dropna=False)["excedente_t"].sum().reset_index()
    m = mun.merge(z[keys + ["excedente_t"]], on=keys, suffixes=("_mun", "_zon"))
    assert (m["excedente_t_mun"] - m["excedente_t_zon"]).abs().max() < 1e-6


@requiere_resultados
def test_auditoria_recortes_preserva_fuente():
    """Los recortes negativos quedan auditados y la oferta fuente sigue teniendo negativos."""
    aud = pd.read_csv(OUT / "excedentes_auditoria_recortes.csv")
    fuente = pd.read_csv(common.DATA_RES_ML / "oferta_escenarios.csv")
    # si hubo recortes, la fuente original debe conservar valores negativos
    if len(aud) > 0:
        assert (fuente[["oferta_bajo", "oferta_base", "oferta_alto"]] < 0).any().any()
        assert (aud["oferta_recortada_t"] == 0).all()


@requiere_resultados
def test_sobreoferta_no_triplicada(excedentes):
    """La alerta de sobreoferta depende sólo de la oferta, no del escenario de consumo."""
    sub = excedentes[excedentes["escenario_oferta"] == "base"]
    g = sub.groupby(["producto", "cod_dane", "anio"])["sobreoferta"].nunique(dropna=False)
    assert (g <= 1).all(), "sobreoferta varía con el escenario de consumo"


# ----------------------------- TAREA #4 -----------------------------------

@requiere_resultados
def test_27_combinaciones_por_anio(escenarios):
    comb = escenarios.groupby("anio")["id_escenario"].nunique()
    assert (comb == 27).all(), comb.to_dict()


@requiere_resultados
def test_contrato_columnas_samuel(escenarios):
    requeridas = {
        "id_escenario", "oferta", "consumo", "pct_nacional", "pct_exportacion",
        "zona", "volumen_nacional", "volumen_exportacion",
        "anio", "alcance", "cobertura_oferta_pct",
    }
    assert requeridas <= set(escenarios.columns), requeridas - set(escenarios.columns)


@requiere_resultados
def test_proporciones_suman_uno(escenarios):
    assert ((escenarios["pct_nacional"] + escenarios["pct_exportacion"] - 1.0).abs() < 1e-9).all()


@requiere_resultados
def test_volumenes_conservan_excedente(escenarios, excedentes):
    """volumen_nacional + volumen_exportacion == excedente de la zona ese año/combinación."""
    esc = escenarios.copy()
    esc["suma"] = esc["volumen_nacional"] + esc["volumen_exportacion"]
    # excedente por zona de la tarea #3
    zexc = (
        excedentes.groupby(["zona", "anio", "escenario_oferta", "escenario_consumo"])["excedente_t"]
        .sum().reset_index()
    )
    m = esc.merge(
        zexc, left_on=["zona", "anio", "oferta", "consumo"],
        right_on=["zona", "anio", "escenario_oferta", "escenario_consumo"],
    )
    assert (m["suma"] - m["excedente_t"]).abs().max() < 1.0


# ----------------------------- ADAPTADOR ----------------------------------

@requiere_resultados
def test_adaptador_selecciona_anio_exacto():
    from arendonc2.adaptador import preparar_para_solver

    pkg = preparar_para_solver("2025_Obase_Cbase_M50_50", 2025)
    assert pkg.anio == 2025
    assert pkg.excedente_municipio["cod_dane"].nunique() == 42
    assert (pkg.excedente_municipio["excedente_t"] >= 0).all()


@requiere_resultados
def test_adaptador_rechaza_anio_incoherente():
    from arendonc2.adaptador import preparar_para_solver

    with pytest.raises(ValueError):
        preparar_para_solver("2025_Obase_Cbase_M50_50", 2024)


@requiere_resultados
def test_adaptador_coherencia_municipal_zonal():
    from arendonc2.adaptador import preparar_para_solver

    pkg = preparar_para_solver("2024_Oalto_Calto_M20_80", 2024)
    mun = pkg.excedente_municipio.groupby("zona")["excedente_t"].sum().round(2)
    zon = pkg.volumen_por_zona.set_index("zona")["excedente_t"].round(2)
    a, b = mun.align(zon, join="outer", fill_value=0.0)
    assert (a - b).abs().max() < 1.0


@requiere_resultados
def test_cobertura_parcial_visible_en_archivos(escenarios):
    assert "cobertura_oferta_pct" in escenarios.columns
    assert (escenarios["cobertura_oferta_pct"] <= 100.0).all()
    # existe al menos un caso de cobertura < 100 (productos pendientes)
    assert (escenarios["cobertura_oferta_pct"] < 100.0).any()
