# Checklist de Validación de Datasets y Simulación Streaming

Este documento recoge el *checklist oficial* para validar los datasets de tráfico (30 días y 120 días) con los tres algoritmos de la aplicación —MAD estacional, Isolation Forest y Random Cut Forest— así como los pasos futuros para implementar un modo **Streaming (Replay)** que permita simular operación real.

---

# ✅ 1. Checklist de Validación de Datasets (30 días y 120 días)

## 📌 Parámetros iniciales recomendados

### **MAD estacional (dow + minuto)**
- Ventana (datasets 120 d): **56 días**
- Ventana (datasets 30 d): **21–28 días**
- Threshold: **3.5–4.0 MADs** (si hay ruido → 4.5)
- `mad_floor`: **1.5–2.0**
- `min_obs_per_bucket`: **7–8**
- Post-regla de segmentos: **5 minutos consecutivos**, tolerancia **1**

### **Isolation Forest**
- `contamination`: **0.005–0.01** (0.5–1%)

### **Random Cut Forest**
- `n_trees`: 100
- `tree_size`: 512
- `shingle_size`: 1
- `contamination`: **0.002–0.003**

---

## 🟥 Dataset: Accidente (4 eventos, 120 días)
### ✔ Esperado
- Detecciones claras en los **tres accidentes**.
- Picos de ❌ concentradas en ventanas concretas (08:00–09:30 y 18:00–19:30).

### 🔧 Ajustes si algo falla
- Si salen ❌ dispersas → Threshold a **4.0** o `mad_floor` a **2.0**.
- Si falta sensibilidad → Threshold **3.5**.

---

## 🟨 Dataset: Evento Estadio (3 eventos, 120 días)
### ✔ Esperado
- ❌ en pre-evento (17:30–19:30) y post-evento (21:45–22:45).
- IF y RCF deberían detectar patrones parecidos.

### 🔧 Ajustes si algo falla
- Si se detectan demasiados minutos “normales” → Threshold **4.5**.

---

## 🟩 Dataset: Puente / Festivo (120 días)
### ✔ Esperado
- Muy pocas ❌ dentro de los días festivos.
- Posibles ❌ al **inicio/fin** del puente.

### 🔧 Ajustes si algo falla
- Si aparecen franjas diarias → threshold **4.5** o mad_floor **2.0**.

---

## 🔁 Dataset: Desvío Temporal (2 semanas)
### ✔ Esperado
- ❌ concentradas **solo al inicio del desvío**.
- Luego disminuyen al adaptarse la ventana.

### 🔧 Ajustes si algo falla
- Si persiste demasiada alarma → aumentar ventana (56→70 días).

---

## 🌙 Dataset: Corte Nocturno (120 días)
### ✔ Esperado
- Bloques nocturnos (01:00–04:00) marcados como ❌.
- Nada significativo fuera de esos bloques.

### 🔧 Ajustes si algo falla
- Si hay falsas alarmas de madrugada → `mad_floor` **2.0**.

---

## 🛠 Dataset: Sensor Defectuoso (120 días)
### ✔ Esperado
- ❌ durante: spikes, ruido alto, dropouts.
- RCF captará mucho ruido, IF un poco menos.

### 🔧 Ajustes si algo falla
- Threshold MAD a **4.0–4.5**.
- En RCF → contamination **0.002**.

---

## 📊 Datasets de 30 días (normal, incidencias, ruido…)
### ✔ Reglas generales
- Ventana: **21–28 días**.
- Tráfico normal → casi sin ❌.
- Incidencias → ❌ localizadas.
- Ruido alto → marcará spikes/dropouts; no debe marcar días completos.

### 🔧 Ajustes
- Reduce ventana si ves poca adaptación.
- Threshold más alto si hay demasiado ruido.

---

# 🟪 2. Interpretación del Heatmap (dow × minuto)

### ✔ ¿Qué representa?
- Tasa de anomalías por **día de la semana** (0=Lunes..6=Domingo) y **minuto del día** (0..1439).

### 🧠 ¿Para qué sirve?
- Identificar **falsos positivos sistemáticos**.
- Ver si el modelo captura **eventos reales** sin “alfombrar”.

### 🧭 Cómo interpretarlo
- **Azul oscuro (~0%)** → normalidad estable.
- **Manchas amarillas aisladas** → anomalías reales (accidentes, spikes…).
- **Franjas completas** → threshold demasiado bajo o mad_floor demasiado pequeño.

### ✔ Acciones según visualización
| Patrón observado | Acción recomendada |
|------------------|--------------------|
| Franjas amplias | Subir threshold (3.5→4.5) o mad_floor (1.5→2.0) |
| Manchas pequeñas | OK: anomalías reales |
| Azul completo | OK: dataset estable |

---

# 🚀 3. Checklist para futura implementación del modo **Streaming / Replay**

## 🎛 Configuración en UI
- [ ] Toggle: **Modo Streaming (Replay)**.
- [ ] Selectbox: **Velocidad** (x1, x5, x10).
- [ ] Slider: **Paso de tick** (1–15 min).
- [ ] Botones: **▶ Play**, **⏸ Pause**, **⏭ Step**.

## 🧠 Lógica de operación
- [ ] Mantener índice `stream_index`.
- [ ] En cada tick: añadir **k minutos** al buffer `df_stream`.
- [ ] Recalcular baseline MAD sobre la **ventana retrospectiva** del buffer.
- [ ] Puntuar solo el **chunk nuevo** (eficiente).
- [ ] Añadir las nuevas anomalías a `resultados`.
- [ ] Refrescar interfaz (`st.experimental_rerun`).

## 📈 Gráficos
- [ ] Mostrar solo `df_stream` (no todo el dataset).
- [ ] Recalcular score plot en cada tick.

## 🗂️ Logging
- [ ] Guardar eventos detectados por tick.
- [ ] Guardar parámetros usados.
- [ ] Exportable como CSV/JSON.

---

# 🎯 4. Resultado esperado final
- Modelo MAD estable, sin “alfombra roja”.
- RCF e IF calibrados y comparables.
- Heatmap limpio.
- Modo Streaming para simular operación real.

