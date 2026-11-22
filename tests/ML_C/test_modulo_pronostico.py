"""Pruebas del módulo de pronóstico. Correr desde la raíz: pytest tests/ML_C -q"""
from importlib import import_module
import numpy as np, pandas as pd, pytest
from common import ROOT, CLEAN, RES, CFG, objetivos, ORIGENES, ANIO_FIN


def leer(f, **kw):
    if not f.exists():
        pytest.skip(f"falta {f.relative_to(ROOT)}")
    return pd.read_csv(f, **kw)


def test_rutas_apuntan_a_la_raiz():
    assert (ROOT / "config/ML_C/parametros.yaml").exists()
    assert RES == ROOT / "data/results/ML_Ce"


def test_tabla_limpia():
    d = leer(CLEAN / "produccion_valle_clean.csv", dtype={"cod_dane": str})
    assert d.cod_dane.nunique() == 42 and d.cod_dane.str.len().eq(5).all()
    assert not d.duplicated(["anio", "cod_dane", "producto"]).any()
    assert (d.produccion_t >= 0).all()


def test_conteos_de_productos():
    lp = leer(CLEAN / "lista_productos.csv")
    n = CFG["limpieza"]["n_detallados"]
    assert lp.estado.value_counts().to_dict() == {"detallado": n, "simplificado": 22, "excluido": 13}


def test_walk_forward_sin_fugas():
    for O in ORIGENES:
        assert all(O + h <= ANIO_FIN for h in objetivos(O))
    pr = leer(RES / "predicciones_baselines.csv", dtype={"cod_dane": str})
    assert (pr.anio_objetivo == pr.origen_anio + pr.horizonte).all()
    assert (pr.anio_objetivo > pr.origen_anio).all()


def test_baseline_ingenuo():
    b5 = import_module("05_baselines")
    y = pd.Series([1.0, 2.0, 5.0], index=[2000, 2001, 2002])
    assert list(b5.f_naive(y, 3)) == [5.0, 5.0, 5.0]
    assert np.allclose(b5.f_drift(y, 2), [7.0, 9.0])


def test_contrato_oferta_escenarios():
    o = leer(RES / "oferta_escenarios.csv", dtype={"cod_dane": str})
    assert list(o.columns) == ["producto", "cod_dane", "año", "oferta_bajo", "oferta_base", "oferta_alto"]
    assert o.notna().all().all()
    assert ((o.oferta_bajo <= o.oferta_base) & (o.oferta_base <= o.oferta_alto)).all()
    assert set(o["año"]) == set(range(2024, 2029))


def test_coherencia_municipios_departamento():
    o = leer(RES / "oferta_escenarios.csv", dtype={"cod_dane": str})
    dep = leer(RES / "oferta_departamento.csv")
    s = o.groupby(["producto", "año"])["oferta_base"].sum().reset_index().merge(dep, on=["producto", "año"], suffixes=("_m", "_d"))
    assert np.allclose(s.oferta_base_m, s.oferta_base_d, atol=1.0)


def test_valor_producto():
    v = leer(CLEAN / "valor_producto.csv", dtype={"cod_dane": str})
    con = v[v.precio_cop_kg.notna()]
    assert (con.precio_cop_kg > 0).all()
    assert np.allclose(con.valor_cop, con.produccion_t * 1000 * con.precio_cop_kg, rtol=1e-3, atol=1e3)
    assert set(v.tipo_precio) <= {"directo", "derivado", "sin_precio"}


def test_oni_anual():
    o = leer(CLEAN / "oni.csv")
    assert o.anio.is_unique and o.anio.min() <= 2000 and o.anio.max() >= ANIO_FIN
    assert o.oni.between(-3, 3).all()


def test_metricas_modelo_final():
    mf = leer(RES / "metricas_modelo_final.csv", dtype={"horizonte": str})
    pr = leer(RES / "predicciones_comparacion.csv", dtype={"cod_dane": str})
    tot = mf.query("producto == 'TOTAL' and alcance == 'todos' and horizonte == 'todos' and modelo == 'naive_lgbm'")
    assert len(tot) == 1
    final = (pr.naive + pr.lgbm) / 2
    assert np.isclose(tot.WAPE.iloc[0], (final - pr.real).abs().sum() / pr.real.abs().sum(), atol=1e-4)
    assert set(mf.horizonte) == {"todos", "1", "2", "3", "4", "5"}


def test_modelo_final_usa_oni():
    """El modelo final reportado es la variante con ONI del experimento 06_lgbm.py --comparar-oni."""
    assert CFG["pronostico"]["usar_oni"] is True
    oni = leer(RES / "metricas_oni.csv")
    mf = leer(RES / "metricas_modelo_final.csv", dtype={"horizonte": str})
    con = oni.query("variante == 'con_oni' and alcance == 'todos' and modelo == 'naive_lgbm'").MASE.iloc[0]
    oficial = mf.query("producto == 'TOTAL' and alcance == 'todos' and horizonte == 'todos' and modelo == 'naive_lgbm'").MASE.iloc[0]
    assert np.isclose(con, oficial, atol=1e-4)
