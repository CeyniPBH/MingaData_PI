"""Revisa formato, conteos y consistencia de las entregas del módulo. Imprime OK / FALLA / PENDIENTE."""
import sys
import numpy as np, pandas as pd
from common import ROOT, CLEAN, RES
fallos, avisos = [], []

def ok(cond, msg):
    print(("  OK  " if cond else "  FALLA ") + msg)
    if not cond: fallos.append(msg)

def leer(f, **kw):
    if not f.exists():
        ok(False, f"existe {f.relative_to(ROOT)}"); return None
    return pd.read_csv(f, **kw)

def main():
    print("== produccion_valle_clean / lista_productos")
    d = leer(CLEAN / "produccion_valle_clean.csv", dtype={"cod_dane": str})
    lp = leer(CLEAN / "lista_productos.csv")
    if d is not None:
        ok(d.cod_dane.nunique() == 42 and (d.cod_dane.str.len() == 5).all(), "42 municipios con código DANE de 5 dígitos")
        ok(not d.duplicated(["anio", "cod_dane", "producto"]).any(), "sin duplicados (año, municipio, producto)")
        ok(d.anio.min() == 2000 and d.anio.max() == 2023, "años 2000-2023")
    if lp is not None:
        ok(lp.estado.value_counts().to_dict() == {"detallado": 22, "simplificado": 22, "excluido": 13}, "conteos 22 detallados / 22 simplificados / 13 excluidos")

    print("== coordenadas y matriz de tiempos")
    mc = leer(CLEAN / "municipios_coordenadas.csv", dtype={"cod_dane": str})
    dc = leer(CLEAN / "destinos_coordenadas.csv")
    m = leer(CLEAN / "matriz_tiempos.csv", dtype={"origen": str, "destino": str})
    if mc is not None:
        ok(len(mc) == 42 and mc.lat.between(0, 14).all() and mc.lon.between(-80, -66).all(), "42 coordenadas dentro de Colombia")
    if m is not None and mc is not None and dc is not None:
        esperado = len(mc) * (len(mc) + len(dc))
        ok(len(m) == esperado and m.minutos.notna().all(), f"matriz completa sin huecos ({esperado} filas)")
        ok(set(m.origen) == set(mc.cod_dane), "todos los municipios aparecen como origen")
        ok(set(dc.id_destino) <= set(m.destino), "todos los destinos están en la matriz")
        print(f"      metodo de la matriz: {sorted(m.metodo.unique())}")
        if (m.metodo == "aproximado").any(): avisos.append("La matriz de tiempos sigue siendo APROXIMADA (reemplazar con OSM/OSRM).")

    print("== oferta_escenarios")
    o = leer(RES / "oferta_escenarios.csv", dtype={"cod_dane": str})
    if o is not None:
        ok(list(o.columns) == ["producto", "cod_dane", "año", "oferta_bajo", "oferta_base", "oferta_alto"], "columnas exactas del contrato")
        ok(o.notna().all().all(), "sin nulos")
        ok(((o.oferta_bajo <= o.oferta_base) & (o.oferta_base <= o.oferta_alto)).all(), "bajo <= base <= alto")
        ok(set(o["año"].unique()) == set(range(2024, 2029)), "horizonte 2024-2028")
        n_ser = o[["producto", "cod_dane"]].drop_duplicates().shape[0]
        ok(len(o) == n_ser * 5, f"5 años por serie ({n_ser} series)")
        dep = leer(RES / "oferta_departamento.csv")
        if dep is not None:
            s = o.groupby(["producto", "año"])["oferta_base"].sum().reset_index().merge(dep, on=["producto", "año"], suffixes=("_m", "_d"))
            ok(np.allclose(s.oferta_base_m, s.oferta_base_d, rtol=1e-3, atol=0.05 * len(o) / len(s)), "municipios suman el total departamental")

    print("== archivos externos")
    contratos = {"valor_producto.csv": ["producto", "cod_dane", "anio", "produccion_t", "precio_cop_kg", "valor_cop"],
                 "precio_producto_anual.csv": ["producto", "anio", "precio_cop_kg", "tipo_precio"],
                 "oni.csv": ["anio", "oni"],
                 "consumo_percapita.csv": ["item_faostat", "anio", "kg_per_capita_anio"],
                 "comercio_ica_frontera.csv": ["anio", "tipo_comercio", "producto_ica", "puerto", "toneladas"],
                 "poblacion_municipal.csv": ["cod_dane", "anio", "poblacion"]}
    for nombre, cols in contratos.items():
        f = CLEAN / nombre
        if not f.exists():
            print(f"  PENDIENTE {nombre}"); avisos.append(f"Falta data/clean/{nombre}"); continue
        x = pd.read_csv(f)
        ok(all(c in x.columns for c in cols) and len(x) > 0, f"{nombre} con columnas {cols}")
    pm = leer(CLEAN / "produccion_promedio_municipio.csv")
    if pm is not None and "valor_prom_cop_2019_2023" not in pm.columns:
        avisos.append("produccion_promedio_municipio.csv aún no tiene valor (correr 04_fuentes_externas.py)")

    print("\nAVISOS:" if avisos else "\nSin avisos.")
    for a in avisos: print("  -", a)
    print(f"\nRESULTADO: {'TODO OK' if not fallos else str(len(fallos)) + ' fallas'}")
    sys.exit(1 if fallos else 0)

if __name__ == "__main__":
    main()
