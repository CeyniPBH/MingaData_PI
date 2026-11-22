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

# Los polígonos GADM no se versionan (data/raw/geo/ está en .gitignore).
requiere_geometrias = pytest.mark.skipif(
    not (common.DATA_GEO / "gadm41_COL_2.json.zip").exists(),
    reason="Falta data/raw/geo/gadm41_COL_2.json.zip; descargarlo con python src/arendonc2/descargar_geometrias.py.",
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
@requiere_geometrias
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


@requiere_resultados
def test_emparejamiento_geometrias_1a1():
    """Auditoría 2: 42 municipios emparejados 1:1 con GADM, sin ambigüedad."""
    emp = pd.read_csv(OUT / "emparejamiento_gadm_dane.csv", dtype={"cod_dane": str})
    assert len(emp) == 42
    assert (emp["emparejado"] == "sí").all()
    assert emp["nombre_gadm_NAME_2"].notna().all()
    # ningún polígono GADM usado más de una vez
    assert emp["clave_match_gadm"].duplicated().sum() == 0


@requiere_resultados
@requiere_geometrias
def test_features_usan_coordenadas_proyectadas():
    """Auditoría 3: el método espacial por defecto proyecta a EPSG:3116 con escala común."""
    from arendonc2 import zonas_acopio as za

    cfg = common.cargar_config()
    assert cfg["zonas"]["espacio"] == "proyectado_escala_comun"
    geo = za.cargar_geometrias(cfg)
    feats = za.construir_features(geo, cfg)
    assert {"x_proj_m", "y_proj_m"}.issubset(feats.columns)
    # escala común: el aspect ratio real (N-S > E-W) se conserva en las features z
    assert feats["lat_z"].std() > feats["lon_z"].std()


# ----------------------------- TAREA #3 -----------------------------------

@requiere_resultados
def test_cuotas_reparto_suman_uno():
    cu = pd.read_csv(OUT / "faostat_mapeo_cuotas.csv")
    rep = cu[cu["tipo_mapeo"] == "reparto_categoria"]
    sumas = rep.groupby("item_o_categoria")["cuota"].sum()
    assert ((sumas - 1.0).abs() < 1e-6).all(), sumas.to_dict()


@requiere_resultados
def test_excedentes_no_negativos(excedentes):
    # excedente conocido: no negativo. Pendientes: NaN (desconocido), no 0 ni negativo.
    conocidos = excedentes[excedentes["consumo_pendiente"] == 0]
    assert (conocidos["excedente_t"] >= 0).all()
    pend = excedentes[excedentes["consumo_pendiente"] == 1]
    assert pend["excedente_t"].isna().all(), "excedente de pendientes debe ser nulo (NaN)"


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
def test_ningun_item_faostat_en_dos_grupos():
    """Auditoría 1: ningún ítem/categoría FAOSTAT se usa en grupos de tipo distinto,
    ni un ítem sumado se asigna a más de un producto."""
    cu = pd.read_csv(OUT / "faostat_mapeo_cuotas.csv")
    usados = cu[cu["tipo_mapeo"].isin(["suma_items", "reparto_categoria"])]
    # un nombre no puede aparecer en dos tipos distintos
    por_nombre = usados.groupby("item_o_categoria")["tipo_mapeo"].nunique()
    assert (por_nombre == 1).all(), por_nombre[por_nombre > 1].to_dict()
    # un item 'suma_items' no puede estar en más de un producto
    si = usados[usados["tipo_mapeo"] == "suma_items"]["item_o_categoria"].value_counts()
    assert (si == 1).all(), si[si > 1].to_dict()


@requiere_resultados
def test_materia_prima_sin_factor_es_pendiente():
    """Auditoría 1: productos que exigen conversión materia prima -> consumible sin
    factor respaldado deben estar como pendientes (no utilizables)."""
    aud = pd.read_csv(OUT / "auditoria_mapeo_faostat.csv")
    deben_pendientes = {"Café", "Caña panelera", "Cacao", "Coco", "Macadamia",
                        "Sacha Inchi", "Stevia", "Té", "Ají", "Cebolla Larga"}
    estado = aud.set_index("producto")["estado"].to_dict()
    for p in deben_pendientes:
        assert estado.get(p) == "pendiente", f"{p} debería ser pendiente, es {estado.get(p)}"


@requiere_resultados
def test_consumos_desconocidos_identificados(excedentes):
    """Productos pendientes: consumo y excedente DESCONOCIDOS (nulo/NaN), con motivo,
    y oferta conservada. No se sustituye por 0 silencioso ni se cuentan como excedente."""
    pend = pd.read_csv(OUT / "excedentes_pendientes.csv")
    assert len(pend) >= 1
    marcados = excedentes[excedentes["consumo_pendiente"] == 1]
    assert set(pend["producto"]) <= set(marcados["producto"].unique())
    # consumo DESCONOCIDO -> nulo (NaN), nunca 0
    assert marcados["consumo_local_t"].isna().all()
    # excedente DESCONOCIDO -> nulo (NaN)
    assert marcados["excedente_t"].isna().all()
    # oferta original conservada (hay oferta positiva entre los pendientes)
    assert (marcados["oferta_t"] > 0).any()
    # motivo del pendiente presente y no vacío
    assert "motivo_pendiente" in excedentes.columns
    assert (marcados["motivo_pendiente"].astype(str).str.len() > 0).all()


@requiere_resultados
def test_totales_municipales_igual_zonales(excedentes):
    z = pd.read_csv(OUT / "excedentes_por_zona.csv")
    keys = ["zona", "producto", "anio", "escenario_oferta", "escenario_consumo"]
    # comparar sólo productos con consumo conocido (los pendientes son NaN en ambos lados)
    conocidos = excedentes[excedentes["consumo_pendiente"] == 0]
    mun = conocidos.groupby(keys, dropna=False)["excedente_t"].sum().reset_index()
    zc = z[z["consumo_pendiente"] == 0]
    m = mun.merge(zc[keys + ["excedente_t"]], on=keys, suffixes=("_mun", "_zon"))
    assert (m["excedente_t_mun"] - m["excedente_t_zon"]).abs().max() < 1e-6
    # los pendientes en por_zona deben tener excedente nulo (NaN)
    zp = z[z["consumo_pendiente"] == 1]
    assert zp["excedente_t"].isna().all()


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
    """volumen_nacional + volumen_exportacion == excedente CONOCIDO de la zona ese
    año/combinación (los productos pendientes no aportan volumen)."""
    esc = escenarios.copy()
    esc["suma"] = esc["volumen_nacional"] + esc["volumen_exportacion"]
    # excedente por zona SÓLO de productos con consumo conocido
    conocidos = excedentes[excedentes["consumo_pendiente"] == 0]
    zexc = (
        conocidos.groupby(["zona", "anio", "escenario_oferta", "escenario_consumo"])["excedente_t"]
        .sum().reset_index()
    )
    m = esc.merge(
        zexc, left_on=["zona", "anio", "oferta", "consumo"],
        right_on=["zona", "anio", "escenario_oferta", "escenario_consumo"],
    )
    assert (m["suma"] - m["excedente_t"]).abs().max() < 1.0


@requiere_resultados
def test_pendiente_no_aumenta_volumenes_optimizacion(escenarios, excedentes):
    """PRUEBA ESPECÍFICA (auditoría): un producto con oferta positiva y consumo
    DESCONOCIDO no debe aumentar los volúmenes disponibles para optimización.

    Se toma un producto pendiente con oferta > 0 y se comprueba que:
      (a) su excedente es nulo (no entra como volumen), y
      (b) el volumen total de los escenarios iguala el excedente CONOCIDO, sin
          sumar la oferta del pendiente.
    """
    pend = excedentes[excedentes["consumo_pendiente"] == 1]
    # debe existir al menos un pendiente con oferta positiva (p. ej. Café, Caña panelera)
    con_oferta = pend[pend["oferta_t"] > 0]
    assert not con_oferta.empty, "se esperaba al menos un pendiente con oferta > 0"
    assert con_oferta["excedente_t"].isna().all(), "un pendiente no debe aportar excedente"

    # Para una combinación concreta, el volumen total de escenarios NO incluye la
    # oferta de los pendientes.
    anio, eo, ec = 2024, "base", "base"
    sub = escenarios[(escenarios["anio"] == anio) & (escenarios["oferta"] == eo)
                     & (escenarios["consumo"] == ec) & (escenarios["pct_nacional"] == 0.8)]
    vol_total = (sub["volumen_nacional"] + sub["volumen_exportacion"]).sum()

    e = excedentes[(excedentes["anio"] == anio) & (excedentes["escenario_oferta"] == eo)
                   & (excedentes["escenario_consumo"] == ec)]
    exc_conocido = e[e["consumo_pendiente"] == 0]["excedente_t"].sum()
    oferta_pendiente = e[e["consumo_pendiente"] == 1]["oferta_t"].sum()

    assert abs(vol_total - exc_conocido) < 1.0
    # el volumen de optimización es estrictamente menor que (conocido + oferta pendiente)
    assert vol_total < exc_conocido + oferta_pendiente - 1.0
    assert oferta_pendiente > 0


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
