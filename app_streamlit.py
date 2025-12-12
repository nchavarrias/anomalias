import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
from collections import deque

from sklearn.ensemble import IsolationForest  # Isolation Forest[web:143]

# ============================================================================
# CONFIGURACIÓN STREAMLIT
# ============================================================================

st.set_page_config(
    page_title="Detector de Anomalías - Tráfico",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    .main { padding-top: 2rem; }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .anomaly {
        background-color: #ffcccc;
        padding: 0.5rem;
        border-left: 4px solid #ff0000;
        border-radius: 0.25rem;
        margin: 0.25rem 0;
    }
    .normal {
        background-color: #ccffcc;
        padding: 0.5rem;
        border-left: 4px solid #00cc00;
        border-radius: 0.25rem;
        margin: 0.25rem 0;
    }
</style>
""",
    unsafe_allow_html=True,
)

# ============================================================================
# CLASE 1: DETECTOR MAD (VENTANA DESLIZANTE)
# ============================================================================


class TrafficAnomalyDetectorMAD:
    """
    Detector de anomalías basado en:
    - Baseline = mediana de intensidad
    - MAD = mediana(|x - mediana|)
    - Score = |x - baseline| / MAD
    - Anomalía si score > threshold

    Usa solo los últimos `window_days` días del dataset para calcular baseline.[web:29][web:121]
    """

    def __init__(self, window_days=42, threshold=3.5):
        self.window_days = window_days
        self.window_minutos = window_days * 1440
        self.threshold = threshold

        self.buffer = deque(maxlen=self.window_minutos)
        self.baseline_med = None
        self.baseline_mad = None
        self.baseline_ts = None

        self.anomalias_detectadas = []
        self.score_history = []

    def _filtrar_ventana(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp")
        if df.empty:
            return df

        t_max = df["timestamp"].max()
        t_min = t_max - pd.Timedelta(days=self.window_days)
        df_win = df[df["timestamp"] >= t_min]

        if len(df_win) < 100:
            df_win = df

        return df_win

    def cargar_historico(self, df: pd.DataFrame):
        df_win = self._filtrar_ventana(df)
        intensity = df_win["intensity"].values

        if len(intensity) == 0:
            self.baseline_med = None
            self.baseline_mad = None
            self.baseline_ts = None
            return {"mediana": np.nan, "mad": np.nan, "puntos": 0}

        self.baseline_med = np.median(intensity)
        desviaciones = np.abs(intensity - self.baseline_med)
        mad_val = np.median(desviaciones)
        self.baseline_mad = mad_val if mad_val > 0 else np.std(intensity)

        self.baseline_ts = df_win["timestamp"].max()
        self.buffer = deque(intensity, maxlen=self.window_minutos)

        return {
            "mediana": self.baseline_med,
            "mad": self.baseline_mad,
            "puntos": len(intensity),
        }

    def procesar_punto(self, timestamp, intensity, threshold=None):
        if (
            self.baseline_med is None
            or self.baseline_mad is None
            or self.baseline_mad == 0
        ):
            return None

        th = threshold if threshold is not None else self.threshold
        score = abs((intensity - self.baseline_med) / self.baseline_mad)
        es_anomalia = score > th

        self.buffer.append(intensity)

        res = {
            "timestamp": timestamp,
            "intensity": intensity,
            "expected": self.baseline_med,
            "score": score,
            "es_anomalia": es_anomalia,
            "confianza": min(score / th, 1.0) if th > 0 else 0.0,
        }

        self.score_history.append(res)
        if es_anomalia:
            self.anomalias_detectadas.append(res)

        return res

    def procesar_lote(self, df: pd.DataFrame, threshold=None):
        resultados = []
        th = threshold if threshold is not None else self.threshold

        for _, row in df.iterrows():
            r = self.procesar_punto(row["timestamp"], row["intensity"], threshold=th)
            if r is not None:
                resultados.append(r)

        return resultados

    def get_estadisticas(self):
        return {
            "total_anomalias": len(self.anomalias_detectadas),
            "baseline_mediana": self.baseline_med,
            "baseline_mad": self.baseline_mad,
            "buffer_tamaño": len(self.buffer),
            "baseline_edad_horas": (
                (datetime.now() - self.baseline_ts).total_seconds() / 3600
                if self.baseline_ts is not None
                else None
            ),
            "ultima_anomalia": (
                self.anomalias_detectadas[-1]["timestamp"]
                if self.anomalias_detectadas
                else None
            ),
        }


# ============================================================================
# CLASE 2: DETECTOR ISOLATION FOREST
# ============================================================================


class TrafficAnomalyDetectorIForest:
    """
    Detector de anomalías basado en Isolation Forest (sklearn).[web:140][web:143]

    - Entrena un bosque de árboles que aíslan puntos "raros".
    - Devuelve score (cuanto más negativo, más anómalo) y etiqueta.
    """

    def __init__(self, contamination=0.01, random_state=42):
        self.contamination = contamination
        self.random_state = random_state

        self.modelo = None
        self.fitted = False

        self.anomalias_detectadas = []
        self.score_history = []

    def cargar_historico(self, df: pd.DataFrame):
        """
        Entrena el IsolationForest sobre las features disponibles.
        Aquí usamos solo intensity, pero puedes añadir occupancy, etc.[web:17][web:146]
        """
        df = df.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp")

        X = df[["intensity"]].values  # extender con más features si quieres

        self.modelo = IsolationForest(
            contamination=self.contamination,
            random_state=self.random_state,
        )
        self.modelo.fit(X)
        self.fitted = True

        return {"puntos": len(df)}

    def procesar_lote(self, df: pd.DataFrame):
        if not self.fitted or self.modelo is None:
            return []

        df = df.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp")

        X = df[["intensity"]].values

        # predict: 1 = normal, -1 = anomalía
        y_pred = self.modelo.predict(X)
        scores = self.modelo.score_samples(X)  # mayor = más normal, más bajo = más raro[web:140]

        resultados = []
        self.anomalias_detectadas = []
        self.score_history = []

        # normalizamos el score a algo positivo para compararlo visualmente
        score_min = scores.min()
        score_max = scores.max()
        denom = score_max - score_min if score_max > score_min else 1.0
        scores_norm = (scores - score_min) / denom

        for i, row in df.iterrows():
            es_anomalia = y_pred[i] == -1
            score_norm = 1.0 - scores_norm[i]  # 0 normal, 1 muy raro

            res = {
                "timestamp": row["timestamp"],
                "intensity": row["intensity"],
                "expected": np.nan,  # IF no da baseline explícito
                "score": score_norm,
                "es_anomalia": es_anomalia,
                "confianza": score_norm,
            }

            resultados.append(res)
            self.score_history.append(res)
            if es_anomalia:
                self.anomalias_detectadas.append(res)

        return resultados

    def get_estadisticas(self):
        return {
            "total_anomalias": len(self.anomalias_detectadas),
            "baseline_mediana": np.nan,
            "baseline_mad": np.nan,
            "buffer_tamaño": len(self.score_history),
            "baseline_edad_horas": None,
            "ultima_anomalia": (
                self.anomalias_detectadas[-1]["timestamp"]
                if self.anomalias_detectadas
                else None
            ),
        }


# ============================================================================
# INICIALIZACIÓN DE ESTADO
# ============================================================================

if "algoritmo" not in st.session_state:
    st.session_state.algoritmo = "MAD (Ventana deslizante)"

if "detector" not in st.session_state:
    st.session_state.detector = None

if "df_cargado" not in st.session_state:
    st.session_state.df_cargado = None

if "resultados" not in st.session_state:
    st.session_state.resultados = []

if "threshold_actual" not in st.session_state:
    st.session_state.threshold_actual = 3.5

if "window_days" not in st.session_state:
    st.session_state.window_days = 42

if "contamination_iforest" not in st.session_state:
    st.session_state.contamination_iforest = 0.01


# ============================================================================
# CABECERA
# ============================================================================

st.title("🚗 Detector de Anomalías en Tráfico")
st.markdown(
    """
Compara dos algoritmos de detección de anomalías:
- **MAD con ventana deslizante** (robusto estadístico).[web:29][web:121]  
- **Isolation Forest** (modelo basado en árboles de aislamiento).[web:140][web:143]
"""
)

# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    st.header("⚙️ Configuración")

    # Algoritmo
    st.subheader("0️⃣ Algoritmo")
    algoritmo = st.selectbox(
        "Método de detección:",
        ["MAD (Ventana deslizante)", "Isolation Forest"],
        index=0 if st.session_state.algoritmo == "MAD (Ventana deslizante)" else 1,
    )
    st.session_state.algoritmo = algoritmo

    # Dataset
    st.subheader("1️⃣ Dataset")

    datasets_disponibles = [
        "Subir CSV personalizado",
        "Tráfico Normal (30 días)",
        "Con Incidencias (3 eventos)",
        "Cambio Gradual (Obra)",
        "Ruido Alto (Sensores malos)",
        "Últimas 24 horas + Anomalía",
    ]

    dataset_seleccionado = st.selectbox("Dataset:", datasets_disponibles)

    archivo_map = {
        "Tráfico Normal (30 días)": "datos_trafico/trafico_normal.csv",
        "Con Incidencias (3 eventos)": "datos_trafico/trafico_con_incidencias.csv",
        "Cambio Gradual (Obra)": "datos_trafico/trafico_cambio_gradual.csv",
        "Ruido Alto (Sensores malos)": "datos_trafico/trafico_ruido_alto.csv",
        "Últimas 24 horas + Anomalía": "datos_trafico/trafico_ultimas_24h.csv",
    }

    if dataset_seleccionado == "Subir CSV personalizado":
        archivo_cargado = st.file_uploader(
            "Subir CSV", type=["csv"], help="CSV con columnas: timestamp, intensity"
        )
        archivo_usar = archivo_cargado
    else:
        archivo_usar = archivo_map.get(dataset_seleccionado)

    # Botón cargar
    if st.button("📂 Cargar Dataset", key="btn_cargar"):
        try:
            if isinstance(archivo_usar, str):
                df = pd.read_csv(archivo_usar)
            else:
                df = pd.read_csv(archivo_usar)

            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.sort_values("timestamp").reset_index(drop=True)

            st.session_state.df_cargado = df

            # Crear detector según algoritmo
            if algoritmo.startswith("MAD"):
                st.session_state.detector = TrafficAnomalyDetectorMAD(
                    window_days=st.session_state.window_days,
                    threshold=st.session_state.threshold_actual,
                )
                stats_base = st.session_state.detector.cargar_historico(df)
                st.session_state.resultados = st.session_state.detector.procesar_lote(
                    df, threshold=st.session_state.threshold_actual
                )
                st.success(
                    f"MAD entrenado con {stats_base['puntos']} puntos "
                    f"(mediana={stats_base['mediana']:.1f}, MAD={stats_base['mad']:.2f})"
                )
            else:
                st.session_state.detector = TrafficAnomalyDetectorIForest(
                    contamination=st.session_state.contamination_iforest
                )
                stats_base = st.session_state.detector.cargar_historico(df)
                st.session_state.resultados = st.session_state.detector.procesar_lote(df)
                st.success(
                    f"Isolation Forest entrenado con {stats_base['puntos']} puntos, "
                    f"contamination={st.session_state.contamination_iforest:.3f}"
                )

        except Exception as e:
            st.error(f"❌ Error cargando datos: {str(e)}")

    st.divider()

    # Parámetros según algoritmo
    st.subheader("2️⃣ Parámetros")

    if algoritmo.startswith("MAD"):
        window_days = st.slider(
            "Ventana histórica (días):",
            min_value=7,
            max_value=90,
            value=st.session_state.window_days,
            step=7,
        )
        st.session_state.window_days = window_days

        threshold = st.slider(
            "Threshold (MADs):",
            min_value=1.5,
            max_value=5.0,
            value=st.session_state.threshold_actual,
            step=0.1,
        )
        st.session_state.threshold_actual = threshold
    else:
        contamination = st.slider(
            "Contamination (proporción esperada de anomalías):",
            min_value=0.001,
            max_value=0.1,
            value=st.session_state.contamination_iforest,
            step=0.001,
        )
        st.session_state.contamination_iforest = contamination

    st.divider()

    # Recalcular
    st.subheader("3️⃣ Recalcular")

    if st.button("🔄 Recalcular con parámetros actuales", key="btn_recalc"):
        if st.session_state.df_cargado is None:
            st.warning("⚠️ Carga un dataset primero.")
        else:
            df = st.session_state.df_cargado

            if algoritmo.startswith("MAD"):
                st.session_state.detector = TrafficAnomalyDetectorMAD(
                    window_days=st.session_state.window_days,
                    threshold=st.session_state.threshold_actual,
                )
                stats_base = st.session_state.detector.cargar_historico(df)
                st.session_state.resultados = st.session_state.detector.procesar_lote(
                    df, threshold=st.session_state.threshold_actual
                )
                st.success(
                    f"MAD recalculado (puntos={stats_base['puntos']}, "
                    f"mediana={stats_base['mediana']:.1f}, MAD={stats_base['mad']:.2f})"
                )
            else:
                st.session_state.detector = TrafficAnomalyDetectorIForest(
                    contamination=st.session_state.contamination_iforest
                )
                stats_base = st.session_state.detector.cargar_historico(df)
                st.session_state.resultados = st.session_state.detector.procesar_lote(df)
                st.success(
                    f"Isolation Forest recalculado (puntos={stats_base['puntos']}, "
                    f"contamination={st.session_state.contamination_iforest:.3f})"
                )

    st.divider()

    # Info rápida
    st.subheader("ℹ️ Info rápida")
    det = st.session_state.detector
    if det is not None and st.session_state.df_cargado is not None:
        stats = det.get_estadisticas()
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Anomalías", stats["total_anomalias"])
        with col2:
            st.metric("Puntos procesados", len(st.session_state.resultados))


# ============================================================================
# CONTENIDO PRINCIPAL (TABS)
# ============================================================================

if st.session_state.df_cargado is None or st.session_state.detector is None:
    st.warning("👈 Carga un dataset en la barra lateral para comenzar.")
else:
    df = st.session_state.df_cargado
    resultados = st.session_state.resultados
    detector = st.session_state.detector

    df_res = pd.DataFrame(resultados)
    if not df_res.empty:
        df_res["timestamp"] = pd.to_datetime(df_res["timestamp"])

    tab1, tab2, tab3, tab4 = st.tabs(
        ["📊 Gráficos", "🔴 Anomalías", "📈 Análisis", "ℹ️ Información"]
    )

    # ---------- TAB 1: GRÁFICOS ----------
    with tab1:
        st.subheader("Intensidad de Tráfico con Anomalías")

        if df_res.empty:
            st.info("No hay resultados aún.")
        else:
            df_normales = df_res[~df_res["es_anomalia"]]
            df_anom = df_res[df_res["es_anomalia"]]

            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=df_normales["timestamp"],
                    y=df_normales["intensity"],
                    name="Intensidad (Normal)",
                    mode="lines",
                    line=dict(color="#1f77b4", width=1),
                )
            )
            if len(df_anom) > 0:
                fig.add_trace(
                    go.Scatter(
                        x=df_anom["timestamp"],
                        y=df_anom["intensity"],
                        name="Anomalías",
                        mode="markers",
                        marker=dict(
                            size=9,
                            color="red",
                            symbol="x",
                            line=dict(color="darkred", width=1),
                        ),
                    )
                )

            # Si es MAD, pintamos baseline y bandas
            if isinstance(detector, TrafficAnomalyDetectorMAD):
                if detector.baseline_med is not None:
                    fig.add_hline(
                        y=detector.baseline_med,
                        line_dash="dash",
                        line_color="green",
                        annotation_text=f"Baseline {detector.baseline_med:.0f}",
                        annotation_position="right",
                    )
                    thr = st.session_state.threshold_actual
                    fig.add_hline(
                        y=detector.baseline_med + thr * detector.baseline_mad,
                        line_dash="dot",
                        line_color="orange",
                        opacity=0.5,
                    )
                    fig.add_hline(
                        y=detector.baseline_med - thr * detector.baseline_mad,
                        line_dash="dot",
                        line_color="orange",
                        opacity=0.5,
                    )

            fig.update_layout(
                title=f"Intensidad - Algoritmo: {st.session_state.algoritmo}",
                xaxis_title="Tiempo",
                yaxis_title="Intensidad (veh/min)",
                hovermode="x unified",
                height=500,
                template="plotly_white",
            )
            st.plotly_chart(fig, use_container_width=True)

            # Score
            st.subheader("Score de Anomalía")

            fig2 = go.Figure()
            fig2.add_trace(
                go.Scatter(
                    x=df_res["timestamp"],
                    y=df_res["score"],
                    name="Score",
                    mode="lines",
                    line=dict(color="purple", width=2),
                    fill="tozeroy",
                )
            )

            if isinstance(detector, TrafficAnomalyDetectorMAD):
                thr = st.session_state.threshold_actual
                fig2.add_hline(
                    y=thr,
                    line_dash="dash",
                    line_color="red",
                    annotation_text=f"Threshold {thr:.1f} MADs",
                    annotation_position="right",
                )
                y_title = "Score (MADs desde baseline)"
            else:
                y_title = "Score normalizado (0 normal, 1 muy raro)"

            fig2.update_layout(
                title="Score de Anomalía en el Tiempo",
                xaxis_title="Tiempo",
                yaxis_title=y_title,
                hovermode="x unified",
                height=400,
                template="plotly_white",
            )
            st.plotly_chart(fig2, use_container_width=True)

    # ---------- TAB 2: ANOMALÍAS ----------
    with tab2:
        st.subheader("Detalle de Anomalías")
        if detector.anomalias_detectadas:
            df_anom = pd.DataFrame(detector.anomalias_detectadas)
            df_anom["timestamp"] = pd.to_datetime(df_anom["timestamp"])
            st.dataframe(
                df_anom[["timestamp", "intensity", "score", "confianza"]]
                .assign(
                    timestamp=lambda x: x["timestamp"].dt.strftime(
                        "%Y-%m-%d %H:%M"
                    ),
                    intensity=lambda x: x["intensity"].round(1),
                    score=lambda x: x["score"].round(3),
                    confianza=lambda x: (
                        x["confianza"] * 100
                    ).round(0).astype(int).astype(str)
                    + "%",
                ),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No se han detectado anomalías.")

    # ---------- TAB 3: ANÁLISIS ----------
    with tab3:
        st.subheader("Análisis")
        if isinstance(detector, TrafficAnomalyDetectorMAD):
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Mediana baseline", f"{detector.baseline_med:.1f}")
                st.metric("MAD baseline", f"{detector.baseline_mad:.2f}")
            with col2:
                st.metric("Threshold", f"{st.session_state.threshold_actual:.1f} MADs")
                st.metric("Ventana", f"{st.session_state.window_days} días")
        else:
            st.write(
                f"Isolation Forest con contamination={st.session_state.contamination_iforest:.3f}."
            )

    # ---------- TAB 4: INFORMACIÓN ----------
    with tab4:
        st.subheader("Información del algoritmo")
        if isinstance(detector, TrafficAnomalyDetectorMAD):
            st.markdown(
                """
**MAD (Median Absolute Deviation con ventana deslizante)**[web:29][web:121]  

- Calcula un baseline robusto usando la mediana de la intensidad.
- Mide cuánto se aleja cada punto usando MAD (mediana de las desviaciones absolutas).
- Marca como anomalías los puntos cuya desviación supera un umbral en MADs.
- Usa solo los últimos *N días* seleccionados para calcular el baseline.
"""
            )
        else:
            st.markdown(
                """
**Isolation Forest**[web:140][web:143][web:17]  

- Entrena un bosque de árboles que aíslan observaciones en el espacio de features.
- Los puntos que se aíslan con pocas particiones se consideran anomalías.
- El parámetro *contamination* controla la proporción esperada de anomalías.
- No calcula una línea base explícita, solo un score de rareza por punto.
"""
            )

# ============================================================================
# FOOTER: DESCRIPCIÓN RESUMIDA DEL ALGORITMO SELECCIONADO
# ============================================================================

st.divider()

if st.session_state.algoritmo.startswith("MAD"):
    desc_corta = (
        "MAD con ventana deslizante: baseline robusto por mediana, "
        "ventana temporal configurable y umbral en MADs."
    )
else:
    desc_corta = (
        "Isolation Forest: bosque de árboles que aísla puntos raros; "
        "no usa baseline explícito y controla la proporción de anomalías con 'contamination'."
    )

st.markdown(
    f"""
<div style="text-align: center; color: #666; font-size: 0.9em;">
Algoritmo seleccionado: <b>{st.session_state.algoritmo}</b> — {desc_corta}
</div>
""",
    unsafe_allow_html=True,
)
