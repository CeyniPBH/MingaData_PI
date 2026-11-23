# Capturas del tablero

Esta carpeta guarda las capturas del resumen (pantalla 0) y de la pantalla 4 (tablero
central), que pide el manual.

**Estado: pendientes de una revisión humana en navegador.** El entorno donde se preparó
este PR es headless (sin navegador con interfaz ni automatización autorizada), así que las
capturas a 1440 × 900 no se generaron. No se incluyen imágenes fabricadas.

Verificación que **sí** se ejecutó sobre la pantalla 4 rediseñada: el HTML/JS se ejecutó en
un DOM real con **jsdom** (no solo `node --check`), confirmando que no hay errores de
runtime, que los controles están visibles desde el inicio, que no quedan los modos
`f1/f2/f3`, que abrir detalles no cambia parámetros, que cambiar sede conserva
capacidad/radio/captación/escenario, que cambiar escenario conserva la capacidad y que el
ranking incluye la sede seleccionada con su puesto real. Falta la **revisión visual humana**
(legibilidad, contraste y recortes a 1440 × 900), que requiere una persona.

## Procedimiento para las capturas

1. Levantar el tablero:

   ```bash
   streamlit run src/dashboard/app.py
   ```

2. Abrir `http://localhost:8501` con la ventana del navegador a **1440 px de ancho** y zoom
   **100 %** (1440 × 900 recomendado).

3. **Resumen (pantalla 0):** sede por defecto (Bugalagrande). Verificar que se lean los
   cuatro indicadores, los cuatro gráficos (cuadrícula 2×2) y las respuestas. Guardar como
   `resumen_1440.png`.

4. **Pantalla 4. Tablero central (exploración):** en la **barra lateral**, fijar sede
   Bugalagrande, radio 40 km, captación 20 %, capacidad 100.000 t/año y escenario base.
   Verificar que haya un único juego de controles (en la barra lateral), que el tablero
   muestre la línea de contexto con esa configuración y que el mapa, la superficie/
   composición, el volumen/utilización, el ranking y la comparación territorial se lean sin
   recortes ni espacio vacío excesivo, con desplazamiento vertical solo si hace falta.
   Guardar como `pantalla4_exploracion_1440.png`.

## Figuras del informe afectadas por el rediseño de la pantalla 4

La pantalla 4 pasó de una presentación guiada por preguntas e hipótesis a una herramienta de
exploración (sin bloques "Pregunta 1/2", sin "Hipótesis", sin modos `f1/f2/f3`). Por eso:

- **Figura 9** (`docs/informe/figuras/figura_9_tablero_cobertura.png`): captura de la
  pantalla 4. **Desactualizada**; debe recapturarse.
- **Figura 10** (`docs/informe/figuras/figura_10_tablero_hipotesis.png`): captura de la
  pantalla 4 con la hipótesis desplegada. El bloque de hipótesis **ya no existe**; la figura
  queda **desactualizada**. Debe recapturarse como vista de exploración, o bien el texto del
  informe (sección 5.4 y la tabla de `docs/informe/README.md`) debe ajustarse para no
  describir una "vista de la hipótesis" que ya no está en el tablero. Esa decisión de
  informe queda fuera de este PR (no se tocó `src/informe/` ni `docs/informe/`).

Configuración para ambas capturas, según `docs/informe/README.md`: ventana de 1440 px,
Bugalagrande, 40 km, captación 20 %, escenario base. Conservar nombres y rutas.
