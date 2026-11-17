# Lectura del diagnóstico de calidad (Ceyni → Carlos)

Se evaluaron 724 series activas (producto × municipio) de 44 productos. De 12.501 transiciones anuales comparables, 2.613 (20,9 %) repiten exactamente el valor del año anterior, y 949 (7,6 %) cambian más de 100 % respecto al año previo; 327 se salen de 3 desviaciones estándar de su propia serie. Una parte relevante de la serie parece estimación por consenso y no medición anual, y los saltos coinciden con cambios de metodología o de cobertura, no solo con la producción real. Hay además 295 registros con 0 t en el dato original y 18 filas duplicadas exactas (brevo y té), eliminadas.

Por confianza (reglas en src/02_diagnostico.py): 19 productos altos, 7 medios y 18 bajos. Entre los 22 detallados hay 15 de confianza alta, 4 media y 3 baja (Borojó, Sábila y Ají); entre los 22 simplificados predominan los de confianza baja (15), por tener pocos municipios o pocos años.

Implicación para el pronóstico: con 24 puntos anuales por serie, de los cuales una parte son repeticiones, la validación walk-forward mide el pronóstico contra datos de calidad desigual. Los productos de confianza baja no deben interpretarse como pronósticos independientes, sino como escenarios.
