"""Integra las fuentes externas: precios SIPSA y valor, ONI, consumo FAOSTAT, población DANE y comercio ICA (FRONTERA)."""
import glob, io, re
from pathlib import Path
import numpy as np, pandas as pd
from common import CFG, RAW, CLEAN, RES

SIPSA = RAW / "SIPSA"
MESES = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7, "ago": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dic": 12}

# Producto armonizado del Valle -> productos SIPSA equivalentes (regex sobre el nombre SIPSA; se excluyen importados).
EQUIV_SIPSA = {
    "Plátano": r"^Plátano (?:hartón|dominico|comino)", "Cítricos": r"^(?:Limón|Mandarina|Naranja|Tangelo)",
    "Piña": r"^Piña", "Banano": r"^Banano (?:Urabá|criollo)", "Aguacate": r"^Aguacate", "Vid": r"^Uva (?:Isabela|red globe|roja|verde)",
    "Papaya": r"^Papaya", "Lulo": r"^Lulo$", "Guayaba": r"^Guayaba", "Maracuyá": r"^Maracuyá", "Yuca": r"^Yuca",
    "Borojó": r"^Borojó$", "Guanábana": r"^Guanábana$", "Mora": r"^Mora de Castilla$", "Arracacha": r"^Arracacha",
    "Ají": r"^Ají", "Cebolla Larga": r"^Cebolla junca", "Mango": r"^Mango", "Ciruela": r"^Ciruela roja$",
    "Manzana": r"^Manzana nacional$", "Papa": r"^Papa(?: |$)", "Ulluco": r"^Ulluco$", "Granadilla": r"^Granadilla$",
    "Bananito": r"^Banano bocadillo$", "Coco": r"^Coco$", "Tomate de Árbol": r"^Tomate de árbol$", "Pitaya": r"^Pitahaya$",
    "Fresa": r"^Fresa$", "Curuba": r"^Curuba$", "Zapote": r"^Zapote$", "Durazno": r"^Durazno nacional$", "Gulupa": r"^Gulupa$",
    "Brevo": r"^Breva$", "Uchuva": r"^Uchuva",
}


def num_col(s):
    """Precios SIPSA: '  1.260 ' -> 1260 (punto = miles)."""
    s = s.astype(str).str.strip().str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    return pd.to_numeric(s, errors="coerce")


def leer_sipsa(f):
    txt = open(f, encoding="utf-8", errors="replace").read()
    d = pd.read_csv(io.StringIO(txt[txt.index("\nFecha,") + 1:]), dtype=str)
    d.columns = [c.strip() for c in d.columns]
    pc = next(c for c in d.columns if c.startswith("Precio"))
    d = d[["Fecha", "Grupo", "Producto", "Mercado", pc]].rename(columns={pc: "precio"})
    fe = d["Fecha"].str.strip().str.lower().str.extract(r"^([a-z]+)-(\d{2})$")
    d["mes"], d["anio"] = fe[0].map(MESES), 2000 + pd.to_numeric(fe[1], errors="coerce")
    d["precio"] = num_col(d["precio"])
    return d.dropna(subset=["mes", "anio", "precio", "Producto"])


def precios_sipsa():
    fs = [f for f in glob.glob(str(SIPSA / "*.csv")) if ("recios-mayoristas-20" in f or "anex-SIPSA" in f) and "arroz" not in f]
    if not fs:
        print("  SIPSA: no hay archivos en data/raw/SIPSA (correr 00_descargar_datos.py)"); return None
    d = pd.concat([leer_sipsa(f) for f in fs], ignore_index=True).drop_duplicates()
    d["anio"], d["mes"] = d["anio"].astype(int), d["mes"].astype(int)
    d = d[~d["Producto"].str.contains("importad", case=False)]
    d["ambito"] = np.where(d["Mercado"].isin(CFG["sipsa"]["mercados_valle"]), "valle", "nacional")
    mens_v = d[d.ambito == "valle"].groupby(["Producto", "anio", "mes"])["precio"].mean()
    mens_n = d.groupby(["Producto", "anio", "mes"])["precio"].median()
    an = pd.concat([mens_v.groupby(["Producto", "anio"]).agg(["mean", "size"]).assign(ambito="valle"),
                    mens_n.groupby(["Producto", "anio"]).agg(["mean", "size"]).assign(ambito="nacional")]).reset_index()
    an.columns = ["producto_sipsa", "anio", "precio_cop_kg", "n_meses", "ambito"]
    an = an.merge(d.drop_duplicates("Producto")[["Producto", "Grupo"]].rename(columns={"Producto": "producto_sipsa", "Grupo": "grupo"}))
    print(f"  SIPSA: {len(fs)} archivos, {len(d):,} registros, {d.Producto.nunique()} productos, años {d.anio.min()}-{d.anio.max()}")
    return an


def precio_por_producto(an, productos):
    """Precio anual por producto del Valle: mercados del Valle si existen; si no, mediana nacional."""
    filas = []
    deriv = CFG["sipsa"]["factores_derivados"]
    for p in productos:
        if p in deriv:
            patron, factor, tipo = "^" + re.escape(deriv[p]["sipsa"]), deriv[p]["factor"], "derivado"
        elif p in EQUIV_SIPSA:
            patron, factor, tipo = EQUIV_SIPSA[p], 1.0, "directo"
        else:
            continue
        m = an[an.producto_sipsa.str.contains(patron, regex=True)]
        for anio, g in m.groupby("anio"):
            gv = g[g.ambito == "valle"]
            gg, amb = (gv, "valle") if len(gv) else (g[g.ambito == "nacional"], "nacional")
            filas.append(dict(producto=p, anio=anio, precio_cop_kg=gg.precio_cop_kg.mean() * factor, ambito=amb, tipo_precio=tipo,
                              factor=factor, productos_sipsa="; ".join(sorted(gg.producto_sipsa.unique())), n_meses=int(gg.n_meses.max())))
    return pd.DataFrame(filas)


def valor_producto(pp):
    prod = pd.read_csv(CLEAN / "produccion_valle_clean.csv", dtype={"cod_dane": str})
    a, b = CFG["sipsa"]["anios_precio_referencia"]
    ref = (pp[pp.anio.between(a, b)].groupby("producto")
           .agg(precio_ref=("precio_cop_kg", "mean"), tipo_precio=("tipo_precio", "first"), ambito=("ambito", lambda s: s.mode().iat[0])))
    v = prod[["producto", "cod_dane", "municipio", "anio", "produccion_t"]].merge(ref, on="producto", how="left")
    v = v.merge(pp[["producto", "anio", "precio_cop_kg"]].rename(columns={"precio_cop_kg": "precio_corriente_cop_kg"}), on=["producto", "anio"], how="left")
    v["precio_cop_kg"] = v.pop("precio_ref")
    v["valor_cop"] = v.produccion_t * 1000 * v.precio_cop_kg
    v["valor_corriente_cop"] = v.produccion_t * 1000 * v.precio_corriente_cop_kg
    v["tipo_precio"] = v["tipo_precio"].fillna("sin_precio")
    cols = ["producto", "cod_dane", "municipio", "anio", "produccion_t", "precio_cop_kg", "valor_cop",
            "precio_corriente_cop_kg", "valor_corriente_cop", "tipo_precio", "ambito"]
    return v[cols].sort_values(["producto", "cod_dane", "anio"])


def ranking_valor(v):
    lp = pd.read_csv(CLEAN / "lista_productos.csv")
    a, b = CFG["limpieza"]["ventana_activa"]
    w = v[v.anio.between(a, b)].groupby("producto")["valor_cop"].sum(min_count=1)
    r = lp[lp.estado != "excluido"][["producto", "familia", "estado", "ranking_toneladas", "produccion_t_2019_2023"]].copy()
    r["valor_cop_2019_2023"] = r.producto.map(w)
    r["ranking_valor"] = r["valor_cop_2019_2023"].rank(ascending=False, method="first")
    n = CFG["limpieza"]["n_detallados"]
    r["estado_si_ranking_valor"] = np.where(r.ranking_valor <= n, "detallado", "simplificado")
    r["cambia"] = r.estado != r.estado_si_ranking_valor
    return r.sort_values("ranking_valor", na_position="last")


def oni():
    oficial = RAW / "oni.ascii.txt"
    if oficial.exists():
        o = pd.read_csv(oficial, sep=r"\s+")
        o = o.rename(columns={"YR": "Year", "ANOM": "ANOM"}); fuente = "oni.ascii.txt"
    elif glob.glob(str(RAW / "ONI_NOAA_CPC_*.csv")):
        o = pd.read_csv(glob.glob(str(RAW / "ONI_NOAA_CPC_*.csv"))[0]); fuente = "ONI_NOAA_CPC (transcripción)"
    else:
        o = pd.read_csv(glob.glob(str(RAW / "*Nino*.csv"))[0]).rename(columns={"Value": "ANOM"}); fuente = "Monthly ONI Long"
    a = o.groupby("Year")["ANOM"].agg(oni="mean", n_estaciones="size", oni_max="max", oni_min="min").reset_index().rename(columns={"Year": "anio"})
    a = a[a.n_estaciones == 12].copy()
    a["fase"] = np.select([a.oni >= 0.5, a.oni <= -0.5], ["Niño", "Niña"], "neutral")
    print(f"  ONI: fuente {fuente}, años {a.anio.min()}-{a.anio.max()}")
    return a.round(3)


def consumo_faostat():
    f = glob.glob(str(RAW / "FAOSTAT*.csv"))
    if not f: return None
    x = pd.read_csv(f[0])
    x = x[x.Element.str.contains("Food supply quantity")]
    out = x.rename(columns={"Item": "item_faostat", "Item Code (FBS)": "codigo_item", "Year": "anio", "Value": "kg_per_capita_anio", "Flag": "flag", "Area": "pais"})
    print(f"  FAOSTAT: {out.item_faostat.nunique()} ítems, años {out.anio.min()}-{out.anio.max()}")
    return out[["pais", "item_faostat", "codigo_item", "anio", "kg_per_capita_anio", "flag"]]


def poblacion_dane():
    """Acepta un CSV del DANE en data/raw/ con nombre que empiece por 'poblacion' o 'DANE_proyecciones'."""
    fs = glob.glob(str(RAW / "poblacion*.csv")) + glob.glob(str(RAW / "DANE_proyecciones*.csv"))
    if not fs:
        print("  Población: PENDIENTE (falta archivo DANE en data/raw/, ver README)"); return None
    x = pd.read_csv(fs[0], dtype=str)
    low = {c: c.lower() for c in x.columns}
    c_cod = next(c for c in x.columns if "mpio" in low[c] or "cod" in low[c])
    c_an = next(c for c in x.columns if low[c] in ("año", "ano", "anio", "year"))
    c_pob = next(c for c in x.columns if "total" in low[c] or "pobl" in low[c])
    out = pd.DataFrame({"cod_dane": x[c_cod].str.replace(r"\D", "", regex=True).str.zfill(5), "anio": pd.to_numeric(x[c_an]),
                        "poblacion_total": pd.to_numeric(x[c_pob].str.replace(r"[.,\s]", "", regex=True))})
    out = out[out.cod_dane.str.startswith("76")].groupby(["cod_dane", "anio"], as_index=False)["poblacion_total"].sum()
    print(f"  Población: {out.cod_dane.nunique()} municipios, años {out.anio.min()}-{out.anio.max()}")
    return out


def comercio_ica():
    """Resume las inspecciones fitosanitarias ICA (archivos FRONTERA_*) a toneladas por año, producto y puerto."""
    fs = sorted(glob.glob(str(SIPSA / "FRONTERA_*.csv")))
    if not fs:
        print("  FRONTERA: sin archivos crudos; se conserva data/clean/comercio_ica_frontera.csv si existe"); return None
    a_t = {"KILOGRAMOS": 1e-3, "TONELADAS": 1.0, "GRAMOS": 1e-6, "LIBRAS": 0.45359237e-3}
    usa = ["ACTIVIDAD", "TIPO_COMERCIO", "FECHA_INSPECCION", "PUERTO_ENTRADA", "PUERTO_SALIDA", "TIPO_PRODUCTO", "PRODUCTO", "CANTIDAD", "UNIDAD_MEDIDA"]
    partes = []
    for f in fs:
        x = pd.read_csv(f, dtype=str, usecols=usa)
        x = x[x.ACTIVIDAD == "AGRICOLA"]
        x["anio"] = pd.to_datetime(x.FECHA_INSPECCION, dayfirst=True, errors="coerce").dt.year
        x["cantidad"] = pd.to_numeric(x.CANTIDAD.str.replace(",", ".", regex=False), errors="coerce")
        uni = x.UNIDAD_MEDIDA.fillna("").str.upper()
        fac = pd.Series(np.nan, index=x.index)
        for k, v in a_t.items(): fac[uni.str.startswith(k)] = v
        x["toneladas"] = x.cantidad * fac
        x["unidades"] = np.where(uni.str.startswith("UNIDADES"), x.cantidad, np.nan)
        x["puerto"] = np.where(x.TIPO_COMERCIO == "EXPORTACIONES", x.PUERTO_SALIDA, x.PUERTO_ENTRADA)
        g = x.groupby(["anio", "TIPO_COMERCIO", "TIPO_PRODUCTO", "PRODUCTO", "puerto"], dropna=False).agg(
            toneladas=("toneladas", "sum"), unidades=("unidades", "sum"), n_registros=("cantidad", "size")).reset_index()
        partes.append(g)
    out = pd.concat(partes).groupby(["anio", "TIPO_COMERCIO", "TIPO_PRODUCTO", "PRODUCTO", "puerto"], dropna=False).sum().reset_index()
    out.columns = ["anio", "tipo_comercio", "tipo_producto", "producto_ica", "puerto", "toneladas", "unidades", "n_registros"]
    out["anio"] = out.anio.astype("Int64")
    out["estado_dato"] = np.select([out.anio <= 2023, out.anio <= 2025], ["cerrado", "provisional"], "provisional/preliminar")
    print(f"  FRONTERA: {len(fs)} archivos -> {len(out):,} filas agregadas, años {out.anio.min()}-{out.anio.max()}")
    return out


def main():
    an = precios_sipsa()
    if an is not None:
        an.round(1).to_csv(CLEAN / "precios_sipsa_anual.csv", index=False, encoding="utf-8-sig")
        lp = pd.read_csv(CLEAN / "lista_productos.csv")
        pp = precio_por_producto(an, lp.producto)
        pp.round(1).to_csv(CLEAN / "precio_producto_anual.csv", index=False, encoding="utf-8-sig")
        v = valor_producto(pp)
        v.round({"precio_cop_kg": 2, "precio_corriente_cop_kg": 2, "valor_cop": 0, "valor_corriente_cop": 0}).to_csv(CLEAN / "valor_producto.csv", index=False, encoding="utf-8-sig")
        sin = sorted(lp.loc[(lp.estado != "excluido") & ~lp.producto.isin(pp.producto), "producto"])
        print(f"  Valor: {pp.producto.nunique()} productos con precio; activos sin precio ({len(sin)}): {', '.join(sin)}")

        a, b = CFG["limpieza"]["ventana_activa"]
        prom = pd.read_csv(CLEAN / "produccion_promedio_municipio.csv", dtype={"cod_dane": str}).drop(columns=["valor_prom_cop_2019_2023"], errors="ignore")
        vm = v[v.anio.between(a, b)].groupby(["cod_dane", "producto"])["valor_cop"].sum(min_count=1) / (b - a + 1)
        prom["valor_prom_cop_2019_2023"] = prom.set_index(["cod_dane", "producto"]).index.map(vm)
        prom.round(1).to_csv(CLEAN / "produccion_promedio_municipio.csv", index=False, encoding="utf-8-sig")

        r = ranking_valor(v)
        r.to_csv(RES / "ranking_valor_vs_toneladas.csv", index=False, encoding="utf-8-sig")
        print(f"  Ranking por valor: {int(r.cambia.sum())} productos cambiarían de grupo")

    oni().to_csv(CLEAN / "oni.csv", index=False, encoding="utf-8-sig")
    c = consumo_faostat()
    if c is not None: c.to_csv(CLEAN / "consumo_percapita.csv", index=False, encoding="utf-8-sig")
    p = poblacion_dane()
    if p is not None: p.to_csv(CLEAN / "poblacion_municipal.csv", index=False, encoding="utf-8-sig")
    ci = comercio_ica()
    if ci is not None: ci.round(3).to_csv(CLEAN / "comercio_ica_frontera.csv", index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    main()
