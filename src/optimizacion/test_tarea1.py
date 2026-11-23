"""
Script de prueba automatizada para verificar que la Tarea 1 está completa al 100%.

Ejecuta: python src/optimizacion/test_tarea1.py
"""

import os
import sys
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ERRORES = []
EXITOS = []


def check(condicion, mensaje):
    if condicion:
        EXITOS.append(f"  [OK] {mensaje}")
    else:
        ERRORES.append(f"  [FAIL] {mensaje}")


def main():
    print("=" * 70)
    print("VERIFICACIÓN TAREA 1: Formulación y esqueleto OR-Tools")
    print("=" * 70)
    print()

    # 1. Verificar que existe docs/formulacion_optimizacion.md
    print("--- 1. Documento de formulación ---")
    path_md = ROOT / "docs" / "formulacion_optimizacion.md"
    check(path_md.exists(), f"docs/formulacion_optimizacion.md existe")

    if path_md.exists():
        contenido = path_md.read_text(encoding="utf-8")
        check("Variables de decisión" in contenido, "Contiene sección de variables de decisión")
        check("x_c" in contenido or "x = " in contenido, "Define variable de apertura de central (x_c)")
        check("y_s" in contenido or "y = " in contenido, "Define variable de apertura de satélite (y_s)")
        check("z_{m,s}" in contenido or "z[" in contenido, "Define variable de asignación municipio→satélite (z_ms)")
        check("w_{s,c}" in contenido or "w[" in contenido, "Define variable de asignación satélite→central (w_sc)")
        check("k" in contenido.lower() or "k =" in contenido, "Define número de satélites como parámetro k")
        check("3" in contenido and "8" in contenido, "Menciona rango k de 3 a 8")
        check("capacidad" in contenido.lower() or "cap_" in contenido.lower(), "Menciona capacidad mínima/máxima")
        check("Z1" in contenido or "Z_1" in contenido or "Z₁" in contenido, "Define objetivo Z1 (recolección)")
        check("Z2" in contenido or "Z_2" in contenido or "Z₂" in contenido, "Define objetivo Z2 (distribución)")
        check("Buenaventura" in contenido, "Incluye destino Buenaventura")
        check("Palmira" in contenido, "Incluye destino Aeropuerto Palmira")
        check("Cali" in contenido, "Incluye destino Cali")
        check("Bogotá" in contenido or "Bogota" in contenido, "Incluye destino Bogotá")
        check("Medellín" in contenido or "Medellin" in contenido, "Incluye destino Medellín")
        check("zonas.csv" in contenido, "Lista columnas esperadas de zonas.csv")
        check("escenarios.csv" in contenido or "oferta_escenarios" in contenido, "Lista columnas de escenarios/oferta")
        check("matriz_tiempos.csv" in contenido, "Lista columnas de matriz_tiempos.csv")

    # 2. Verificar que existe el script del modelo
    print("\n--- 2. Script del modelo OR-Tools ---")
    path_py = ROOT / "src" / "optimizacion" / "modelo_esqueleto.py"
    check(path_py.exists(), f"src/optimizacion/modelo_esqueleto.py existe")

    # 3. Ejecutar el modelo y verificar salida
    print("\n--- 3. Ejecución del modelo con datos ficticios ---")

    # Importar el módulo dinámicamente
    spec = importlib.util.spec_from_file_location("modelo_esqueleto", path_py)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
        check(True, "El módulo se importa sin errores")

        resultado = mod.resolver_modelo(
            mod.MUNICIPIOS_FICTICIOS,
            mod.DESTINOS_FICTICIOS,
            mod.generar_matriz_tiempos(mod.MUNICIPIOS_FICTICIOS, mod.DESTINOS_FICTICIOS)[0],
            k=mod.K_SATELITES,
            lam=mod.LAMBDA,
            pct_nac=mod.PCT_NACIONAL,
            pct_exp=mod.PCT_EXPORTACION,
        )

        check(resultado["status"] in ("OPTIMAL", "FEASIBLE"), f"Modelo devuelve estado factible: {resultado['status']}")
        check(resultado["central"] is not None, f"Devuelve una central: {resultado['central']}")
        check(len(resultado["satelites"]) == mod.K_SATELITES,
              f"Devuelve exactamente k={mod.K_SATELITES} acopios satélite (obtuvo {len(resultado['satelites'])})")
        check(resultado["costo_recoleccion"] is not None and resultado["costo_recoleccion"] > 0,
              f"Calcula costo de recolección: {resultado['costo_recoleccion']:,.0f}")
        check(resultado["costo_distribucion"] is not None and resultado["costo_distribucion"] > 0,
              f"Calcula costo de distribución: {resultado['costo_distribucion']:,.0f}")
        check(resultado["costo_total"] is not None and resultado["costo_total"] > 0,
              f"Calcula costo total ponderado: {resultado['costo_total']:,.0f}")
        check(len(resultado["asignaciones_municipio_satelite"]) > 0,
              f"Hay asignaciones municipio→satélite ({len(resultado['asignaciones_municipio_satelite'])})")
        check(len(resultado["asignaciones_satelite_central"]) > 0,
              f"Hay asignaciones satélite→central ({len(resultado['asignaciones_satelite_central'])})")

        # Verificar que cada municipio esté asignado a exactamente un satélite
        municipios_asignados = [m for (m, s) in resultado["asignaciones_municipio_satelite"]]
        check(len(municipios_asignados) == len(mod.MUNICIPIOS_FICTICIOS),
              f"Todos los {len(mod.MUNICIPIOS_FICTICIOS)} municipios están asignados")

        # Verificar que cada satélite esté asignado a la central
        satelites_asignados = [s for (s, c) in resultado["asignaciones_satelite_central"]]
        check(len(satelites_asignados) == len(resultado["satelites"]),
              "Todos los satélites están asignados a la central")

        # Verificar que los destinos estén definidos
        check(len(mod.DESTINOS_FICTICIOS) >= 5, f"Se definen {len(mod.DESTINOS_FICTICIOS)} destinos (mínimo 5)")
        dest_nombres = [d[1] for d in mod.DESTINOS_FICTICIOS]
        check(any("Buenaventura" in n for n in dest_nombres), "Incluye Buenaventura")
        check(any("Palmira" in n for n in dest_nombres), "Incluye Aeropuerto Palmira")
        check(any("Cali" in n for n in dest_nombres), "Incluye Cali")
        check(any("Bogot" in n for n in dest_nombres), "Incluye Bogotá")
        check(any("Medell" in n for n in dest_nombres), "Incluye Medellín")

    except Exception as e:
        check(False, f"Error al ejecutar el modelo: {e}")

    # 4. Verificar que OR-Tools use CBC
    print("\n--- 4. Solver OR-Tools ---")
    check("CBC" in path_py.read_text(encoding="utf-8"), "El script usa el solver CBC de OR-Tools")
    check("pywraplp" in path_py.read_text(encoding="utf-8"), "El script importa pywraplp de OR-Tools")

    # RESUMEN
    print("\n" + "=" * 70)
    print("RESUMEN DE VERIFICACIÓN")
    print("=" * 70)
    print(f"[OK] Exitos: {len(EXITOS)}")
    print(f"[FAIL] Errores: {len(ERRORES)}")
    print()

    if ERRORES:
        print("ERRORES ENCONTRADOS:")
        for e in ERRORES:
            print(e)
        print()
        print("ATENCION: LA TAREA 1 NO ESTA COMPLETA AL 100%. Corrige los errores arriba.")
        return 1
    else:
        print("TODAS LAS VERIFICACIONES PASARON.")
        print("La Tarea 1 está completa al 100% y lista para entregar.")
        print()
        print("Puedes pasar el texto de docs/formulacion_optimizacion.md a Carlos")
        print("para que arme el diagrama de la frontera ML - optimizacion.")
        return 0


if __name__ == "__main__":
    sys.exit(main())