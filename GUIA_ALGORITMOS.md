# Guía Simple de Algoritmos de Detección de Anomalías (Tráfico Urbano)

> Documento para acompañar la app de Streamlit. Explicaciones claras y breves para poder contarlas a cualquier persona.

---

## 🚦 Visión general
Cada algoritmo es una forma distinta de decidir si un punto "destaca demasiado" o **rompe el patrón normal** del tráfico.

- **MAD (Median Absolute Deviation)**: compara cada punto con el **valor típico** (mediana) y mide cuántas desviaciones MAD se aleja.
- **Isolation Forest**: intenta **aislar** las observaciones con particiones aleatorias; las que se aíslan antes son más raras.
- **Random Cut Forest (RCF)**: hace **cortes aleatorios** y mide cuánto **deforma/rompe** la estructura cada punto (score *codisp*).

---

## 1️⃣ MAD (Median Absolute Deviation)

### ¿Qué idea utiliza?
Calcula una **línea base** (la **mediana**) en una ventana histórica (p. ej., 42 días) y el **MAD** (mediana de las desviaciones absolutas). Para cada punto:

> *¿Se aleja más de X veces el MAD respecto a la mediana?*

**Score:** 

```
score = |x_t - mediana| / MAD
```

Se marca como anomalía si `score > threshold` (en MADs).

### Metáfora
"Normalmente pasan entre 20 y 40 coches. Si hoy pasan 100, suena raro".

### Umbral que se ajusta
- **Threshold (MADs)**: cuántas MADs permites antes de decir "esto es raro".
  - Alto → menos anomalías (más conservador).
  - Bajo → más anomalías (más sensible).

### Pros / Contras
- ✅ **Muy simple** y **explicable**. Robusto a picos aislados.
- ❌ Puede **perder** anomalías **sutiles** (cambios de forma/tendencia suave).

---

## 2️⃣ Isolation Forest

### ¿Qué idea utiliza?
Construye **árboles aleatorios** que separan los datos con preguntas del tipo "¿mayor o menor que…?". Si un punto se **aísla en pocas particiones**, es **raro**.

### Metáfora
Coches aparcados en grupo: el que queda **muy separado** se ve rápido.

### Umbral que se ajusta
- **Contamination** (proporción esperada de anomalías):
  - 0.01 ⇒ ~1% más raros serán etiquetados.
  - Es un **umbral relativo** (porcentaje), no absoluto.

### Pros / Contras
- ✅ Capta **formas raras** y funciona bien con **múltiples variables** (si las añades).
- ❌ La interpretación del score es **menos directa**; depende del porcentaje elegido.

---

## 3️⃣ Random Cut Forest (RCF)

### ¿Qué idea utiliza?
Crea un **bosque** de árboles con **cortes aleatorios**. Para cada punto calcula cuánto **rompe** la estructura global (**codisp**). Normalizamos ese score a 0..1.

### Metáfora
Un bloque de gelatina (los datos): si metes una cuchara (el punto), la gelatina se **deforma**. Cuanta más deformación, más raro el punto.

### Umbrales/parámetros que se ajustan
- **Contamination**: percentil de rareza (top *p*%).
- **Shingle size**: tamaño de **ventana temporal** (usa últimos *k* valores como vector) → capta **forma** y reduce falsos positivos puntuales.
- **Tree size / n_trees**: tamaño y número de árboles → equilibrio entre **estabilidad** y **tiempo**.

### Pros / Contras
- ✅ Detecta **anomalías sutiles** (cambios de forma, micro‑picos, transiciones).
- ❌ Es el más **sensible** por defecto; sin calibración puede **marcar de más**.

---

## 🧭 Resumen en una tabla

| Algoritmo | Cómo funciona (muy simple) | Mejor en… | Peligro principal |
|---|---|---|---|
| **MAD** | Compara con el valor típico (mediana) en MADs. | **Picos grandes** y caídas claras. | Se **pierde** cambios sutiles. |
| **Isolation Forest** | Aísla puntos con pocas particiones aleatorias. | **Formas raras**, multivariado. | Depende del **porcentaje** elegido. |
| **RCF** | Mide cuánto **rompe** la estructura (codisp). | **Cambios sutiles**, estructura temporal. | **Demasiado sensible** si no se calibra. |

---

## 🏆 Recomendación para tráfico urbano
- **Operación diaria (estable):** usar **MAD** como base (ventana amplia, threshold ~3.2–3.8).
- **Patrones complejos / multivariado:** añadir **Isolation Forest** (contamination ~0.005–0.01).
- **Búsqueda de sutiles / exploración:** **RCF** con configuración **conservadora**:
  - `contamination = 0.001–0.003`
  - `shingle_size = 3` (o 5 si hay ruido)
  - `tree_size = 512`, `n_trees = 80–100`

**Idea para explicar a tu equipo:**
> “MAD es mi línea base, simple y estable. Isolation Forest me ayuda cuando hay más señales o formas raras. RCF lo uso para detectar anomalías sutiles, pero lo calibro para que no marque de más.”
