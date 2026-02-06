

# TODO — Detector de Anomalías de Tráfico

> Estado: activo · Última actualización: 2026-01-23  
> App: Streamlit · Algoritmos: MAD, Isolation Forest, Random Cut Forest (RCF)

---

## 🧭 Roadmap por fases

### Fase 1 — UX y Operación (semanas 1–2)
- [x] **Presets por escenario** (Normal / Obra / Accidente / Sensor ruidoso).  
- [ ] **Descarga de anomalías** (CSV/Excel) desde la pestaña **🔴 Anomalías**.  
- [ ] **Informe PDF** (gráficos + parámetros + estadísticas clave).  
- [ ] **Comparativa lado a lado** (tres algoritmos en paralelo, mismos ejes y ventana).  
- [ ] **Anotaciones** en gráficos (festivos, obras, incidentes).  
- [ ] **Tema oscuro/claro** (toggle).  
- [ ] **Validación CSV** (timestamp, intensidad, ordenación, duplicados).

**Criterio de “Hecho”:**  
El usuario puede cargar un dataset, elegir un preset, comparar algoritmos en paralelo, descargar anomalías y generar un informe PDF sin errores.

---

### Fase 2 — Modelos y Explicabilidad (semanas 3–5)
- [ ] **STL + residuo** como algoritmo adicional.  
- [ ] **LOF (Local Outlier Factor)** como algoritmo adicional.  
- [ ] **ARIMA/Prophet (residuos)** para detección por error de predicción.  
- [ ] **Explicabilidad (IF/RCF)**: contribuciones/SHAP (si multivariante).  
- [ ] **Detección de cambios de régimen** (rupturas sostenidas, no solo picos).  
- [ ] **Auto-tuner de umbrales** (objetivo de tasa de alertas/semana).

**Criterio de “Hecho”:**  
El usuario puede elegir 2+ algoritmos nuevos, ver explicaciones del porqué de una anomalía, y ajustar umbrales con una guía interactiva de sensibilidad.

---

### Fase 3 — Integraciones y Streaming (semanas 6–8)
- [ ] **API REST `/predict`** (POST datos → respuesta con score/etiqueta).  
- [ ] **Webhook/Teams/Slack** para alertas en tiempo real.  
- [ ] **Streaming** (refresh programado + RCF deslizante).  
- [ ] **Persistencia** en SQLite/PostgreSQL (datasets, parámetros, resultados).  
- [ ] **Jobs programados** (resúmenes diarios/semanales por correo).

**Criterio de “Hecho”:**  
La app puede operar continua o periódicamente, enviar alertas y exponer predicción vía API, con histórico persistente y reproducible.

---

## 🔧 Backlog por áreas

### 1) Datos / Entrada
- [ ] Cargar **múltiples datasets** y **compararlos** (dual/triple view). *(P2 · UX)*  
- [ ] **Simulador** de escenarios (picos, obras, festivos, ruido, sensor roto). *(P3 · I+D)*  
- [ ] Carga por **API externa** (DGT / fuentes municipales) + caché. *(P3 · Integración)*  
- [ ] **Validación CSV** con reporte: columnas, formatos, NaNs, duplicados, gaps. *(P1 · Calidad)*

### 2) Algoritmos
- [ ] **STL+Residuo** (statsmodels) con umbral MAD sobre residuo. *(P1 · Núcleo)*  
- [ ] **LOF** (scikit-learn) con ventana configurable. *(P2 · Núcleo)*  
- [ ] **ARIMA/Prophet** (forecast + residuo). *(P2 · Núcleo)*  
- [ ] **Ensemble** (voto MAD+IF+RCF; score promedio o máximo). *(P2 · I+D)*  
- [ ] **RCF streaming**: bosque deslizante con “forgetting”. *(P3 · Rendimiento)*

### 3) UX / Visualización
- [ ] **Comparativa lado a lado** (sincronizar zoom, rango temporal). *(P1)*  
- [ ] **Heatmap semanal** (hora×día) con marcadores de anomalías. *(P2)*  
- [ ] **Boxplots diarios** (distribución + outliers). *(P2)*  
- [ ] **Timeline** con tooltips enriquecidos (score, parámetros, contexto). *(P1)*  
- [ ] **Modo Focus**: contexto ±N minutos alrededor de cada anomalía. *(P1)*  
- [ ] **Anotaciones externas** (API o CSV de eventos). *(P1)*  
- [ ] **Tema oscuro** / claro (toggle). *(P1)*

### 4) Explicabilidad
- [ ] **Feature importance/SHAP** para IF/RCF (si multivariante). *(P2)*  
- [ ] **Curva de sensibilidad**: detecciones vs umbral (MAD/RCF). *(P2)*  
- [ ] **Indicadores de tendencia** (slopes antes/después del evento). *(P2)*  
- [ ] **Cambios de régimen** (rupturas tipo BOCPD/ruptures). *(P2–P3)*

### 5) Exportación / Reporting
- [x] **Descarga CSV/Excel** de anomalías (con filtros por severidad y fecha). *(P1)*  
- [ ] **Informe PDF**: portada, parámetros, gráficos, tabla de anomalías, apéndice. *(P1)*  
- [ ] **Exportar thresholds y presets** como JSON (reproducibilidad). *(P1)*  
- [ ] **Reportes programados** por email (diario/semanal). *(P3)*

### 6) Backend / Integración
- [ ] **REST API** `/predict` y `/health`. *(P3)*  
- [ ] **Webhook/Teams/Slack** para alertas por umbral de confianza. *(P3)*  
- [ ] **Persistencia** (SQLite→PostgreSQL) con migraciones mínimas. *(P3)*  
- [ ] **MQTT/Kafka** (opcional) para ingestión streaming. *(P3)*

### 7) Evaluación / Métricas
- [ ] Pestaña de **calidad** (si hay etiquetas): Precision/Recall/F1/AUC. *(P2)*  
- [ ] **Ranking** de top anomalías por severidad/impacto. *(P1)*  
- [ ] Métricas operativas: median time-to-detect, #notificaciones/día, %falsos positivos. *(P2)*

### 8) Rendimiento
- [ ] **Cache** de scoring por algoritmo/parámetros/dataset. *(P2)*  
- [ ] **Resampling** automático cuando hay millones de puntos (downsampling para gráficos). *(P2)*  
- [ ] **Paralelización** en RCF (multiproceso opcional). *(P3)*  
- [ ] **Límites de seguridad** (máx. puntos, fallback a muestra). *(P1)*

### 9) Test y Calidad
- [ ] **Unit tests** básicos para MAD/IF/RCF (score esperado en sintéticos). *(P1)*  
- [ ] **Datasets sintéticos** con anomalías conocidas (golden). *(P1)*  
- [ ] **CI simple** (lint + tests) para evitar regresiones. *(P2)*  
- [ ] **Chequear consistencia temporal** (orden, gaps, duplicados). *(P1)*

---

## 🎛️ Presets propuestos (para añadir a la barra lateral)

> **Objetivo**: acelerar el tuning con configuraciones recomendadas por escenario.

- **Preset — Normal (recomendado)**  
  - MAD: `window_days=42`, `threshold=3.5`  
  - IF: `contamination=0.005–0.01`  
  - RCF: `n_trees=80`, `tree_size=512`, `shingle=3`, `contamination=0.0015`

- **Preset — Obra / cambio paulatino**  
  - MAD: `window_days=21–28`, `threshold=3.2`  
  - IF: `contamination=0.01–0.02`  
  - RCF: `shingle=3–5`, `contamination=0.005–0.01`, `tree_size=512`

- **Preset — Accidente / pico brusco**  
  - MAD: `threshold=2.8–3.0`  
  - IF: `contamination=0.01–0.02`  
  - RCF: `shingle=1–3`, `contamination=0.003–0.005`

- **Preset — Sensor ruidoso**  
  - MAD: `threshold=4.0–4.5`  
  - IF: `contamination=0.003–0.008`  
  - RCF: `shingle=5`, `tree_size=256–512`, `contamination=0.001–0.003`

---

## 🧾 Definiciones y convenciones

- **Prioridades**:  
  - **P1**: alta (mejora directa de uso/operación).  
  - **P2**: media (valor claro, no bloqueante).  
  - **P3**: baja/I+D (estratégico o exploratorio).

- **Etiquetas**:  
  - *UX*, *Núcleo*, *I+D*, *Integración*, *Rendimiento*, *Calidad*.

- **Criterio de “Hecho”** (DoD) por defecto:  
  - Funciona en datasets de ejemplo.  
  - Controles en la UI, feedback claro (mensajes, spinners).  
  - Errores controlados (sin stacktrace expuesto).  
  - Probado con al menos un dataset “normal” y uno con anomalías.

---

## 📌 Notas operativas

- Ejecutar siempre la app con el **mismo entorno** que contiene dependencias:  
  `uv run streamlit run app.py`  
- Paquetes recomendados: `setuptools`, `rrcf` **o** `rrcf2`, `statsmodels` (para STL), `pmdarima/prophet` (si se usan).  
- Mantener **límites de seguridad** (máx. puntos por RCF) para evitar bloqueos UI.

``

