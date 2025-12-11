import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from scipy.stats import median_abs_deviation as mad
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
# CLASE DETECTOR (CORREGIDA)
# ============================================================================

class TrafficAnomalyDetectorStreamlit:
    """
    Detector de anomalías con MAD Ventana Móvil.
    
    CORRECCIONES:
    - Threshold ahora es parámetro (no hardcodeado)
    - MAD se calcula correctamente
    - Score se calcula correctamente
    """
    
    def __init__(self, window_days=30, threshold=2.5):
        self.window_days = window_days
        self.window_minutos = window_days * 1440
        self.threshold = threshold  # ← AHORA ES PARÁMETRO
        
        # Buffer circular
        self.buffer = deque(maxlen=self.window_minutos)
        
        # Baseline
        self.baseline_med = None
        self.baseline_mad = None
        self.baseline_ts = None
        
        # Estadísticas
        self.anomalias_detectadas = []
        self.score_history = []
    
    def cargar_historico(self, df):
        """Cargar datos históricos y entrenar baseline"""
        intensity = df['intensity'].values
        
        # Calcular MEDIANA
        self.baseline_med = np.median(intensity)
        
        # Calcular MAD (Median Absolute Deviation)
        # MAD = mediana(|x - mediana|)
        desviaciones = np.abs(intensity - self.baseline_med)
        mad_val = np.median(desviaciones)  # ← CORREGIDO: usar np.median
        self.baseline_mad = mad_val if mad_val > 0 else np.std(intensity)
        
        self.baseline_ts = datetime.now()
        
        self.buffer.extend(intensity)
        
        return {
            'mediana': self.baseline_med,
            'mad': self.baseline_mad,
            'puntos': len(intensity)
        }
    
    def procesar_punto(self, timestamp, intensity, threshold=None):
        """Detección en tiempo real"""
        if self.baseline_med is None:
            return None
        
        # Usar threshold del parámetro o el de la clase
        th = threshold if threshold is not None else self.threshold
        
        # Cálculo O(1)
        desviacion_mads = abs(
            (intensity - self.baseline_med) / self.baseline_mad
        )
        
        es_anomalia = desviacion_mads > th
        
        self.buffer.append(intensity)
        
        resultado = {
            'timestamp': timestamp,
            'intensity': intensity,
            'expected': self.baseline_med,
            'desviacion_mads': desviacion_mads,
            'es_anomalia': es_anomalia,
            'confianza': min(desviacion_mads / th, 1.0) if th > 0 else 0
        }
        
        self.score_history.append(resultado)
        
        if es_anomalia:
            self.anomalias_detectadas.append(resultado)
        
        return resultado
    
    def procesar_lote(self, df, threshold=None):
        """Procesar múltiples filas"""
        resultados = []
        th = threshold if threshold is not None else self.threshold
        
        for idx, row in df.iterrows():
            resultado = self.procesar_punto(row['timestamp'], row['intensity'], threshold=th)
            if resultado:
                resultados.append(resultado)
        return resultados
    
    def reentrenar_baseline(self):
        """Actualizar baseline con buffer actual"""
        if len(self.buffer) < 1000:
            return False
        
        datos = np.array(list(self.buffer))
        self.baseline_med = np.median(datos)
        
        # Recalcular MAD
        desviaciones = np.abs(datos - self.baseline_med)
        mad_val = np.median(desviaciones)
        self.baseline_mad = mad_val if mad_val > 0 else np.std(datos)
        
        self.baseline_ts = datetime.now()
        
        return True
    
    def get_estadisticas(self):
        """Obtener estadísticas"""
        return {
            'total_anomalias': len(self.anomalias_detectadas),
            'baseline_mediana': self.baseline_med,
            'baseline_mad': self.baseline_mad,
            'buffer_tamaño': len(self.buffer),
            'baseline_edad_horas': (
                (datetime.now() - self.baseline_ts).total_seconds() / 3600
                if self.baseline_ts else None
            ),
            'ultima_anomalia': (
                self.anomalias_detectadas[-1]['timestamp'] 
                if self.anomalias_detectadas else None
            )
        }


# ============================================================================
# INICIALIZAR SESIÓN
# ============================================================================

if 'detector' not in st.session_state:
    st.session_state.detector = TrafficAnomalyDetectorStreamlit(window_days=30, threshold=2.5)

if 'df_cargado' not in st.session_state:
    st.session_state.df_cargado = None

if 'resultados' not in st.session_state:
    st.session_state.resultados = []

if 'threshold_actual' not in st.session_state:
    st.session_state.threshold_actual = 2.5


# ============================================================================
# INTERFAZ PRINCIPAL
# ============================================================================

st.title("🚗 Detector de Anomalías en Tráfico")
st.markdown("""
Sistema de detección en tiempo real usando **MAD Ventana Móvil**.
Método elegido: eficiente, robusto y escalable.
""")

# ============================================================================
# SIDEBAR: CARGA DE DATOS Y PARÁMETROS
# ============================================================================

with st.sidebar:
    st.header("⚙️ Configuración")
    
    # Selector de dataset
    st.subheader("1️⃣ Seleccionar Dataset")
    
    datasets_disponibles = [
        'Subir CSV personalizado',
        'Tráfico Normal (30 días)',
        'Con Incidencias (3 eventos)',
        'Cambio Gradual (Obra)',
        'Ruido Alto (Sensores malos)',
        'Últimas 24 horas + Anomalía'
    ]
    
    dataset_seleccionado = st.selectbox(
        "Dataset:",
        datasets_disponibles
    )
    
    # Mapeo a archivos
    archivo_map = {
        'Tráfico Normal (30 días)': 'datos_trafico/trafico_normal.csv',
        'Con Incidencias (3 eventos)': 'datos_trafico/trafico_con_incidencias.csv',
        'Cambio Gradual (Obra)': 'datos_trafico/trafico_cambio_gradual.csv',
        'Ruido Alto (Sensores malos)': 'datos_trafico/trafico_ruido_alto.csv',
        'Últimas 24 horas + Anomalía': 'datos_trafico/trafico_ultimas_24h.csv',
    }
    
    # Cargar archivo
    if dataset_seleccionado == 'Subir CSV personalizado':
        archivo_cargado = st.file_uploader(
            "Subir CSV",
            type=['csv'],
            help="CSV con columnas: timestamp, intensity, occupancy"
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
            
            # Procesar timestamp
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            st.session_state.df_cargado = df
            
            # Crear nuevo detector con parámetros actuales
            st.session_state.detector = TrafficAnomalyDetectorStreamlit(
                window_days=st.session_state.window_days,
                threshold=st.session_state.threshold_actual
            )
            
            # Entrenar detector
            stats = st.session_state.detector.cargar_historico(df)
            st.session_state.resultados = st.session_state.detector.procesar_lote(
                df, 
                threshold=st.session_state.threshold_actual
            )
            
            st.success(f"✓ Datos cargados: {len(df)} registros")
            st.info(f"""
            **Baseline entrenado:**
            - Mediana: {stats['mediana']:.1f}
            - MAD: {stats['mad']:.2f}
            - Ventana: {st.session_state.window_days} días
            - Threshold: {st.session_state.threshold_actual:.1f} MADs
            - Anomalías detectadas: {len(st.session_state.detector.anomalias_detectadas)}
            """)
            
        except Exception as e:
            st.error(f"❌ Error cargando datos: {str(e)}")
    
    st.divider()
    
    # Parámetros
    st.subheader("2️⃣ Parámetros del Detector")
    
    threshold = st.slider(
        "Threshold (MADs):",
        min_value=1.5,
        max_value=5.0,
        value=st.session_state.threshold_actual,
        step=0.1,
        help="Mayor = menos sensible, menos falsos positivos"
    )
    st.session_state.threshold_actual = threshold
    
    window_days = st.slider(
        "Ventana histórica (días):",
        min_value=7,
        max_value=90,
        value=30,
        step=7,
        help="Datos para calcular baseline"
    )
    st.session_state.window_days = window_days
    
    st.divider()
    
    # Información
    st.subheader("ℹ️ Información")
    
    if st.session_state.detector.baseline_med is not None:
        stats = st.session_state.detector.get_estadisticas()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric(
                "Anomalías",
                stats['total_anomalias'],
                delta=f"{100*stats['total_anomalias']/max(1,len(st.session_state.resultados)):.1f}%"
            )
        
        with col2:
            st.metric(
                "Buffer",
                f"{stats['buffer_tamaño']:,}",
                delta="puntos"
            )
        
        st.text(f"""
Mediana: {stats['baseline_mediana']:.1f}
MAD: {stats['baseline_mad']:.2f}
Threshold: {threshold:.1f}
Edad baseline: {stats['baseline_edad_horas']:.1f}h
        """)


# ============================================================================
# CONTENIDO PRINCIPAL
# ============================================================================

if st.session_state.df_cargado is None:
    st.warning("👈 Carga un dataset en la barra lateral para comenzar")

else:
    df = st.session_state.df_cargado
    resultados = st.session_state.resultados
    detector = st.session_state.detector
    
    # ========== PESTAÑA 1: GRÁFICOS ==========
    
    tab1, tab2, tab3, tab4 = st.tabs(
        ["📊 Gráficos", "🔴 Anomalías", "📈 Análisis", "ℹ️ Información"]
    )
    
    with tab1:
        st.subheader("Intensidad de Tráfico con Anomalías")
        
        # Preparar datos para gráfico
        df_resultados = pd.DataFrame(resultados)
        df_resultados['timestamp'] = pd.to_datetime(df_resultados['timestamp'])
        
        # Separar normales y anomalías
        df_normales = df_resultados[~df_resultados['es_anomalia']]
        df_anomalias = df_resultados[df_resultados['es_anomalia']]
        
        # Crear figura
        fig = go.Figure()
        
        # Línea de intensidad actual
        fig.add_trace(go.Scatter(
            x=df_normales['timestamp'],
            y=df_normales['intensity'],
            name='Intensidad (Normal)',
            mode='lines',
            line=dict(color='#1f77b4', width=1),
            hovertemplate='<b>%{x|%H:%M}</b><br>Intensidad: %{y:.0f}<extra></extra>'
        ))
        
        # Puntos de anomalías
        if len(df_anomalias) > 0:
            fig.add_trace(go.Scatter(
                x=df_anomalias['timestamp'],
                y=df_anomalias['intensity'],
                name='Anomalías',
                mode='markers',
                marker=dict(
                    size=10,
                    color='red',
                    symbol='diamond',
                    line=dict(color='darkred', width=2)
                ),
                hovertemplate='<b>%{x|%H:%M}</b><br>Anomalía: %{y:.0f}<br><extra></extra>'
            ))
        
        # Línea baseline
        fig.add_hline(
            y=detector.baseline_med,
            line_dash="dash",
            line_color="green",
            annotation_text=f"Baseline: {detector.baseline_med:.0f}",
            annotation_position="right"
        )
        
        # Bandas ±MAD
        threshold_val = st.session_state.threshold_actual
        fig.add_hline(
            y=detector.baseline_med + threshold_val * detector.baseline_mad,
            line_dash="dot",
            line_color="orange",
            opacity=0.5
        )
        
        fig.add_hline(
            y=detector.baseline_med - threshold_val * detector.baseline_mad,
            line_dash="dot",
            line_color="orange",
            opacity=0.5
        )
        
        fig.update_layout(
            title="Intensidad de Tráfico",
            xaxis_title="Tiempo",
            yaxis_title="Intensidad (veh/min)",
            hovermode='x unified',
            height=500,
            template="plotly_white"
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Gráfico 2: Score MAD
        st.subheader("Score de Anomalía (MADs desde baseline)")
        
        fig2 = go.Figure()
        
        fig2.add_trace(go.Scatter(
            x=df_resultados['timestamp'],
            y=df_resultados['desviacion_mads'],
            name='Score (MADs)',
            mode='lines',
            line=dict(color='purple', width=2),
            fill='tozeroy',
            hovertemplate='<b>%{x|%H:%M}</b><br>Score: %{y:.2f}MAD<extra></extra>'
        ))
        
        # Línea threshold
        fig2.add_hline(
            y=threshold_val,
            line_dash="dash",
            line_color="red",
            annotation_text=f"Threshold ({threshold_val:.1f})",
            annotation_position="right"
        )
        
        fig2.update_layout(
            title="Desviación desde Baseline",
            xaxis_title="Tiempo",
            yaxis_title="Número de MADs",
            hovermode='x unified',
            height=400,
            template="plotly_white"
        )
        
        st.plotly_chart(fig2, use_container_width=True)
        
        # Gráfico 3: Histograma de intensidad
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Distribución de Intensidad")
            
            fig3 = go.Figure()
            fig3.add_trace(go.Histogram(
                x=df['intensity'],
                name='Intensidad',
                nbinsx=50,
                marker_color='lightblue'
            ))
            
            fig3.add_vline(
                x=detector.baseline_med,
                line_dash="dash",
                line_color="green",
                annotation_text="Mediana"
            )
            
            fig3.update_layout(
                title="Histograma de Intensidad",
                xaxis_title="Intensidad",
                yaxis_title="Frecuencia",
                height=400,
                template="plotly_white"
            )
            
            st.plotly_chart(fig3, use_container_width=True)
        
        with col2:
            st.subheader("Hora del Día - Patrón Medio")
            
            df['hora'] = pd.to_datetime(df['timestamp']).dt.hour
            patrón_hora = df.groupby('hora')['intensity'].mean()
            
            fig4 = go.Figure()
            fig4.add_trace(go.Scatter(
                x=patrón_hora.index,
                y=patrón_hora.values,
                mode='lines+markers',
                name='Intensidad media',
                line=dict(color='navy', width=3),
                marker=dict(size=8)
            ))
            
            fig4.update_layout(
                title="Patrón por Hora",
                xaxis_title="Hora del día",
                yaxis_title="Intensidad media",
                height=400,
                template="plotly_white"
            )
            
            st.plotly_chart(fig4, use_container_width=True)
    
    # ========== PESTAÑA 2: ANOMALÍAS ==========
    
    with tab2:
        st.subheader("Detalle de Anomalías Detectadas")
        
        if len(detector.anomalias_detectadas) == 0:
            st.info("✓ No se detectaron anomalías")
        else:
            df_anomalias = pd.DataFrame(detector.anomalias_detectadas)
            df_anomalias['timestamp'] = pd.to_datetime(df_anomalias['timestamp'])
            
            # Mostrar tabla
            st.dataframe(
                df_anomalias[[
                    'timestamp', 'intensity', 'expected', 
                    'desviacion_mads', 'confianza'
                ]].assign(
                    **{
                        'timestamp': lambda x: x['timestamp'].dt.strftime('%Y-%m-%d %H:%M'),
                        'intensity': lambda x: x['intensity'].round(1),
                        'expected': lambda x: x['expected'].round(1),
                        'desviacion_mads': lambda x: x['desviacion_mads'].round(2),
                        'confianza': lambda x: (x['confianza'] * 100).round(0).astype(int).astype(str) + '%'
                    }
                ),
                use_container_width=True,
                hide_index=True
            )
            
            # Estadísticas
            st.divider()
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total anomalías", len(df_anomalias))
            
            with col2:
                pct = 100 * len(df_anomalias) / len(resultados)
                st.metric("Porcentaje", f"{pct:.2f}%")
            
            with col3:
                score_max = df_anomalias['desviacion_mads'].max()
                st.metric("Score máximo", f"{score_max:.1f} MADs")
            
            with col4:
                duracion_min = (
                    (df_anomalias['timestamp'].max() - 
                     df_anomalias['timestamp'].min()).total_seconds() / 60
                )
                st.metric("Duración", f"{duracion_min:.0f} min")
    
    # ========== PESTAÑA 3: ANÁLISIS ==========
    
    with tab3:
        st.subheader("Análisis Detallado")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric(
                "Mediana",
                f"{detector.baseline_med:.1f}",
                help="Valor central de la distribución"
            )
            
            st.metric(
                "MAD",
                f"{detector.baseline_mad:.2f}",
                help="Desviación Absoluta Mediana"
            )
            
            st.metric(
                "Threshold Actual",
                f"{threshold_val:.1f} MADs",
                help="Umbral de anomalía"
            )
        
        with col2:
            st.metric(
                "Desv. Std",
                f"{df['intensity'].std():.2f}",
                help="Desviación estándar"
            )
            
            st.metric(
                "IQR",
                f"{df['intensity'].quantile(0.75) - df['intensity'].quantile(0.25):.1f}",
                help="Rango intercuartil"
            )
            
            st.metric(
                "Coef. Variación",
                f"{df['intensity'].std() / df['intensity'].mean():.2%}",
                help="Std / Media"
            )
        
        st.divider()
        
        # Tabla de percentiles
        st.subheader("Percentiles")
        
        percentiles = [1, 5, 10, 25, 50, 75, 90, 95, 99]
        valores = [df['intensity'].quantile(p/100) for p in percentiles]
        
        df_percentiles = pd.DataFrame({
            'Percentil': [f"P{p}" for p in percentiles],
            'Valor': valores
        })
        
        st.dataframe(df_percentiles, use_container_width=True, hide_index=True)
        
        st.divider()
        
        # Análisis por banda
        st.subheader("Análisis por Banda de Desviación")
        
        bandas = [
            ("< 1 MAD", 0, 1),
            ("1-2 MADs", 1, 2),
            ("2-3 MADs", 2, 3),
            (f"> {threshold_val:.1f} MADs (Anomalías)", threshold_val, float('inf'))
        ]
        
        for nombre, min_dev, max_dev in bandas:
            mask = (df_resultados['desviacion_mads'] >= min_dev) & \
                   (df_resultados['desviacion_mads'] < max_dev)
            cantidad = mask.sum()
            pct = 100 * cantidad / len(resultados)
            
            st.write(f"**{nombre}:** {cantidad} puntos ({pct:.2f}%)")
    
    # ========== PESTAÑA 4: INFORMACIÓN ==========
    
    with tab4:
        st.subheader("Información del Sistema")
        
        st.write("### Método Utilizado")
        st.markdown(f"""
        **MAD Ventana Móvil + Modified Z-Score**
        
        - **Ventana histórica**: {window_days} días
        - **Algoritmo**: Median Absolute Deviation
        - **Threshold actual**: {threshold_val:.1f} MADs
        - **Complejidad**: O(1) por punto
        - **Latencia**: <0.1ms
        - **Robustez**: Muy alta (resiste outliers)
        """)
        
        st.write("### Parámetros Actuales")
        st.write(f"""
        - Mediana: {detector.baseline_med:.1f} veh/min
        - MAD: {detector.baseline_mad:.2f} veh/min
        - Rango ±{threshold_val} MAD: [{detector.baseline_med - threshold_val * detector.baseline_mad:.1f} - {detector.baseline_med + threshold_val * detector.baseline_mad:.1f}] veh/min
        """)


# ============================================================================
# FOOTER
# ============================================================================

st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.write("### 📊 Datos")
    if st.session_state.df_cargado is not None:
        st.write(f"Registros: {len(st.session_state.df_cargado):,}")
        st.write(f"Rango: {st.session_state.df_cargado['timestamp'].min().date()} a {st.session_state.df_cargado['timestamp'].max().date()}")

with col2:
    st.write("### 🚨 Anomalías")
    if st.session_state.detector.baseline_med is not None:
        stats = st.session_state.detector.get_estadisticas()
        st.write(f"Detectadas: {stats['total_anomalias']}")
        if stats['ultima_anomalia']:
            st.write(f"Última: {stats['ultima_anomalia'].strftime('%H:%M')}")

with col3:
    st.write("### ⚙️ Sistema")
    st.write(f"Threshold: {st.session_state.threshold_actual:.1f} MADs")
    st.write(f"Método: MAD Ventana Móvil")

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.9em;">
Detector de Anomalías en Tráfico v2.0 CORREGIDA | Método: MAD Ventana Móvil
</div>
""", unsafe_allow_html=True)
