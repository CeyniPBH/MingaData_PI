"""
Orquestador reproducible de los módulos de arendonc2.

Ejecuta en orden:
  0. Descarga geometrías GADM (si faltan).
  1. Población municipal DANE (si falta).
  2. Tarea #2 — zonas de acopio.
  3. Tarea #3 — excedentes.
  4. Tarea #4 — escenarios de optimización.
  5. Demostración del adaptador para Samuel.

Uso: python src/arendonc2/ejecutar_todo.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from arendonc2 import common
from arendonc2 import descargar_geometrias, poblacion
from arendonc2 import zonas_acopio, excedentes, escenarios
from arendonc2.adaptador import preparar_para_solver


def main():
    t0 = time.time()
    cfg = common.cargar_config()

    print("\n### 0. Geometrías GADM ###")
    descargar_geometrias.main()

    print("\n### 1. Población municipal DANE ###")
    poblacion.descargar()
    poblacion.generar(cfg["excedentes"]["anios"])

    print("\n### 2. Tarea #2 — Zonas de acopio ###")
    zonas_acopio.ejecutar(cfg, guardar=True)

    print("\n### 3. Tarea #3 — Excedentes ###")
    excedentes.ejecutar(cfg, guardar=True)

    print("\n### 4. Tarea #4 — Escenarios de optimización ###")
    escenarios.ejecutar(cfg, guardar=True)

    print("\n### 5. Demostración adaptador (Samuel) ###")
    pkg = preparar_para_solver("2024_Obase_Cbase_M80_20", 2024)
    print(f"  id={pkg.id_escenario} municipios={pkg.excedente_municipio['cod_dane'].nunique()} "
          f"excedente_total={pkg.excedente_municipio['excedente_t'].sum():,.0f} t "
          f"cobertura={pkg.cobertura_oferta_pct}%")

    print(f"\nLISTO en {time.time() - t0:.1f}s. Resultados en data/results/ y data/results/arendonc2/.")


if __name__ == "__main__":
    main()
