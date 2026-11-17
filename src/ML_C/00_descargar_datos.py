"""Descarga y descomprime los datos crudos pesados (data/raw/SIPSA) que no se guardan en Git.

Uso:
    python src/ML_C/00_descargar_datos.py               # descarga el zip del Release y lo descomprime
    python src/ML_C/00_descargar_datos.py --zip RUTA    # usa un zip ya descargado (Drive, USB, etc.)
    python src/ML_C/00_descargar_datos.py --empaquetar  # (solo quien tiene los datos) crea el zip para subirlo
"""
import hashlib, sys, urllib.request, zipfile
from pathlib import Path
from common import CFG, RAW

DESTINO = RAW / "SIPSA"
ZIP_LOCAL = RAW / CFG["datos_raw"]["zip_nombre"]


def sha256(f):
    h = hashlib.sha256()
    with open(f, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def ya_existe():
    return DESTINO.exists() and any(DESTINO.glob("FRONTERA_*.csv")) and any(DESTINO.glob("*recios-mayoristas*.csv"))


def descargar(url, f):
    print(f"Descargando {url}\n  -> {f}")
    with urllib.request.urlopen(url) as r, open(f, "wb") as out:
        total, n = int(r.headers.get("Content-Length", 0)), 0
        while chunk := r.read(1 << 20):
            out.write(chunk); n += len(chunk)
            if total: print(f"\r  {n / 1e6:,.0f} / {total / 1e6:,.0f} MB", end="")
    print()


def descomprimir(f):
    esperado = CFG["datos_raw"].get("zip_sha256") or ""
    if esperado and sha256(f) != esperado:
        sys.exit(f"El sha256 de {f.name} no coincide con config/ML_C/parametros.yaml; vuelve a descargarlo.")
    with zipfile.ZipFile(f) as z:
        z.extractall(RAW)                      # el zip contiene la carpeta SIPSA/
    print(f"Descomprimido en {DESTINO} ({len(list(DESTINO.glob('*.csv')))} archivos)")


def empaquetar():
    f = RAW / CFG["datos_raw"]["zip_nombre"]
    with zipfile.ZipFile(f, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(DESTINO.glob("*.csv")):
            z.write(p, f"SIPSA/{p.name}")
    print(f"Creado {f} ({f.stat().st_size / 1e6:,.1f} MB)\nsha256: {sha256(f)}")
    print("Súbelo como asset del Release 'datos-v1' en GitHub y pega el sha256 en config/ML_C/parametros.yaml.")


def main():
    args = sys.argv[1:]
    if "--empaquetar" in args:
        return empaquetar()
    if ya_existe() and "--forzar" not in args:
        print(f"Los datos ya están en {DESTINO}; nada que hacer (usa --forzar para repetir).")
        return
    if "--zip" in args:
        f = Path(args[args.index("--zip") + 1]).expanduser()
    elif ZIP_LOCAL.exists():
        f = ZIP_LOCAL
    else:
        f = ZIP_LOCAL
        try:
            descargar(CFG["datos_raw"]["zip_url"], f)
        except Exception as e:
            f.unlink(missing_ok=True)
            print(f"AVISO: no se pudo descargar ({e}).\n  Las tablas procesadas de data/clean/ ya están en el repo, así que el resto del módulo\n"
                  "  corre igual. Solo necesitas el zip para regenerar precios/comercio desde cero.")
            return
    descomprimir(f)


if __name__ == "__main__":
    main()
