"""Tarea 1 (Ceyni): carga del Dataset 1, armonización de categorías y lista de productos.
Uso:  python src/01_limpieza.py   (desde la raíz del repo)
Entradas : data/raw/Consolidado_agrícola_..._cultivos_permanentes_...csv
Salidas  : data/clean/produccion_valle_clean.csv  (y .parquet si hay pyarrow)
           data/clean/lista_productos.csv
           data/results/decisiones_armonizacion.csv
"""
from pathlib import Path
import glob
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, CLEAN, RES = ROOT / "data/raw", ROOT / "data/clean", ROOT / "data/results"
CLEAN.mkdir(parents=True, exist_ok=True); RES.mkdir(parents=True, exist_ok=True)

# ---- Parámetros editables ---------------------------------------------------
N_DETALLADOS = 22                      # productos que se modelan en detalle
VENTANA_ACTIVA = (2019, 2023)          # un producto sin producción aquí se excluye
# Criterio PROVISIONAL del ranking de detallados: toneladas acumuladas en la
# ventana. Cuando exista valor_producto.csv (SIPSA) cambiar a valor.
HARMONIZAR = {                         # producto original -> producto armonizado
    "Aguacate Hass": "Aguacate",
    "Limón": "Cítricos", "Mandarina": "Cítricos", "Naranja": "Cítricos",
}
MOTIVOS = {
    "Aguacate Hass": "Separado desde 2020; se suma a 'Aguacate' para conservar la serie desde 2000.",
    "Limón": "Desagregado desde 2021 (antes dentro de 'Cítricos'); se suma a 'Cítricos'.",
    "Mandarina": "Desagregado desde 2021 (antes dentro de 'Cítricos'); se suma a 'Cítricos'.",
    "Naranja": "Desagregado desde 2021 (antes dentro de 'Cítricos'); se suma a 'Cítricos'.",
}

def num(s: pd.Series) -> pd.Series:
    """Los CSV traen separador de miles con coma ('2,000', '76,001', '1,139.4')."""
    return pd.to_numeric(s.astype(str).str.replace(",", "", regex=False), errors="coerce")

def main():
    f = glob.glob(str(RAW / "*permanentes*.csv"))[0]
    df = pd.read_csv(f, dtype=str)
    n_raw = len(df)
    df["anio"] = num(df["Año"]).astype(int)
    df["cod_dane"] = num(df["Id_municipio"]).astype(int).astype(str).str.zfill(5)
    for a, b in [("Hectareas_sembradas", "ha_sembradas"), ("Hectareas_cosechadas", "ha_cosechadas"),
                 ("Produccion_toneladas", "produccion_t")]:
        df[b] = num(df[a])
    df = df.rename(columns={"Municipio": "municipio", "Cultivo": "producto_original", "Tipo_cultivo": "familia"})
    df = df[["anio", "cod_dane", "municipio", "producto_original", "familia", "ha_sembradas", "ha_cosechadas", "produccion_t"]]

    # 1) duplicados exactos (se borran ANTES de armonizar)
    n_dup = int(df.duplicated().sum())
    df = df.drop_duplicates().copy()

    # 2) escritura de familia + cartuchos a flores
    df["familia"] = df["familia"].replace({"Raíces y tubérculos": "Raíces y Tubérculos"})
    df.loc[df["producto_original"] == "Cartuchos", "familia"] = "Flores"

    # 3) armonización de productos y SUMA de lo que queda con la misma llave
    df["producto"] = df["producto_original"].replace(HARMONIZAR)
    fam = df.groupby("producto")["familia"].agg(lambda s: s.mode().iat[0])
    g = (df.groupby(["anio", "cod_dane", "municipio", "producto"], as_index=False)
           [["ha_sembradas", "ha_cosechadas", "produccion_t"]].sum())
    g["familia"] = g["producto"].map(fam)
    g["rendimiento_t_ha"] = (g["produccion_t"] / g["ha_cosechadas"]).where(g["ha_cosechadas"] > 0)
    assert not g.duplicated(["anio", "cod_dane", "producto"]).any()
    g = g.sort_values(["producto", "cod_dane", "anio"]).reset_index(drop=True)

    # 4) lista de productos
    a, b = VENTANA_ACTIVA
    w = g[g.anio.between(a, b)]
    prod_w = w.groupby("producto")["produccion_t"].sum()
    lista = (g.groupby("producto").agg(familia=("familia", "first"), anio_ini=("anio", "min"), anio_fin=("anio", "max"),
                                       n_municipios=("cod_dane", "nunique"), n_filas=("anio", "size")).reset_index())
    lista["produccion_t_2019_2023"] = lista["producto"].map(prod_w).fillna(0.0)
    lista["n_municipios_2019_2023"] = lista["producto"].map(w[w.produccion_t > 0].groupby("producto")["cod_dane"].nunique()).fillna(0).astype(int)
    activos = lista[lista.produccion_t_2019_2023 > 0].sort_values("produccion_t_2019_2023", ascending=False)
    det = set(activos.head(N_DETALLADOS)["producto"])
    lista["estado"] = lista.apply(lambda r: "excluido" if r.produccion_t_2019_2023 <= 0
                                  else ("detallado" if r["producto"] in det else "simplificado"), axis=1)
    lista["ranking_toneladas"] = lista["produccion_t_2019_2023"].rank(ascending=False, method="first").astype(int)
    lista = lista.sort_values(["estado", "ranking_toneladas"]).reset_index(drop=True)

    # 5) decisiones de armonización (para Carlos)
    filas = [("Separador de miles en el CSV", "Todas", "Se limpian comas antes de convertir (año, id municipio, hectáreas, toneladas).", "Evita años como '2,000' y códigos DANE mal formados."),
             ("Código DANE", "Id_municipio", "Se convierte a texto de 5 dígitos (zfill).", "Coincide con DIVIPOLA para los 42 municipios.")]
    filas.append(("Filas duplicadas exactas", "Brevo, Té", f"Se eliminan {n_dup} filas idénticas (antes de armonizar).", "Duplicado de captura; no aporta información."))
    filas.append(("Escritura de familia", "Raíces y tubérculos", "'Raíces y tubérculos' -> 'Raíces y Tubérculos'.", "Dos escrituras de la misma familia."))
    filas.append(("Cartuchos", "Cartuchos", "Se reclasifica de Raíces y Tubérculos a Flores.", "Es una flor; queda excluido por no tener producción 2019-2023."))
    for k, v in HARMONIZAR.items():
        filas.append(("Cambio de desagregación", k, f"Se suma a '{v}'.", MOTIVOS[k]))
    filas.append(("Rendimiento", "Todos", "Se recalcula como producción / ha cosechadas tras sumar.", "El rendimiento original no es sumable."))
    filas.append(("Productos sin producción 2019-2023", f"{(lista.estado=='excluido').sum()} productos", "Se excluyen del modelado.", "No hay producción reciente que pronosticar."))
    pd.DataFrame(filas, columns=["decision", "producto_o_campo", "accion", "motivo"]).to_csv(RES / "decisiones_armonizacion.csv", index=False, encoding="utf-8-sig")

    # 6) guardar
    g.to_csv(CLEAN / "produccion_valle_clean.csv", index=False, encoding="utf-8-sig")
    try:
        g.to_parquet(CLEAN / "produccion_valle_clean.parquet", index=False)
    except Exception as e:
        print("parquet omitido:", e)
    lista.to_csv(CLEAN / "lista_productos.csv", index=False, encoding="utf-8-sig")

    # 7) verificación contra la propuesta
    print(f"filas crudas {n_raw} | duplicados exactos {n_dup} | filas limpias {len(g)}")
    print(f"cultivos originales {df.producto_original.nunique()} -> armonizados {g['producto'].nunique()}")
    print("estado:", lista.estado.value_counts().to_dict(), "| municipios:", g.cod_dane.nunique(), "| años", g.anio.min(), g.anio.max())

if __name__ == "__main__":
    main()
