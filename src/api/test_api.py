"""Prueba funcional de la API REST de MingaData_PI.

Verifica que los endpoints responden correctamente:
  - GET  /health
  - GET  /modelo/info
  - POST /predict
  - GET  /metricas

Ejecuta:
    python src/api/test_api.py
    # O con la API corriendo en otro terminal:
    # uvicorn src.api.main:app --reload
"""

import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

try:
    from fastapi.testclient import TestClient
    from api.main import app
except Exception as e:
    print(f"No se pudo importar la API: {e}")
    sys.exit(1)

client = TestClient(app)
errores = []
exitos = []


def check(condicion, mensaje):
    if condicion:
        exitos.append(f"  [OK] {mensaje}")
    else:
        errores.append(f"  [FAIL] {mensaje}")


def main():
    print("=" * 70)
    print("PRUEBA FUNCIONAL DE LA API REST - MINGADATA")
    print("=" * 70)
    print()

    # --- 1. Endpoint raíz ---
    print("--- 1. Endpoint raíz ---")
    r = client.get("/")
    check(r.status_code == 200, f"GET / devuelve 200 (obtuvo {r.status_code})")
    datos = r.json()
    check("endpoints" in datos, "GET / lista endpoints disponibles")

    # --- 2. Health ---
    print("\n--- 2. Health ---")
    r = client.get("/health")
    check(r.status_code == 200, f"GET /health devuelve 200 (obtuvo {r.status_code})")
    datos = r.json()
    check("status" in datos, "GET /health tiene campo status")
    check("modelo_cargado" in datos, "GET /health indica si el modelo está cargado")

    # --- 3. Info del modelo ---
    print("\n--- 3. Info del modelo ---")
    r = client.get("/modelo/info")
    if r.status_code == 200:
        check(True, "GET /modelo/info devuelve 200 (modelo cargado)")
    elif r.status_code == 404:
        check(True, "GET /modelo/info devuelve 404 (no hay modelo cargado, esperado en test sin modelo)")
    else:
        check(False, f"GET /modelo/info devuelve {r.status_code} inesperado")

    # --- 4. Predicción ---
    print("\n--- 4. Predicción ---")
    payload = {
        "producto": "Caña de azúcar",
        "cod_dane": "76113",
        "horizonte": 1,
        "anio_objetivo": 2024,
    }
    r = client.post("/predict", json=payload)
    if r.status_code == 200:
        check(True, "POST /predict devuelve 200 (predicción exitosa)")
        datos = r.json()
        check("prediccion_t" in datos, "Respuesta incluye prediccion_t")
        check("producto" in datos, "Respuesta incluye producto")
        check("horizonte" in datos, "Respuesta incluye horizonte")
    elif r.status_code == 503:
        check(True, "POST /predict devuelve 503 (modelo no cargado, esperado en test sin modelo)")
    else:
        check(False, f"POST /predict devuelve {r.status_code} inesperado")

    # --- 5. Métricas ---
    print("\n--- 5. Métricas ---")
    r = client.get("/metricas")
    check(r.status_code == 200, f"GET /metricas devuelve 200 (obtuvo {r.status_code})")
    datos = r.json()
    check("metricas" in datos, "GET /metricas tiene campo metricas")

    # --- 6. Docs de OpenAPI ---
    print("\n--- 6. Documentación OpenAPI ---")
    r = client.get("/docs")
    check(r.status_code == 200, f"GET /docs devuelve 200 (obtuvo {r.status_code})")

    # --- Resumen ---
    print("\n" + "=" * 70)
    print("RESUMEN DE PRUEBA FUNCIONAL")
    print("=" * 70)
    print(f"[OK] Exitos: {len(exitos)}")
    print(f"[FAIL] Errores: {len(errores)}")
    print()

    for e in exitos:
        print(e)
    for e in errores:
        print(e)

    if errores:
        print("\nLA API TIENE ERRORES. Revisar arriba.")
        return 1
    print("\nLA API PASÓ TODAS LAS PRUEBAS FUNCIONALES.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
