import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
from collections import deque
import os

# ============================================================================
# CONFIGURACIÓN STREAMLIT
# ============================================================================

st.set_page_config(
    page_title="Detector de Anomalías - Tráfico",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
st.markdown("""
<style>
    .main {
        padding-top: 2rem;
    }
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
""", unsafe_allow_html=True)


# ============================================================================
# CLASE DETECTOR (CON VENTANA APLICADA)
# ============================================================================

class TrafficAnomalyDetectorStreamlit:
    """
    Detector de anomalías con MAD Ventana Móvil.

    - window_days: define cuántos días de historia se usan para el baseline
      (últimos N días del dataset).
    - threshold: umbral en MADs.
    """

    def __init__(self, window_days=30, threshold=2.5):
        self.window_days = window_days
        self.window_minutos = window_days * 1440
        self.threshold = threshold

        # Buffer circular sobre intensidades
        self.buffer = deque(maxlen=self.window_minutos)

        # Baseline
        self.baseline_med = None
        self.baseline_mad = None
        self.baseline_ts = None

        # Estadísticas
        self.anomalias_detectadas = []
        self.score_history = []

    def _filtrar_ventana(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Filtra df para usar solo los últimos `window_days` días
        según la columna timestamp.
        """
        df = df.copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')

        if df.empty:
            return df

        t_max = df['timestamp'].max()
        t_min = t_max - pd.Timedelta(days=self.window_days)
        df_win = df[df['timestamp'] >= t_min]

        # Si por lo que sea hay muy pocos puntos, usa todo el df
        if len(df_win) < 100:
            df_win = df

        return df_win

    def cargar_historico(self, df: pd.DataFrame):
        """
        Carga datos históricos, aplica ventana de días,
        y calcula baseline (mediana y MAD).
        """
        df_win = self._filtrar_ventana(df)
        intensity = df_win['intensity'].values

        if len(intensity) == 0:
            self.baseline_med = None
            self.baseline_mad = None
            self.baseline_ts = None
            return {"mediana": np.nan, "mad": np.nan, "puntos": 0}

        # Mediana
        self.baseline_med = np.median(intensity)

        # MAD = mediana(|x - mediana|)
        desviaciones = np.abs(intensity - self.baseline_med)
        mad_val = np.median(desviaciones)
        self.baseline_mad = mad_val if mad_val > 0 else np.std(intensity)

        self.baseline_ts = df_win['timestamp'].max()
        self.buffer = deque(intensity, maxlen=self.window_minutos)

        return {
            "mediana": self.baseline_med,
            "mad": self.baseline_mad,
            "puntos": len(intensity),
        }

    def procesar_punto(self, timestamp, intensity, threshold=None):
        """
        Procesa un punto en tiempo real.
        """
        if self.baseline_med is None or self.baseline_mad is None or self.baseline_mad == 0:
            return None

        th = threshold if threshold is not None else self.threshold

        desviacion_mads = abs((intensity - self.baseline_med) / self.baseline_mad)
        es_anomalia = desviacion_mads > th

        self.buffer.append(intensity)

        resultado = {
            "timestamp": timestamp,
            "intensity": intensity,
            "expected": self.baseline_med,
            "desviacion_mads": desviacion_mads,
            "es_anomalia": es_anomalia,
            "confianza": min(desviacion_mads / th, 1.0) if th > 0 else 0.0,
        }

        self.score_history.append(resultado)
        if es_anomalia:
            self.anomalias_detectadas.append(resultado)

        return resultado

    def procesar_lote(self, df: pd.DataFrame, threshold=None):
        """
        Procesa un dataframe completo con el baseline ya calculado.
        """
        resultados = []
        th = threshold if threshold is not None else self.threshold

        for _, row in df.iterrows():
            r = self.procesar_punto(row["timestamp"], row["intensity"], threshold=th)
            if r is not None:
                resultados.append(r)

        return resultados

    def get_estadisticas(self):
        """
        Devuelve estadísticas del detector.
        """
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
# INICIALIZAR SESIÓN
# ============================================================================

if "detector" not in st.session_state:
    st.session_state.detector = TrafficAnomalyDetectorStreamlit(window_days=30, threshold=2.5)

if "df_cargado" not in st.session_state:
    st.session_state.df_cargado = None

if "resultados" not in st.session_state:
    st.session_state.resultados = []

if "threshold_actual" not in st.session_state:
    st.session_state.threshold_actual = 2.5

if "window_days" not in st.session_state:
    st.session_state.window_days = 30


# ============================================================================
# INTERFAZ PRINCIPAL
# ============================================================================

st.title("🚗 Detector de Anomalías en Tráfico")
st.markdown(
    """
Sistema de detección en tiempo real usando **MAD Ventana Móvil**.
Método robusto frente a outliers.[web:121]
"""
)

# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    st.header("⚙️ Configuración")

    # 1) Selección de dataset
    st.subheader("1️⃣ Seleccionar Dataset")

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
            "Subir CSV",
            type=["csv"],
            help="CSV con columnas: timestamp, intensity, occupancy",
        )
        archivo_usar = archivo_cargado
    else:
        archivo_usar = archivo_map.get(dataset_seleccionado)

    # 2) Botón cargar dataset
    if st.button("📂 Cargar Dataset", key="btn_cargar"):
        try:
            if isinstance(archivo_usar, str):
                df = pd.read_csv(archivo_usar)
            else:
                df = pd.read_csv(archivo_usar)

            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.sort_values("timestamp").reset_index(drop=True)

            st.session_state.df_cargado = df

            # Nuevo detector con parámetros actuales
            st.session_state.detector = TrafficAnomalyDetectorStreamlit(
                window_days=st.session_state.window_days,
                threshold=st.session_state.threshold_actual,
            )

            stats_baseline = st.session_state.detector.cargar_historico(df)
            st.session_state.resultados = st.session_state.detector.procesar_lote(
                df, threshold=st.session_state.threshold_actual
            )

            st.success(f"✓ Datos cargados: {len(df)} registros")
            st.info(
                f"""
**Baseline entrenado (ventana aplicada):**
- Puntos usados: {stats_baseline['puntos']}
- Mediana: {stats_baseline['mediana']:.1f}
- MAD: {stats_baseline['mad']:.2f}
- Ventana: {st.session_state.window_days} días
- Threshold: {st.session_state.threshold_actual:.1f} MADs
"""
            )

        except Exception as e:
            st.error(f"❌ Error cargando datos: {str(e)}")

    st.divider()

    # 3) Parámetros
    st.subheader("2️⃣ Parámetros del Detector")

    window_days = st.slider(
        "Ventana histórica (días):",
        min_value=7,
        max_value=90,
        value=st.session_state.window_days,
        step=7,
        help="Días de historia usados para calcular baseline (últimos N días del dataset).",
    )
    st.session_state.window_days = window_days

    threshold = st.slider(
        "Threshold (MADs):",
        min_value=1.5,
        max_value=5.0,
        value=st.session_state.threshold_actual,
        step=0.1,
        help="Mayor = menos sensible, menos falsos positivos.",
    )
    st.session_state.threshold_actual = threshold

    st.divider()

    # 4) Botón recalcular
    st.subheader("3️⃣ Recalcular con nuevos parámetros")

    if st.button("🔄 Recalcular", key="btn_recalc"):
        if st.session_state.df_cargado is not None:
            if "detector" in st.session_state:
                del st.session_state.detector

            st.session_state.detector = TrafficAnomalyDetectorStreamlit(
                window_days=st.session_state.window_days,
                threshold=st.session_state.threshold_actual,
            )

            df = st.session_state.df_cargado
            stats_baseline = st.session_state.detector.cargar_historico(df)
            st.session_state.resultados = st.session_state.detector.procesar_lote(
                df, threshold=st.session_state.threshold_actual
            )

            st.success(
                f"✓ Recalculado (puntos ventana: {stats_baseline['puntos']}, "
                f"mediana: {stats_baseline['mediana']:.1f}, MAD: {stats_baseline['mad']:.2f})"
            )
        else:
            st.warning("⚠️ Carga un dataset primero.")

    st.divider()

    # 5) Info rápida
    st.subheader("ℹ️ Información rápida")

    det = st.session_state.detector
    if det.baseline_med is not None:
        stats = det.get_estadisticas()

        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                "Anomalías",
                stats["total_anomalias"],
                delta=f"{100 * stats['total_anomalias'] / max(1, len(st.session_state.resultados)):.1f}%",
            )
        with col2:
            st.metric("Buffer", f"{stats['buffer_tamaño']:,}", delta="puntos")

        st.text(
            f"""
Parámetros actuales:
- Ventana: {st.session_state.window_days} días
- Threshold: {st.session_state.threshold_actual:.1f} MADs
- Mediana: {stats['baseline_mediana']:.1f}
- MAD: {stats['baseline_mad']:.2f}
"""
        )


# ============================================================================
# CONTENIDO PRINCIPAL
# ============================================================================

if st.session_state.df_cargado is None:
    st.warning("👈 Carga un dataset en la barra lateral para comenzar")
else:
    df = st.session_state.df_cargado
    resultados = st.session_state.resultados
    detector = st.session_state.detector

    tab1, tab2, tab3, tab4 = st.tabs(
        ["📊 Gráficos", "🔴 Anomalías", "📈 Análisis", "ℹ️ Información"]
    )

    # ---------- TAB 1: GRÁFICOS ----------
    with tab1:
        st.subheader("Intensidad de Tráfico con Anomalías")

        df_res = pd.DataFrame(resultados)
        df_res["timestamp"] = pd.to_datetime(df_res["timestamp"])

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
                        size=10, color="red", symbol="diamond", line=dict(color="darkred", width=2)
                    ),
                )
            )

        if detector.baseline_med is not None:
            fig.add_hline(
                y=detector.baseline_med,
                line_dash="dash",
                line_color="green",
                annotation_text=f"Baseline: {detector.baseline_med:.0f}",
                annotation_position="right",
            )

            thr_val = st.session_state.threshold_actual
            fig.add_hline(
                y=detector.baseline_med + thr_val * detector.baseline_mad,
                line_dash="dot",
                line_color="orange",
                opacity=0.5,
            )
            fig.add_hline(
                y=detector.baseline_med - thr_val * detector.baseline_mad,
                line_dash="dot",
                line_color="orange",
                opacity=0.5,
            )

        fig.update_layout(
            title="Intensidad de Tráfico",
            xaxis_title="Tiempo",
            yaxis_title="Intensidad (veh/min)",
            hovermode="x unified",
            height=500,
            template="plotly_white",
        )

        st.plotly_chart(fig, use_container_width=True)

        # Score MAD
        st.subheader("Score de Anomalía (MADs desde baseline)")

        fig2 = go.Figure()
        fig2.add_trace(
            go.Scatter(
                x=df_res["timestamp"],
                y=df_res["desviacion_mads"],
                name="Score (MADs)",
                mode="lines",
                line=dict(color="purple", width=2),
                fill="tozeroy",
            )
        )

        fig2.add_hline(
            y=st.session_state.threshold_actual,
            line_dash="dash",
            line_color="red",
            annotation_text=f"Threshold ({st.session_state.threshold_actual:.1f})",
            annotation_position="right",
        )

        fig2.update_layout(
            title="Desviación desde Baseline",
            xaxis_title="Tiempo",
            yaxis_title="Número de MADs",
            hovermode="x unified",
            height=400,
            template="plotly_white",
        )

        st.plotly_chart(fig2, use_container_width=True)

    # ---------- TAB 2: ANOMALÍAS ----------
    with tab2:
        st.subheader("Detalle de Anomalías Detectadas")

        if len(detector.anomalias_detectadas) == 0:
            st.info("✓ No se detectaron anomalías")
        else:
            df_anomalias = pd.DataFrame(detector.anomalias_detectadas)
            df_anomalias["timestamp"] = pd.to_datetime(df_anomalias["timestamp"])

            st.dataframe(
                df_anomalias[
                    ["timestamp", "intensity", "expected", "desviacion_mads", "confianza"]
                ]
                .assign(
                    timestamp=lambda x: x["timestamp"].dt.strftime("%Y-%m-%d %H:%M"),
                    intensity=lambda x: x["intensity"].round(1),
                    expected=lambda x: x["expected"].round(1),
                    desviacion_mads=lambda x: x["desviacion_mads"].round(2),
                    confianza=lambda x: (x["confianza"] * 100).round(0).astype(int).astype(str)
                    + "%",
                ),
                use_container_width=True,
                hide_index=True,
            )

    # ---------- TAB 3: ANÁLISIS ----------
    with tab3:
        st.subheader("Análisis Detallado")

        col1, col2 = st.columns(2)

        with col1:
            st.metric("Mediana", f"{detector.baseline_med:.1f}")
            st.metric("MAD", f"{detector.baseline_mad:.2f}")
            st.metric("Threshold Actual", f"{st.session_state.threshold_actual:.1f} MADs")
        with col2:
            st.metric("Desv. Std", f"{df['intensity'].std():.2f}")
            iqr = df["intensity"].quantile(0.75) - df["intensity"].quantile(0.25)
            st.metric("IQR", f"{iqr:.1f}")
            cv = df["intensity"].std() / df["intensity"].mean()
            st.metric("Coef. Variación", f"{cv:.2%}")

    # ---------- TAB 4: INFORMACIÓN ----------
    with tab4:
        st.subheader("Información del Sistema")
        st.markdown(
            f"""
**Método:** MAD Ventana Móvil sobre últimos {st.session_state.window_days} días.[web:121][web:127]

- Ventana histórica: {st.session_state.window_days} días
- Threshold actual: {st.session_state.threshold_actual:.1f} MADs
- Mediana baseline: {detector.baseline_med:.1f}
- MAD baseline: {detector.baseline_mad:.2f}
"""
        )
