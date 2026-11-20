"""Valida la ingesta cruda antes de ejecutar el pipeline.

Revisa las ocho fuentes del proyecto: existencia, codificación, columnas
esperadas, tipos, rangos, nulos, duplicados y conteos mínimos. Escribe un log
en data/logs/ingesta_YYYYMMDD.log y un resumen JSON para auditoría.

Uso:
    python src/ML_C/00b_validar_ingesta.py
    python src/ML_C/00b_validar_ingesta.py --estricto   # OMITIDA también falla
    python src/ML_C/00b_validar_ingesta.py --json data/logs/ingesta_ultima.json
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
CLEAN = ROOT / "data" / "clean"
LOGS = ROOT / "data" / "logs"
SIPSA = RAW / "SIPSA"

OK, FALLA, OMITIDA = "OK", "FALLA", "OMITIDA"


@dataclass
class Resultado:
    fuente: str
    estado: str
    detalle: str
    filas: int | None = None
    archivos: int | None = None
    avisos: list[str] = field(default_factory=list)


def _cod_dane(valor: object) -> str:
    return re.sub(r"\D", "", str(valor)).zfill(5)


def _leer_gobernacion(patron: str, nombre: str) -> Resultado:
    archivos = sorted(RAW.glob(patron))
    if not archivos:
        return Resultado(nombre, FALLA, f"No se encontró data/raw/{patron}")
    avisos, filas = [], []
    columnas = {"Año", "Id_municipio", "Municipio", "Cultivo", "Produccion_toneladas"}
    for archivo in archivos:
        try:
            df = pd.read_csv(
                archivo,
                encoding="utf-8-sig",
                dtype={"Id_municipio": str},
                thousands=",",
                low_memory=False,
            )
        except UnicodeDecodeError:
            return Resultado(nombre, FALLA, f"{archivo.name}: no es UTF-8; revisar codificación")
        faltantes = columnas - set(df.columns)
        if faltantes:
            return Resultado(nombre, FALLA, f"{archivo.name}: faltan columnas {sorted(faltantes)}")
        df["cod_dane"] = df["Id_municipio"].map(_cod_dane)
        df["anio"] = pd.to_numeric(df["Año"], errors="coerce")
        df["produccion_t"] = pd.to_numeric(df["Produccion_toneladas"], errors="coerce")
        if df["anio"].isna().any() or not df["anio"].between(2000, 2023).all():
            return Resultado(nombre, FALLA, f"{archivo.name}: años fuera de 2000-2023")
        if df["cod_dane"].nunique() != 42:
            return Resultado(nombre, FALLA,
                             f"{archivo.name}: {df['cod_dane'].nunique()} municipios (esperados 42)")
        if (df["produccion_t"].dropna() < 0).any():
            return Resultado(nombre, FALLA, f"{archivo.name}: producción negativa")
        claves = ["anio", "cod_dane", "Cultivo"] + (["Ciclo"] if "Ciclo" in df else [])
        exactos = int(df.duplicated().sum())
        duplicados_llave = int(df.duplicated(claves).sum())
        if exactos:
            avisos.append(f"{archivo.name}: {exactos} filas duplicadas exactas "
                          "(01_limpieza.py las elimina antes de armonizar)")
        if duplicados_llave > exactos:
            avisos.append(f"{archivo.name}: {duplicados_llave - exactos} duplicados de llave "
                          f"{claves} con valores distintos; revisar si se usa esta fuente")
        nulos = int(df[list(columnas)].isna().sum().sum())
        if nulos:
            avisos.append(f"{archivo.name}: {nulos} nulos en columnas clave")
        filas.append(len(df))
    return Resultado(nombre, OK, f"{len(archivos)} archivo(s); 42 municipios; 2000-2023",
                     filas=sum(filas), archivos=len(archivos), avisos=avisos)


def _leer_sipsa() -> Resultado:
    precios = sorted(SIPSA.glob("anex-SIPSA*.csv")) + sorted(SIPSA.glob("series-historicas*.csv"))
    if not precios:
        return Resultado("SIPSA precios", FALLA,
                         "No hay CSV de precios en data/raw/SIPSA (correr 00_descargar_datos.py)")
    if len(precios) < 12:
        return Resultado("SIPSA precios", FALLA,
                         f"Solo {len(precios)} archivos mensuales; se esperan al menos 12")
    muestra, avisos = [], []
    for archivo in precios[:4]:
        encabezado = None
        with open(archivo, encoding="utf-8-sig", errors="replace") as fh:
            for i, linea in enumerate(fh):
                if linea.startswith("Fecha,") or linea.startswith('"Fecha"'):
                    encabezado = i
                    break
        if encabezado is None:
            return Resultado("SIPSA precios", FALLA,
                             f"{archivo.name}: no se encontró el encabezado 'Fecha,'")
        df = pd.read_csv(archivo, encoding="utf-8-sig", skiprows=encabezado, nrows=2000)
        df.columns = [c.strip() for c in df.columns]
        requeridas = {"Fecha", "Producto", "Mercado"}
        if not requeridas.issubset(df.columns):
            return Resultado("SIPSA precios", FALLA,
                             f"{archivo.name}: faltan columnas {sorted(requeridas - set(df.columns))}")
        precio = next((c for c in df.columns if c.startswith("Precio")), None)
        if precio is None:
            return Resultado("SIPSA precios", FALLA, f"{archivo.name}: falta columna de precio")
        if df["Fecha"].isna().any() or df["Producto"].isna().any():
            avisos.append(f"{archivo.name}: nulos en Fecha/Producto")
        muestra.append(len(df))

    frontera = sorted(SIPSA.glob("FRONTERA_*.csv"))
    if not frontera:
        return Resultado("SIPSA precios / ICA", FALLA,
                         "No hay archivos FRONTERA_*.csv (comercio ICA)")
    columnas_f = {"ACTIVIDAD", "TIPO_COMERCIO", "FECHA_INSPECCION", "PRODUCTO",
                  "CANTIDAD", "UNIDAD_MEDIDA"}
    for archivo in frontera[:2]:
        df = pd.read_csv(archivo, encoding="utf-8-sig", nrows=2000)
        faltantes = columnas_f - set(df.columns)
        if faltantes:
            return Resultado("SIPSA precios / ICA", FALLA,
                             f"{archivo.name}: faltan columnas {sorted(faltantes)}")
        cantidad = pd.to_numeric(df["CANTIDAD"], errors="coerce")
        if cantidad.isna().mean() > 0.05:
            avisos.append(f"{archivo.name}: >5 % de CANTIDAD no numérica")
    return Resultado("SIPSA precios / ICA", OK,
                     f"{len(precios)} archivos de precios y {len(frontera)} de FRONTERA",
                     filas=sum(muestra), archivos=len(precios) + len(frontera), avisos=avisos)


def _leer_divipola() -> Resultado:
    archivos = sorted(RAW.glob("DIVIPOLA*.csv"))
    if not archivos:
        return Resultado("DIVIPOLA", FALLA, "No se encontró DIVIPOLA en data/raw/")
    df = pd.read_csv(archivos[0], encoding="utf-8-sig", dtype=str)
    columnas = set(df.columns)
    esperadas = {"Código Departamento", "Código Municipio", "Nombre Municipio"}
    if not esperadas.issubset(columnas):
        # La ficha del DANE cambia nombres entre vigencias; se acepta una variante.
        esperadas = {"COD_DPTO", "COD_MUNICIPIO", "NOM_MPIO"}
    if not esperadas.issubset(columnas):
        return Resultado("DIVIPOLA", FALLA,
                         f"{archivos[0].name}: columnas no reconocidas {sorted(columnas)[:8]}")
    col_mun = "Código Municipio" if "Código Municipio" in columnas else "COD_MUNICIPIO"
    codigos = df[col_mun].map(_cod_dane)
    valle = codigos[codigos.str.startswith("76")]
    if valle.nunique() < 42:
        return Resultado("DIVIPOLA", FALLA,
                         f"Solo {valle.nunique()} municipios del Valle (esperados 42)")
    if not valle.str.len().eq(5).all():
        return Resultado("DIVIPOLA", FALLA, "Hay códigos DANE que no tienen 5 dígitos")
    return Resultado("DIVIPOLA", OK, f"{valle.nunique()} municipios del Valle",
                     filas=len(df), archivos=1)


def _leer_matriz_tiempos() -> Resultado:
    ruta = CLEAN / "matriz_tiempos.csv"
    if not ruta.exists():
        return Resultado("OSM / matriz de tiempos", FALLA,
                         "Falta data/clean/matriz_tiempos.csv")
    df = pd.read_csv(ruta, encoding="utf-8-sig", dtype={"origen": str, "destino": str})
    requeridas = {"origen", "destino", "minutos", "distancia_km", "metodo"}
    if not requeridas.issubset(df.columns):
        return Resultado("OSM / matriz de tiempos", FALLA,
                         f"Faltan columnas {sorted(requeridas - set(df.columns))}")
    if df[["origen", "destino", "minutos"]].isna().any().any():
        return Resultado("OSM / matriz de tiempos", FALLA, "Hay nulos en origen/destino/minutos")
    if (df["minutos"] < 0).any() or (df["minutos"] > 24 * 60).any():
        return Resultado("OSM / matriz de tiempos", FALLA, "Minutos fuera del rango 0-1440")
    if df["origen"].nunique() != 42:
        return Resultado("OSM / matriz de tiempos", FALLA,
                         f"{df['origen'].nunique()} orígenes (esperados 42)")
    metodos = sorted(df["metodo"].dropna().unique())
    avisos = []
    if "aproximado" in metodos:
        avisos.append("La matriz es aproximada (línea recta × 1,4 / 45 km/h); OSM/OSRM no está incorporado")
    return Resultado("OSM / matriz de tiempos", OK,
                     f"{len(df):,} pares; métodos {metodos}",
                     filas=len(df), archivos=1, avisos=avisos)


def _leer_faostat() -> Resultado:
    archivos = sorted(RAW.glob("FAOSTAT*.csv"))
    if not archivos:
        return Resultado("FAOSTAT", FALLA, "No se encontró FAOSTAT en data/raw/")
    df = pd.read_csv(archivos[0], encoding="utf-8-sig")
    requeridas = {"Area", "Item", "Year", "Value", "Element"}
    if not requeridas.issubset(df.columns):
        return Resultado("FAOSTAT", FALLA,
                         f"{archivos[0].name}: faltan columnas {sorted(requeridas - set(df.columns))}")
    df = df[df["Element"].astype(str).str.contains("Food supply quantity", case=False)]
    if df.empty:
        return Resultado("FAOSTAT", FALLA, "No hay filas de 'Food supply quantity'")
    if not (df["Area"] == "Colombia").all():
        return Resultado("FAOSTAT", FALLA, "Hay filas de países distintos de Colombia")
    anios = pd.to_numeric(df["Year"], errors="coerce")
    if anios.isna().any() or not anios.between(2010, 2026).all():
        return Resultado("FAOSTAT", FALLA, "Años fuera de 2010-2026")
    if (pd.to_numeric(df["Value"], errors="coerce").dropna() < 0).any():
        return Resultado("FAOSTAT", FALLA, "Valores negativos de consumo")
    return Resultado("FAOSTAT", OK,
                     f"{df['Item'].nunique()} ítems; {int(anios.min())}-{int(anios.max())}",
                     filas=len(df), archivos=1)


def _leer_noaa() -> Resultado:
    archivos = sorted(RAW.glob("ONI_NOAA_CPC_*.csv")) + sorted(RAW.glob("*Nino*.csv"))
    if not archivos:
        return Resultado("NOAA ONI", FALLA, "No se encontró el ONI de NOAA en data/raw/")
    df = pd.read_csv(archivos[0], encoding="utf-8-sig")
    requeridas = {"Year", "MonthNum", "ANOM"}
    if not requeridas.issubset(df.columns):
        return Resultado("NOAA ONI", FALLA,
                         f"{archivos[0].name}: faltan columnas {sorted(requeridas - set(df.columns))}")
    if df.duplicated(["Year", "MonthNum"]).any():
        return Resultado("NOAA ONI", FALLA, "Hay duplicados año-mes")
    meses = df.groupby("Year")["MonthNum"].nunique()
    ultimo = int(df["Year"].max())
    incompletos = meses[(meses != 12) & (meses.index != ultimo)]
    if not incompletos.empty:
        return Resultado("NOAA ONI", FALLA,
                         f"Años intermedios sin 12 meses: {incompletos.index.tolist()[:5]}")
    avisos = []
    if meses.loc[ultimo] != 12:
        avisos.append(f"{ultimo} está incompleto ({meses.loc[ultimo]} meses); es el año en curso")
    if pd.to_numeric(df["ANOM"], errors="coerce").isna().any():
        return Resultado("NOAA ONI", FALLA, "Hay anomalías no numéricas")
    return Resultado("NOAA ONI", OK,
                     f"{int(df.Year.min())}-{ultimo}; 12 meses por año (último año parcial)",
                     filas=len(df), archivos=len(archivos), avisos=avisos)


def _leer_comercio() -> Resultado:
    """Comtrade no se incorporó; ICA FRONTERA cubre el comercio exterior."""
    comtrade = list(RAW.glob("*comtrade*")) + list(RAW.glob("*COMTRADE*"))
    ica = CLEAN / "comercio_ica_frontera.csv"
    if comtrade:
        return Resultado("Comercio (Comtrade/ICA)", OK,
                         f"Comtrade: {len(comtrade)} archivo(s) local(es)")
    if not ica.exists():
        return Resultado("Comercio (Comtrade/ICA)", FALLA,
                         "No hay Comtrade local ni data/clean/comercio_ica_frontera.csv")
    df = pd.read_csv(ica, encoding="utf-8-sig", dtype={"cod_dane": str})
    requeridas = {"anio", "tipo_comercio", "producto_ica", "puerto", "toneladas"}
    if not requeridas.issubset(df.columns):
        return Resultado("Comercio (Comtrade/ICA)", FALLA,
                         f"comercio_ica_frontera.csv: faltan {sorted(requeridas - set(df.columns))}")
    if (df["toneladas"].dropna() < 0).any():
        return Resultado("Comercio (Comtrade/ICA)", FALLA, "Toneladas negativas en comercio ICA")
    return Resultado("Comercio (Comtrade/ICA)", OK,
                     "Comtrade no incorporado; ICA FRONTERA cubre exportaciones/importaciones",
                     filas=len(df), archivos=1,
                     avisos=["Comtrade se evaluó pero no se usó: el comercio exterior se tomó de ICA FRONTERA"])


def _leer_eva() -> Resultado:
    archivo = next(iter(RAW.glob("doi_*EVA*.csv")), None)
    if archivo is None:
        return Resultado("EVA (referencia)", OMITIDA,
                         "No se encontró la referencia EVA/CEDE; los consolidados de Gobernación ya la incorporan")
    texto = archivo.read_text(encoding="utf-8", errors="replace")
    if len(texto.strip()) < 10:
        return Resultado("EVA (referencia)", FALLA, f"{archivo.name}: archivo vacío")
    return Resultado("EVA (referencia)", OK,
                     "Archivo de referencia bibliográfica (no contiene microdatos); "
                     "los consolidados de Gobernación son la fuente operativa",
                     filas=1, archivos=1)


def validar(estricto: bool = False) -> list[Resultado]:
    resultados = [
        _leer_gobernacion("Consolidado_agr*permanentes*.csv", "Gobernación (permanentes)"),
        _leer_gobernacion("Consolidado_agr*transitorios*.csv", "Gobernación (transitorios)"),
        _leer_eva(),
        _leer_sipsa(),
        _leer_divipola(),
        _leer_matriz_tiempos(),
        _leer_faostat(),
        _leer_noaa(),
        _leer_comercio(),
    ]
    if estricto:
        for r in resultados:
            if r.estado == OMITIDA:
                r.estado = FALLA
    return resultados


def _configurar_log() -> Path:
    LOGS.mkdir(parents=True, exist_ok=True)
    ruta = LOGS / f"ingesta_{datetime.now():%Y%m%d}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[logging.FileHandler(ruta, encoding="utf-8")],
        force=True,
    )
    return ruta


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--estricto", action="store_true", help="Trata OMITIDA como falla")
    ap.add_argument("--json", type=Path, default=LOGS / "ingesta_ultima.json",
                    help="Ruta del resumen JSON")
    ap.add_argument("--sin-log", action="store_true", help="No escribe log en data/logs/")
    args = ap.parse_args(argv)

    ruta_log = None if args.sin_log else _configurar_log()
    logging.info("Inicio de validación de ingesta")
    resultados = validar(estricto=args.estricto)

    print("\n" + "=" * 78)
    print("VALIDACIÓN DE INGESTA - MINGADATA")
    print("=" * 78)
    for r in resultados:
        filas = f"{r.filas:,}" if r.filas is not None else "-"
        print(f"[{r.estado:7s}] {r.fuente:32s} filas={filas:>9s}  {r.detalle}")
        for aviso in r.avisos:
            print(f"          AVISO: {aviso}")
        logging.info("%s | %s | filas=%s | %s | avisos=%s",
                     r.estado, r.fuente, filas, r.detalle, "; ".join(r.avisos))

    fallas = [r for r in resultados if r.estado == FALLA]
    omitidas = [r for r in resultados if r.estado == OMITIDA]
    resumen = {
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "estricto": args.estricto,
        "total": len(resultados),
        "ok": sum(r.estado == OK for r in resultados),
        "fallas": len(fallas),
        "omitidas": len(omitidas),
        "resultados": [r.__dict__ for r in resultados],
        "log": str(ruta_log) if ruta_log else None,
    }
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")

    print("-" * 78)
    print(f"OK: {resumen['ok']} | FALLAS: {resumen['fallas']} | OMITIDAS: {resumen['omitidas']}")
    print(f"Resumen JSON: {args.json.relative_to(ROOT)}")
    if ruta_log:
        print(f"Log: {ruta_log.relative_to(ROOT)}")
    if fallas:
        print("\nCorrige las fuentes marcadas como FALLA antes de continuar.", file=sys.stderr)
        logging.error("Validación con %d fallas", len(fallas))
        return 1
    logging.info("Validación completada sin fallas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
