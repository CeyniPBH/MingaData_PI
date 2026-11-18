"""
TAREA #3 — Excedentes bajo escenarios de oferta y consumo.

Estima cuánta producción de cada producto sobra frente al consumo local, tratando
el consumo como un supuesto con escenarios (bajo/base/alto, factores 0.8/1.0/1.2).

Fórmulas (por producto, municipio, año):
  consumo_local_t   = kg_per_capita_anio * poblacion * factor_consumo / 1000
  excedente_municipal_t = max(0, oferta_t - consumo_local_t)

Genera las 9 combinaciones (3 oferta × 3 consumo) y agrega por zona DESPUÉS de
recortar el excedente municipal a >= 0.

Reglas clave:
  - Consumo per cápita FAOSTAT: se usa el último año disponible (2023) para todos
    los años proyectados (no hay serie futura); se documenta como supuesto.
  - Categorías FAOSTAT amplias se reparten entre cultivos equivalentes por su
    producción histórica regional 2019-2023; las cuotas suman 1 por categoría.
  - Productos sin equivalencia (pendiente=true): consumo_local = 0 pero marcados
    'consumo_pendiente' = 1 y 'motivo_pendiente'. NUNCA se asume consumo cero
    para un producto con equivalencia desconocida sin marcarlo.
  - Caña de azúcar excluida.
  - Límites inferiores negativos del pronóstico se recortan a 0 y se registran
    en auditoría; los archivos fuente quedan intactos.
  - Sobreoferta: oferta > media_hist + 1 desv. estándar muestral (2019-2023).
    Si falta historia suficiente, la alerta queda 'sin determinar'.

Salidas:
  - data/results/excedentes.csv
  - data/results/arendonc2/excedentes_por_zona.csv
  - data/results/arendonc2/excedentes_cobertura.csv
  - data/results/arendonc2/excedentes_pendientes.csv
  - data/results/arendonc2/faostat_mapeo_cuotas.csv
  - data/results/arendonc2/excedentes_auditoria_recortes.csv

Uso: python src/arendonc2/excedentes.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
    from arendonc2 import common
else:
    from . import common

MAPEO_YAML = common.ROOT / "config" / "arendonc2" / "mapeo_faostat.yaml"


# --------------------------------------------------------------------------
# Mapeo FAOSTAT y cuotas de reparto
# --------------------------------------------------------------------------

def cargar_mapeo() -> dict:
    with open(MAPEO_YAML, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)["mapeos"]


def construir_cuotas(mapeo: dict, lista_productos: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """
    Para cada categoría FAOSTAT compartida, calcula la cuota de reparto por
    producto = producción_2019_2023 del producto / suma de la categoría.
    Las cuotas suman 1 dentro de cada categoría.

    Devuelve DataFrame: producto, tipo_mapeo, item_o_categoria, cuota, prod_2019_2023, nota.
    """
    excluidos = set(cfg["general"]["productos_excluidos"])
    prod_hist = lista_productos.set_index("producto")["produccion_t_2019_2023"].to_dict()

    # Agrupar productos por categoría compartida
    por_categoria: dict[str, list[str]] = {}
    for p, v in mapeo.items():
        if p in excluidos:
            continue
        if "categoria_compartida" in v:
            por_categoria.setdefault(v["categoria_compartida"], []).append(p)

    filas = []
    for p, v in mapeo.items():
        if p in excluidos:
            continue
        nota = v.get("nota", "")
        if v.get("pendiente"):
            filas.append({
                "producto": p, "tipo_mapeo": "pendiente",
                "item_o_categoria": "", "cuota": np.nan,
                "prod_2019_2023": prod_hist.get(p, np.nan), "nota": nota,
            })
        elif "items" in v:
            for it in v["items"]:
                filas.append({
                    "producto": p, "tipo_mapeo": "suma_items",
                    "item_o_categoria": it, "cuota": 1.0,
                    "prod_2019_2023": prod_hist.get(p, np.nan), "nota": nota,
                })
        elif "categoria_compartida" in v:
            cat = v["categoria_compartida"]
            total = sum(prod_hist.get(q, 0.0) for q in por_categoria[cat])
            cuota = (prod_hist.get(p, 0.0) / total) if total > 0 else 0.0
            filas.append({
                "producto": p, "tipo_mapeo": "reparto_categoria",
                "item_o_categoria": cat, "cuota": cuota,
                "prod_2019_2023": prod_hist.get(p, np.nan), "nota": nota,
            })
    df = pd.DataFrame(filas)

    # Verificación 1: cuotas de reparto suman 1 por categoría (precisión completa)
    rep = df[df["tipo_mapeo"] == "reparto_categoria"]
    sumas = rep.groupby("item_o_categoria")["cuota"].sum()
    malas = sumas[(sumas - 1.0).abs() > 1e-9]
    if len(malas) > 0:
        raise RuntimeError(f"Cuotas de reparto no suman 1: {malas.to_dict()}")

    # Verificación 2: ningún ítem/categoría FAOSTAT se usa en dos grupos distintos
    # (un ítem sumado por un producto no puede además repartirse en otro, etc.)
    usados = df[df["tipo_mapeo"].isin(["suma_items", "reparto_categoria"])]
    dup = usados["item_o_categoria"].value_counts()
    # un ítem de reparto aparece una vez por producto de su categoría: eso es válido.
    # lo inválido es que el MISMO nombre aparezca en tipos distintos.
    por_nombre = usados.groupby("item_o_categoria")["tipo_mapeo"].nunique()
    mezclados = por_nombre[por_nombre > 1]
    if len(mezclados) > 0:
        raise RuntimeError(
            f"Ítems FAOSTAT usados en grupos de tipo distinto: {mezclados.index.tolist()}"
        )
    # un ítem 'suma_items' no puede repartirse entre varios productos
    suma_items_dup = (
        usados[usados["tipo_mapeo"] == "suma_items"]["item_o_categoria"].value_counts()
    )
    item_repetido = suma_items_dup[suma_items_dup > 1]
    if len(item_repetido) > 0:
        raise RuntimeError(
            f"Ítem FAOSTAT (suma_items) asignado a más de un producto: {item_repetido.to_dict()}"
        )
    return df


def consumo_percapita_por_producto(cuotas: pd.DataFrame, consumo: pd.DataFrame,
                                   anio_ref: int) -> pd.DataFrame:
    """
    Consumo per cápita (kg/persona/año) base por producto usando el año de referencia.
      - suma_items: suma de los ítems.
      - reparto_categoria: consumo de la categoría * cuota del producto.
      - pendiente: NaN (se marca aparte, no se asume 0).
    """
    cons_ref = consumo[consumo["anio"] == anio_ref].set_index("item_faostat")["kg_per_capita_anio"]
    filas = []
    for p, g in cuotas.groupby("producto"):
        tipo = g["tipo_mapeo"].iloc[0]
        if tipo == "pendiente":
            filas.append({"producto": p, "kg_per_capita": np.nan, "pendiente": 1,
                          "motivo": g["nota"].iloc[0]})
            continue
        kg = 0.0
        faltan = []
        for _, r in g.iterrows():
            base = cons_ref.get(r["item_o_categoria"])
            if base is None:
                faltan.append(r["item_o_categoria"])
                continue
            kg += base * (r["cuota"] if tipo == "reparto_categoria" else 1.0)
        if faltan:
            filas.append({"producto": p, "kg_per_capita": np.nan, "pendiente": 1,
                          "motivo": f"Ítems FAOSTAT sin dato {anio_ref}: {faltan}"})
        else:
            filas.append({"producto": p, "kg_per_capita": round(kg, 6), "pendiente": 0, "motivo": ""})
    return pd.DataFrame(filas)


# --------------------------------------------------------------------------
# Oferta en formato largo con escenarios + auditoría de recortes negativos
# --------------------------------------------------------------------------

def oferta_larga_con_auditoria(cfg: dict):
    """
    Pasa oferta de ancho (bajo/base/alto) a largo (escenario_oferta, oferta_t) y
    recorta a >= 0 los valores negativos (sólo el pronóstico 'bajo' puede serlo),
    registrando los originales en una auditoría. Excluye productos excluidos.
    """
    excluidos = set(cfg["general"]["productos_excluidos"])
    o = common.leer_oferta_escenarios()
    o = o[~o["producto"].isin(excluidos)].copy()

    largo = o.melt(
        id_vars=["producto", "cod_dane", "anio"],
        value_vars=["oferta_bajo", "oferta_base", "oferta_alto"],
        var_name="escenario_oferta", value_name="oferta_t",
    )
    largo["escenario_oferta"] = largo["escenario_oferta"].str.replace("oferta_", "", regex=False)

    # Auditoría de recortes negativos
    neg = largo[largo["oferta_t"] < 0].copy()
    neg = neg.rename(columns={"oferta_t": "oferta_original_t"})
    neg["oferta_recortada_t"] = 0.0
    auditoria = neg[["producto", "cod_dane", "anio", "escenario_oferta",
                     "oferta_original_t", "oferta_recortada_t"]].reset_index(drop=True)

    largo["oferta_t"] = largo["oferta_t"].clip(lower=0.0)
    return largo, auditoria


# --------------------------------------------------------------------------
# Sobreoferta (alerta coyuntural)
# --------------------------------------------------------------------------

def calcular_umbral_sobreoferta(cfg: dict) -> pd.DataFrame:
    """
    Umbral por producto-municipio = media_hist + n_desv * desv. estándar muestral
    de la producción 2019-2023. Si hay menos de 'sobreoferta_min_anios' años,
    el umbral queda NaN (alerta 'sin determinar').
    """
    ventana = cfg["excedentes"]["ventana_historica"]
    n_desv = cfg["excedentes"]["sobreoferta_n_desv"]
    min_anios = cfg["excedentes"]["sobreoferta_min_anios"]
    excluidos = set(cfg["general"]["productos_excluidos"])

    prod = common.leer_produccion_valle()
    col_anio = "anio" if "anio" in prod.columns else "año"
    prod = prod[(prod[col_anio].isin(ventana)) & (~prod["producto"].isin(excluidos))]

    filas = []
    for (p, c), g in prod.groupby(["producto", "cod_dane"]):
        vals = g["produccion_t"].dropna().to_numpy()
        n = len(vals)
        if n >= min_anios:
            media = float(vals.mean())
            sd = float(vals.std(ddof=1)) if n > 1 else 0.0
            umbral = media + n_desv * sd
            filas.append({"producto": p, "cod_dane": c, "umbral_sobreoferta_t": umbral,
                          "n_anios_hist": n})
        else:
            filas.append({"producto": p, "cod_dane": c, "umbral_sobreoferta_t": np.nan,
                          "n_anios_hist": n})
    return pd.DataFrame(filas)


# --------------------------------------------------------------------------
# Pipeline principal
# --------------------------------------------------------------------------

def ejecutar(cfg: dict | None = None, guardar: bool = True) -> dict:
    if cfg is None:
        cfg = common.cargar_config()
    common.asegurar_directorios()

    anio_consumo_ref = cfg["excedentes"]["anio_consumo_referencia"]
    factores = cfg["excedentes"]["factores_consumo"]

    # --- zonas (de la tarea #2) ---
    zonas_path = common.DATA_RES / "zonas.csv"
    if not zonas_path.exists():
        raise FileNotFoundError("Falta data/results/zonas.csv. Corre primero la tarea #2.")
    zonas = pd.read_csv(zonas_path, dtype={"cod_dane": str})[["cod_dane", "zona"]]

    # --- mapeo FAOSTAT y consumo per cápita por producto ---
    mapeo = cargar_mapeo()
    lista = common.leer_lista_productos()
    cuotas = construir_cuotas(mapeo, lista, cfg)
    consumo = common.leer_consumo_percapita()
    cpp = consumo_percapita_por_producto(cuotas, consumo, anio_consumo_ref)

    # --- población ---
    pob_path = common.DATA_CLEAN / "poblacion_municipal.csv"
    if not pob_path.exists():
        raise FileNotFoundError(
            "Falta data/clean/poblacion_municipal.csv. Corre: python src/arendonc2/poblacion.py"
        )
    pob = pd.read_csv(pob_path, dtype={"cod_dane": str})[["cod_dane", "anio", "poblacion_total"]]

    # --- oferta larga + auditoría ---
    oferta_larga, auditoria = oferta_larga_con_auditoria(cfg)

    # --- construir las 9 combinaciones ---
    # consumo_local_t = kg_per_capita * poblacion * factor / 1000 (NO depende del esc. oferta)
    base = oferta_larga.merge(pob, on=["cod_dane", "anio"], how="left")
    base = base.merge(cpp[["producto", "kg_per_capita", "pendiente", "motivo"]],
                      on="producto", how="left")

    # expandir por escenario_consumo
    partes = []
    for esc_c, factor in factores.items():
        p = base.copy()
        p["escenario_consumo"] = esc_c
        p["factor_consumo"] = factor
        # consumo: pendiente -> 0 pero marcado; conocido -> fórmula
        kg = p["kg_per_capita"]
        p["consumo_local_t"] = np.where(
            p["pendiente"] == 1,
            0.0,
            kg.fillna(0.0) * p["poblacion_total"].fillna(0.0) * factor / 1000.0,
        )
        p["consumo_pendiente"] = p["pendiente"].fillna(1).astype(int)
        partes.append(p)
    df = pd.concat(partes, ignore_index=True)

    # excedente municipal recortado a >= 0
    df["excedente_municipal_t"] = (df["oferta_t"] - df["consumo_local_t"]).clip(lower=0.0)

    # sobreoferta (depende sólo de oferta: evitar triplicar por escenario_consumo)
    umbral = calcular_umbral_sobreoferta(cfg)
    df = df.merge(umbral, on=["producto", "cod_dane"], how="left")
    df["sobreoferta"] = np.where(
        df["umbral_sobreoferta_t"].isna(), np.nan,
        (df["oferta_t"] > df["umbral_sobreoferta_t"]).astype(float),
    )

    # zona
    df = df.merge(zonas, on="cod_dane", how="left")

    # nombre municipio
    mun = common.leer_municipios_coordenadas()[["cod_dane", "municipio"]]
    df = df.merge(mun, on="cod_dane", how="left")

    # columnas finales (clave con escenario_oferta y escenario_consumo)
    cols = [
        "producto", "cod_dane", "municipio", "zona", "anio",
        "escenario_oferta", "escenario_consumo", "factor_consumo",
        "oferta_t", "kg_per_capita", "poblacion_total", "consumo_local_t",
        "excedente_municipal_t", "consumo_pendiente",
        "umbral_sobreoferta_t", "sobreoferta",
    ]
    excedentes = df[cols].rename(columns={"excedente_municipal_t": "excedente_t",
                                          "consumo_local_t": "consumo_local_t"})
    excedentes = excedentes.sort_values(
        ["producto", "cod_dane", "anio", "escenario_oferta", "escenario_consumo"]
    ).reset_index(drop=True)

    # --- agregación por zona (después de recortar) ---
    por_zona = (
        excedentes.groupby(["zona", "producto", "anio", "escenario_oferta", "escenario_consumo"], dropna=False)
        .agg(
            oferta_t=("oferta_t", "sum"),
            consumo_local_t=("consumo_local_t", "sum"),
            excedente_t=("excedente_t", "sum"),
            n_municipios=("cod_dane", "nunique"),
            consumo_pendiente=("consumo_pendiente", "max"),
        )
        .reset_index()
    )

    # --- cobertura (oferta cubierta por consumo) por año y escenario ---
    # cobertura = consumo_local atendible / oferta (toneladas y %), excluyendo pendientes
    cob = []
    for (anio, eo, ec), g in excedentes.groupby(["anio", "escenario_oferta", "escenario_consumo"]):
        conocidos = g[g["consumo_pendiente"] == 0]
        pend = g[g["consumo_pendiente"] == 1]
        oferta_tot = float(g["oferta_t"].sum())
        oferta_con = float(conocidos["oferta_t"].sum())
        oferta_pen = float(pend["oferta_t"].sum())
        excedente_tot = float(g["excedente_t"].sum())
        cob.append({
            "anio": anio, "escenario_oferta": eo, "escenario_consumo": ec,
            "oferta_total_t": round(oferta_tot, 2),
            "oferta_con_consumo_t": round(oferta_con, 2),
            "oferta_pendiente_consumo_t": round(oferta_pen, 2),
            "pct_oferta_con_consumo": round(100.0 * oferta_con / oferta_tot, 2) if oferta_tot else 0.0,
            "excedente_total_t": round(excedente_tot, 2),
        })
    cobertura = pd.DataFrame(cob).sort_values(["anio", "escenario_oferta", "escenario_consumo"])

    # --- pendientes ---
    pendientes = cpp[cpp["pendiente"] == 1][["producto", "motivo"]].reset_index(drop=True)

    resultado = {
        "excedentes": excedentes,
        "por_zona": por_zona,
        "cobertura": cobertura,
        "pendientes": pendientes,
        "cuotas": cuotas,
        "consumo_pp": cpp,
        "auditoria_recortes": auditoria,
    }

    if guardar:
        excedentes.to_csv(common.DATA_RES / "excedentes.csv", index=False, encoding="utf-8-sig")
        por_zona.to_csv(common.DATA_RES_OUT / "excedentes_por_zona.csv", index=False, encoding="utf-8-sig")
        cobertura.to_csv(common.DATA_RES_OUT / "excedentes_cobertura.csv", index=False, encoding="utf-8-sig")
        pendientes.to_csv(common.DATA_RES_OUT / "excedentes_pendientes.csv", index=False, encoding="utf-8-sig")
        cuotas.to_csv(common.DATA_RES_OUT / "faostat_mapeo_cuotas.csv", index=False, encoding="utf-8-sig")
        cpp.to_csv(common.DATA_RES_OUT / "faostat_consumo_percapita_producto.csv", index=False, encoding="utf-8-sig")
        auditoria.to_csv(common.DATA_RES_OUT / "excedentes_auditoria_recortes.csv", index=False, encoding="utf-8-sig")

    return resultado


def main():
    cfg = common.cargar_config()
    res = ejecutar(cfg, guardar=True)
    exc = res["excedentes"]
    print("=" * 70)
    print("TAREA #3 — EXCEDENTES")
    print("=" * 70)
    print(f"Filas excedentes: {len(exc):,}")
    print(f"Productos: {exc['producto'].nunique()} | Municipios: {exc['cod_dane'].nunique()} | "
          f"Años: {sorted(exc['anio'].unique())}")
    n_comb = exc.groupby('anio')[['escenario_oferta', 'escenario_consumo']].apply(
        lambda g: len(g.drop_duplicates()))
    print(f"Combinaciones oferta×consumo por año: {n_comb.unique().tolist()} (esperado 9)")
    print(f"Excedentes negativos: {(exc['excedente_t'] < 0).sum()} (esperado 0)")
    print(f"Productos pendientes de consumo: {res['pendientes']['producto'].tolist()}")
    print(f"Recortes negativos auditados: {len(res['auditoria_recortes'])}")
    print()
    print("Cobertura por año/escenario (muestra):")
    print(res["cobertura"].head(9).to_string(index=False))
    print()
    print("Archivos escritos: data/results/excedentes.csv y data/results/arendonc2/excedentes_*.csv")


if __name__ == "__main__":
    main()
