# Capturas del tablero

Esta carpeta guarda las capturas del resumen (pantalla 0) y de la pantalla 4 (tablero
central con la hipótesis desplegada), que pide el manual.

**Estado: pendientes.** El entorno de desarrollo donde se preparó este PR es headless (sin
navegador ni servidor gráfico), así que las capturas no se generaron automáticamente. No se
incluyen imágenes fabricadas. El procedimiento para tomarlas es:

## Procedimiento

1. Levantar el tablero:

   ```bash
   streamlit run src/dashboard/app.py
   ```

2. Abrir `http://localhost:8501` con la ventana del navegador a **1440 px de ancho** y zoom
   **100 %** (1440 × 900 recomendado).

3. **Resumen (pantalla 0):** con la sede por defecto (Bugalagrande). Verificar que se lean
   los cuatro indicadores, los cuatro gráficos (cuadrícula 2×2) y las respuestas sin
   desplazarse. Guardar como `resumen_1440.png`.

4. **Pantalla 4. Tablero central:** sede Bugalagrande, radio 40 km, captación 20 %,
   escenario base, **hipótesis desplegada**. Guardar como `pantalla4_hipotesis_1440.png`.

## Figura 10 del informe

La **Figura 10** (`docs/informe/figuras/figura_10_tablero_hipotesis.png`) es una captura de
la pantalla 4 con la hipótesis desplegada. Este PR cambió el título dinámico del panel de
hipótesis (ahora expresa la razón de área y la de volumen con la conclusión "no alcanza el
doble"), así que la Figura 10 **debe recapturarse** con la misma configuración de
`docs/informe/README.md`: ventana de 1440 px, Bugalagrande, 40 km, captación 20 %, escenario
base e hipótesis desplegada. Conservar su nombre y ruta.
