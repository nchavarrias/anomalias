# 🚗 DETECTOR DE ANOMALÍAS - APP COMPLETA

## Descripción

Aplicación Streamlit COMPLETA y FUNCIONAL para detectar anomalías en datos de tráfico usando **MAD Ventana Móvil**.

## ✅ Qué Está INCLUIDO

### 1. Clase Detector Corregida
```python
class TrafficAnomalyDetectorStreamlit:
    def __init__(self, window_days=30, threshold=2.5)
```

**Correcciones implementadas:**
- ✅ Threshold es ahora parámetro (no hardcodeado)
- ✅ MAD se calcula correctamente: `mediana(|x - mediana|)`
- ✅ Score se calcula correctamente: `|intensity - baseline_med| / baseline_mad`
- ✅ Buffer circular para eficiencia O(1)

### 2. Botón "🔄 Recalcular" IMPLEMENTADO
```python
if st.button("🔄 Recalcular con nuevos parámetros", key="btn_recalc"):
    if 'detector' in st.session_state:
        del st.session_state.detector  # ← Borra detector viejo
    
    # ← Crea detector NUEVO con parámetros actuales
    st.session_state.detector = TrafficAnomalyDetectorStreamlit(
        window_days=st.session_state.window_days,
        threshold=st.session_state.threshold_actual
    )
```

**Ubicación:** Sidebar, línea ~180

### 3. Flujo Completo
- ✅ Carga de datasets
- ✅ Entrenamiento de baseline
- ✅ Procesamiento de anomalías
- ✅ 4 pestañas de visualización
- ✅ Actualización de parámetros

## 🚀 Cómo Usar

### PASO 1: Reemplazar archivo

```bash
# En tu proyecto, reemplaza el viejo por este:
cp app_streamlit_COMPLETA.py app_streamlit.py
```

O simplemente copia el contenido de `app_streamlit_COMPLETA.py [99]` a tu `app_streamlit.py`.

### PASO 2: Ejecutar

```bash
uv run streamlit run app_streamlit.py
```

### PASO 3: Usar la App

1. **Carga dataset** en sidebar:
   - Click "📂 Cargar Dataset"
   - Selecciona un dataset

2. **Observa baseline** en sidebar:
   - Mediana
   - MAD
   - Anomalías detectadas

3. **Cambia ventana** en slider:
   - Mueve a 7, 30, 90 días

4. **Click "🔄 Recalcular"**:
   - Se recrea el detector
   - Baseline se recalcula
   - ¡Mediana y MAD cambian!

5. **Observa cambios**:
   - En Tab 📊: Gráficas se actualizan
   - En Tab 🔴: Anomalías cambian
   - En sidebar: Mediana/MAD actualizados

## ✅ Validación: Los 3 Tests

### Test 1: ¿Mediana cambia?

```
1. Carga trafico_normal.csv
2. Lee mediana en sidebar (ej: 100.5)
3. Mueve slider ventana a 7 días
4. Click "🔄 Recalcular"
5. ¿Mediana cambió? (ej: 97.2)
   → SI = ✓ FUNCIONA
   → NO = ❌ ERROR
```

### Test 2: ¿MAD cambia?

```
Mismo que Test 1, pero mira MAD
```

### Test 3: ¿Anomalías cambian?

```
1. Carga trafico_con_incidencias.csv
2. Con ventana 30 + Click recalcular → Anota anomalías (ej: 500)
3. Cambia ventana a 7 + Click recalcular → ¿Disminuyeron? (ej: 200)
   → SI = ✓ FUNCIONA
4. Cambia ventana a 90 + Click recalcular → ¿Aumentaron? (ej: 1000)
   → SI = ✓ FUNCIONA
```

## 📊 Estructura de la App

```
SIDEBAR (Configuración)
├─ 1. Seleccionar Dataset
│  ├─ Tráfico Normal (30 días)
│  ├─ Con Incidencias (3 eventos)
│  ├─ Cambio Gradual (Obra)
│  ├─ Ruido Alto
│  └─ Últimas 24h + Anomalía
├─ Botón "📂 Cargar Dataset"
├─ 2. Parámetros
│  ├─ Slider Ventana (7-90 días)
│  └─ Slider Threshold (1.5-5.0 MADs)
├─ 3. Recalcular
│  └─ Botón "🔄 Recalcular"
└─ ℹ️ Información
   ├─ Anomalías detectadas
   ├─ Mediana
   ├─ MAD
   └─ Buffer tamaño

CONTENIDO PRINCIPAL (4 Pestañas)
├─ 📊 Gráficos
│  ├─ Intensidad con anomalías
│  ├─ Score de anomalía (MADs)
│  ├─ Histograma de intensidad
│  └─ Patrón por hora
├─ 🔴 Anomalías
│  ├─ Tabla de anomalías detectadas
│  └─ Estadísticas (total, %, máximo score, duración)
├─ 📈 Análisis
│  ├─ Estadísticas (Mediana, MAD, Desv.Std, IQR, etc)
│  ├─ Percentiles (P1, P5, P10, ... P99)
│  └─ Análisis por banda de desviación
└─ ℹ️ Información
   ├─ Método utilizado (MAD Ventana Móvil)
   └─ Parámetros actuales
```

## 🔧 Cambios vs Versión Anterior

| Aspecto | Antes | Ahora |
|---------|-------|-------|
| Threshold | Hardcodeado (2.5) | Parámetro en slider |
| Recalcular | No había botón | ✅ Botón "🔄 Recalcular" |
| Detector cacheado | No se borraba | ✅ Se borra con `del` |
| Mediana al cambiar slider | No cambiaba | ✅ Cambia después de recalcular |
| MAD al cambiar slider | No cambiaba | ✅ Cambia después de recalcular |
| Anomalías al cambiar parámetros | No cambiaban | ✅ Cambian después de recalcular |

## 🎯 Líneas Clave

### Botón Recalcular (línea ~180)
```python
if st.button("🔄 Recalcular con nuevos parámetros", key="btn_recalc"):
    if st.session_state.df_cargado is not None:
        if 'detector' in st.session_state:
            del st.session_state.detector  # ← CLAVE: borrar viejo
        
        st.session_state.detector = TrafficAnomalyDetectorStreamlit(
            window_days=st.session_state.window_days,      # ← parámetro
            threshold=st.session_state.threshold_actual     # ← parámetro
        )
```

### Cargar Dataset (línea ~120)
```python
st.session_state.detector = TrafficAnomalyDetectorStreamlit(
    window_days=st.session_state.window_days,
    threshold=st.session_state.threshold_actual
)
```

## 📦 Requisitos

```
streamlit>=1.28
pandas>=1.5
numpy>=1.24
plotly>=5.14
scipy>=1.10
```

## 🛑 Si Algo No Funciona

### Problema: Streamlit sigue mostrando valores viejos

**Solución:**
```bash
# Limpiar caché de Streamlit
rm -rf ~/.streamlit/
uv run streamlit run app_streamlit.py --logger.level=debug
```

### Problema: "KeyError" con session_state

**Causa:** Falta inicializar variable
**Solución:** Verifica que existan estas líneas (alrededor de línea 95):

```python
if 'detector' not in st.session_state:
    st.session_state.detector = ...

if 'df_cargado' not in st.session_state:
    st.session_state.df_cargado = None

if 'threshold_actual' not in st.session_state:
    st.session_state.threshold_actual = 2.5

if 'window_days' not in st.session_state:
    st.session_state.window_days = 30
```

### Problema: Datos no se cargan

**Causa:** Paths de archivos incorrectos
**Solución:** Verifica que existan:
- `datos_trafico/trafico_normal.csv`
- `datos_trafico/trafico_con_incidencias.csv`
- etc.

## 📝 Resumen

| Característica | Estado |
|---|---|
| Clase Detector | ✅ Completa y corregida |
| Slider Ventana | ✅ Funciona |
| Slider Threshold | ✅ Funciona |
| Botón Recalcular | ✅ Implementado |
| Cálculo Mediana | ✅ Correcto |
| Cálculo MAD | ✅ Correcto |
| Cálculo Score | ✅ Correcto |
| Gráficos | ✅ 4 gráficos |
| Anomalías detectadas | ✅ Tabla y estadísticas |
| Análisis | ✅ Percentiles, bandas |
| Información | ✅ Método y parámetros |

## 🎉 ¿Funciona Todo?

Si después de implementar:
1. Cargas un dataset
2. Cambias ventana
3. Click "🔄 Recalcular"
4. Ves cambios en Mediana/MAD/Anomalías

**Entonces: ¡3 BUGS SOLUCIONADOS!** 🚀

## Siguiente Paso

Ahora puedes:
- Ajustar threshold según tus datos
- Usar `analizar_threshold.py` para encontrar el threshold óptimo
- Exportar resultados
- Integrar en producción

¡Listo para usar! 🚗
