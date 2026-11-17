from pathlib import Path
import glob
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW, CLEAN = ROOT / "data/raw", ROOT / "data/clean"
FACTOR_RUTA, VEL_KMH = 1.4, 45.0

# Destinos fuera de DIVIPOLA o con punto específico (lat, lon). El aeropuerto se cargó a mano.
DESTINOS = {
    "DEST_BUENAVENTURA":  ("Puerto de Buenaventura", "76109", None),
    "DEST_AEROPUERTO_PALMIRA": ("Aeropuerto Alfonso Bonilla Aragón (Palmira)", None, (3.5432, -76.3816)),
    "DEST_CALI":          ("Mercado Cali", "76001", None),
    "DEST_BOGOTA":        ("Mercado Bogotá", "11001", None),
    "DEST_MEDELLIN":      ("Mercado Medellín", "05001", None),
}

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0088
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi, dl = p2 - p1, np.radians(lon2) - np.radians(lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))

def main():
    dv = pd.read_csv(glob.glob(str(RAW / "DIVIPOLA*.csv"))[0], dtype=str)
    dv.columns = ["cod_dpto", "dpto", "cod_dane", "nombre", "tipo", "lon", "lat"]
    for c in ("lon", "lat"):
        dv[c] = pd.to_numeric(dv[c].str.replace(",", ".", regex=False))
    prod = pd.read_csv(CLEAN / "produccion_valle_clean.csv", dtype={"cod_dane": str})
    ids = sorted(prod.cod_dane.unique())
    mun = dv[dv.cod_dane.isin(ids)][["cod_dane", "nombre", "lat", "lon"]].copy()
    nom = prod.drop_duplicates("cod_dane").set_index("cod_dane")["municipio"]
    mun["municipio"] = mun.cod_dane.map(nom)
    mun = mun[["cod_dane", "municipio", "lat", "lon"]].sort_values("cod_dane").reset_index(drop=True)
    assert len(mun) == 42, len(mun)
    mun.to_csv(CLEAN / "municipios_coordenadas.csv", index=False, encoding="utf-8-sig")

    nodos = {r.cod_dane: (r.lat, r.lon) for r in mun.itertuples()}
    dest = []
    for did, (nombre, cod, ll) in DESTINOS.items():
        if ll is None:
            r = dv[dv.cod_dane == cod].iloc[0]; ll = (r.lat, r.lon)
        dest.append((did, nombre, ll[0], ll[1]))
    pd.DataFrame(dest, columns=["id_destino", "nombre", "lat", "lon"]).to_csv(CLEAN / "destinos_coordenadas.csv", index=False, encoding="utf-8-sig")

    filas = []
    for o, (la, lo) in nodos.items():
        for d, (lb, lb2) in list(nodos.items()):
            km = 0.0 if o == d else haversine_km(la, lo, lb, lb2) * FACTOR_RUTA
            filas.append((o, d, round(km / VEL_KMH * 60, 1), round(km, 1), "aproximado"))
        for did, _, lb, lb2 in dest:
            km = haversine_km(la, lo, lb, lb2) * FACTOR_RUTA
            filas.append((o, did, round(km / VEL_KMH * 60, 1), round(km, 1), "aproximado"))
    m = pd.DataFrame(filas, columns=["origen", "destino", "minutos", "distancia_km", "metodo"])
    m.to_csv(CLEAN / "matriz_tiempos.csv", index=False, encoding="utf-8-sig")
    n_esp = 42 * 42 + 42 * len(DESTINOS)
    print(f"matriz: {len(m)} filas (esperadas {n_esp}) | huecos: {m.minutos.isna().sum()}")

    # Producción promedio 2019-2023 por municipio y producto (toneladas; se pondera por valor cuando exista SIPSA)
    lp = pd.read_csv(CLEAN / "lista_productos.csv")
    w = prod[prod.anio.between(2019, 2023) & prod["producto"].isin(lp.loc[lp.estado != "excluido", "producto"])]
    pp = (w.groupby(["cod_dane", "municipio", "producto"])["produccion_t"].sum() / 5).rename("prod_prom_t_2019_2023").reset_index()
    pp.to_csv(CLEAN / "produccion_promedio_municipio.csv", index=False, encoding="utf-8-sig")
    print("prod promedio:", pp.shape, "| municipios con producción:", pp.cod_dane.nunique())

if __name__ == "__main__":
    main()
