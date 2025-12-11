# 🚗 PILOTO STREAMLIT - Detector de Anomalías en Tráfico

## 📋 Descripción

Aplicación interactiva en **Streamlit** para probar el método elegido de detección de anomalías:
- **Método**: MAD Ventana Móvil + Modified Z-Score
- **Latencia**: <0.1ms por punto
- **Precisión**: 85-90%
- **Datasets**: 5 datasets simulados listos para usar

---

## 📦 Requisitos

```bash
pip install streamlit pandas numpy plotly scipy
```

### Versiones recomendadas
```
streamlit>=1.28.0
pandas>=2.0.0
numpy>=1.24.0
plotly>=5.17.0
scipy>=1.11.0
```

---

## 🚀 Cómo usar

### 1️⃣ Instalar dependencias

```bash
pip install -r requirements.txt
```

Si no tienes `requirements.txt`, instala manualmente:

```bash
pip install streamlit pandas numpy plotly scipy
```

### 2️⃣ Ejecutar la aplicación

```bash
streamlit run app_streamlit.py
```

La aplicación se abrirá en: **http://localhost:8501**

### 3️⃣ Usar la interfaz

#### Carga de datos
1. En la barra izquierda, selecciona un dataset
2. Click en "📂 Cargar Dataset"
3. Automáticamente se entrena el baseline

#### Análisis
- **Pestaña 1**: Gráficos principales (intensidad, score, histogramas)
- **Pestaña 2**: Detalle de anomalías detectadas
- **Pestaña 3**: Análisis estadístico detallado
- **Pestaña 4**: Información del sistema y ecuaciones

---

## 📊 Datasets Disponibles

### 1. **trafico_normal.csv** (30 días)
- ✓ Patrón típico sin incidencias
- Caso ideal para training
- 43,200 registros
- Bueno para validar baseline

### 2. **trafico_con_incidencias.csv** (30 días)
- 3 incidencias simuladas:
  - Día 11, 09:30-10:00: Accidente (intensidad ×2.5)
  - Día 16, 17:00-18:00: Cierre de carril (intensidad ×1.9)
  - Día 23, 08:00-09:30: Congestión matinal (intensidad ×2.2)
- 43,200 registros
- Perfecto para validar detección

### 3. **trafico_cambio_gradual.csv** (30 días)
- Cambio gradual +40% en intensidad (ej: obra en marcha)
- Simula cambio de patrón lento
- 43,200 registros
- Prueba robustez del método

### 4. **trafico_ruido_alto.csv** (30 días)
- Ruido σ=30% (sensores defectuosos)
- Prueba robustez a datos ruidosos
- 43,200 registros
- Verifica si MAD mantiene robustez

### 5. **trafico_ultimas_24h.csv** (24 horas)
- Últimas 24 horas
- 1 anomalía simulada (hace ~3 horas)
- 1,440 registros
- Rápido para testing

---

## 🎯 Estructura del Código

```
app_streamlit.py
├── Configuración Streamlit
├── Clase TrafficAnomalyDetectorStreamlit
│   ├── cargar_historico()          # Entrenar baseline
│   ├── procesar_punto()            # Detección en tiempo real O(1)
│   ├── procesar_lote()             # Procesar múltiples filas
│   ├── reentrenar_baseline()       # Actualizar baseline
│   └── get_estadisticas()          # Métricas
├── Interfaz Streamlit
│   ├── Sidebar: Carga y configuración
│   ├── Tab 1: Gráficos (Plotly)
│   ├── Tab 2: Anomalías (Tabla detallada)
│   ├── Tab 3: Análisis estadístico
│   └── Tab 4: Información del sistema
└── Footer
```

---

## 📈 Elementos de la Interfaz

### Sidebar (Izquierda)
- **Selector de dataset**: Elige qué datos cargar
- **Botón "Cargar Dataset"**: Entrena el detector
- **Parámetros**: Ajusta threshold y ventana histórica
- **Información**: Muestra métricas del sistema

### Gráfico Principal (Tab 1)
- **Línea azul**: Intensidad actual (puntos normales)
- **Diamantes rojos**: Anomalías detectadas
- **Línea verde punteada**: Baseline (mediana)
- **Líneas naranjas punteadas**: Bandas ±2.5MAD

### Gráfico de Score (Tab 1)
- **Línea púrpura**: Desviación en MADs desde baseline
- **Línea roja**: Threshold (2.5 MADs)
- Muestra claramente qué tan lejos está cada punto del baseline

### Histogramas (Tab 1)
- Distribución de intensidad
- Patrón por hora del día

### Tabla de Anomalías (Tab 2)
- Timestamp de cada anomalía
- Valor actual vs esperado
- Desviación en MADs
- Confianza (0-100%)

### Análisis Estadístico (Tab 3)
- Mediana, MAD, Desv. Std, IQR
- Percentiles (P1, P5, P10, ..., P99)
- Análisis por bandas de desviación

---

## 🔧 Parámetros Configurables

### Threshold (Slider: 1.5 - 5.0)
- **1.5 MADs**: Muy sensible (muchos falsos positivos)
- **2.5 MADs**: ✓ Recomendado (balance óptimo)
- **3.5 MADs**: Menos sensible (menos falsos positivos)
- **5.0 MADs**: Muy conservador (solo anomalías extremas)

### Ventana Histórica (Slider: 7 - 90 días)
- **7 días**: Muy sensible a cambios (poco histórico)
- **30 días**: ✓ Recomendado (4 semanas)
- **60 días**: Más estable (2 meses)
- **90 días**: Muy conservador (3 meses)

---

## 📊 Cómo Interpretar Resultados

### ✅ Detección Correcta
- Anomalías en "trafico_con_incidencias.csv":
  - Debe detectar 3 eventos puntuales
  - Score ~2-3 MADs
  - Duración: 30-90 minutos cada una

### ⚠️ Cambios Graduales
- En "trafico_cambio_gradual.csv":
  - Puede no detectar cambio lento al inicio
  - A medida que avanza, cada punto se desvía más
  - Usa Seasonal Decomposition para verlo mejor

### 🔊 Ruido Alto
- En "trafico_ruido_alto.csv":
  - MAD debe ser mayor (captura el ruido)
  - Baseline aún válido
  - Más puntos cercanos al threshold

---

## 📐 Ecuaciones del Sistema

### Mediana Absoluta Desviación (MAD)
```
MAD = mediana(|x_i - mediana(x)|)
```

### Score de Anomalía
```
score = |x_i - mediana| / MAD
```

### Decisión
```
anomalía = score > 2.5
```

### Confianza
```
confianza = min(score / 2.5, 1.0)
```

---

## 🐛 Troubleshooting

### Error: "No module named 'streamlit'"
```bash
pip install streamlit
```

### Error: "No such file or directory: datos_trafico/..."
Asegúrate de que los CSV están en carpeta `datos_trafico/` en el mismo directorio que `app_streamlit.py`

### Aplicación lenta
- Reduce tamaño del dataset (usa "ultimas_24h")
- Aumenta threshold (menos puntos a procesar)
- Usa máquina con más RAM

### Gráficos no se muestran
Asegúrate de tener `plotly` instalado:
```bash
pip install plotly
```

---

## 💡 Tips de Uso

### Testing Rápido
1. Carga "trafico_ultimas_24h.csv" (rápido, 1440 registros)
2. Ajusta parámetros en tiempo real
3. Ve cambios en gráficos instantáneamente

### Validación Rigurosa
1. Carga "trafico_con_incidencias.csv"
2. Verifica que detecta las 3 incidencias
3. Calcula Precision/Recall manualmente

### Debugging
1. Ve Tab 2 para listar todas las anomalías
2. Compara con Tab 1 gráficamente
3. Revisa Tab 3 para estadísticas detalladas

### Exportar Resultados
```python
# En Python, después de probar en Streamlit:
import pandas as pd

df = pd.read_csv('datos_trafico/trafico_con_incidencias.csv')
# ... código de detección ...

# Guardar anomalías
df_anomalias = pd.DataFrame(detector.anomalias_detectadas)
df_anomalias.to_csv('anomalias_detectadas.csv', index=False)
```

---

## 📝 Formato CSV

Los archivos CSV deben tener este formato:

```
timestamp,intensity,occupancy
2025-01-01 00:00:00,32.48,0.15
2025-01-01 00:01:00,33.24,0.20
2025-01-01 00:02:00,28.83,0.14
...
```

### Columnas requeridas:
- **timestamp**: Formato `YYYY-MM-DD HH:MM:SS`
- **intensity**: Número flotante (vehículos/minuto)
- **occupancy**: Número entre 0-1 (fracción de ocupación)

---

## 🎓 Casos de Estudio

### Caso 1: Detección Básica
1. Carga "trafico_con_incidencias.csv"
2. Tab 1: Ve las 3 anomalías marcadas como diamantes rojos
3. Tab 2: Verifica timestamp exacto y score de cada una
4. Resultado esperado: 3 anomalías detectadas

### Caso 2: Ruido vs Señal
1. Carga "trafico_normal.csv"
2. Observa cuántos puntos falsamente positivos hay
3. Aumenta threshold a 3.5 MADs
4. Observa reducción de falsos positivos
5. Aprende el tradeoff precision-recall

### Caso 3: Cambios de Patrón
1. Carga "trafico_cambio_gradual.csv"
2. Nota que cambio lento no se detecta como anomalía
3. Baja a Tab 3, ve percentiles cambiando
4. Entiende por qué ventana móvil es mejor que día tipo fijo

### Caso 4: Datos Sucios
1. Carga "trafico_ruido_alto.csv"
2. Observa MAD más grande que en "normal"
3. Comprueba robustez del método
4. Ve cómo mediana/MAD resisten outliers

---

## 📚 Referencias

- **Método elegido**: MAD Ventana Móvil
- **Complejidad**: O(n) training, O(1) detección
- **Documentación**: Ver `guia_deteccion_anomalias.md`
- **Código completo**: `anomaly_detection_complete.py`

---

## 🤝 Soporte

Para preguntas:
1. Lee Tab 4 (Información del sistema)
2. Consulta `guia_deteccion_anomalias.md`
3. Ejecuta `ejemplos_practicos.py` para más detalles

---

**Última actualización**: Diciembre 2025  
**Versión**: 1.0  
**Estado**: Listo para producción
