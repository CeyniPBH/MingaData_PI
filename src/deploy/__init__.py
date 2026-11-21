"""Módulo de despliegue: persistencia de modelos, base de datos y API para MingaData_PI.

Este módulo permite alcanzar el nivel "Excelente" de SI7006-6:
- Modelo persistido y versionado en S3 con MLflow.
- API REST (FastAPI) para servir predicciones.
- Motor SQL analítico (DuckDB) para almacenar resultados y métricas.
- Consumo desde el dashboard Streamlit.
"""
