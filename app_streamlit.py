import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import warnings

from sklearn.ensemble import IsolationForest  # Isolation Forest

# ----------------------------------------------------------------------------
# Random Cut Forest (rrcf) con fallback a rrcf2, adaptadores y diagnóstico
# ----------------------------------------------------------------------------
import importlib, sys

RRCF_AVAILABLE = False
RRCF_IMPORT_ERROR = None
RRCF_BACKEND = None  # 'rrcf' | 'rrcf2' | None

try:
    rrcf = importlib.import_module("rrcf")
    RRCF_AVAILABLE = True
    RRCF_BACKEND = "rrcf"
except Exception as e1:
    try:
        rrcf = importlib.import_module("rrcf2")
        RRCF_AVAILABLE = True
        RRCF_BACKEND = "rrcf2"
    except Exception as e2:
        RRCF_IMPORT_ERROR = (
            f"rrcf error: {repr(e1)}\n"
            f"rrcf2 error: {repr(e2)}\n"
            f"Python: {sys.version}\nExec: {sys.executable}\n"
            "Instala en el mismo entorno: 'uv add rrcf' o 'uv add rrcf2'"
        )

# Adaptadores mínimos para diferencias de backend
def _rrcf_shingle(values, size: int):
    # Si el backend expone shingle, úsalo; si no, genera shingling localmente.
    if RRCF_AVAILABLE and hasattr(rrcf, "shingle"):
        try:
            return rrcf.shingle(values, size=size)
        except Exception:
            pass
    arr = np.asarray(values, dtype=float)
    if len(arr) < size:
        return []
    return [arr[i : i + size] for i in range(len(arr) - size + 1)]

def _rrcf_rctree_ctor():
    # Devuelve el constructor de RCTree o lanza un error amigable.
    if not RRCF_AVAILABLE:
        raise RuntimeError("Backend RRCF no disponible.")
    RCTree = getattr(rrcf, "RCTree", None)
    if RCTree is None:
        RCTree = getattr(getattr(rrcf, "rcforest", object), "RCTree", None)
    if RCTree is None:
        raise RuntimeError("No se encontró RCTree en el backend RRCF seleccionado.")
    return RCTree

# ============================================================================
# CONFIGURACIÓN STREAMLIT
# ============================================================================

st.set_page_config(
    page_title="Detector de Anomalías - Tráfico",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Silenciar el warning de pkg_resources (de rrcf) sin ocultar otros avisos
warnings.filterwarnings(
    "ignore",
    message="pkg_resources is deprecated as an API",
    category=UserWarning,
    module="rrcf",
)

# CSS CORREGIDO (sin entidades HTML)
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
# MAD ESTACIONAL (minuto del día + día de la semana)
# ============================================================================

class TrafficAnomalyDetectorMAD:
    """
    MAD estacional para tráfico urbano (minuto del día + día de la semana).

    - Construye baseline por (dow, minute) en la ventana retrospectiva:
        * mediana_dow_min
        * MAD_dow_min = mediana(|x - mediana_dow_min|)
    - Si un bucket tiene datos insuficientes, usa fallback por minuto_del_día (sin dow).
    - Aplica un suelo (mad_floor) para evitar MAD=0.
    - Score_t = |x_t - mediana_bucket| / MAD_bucket

    Notas:
    - dow: 0=Lunes ... 6=Domingo
    - minute: 0..1439
    """

    def __init__(self, window_days=42, threshold=3.5, mad_floor=0.5, min_obs_per_bucket=14):
        self.window_days = int(window_days)
        self.window_minutos = self.window_days * 1440
        self.threshold = float(threshold)

        # Robustez
        self.mad_floor = float(mad_floor)
        self.min_obs_per_bucket = int(min_obs_per_bucket)

        # Tablas estacionales
        self.med_table = None   # shape (7, 1440)
        self.mad_table = None   # shape (7, 1440)
        self.count_table = None # shape (7, 1440)

        # Baselines globales (medianas de tablas)
        self.baseline_med_global = None
        self.baseline_mad_global = None

        self.baseline_ts = None

        # Historial
        self.anomalias_detectadas = []
        self.score_history = []

    @staticmethod
    def _minute_of_day(ts: pd.Timestamp) -> int:
        return ts.hour * 60 + ts.minute

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

    def _compute_minute_baseline(self, df_win: pd.DataFrame):
        """
        Fallback por minuto_del_día (sin distinguir dow).
        Devuelve arrays (med_arr, mad_arr, cnt_arr) de tamaño 1440.
        """
        dfm = df_win.copy()
        dfm["minute"] = dfm["timestamp"].dt.hour * 60 + dfm["timestamp"].dt.minute

        grp = dfm.groupby("minute")["intensity"]
        med_minute = grp.median()

        tmp = dfm[["minute", "intensity"]].merge(
            med_minute.rename("med_m"), left_on="minute", right_index=True
        )
        tmp["abs_dev"] = (tmp["intensity"] - tmp["med_m"]).abs()
        mad_minute = tmp.groupby("minute")["abs_dev"].median()

        count_minute = grp.count()

        med_arr = np.full(1440, np.nan)
        mad_arr = np.full(1440, np.nan)
        cnt_arr = np.zeros(1440, dtype=int)
        for m, v in med_minute.items():
            med_arr[m] = float(v)
        for m, v in mad_minute.items():
            mad_arr[m] = float(v)
        for m, v in count_minute.items():
            cnt_arr[m] = int(v)

        mad_arr = np.where(np.isnan(mad_arr), np.nan, np.maximum(mad_arr, self.mad_floor))
        return med_arr, mad_arr, cnt_arr

    def _compute_dow_minute_baseline(self, df_win: pd.DataFrame, minute_fallback):
        """
        Baseline principal por (dow, minute), con fallback por minuto cuando haga falta.
        """
        med_minute, mad_minute, cnt_minute = minute_fallback

        dfw = df_win.copy()
        dfw["dow"] = dfw["timestamp"].dt.weekday  # 0..6
        dfw["minute"] = dfw["timestamp"].dt.hour * 60 + dfw["timestamp"].dt.minute

        grp = dfw.groupby(["dow", "minute"])["intensity"]
        med = grp.median()

        tmp = dfw[["dow", "minute", "intensity"]].merge(
            med.rename("med_dm"), left_on=["dow", "minute"], right_index=True
        )
        tmp["abs_dev"] = (tmp["intensity"] - tmp["med_dm"]).abs()
        mad = tmp.groupby(["dow", "minute"])["abs_dev"].median()
        counts = grp.count()

        med_table = np.full((7, 1440), np.nan, dtype=float)
        mad_table = np.full((7, 1440), np.nan, dtype=float)
        cnt_table = np.zeros((7, 1440), dtype=int)

        for (d, m), v in med.items():
            med_table[d, m] = float(v)
        for (d, m), v in mad.items():
            mad_table[d, m] = float(v)
        for (d, m), v in counts.items():
            cnt_table[d, m] = int(v)

        for d in range(7):
            for m in range(1440):
                if cnt_table[d, m] < self.min_obs_per_bucket or np.isnan(med_table[d, m]):
                    med_table[d, m] = med_minute[m]
                    mad_table[d, m] = mad_minute[m]
                else:
                    v = mad_table[d, m]
                    if np.isnan(v) or v <= 0:
                        mad_table[d, m] = np.nan if np.isnan(mad_minute[m]) else max(mad_minute[m], self.mad_floor)
                    else:
                        mad_table[d, m] = max(v, self.mad_floor)

        return med_table, mad_table, cnt_table

    def cargar_historico(self, df: pd.DataFrame):
        """
        Construye tablas estacionales (dow, minuto) sobre la ventana.
        """
        df_win = self._filtrar_ventana(df)
        if df_win.empty:
            self.med_table = None
            self.mad_table = None
            self.count_table = None
            self.baseline_ts = None
            self.baseline_med_global = None
            self.baseline_mad_global = None
            return {"puntos": 0, "buckets_validos_pct": 0.0, "mad_mediano_global": np.nan}

        minute_fallback = self._compute_minute_baseline(df_win)
        med_table, mad_table, cnt_table = self._compute_dow_minute_baseline(df_win, minute_fallback)

        self.med_table = med_table
        self.mad_table = mad_table
        self.count_table = cnt_table

        self.baseline_med_global = float(np.nanmedian(self.med_table))
        self.baseline_mad_global = float(np.nanmedian(self.mad_table))
        self.baseline_ts = pd.to_datetime(df_win["timestamp"]).max()

        valid_mask = (cnt_table >= self.min_obs_per_bucket)
        buckets_validos_pct = 100.0 * valid_mask.sum() / valid_mask.size

        return {
            "puntos": len(df_win),
            "buckets_validos_pct": buckets_validos_pct,
            "mad_mediano_global": self.baseline_mad_global,
        }

    def _score_point(self, ts: pd.Timestamp, x: float):
        if self.med_table is None or self.mad_table is None:
            return None

        dow = ts.weekday()
        minute = self._minute_of_day(ts)
        med = self.med_table[dow, minute]
        mad = self.mad_table[dow, minute]

        if np.isnan(med):
            med = self.baseline_med_global if self.baseline_med_global is not None else 0.0
        if np.isnan(mad) or mad <= 0:
            mad = self.mad_floor

        score = abs((x - med) / mad)
        es_anomalia = score > self.threshold

        return {
            "timestamp": ts,
            "intensity": x,
            "expected": med,
            "score": float(score),
            "es_anomalia": bool(es_anomalia),
            "confianza": float(min(score / self.threshold, 1.0)) if self.threshold > 0 else 0.0,
        }

    def procesar_punto(self, timestamp, intensity, threshold=None):
        if threshold is not None and threshold != self.threshold:
            self.threshold = float(threshold)
        r = self._score_point(pd.to_datetime(timestamp), float(intensity))
        if r is None:
            return None
        self.score_history.append(r)
        if r["es_anomalia"]:
            self.anomalias_detectadas.append(r)
        return r

    def procesar_lote(self, df: pd.DataFrame, threshold=None):
        if threshold is not None and threshold != self.threshold:
            self.threshold = float(threshold)

        resultados = []
        if self.med_table is None or self.mad_table is None:
            return resultados

        df = df.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp").reset_index(drop=True)

        self.anomalias_detectadas = []
        self.score_history = []

        for row in df.itertuples(index=False):
            r = self._score_point(row.timestamp, float(row.intensity))
            if r is not None:
                resultados.append(r)
                self.score_history.append(r)
                if r["es_anomalia"]:
                    self.anomalias_detectadas.append(r)

        return resultados

    def get_estadisticas(self):
        return {
            "total_anomalias": len(self.anomalias_detectadas),
            "baseline_mediana": self.baseline_med_global,
            "baseline_mad": self.baseline_mad_global,
            "buffer_tamaño": len(self.score_history),
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
# CLASE 2: DETECTOR ISOLATION FOREST (sin cambios)
# ============================================================================

class TrafficAnomalyDetectorIForest:
    """
    Detector de anomalías basado en Isolation Forest (sklearn).
    """

    def __init__(self, contamination=0.01, random_state=42):
        self.contamination = contamination
        self.random_state = random_state
        self.modelo = None
        self.fitted = False
        self.anomalias_detectadas = []
        self.score_history = []

    def cargar_historico(self, df: pd.DataFrame):
        df = df.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp").reset_index(drop=True)
        X = df[["intensity"]].values
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
        df = df.sort_values("timestamp").reset_index(drop=True)
        X = df[["intensity"]].values
        y_pred = self.modelo.predict(X)
        scores = self.modelo.score_samples(X)
        resultados = []
        self.anomalias_detectadas = []
        self.score_history = []
        score_min = scores.min()
        score_max = scores.max()
        denom = score_max - score_min if score_max > score_min else 1.0
        scores_norm = (scores - score_min) / denom
        for idx, row in enumerate(df.itertuples(index=False)):
            es_anomalia = y_pred[idx] == -1
            score_norm = 1.0 - scores_norm[idx]
            res = {
                "timestamp": row.timestamp,
                "intensity": row.intensity,
                "expected": np.nan,
                "score": float(score_norm),
                "es_anomalia": bool(es_anomalia),
                "confianza": float(score_norm),
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
# CLASE 3: DETECTOR RANDOM CUT FOREST (optimizado y robusto)
# ============================================================================

class TrafficAnomalyDetectorRCF:
    """
    RCF optimizado (sin inserciones temporales al puntuar).
    Robusto a puntos sin cobertura en árboles (ignora NaNs en normalización).
    """

    def __init__(
        self,
        n_trees=100,
        tree_size=256,
        shingle_size=1,
        contamination=0.01,
        random_state=42,
    ):
        self.n_trees = int(n_trees)
        self.tree_size = int(tree_size)
        self.shingle_size = int(shingle_size)
        self.contamination = float(contamination)
        self.random_state = int(random_state)

        self.forest = []
        self.tree_leaves_indexsets = []
        self.fitted = False

        self.timestamps_ = None
        self.intensities_ = None
        self.scores_norm_ = None
        self.threshold_score_norm_ = None

        self.anomalias_detectadas = []
        self.score_history = []

    def _make_series(self, df: pd.DataFrame):
        df = df.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp").reset_index(drop=True)
        values = df["intensity"].astype(float).values
        ts = df["timestamp"].values
        if self.shingle_size > 1:
            shingled = _rrcf_shingle(values, size=self.shingle_size)
            if len(shingled) == 0:
                return np.empty((0, 1)), ts, values
            X = np.vstack([np.asarray(v, dtype=float) for v in shingled])
            ts_adj = ts[self.shingle_size - 1 :]
            intens_adj = values[self.shingle_size - 1 :]
            return X, ts_adj, intens_adj
        else:
            X = values.reshape(-1, 1)
            return X, ts, values

    def cargar_historico(self, df: pd.DataFrame):
        if not RRCF_AVAILABLE:
            self.fitted = False
            return {"puntos": len(df), "nota": "rrcf/rrcf2 no disponible"}
        np.random.seed(self.random_state)
        X, ts, intens = self._make_series(df)
        n = len(X)
        if n == 0:
            self.fitted = False
            return {"puntos": 0}

        tree_size = min(self.tree_size, n)
        self.forest = []
        self.tree_leaves_indexsets = []
        RCTree = _rrcf_rctree_ctor()
        for _ in range(self.n_trees):
            idx = np.random.choice(n, size=tree_size, replace=False)
            tree = RCTree()
            for j in idx:
                tree.insert_point(X[j], index=j)
            self.forest.append(tree)
            self.tree_leaves_indexsets.append(set(tree.leaves.keys()))
        self.timestamps_ = ts
        self.intensities_ = intens
        self.fitted = True
        return {"puntos": n}

    def procesar_lote(self, df: pd.DataFrame):
        if not self.fitted or not self.forest:
            return []
        X, ts, intens = self._make_series(df)
        n = len(X)
        if n == 0:
            return []
        scores = np.zeros(n, dtype=float)
        counts = np.zeros(n, dtype=int)

        # Agregar codisp sólo para hojas presentes (cobertura parcial por submuestreo)
        for t_idx, tree in enumerate(self.forest):
            leaves_set = self.tree_leaves_indexsets[t_idx]
            for i in leaves_set:
                if i < n:
                    cod = tree.codisp(i)
                    scores[i] += cod
                    counts[i] += 1

        # Marcar sin cobertura como NaN
        mask = counts > 0
        scores[~mask] = np.nan
        if np.any(mask):
            scores[mask] = scores[mask] / counts[mask]
            smin = float(np.nanmin(scores))
            smax = float(np.nanmax(scores))
            denom = (smax - smin) if smax > smin else 1.0
            scores_norm = (scores - smin) / denom
            perc = 100.0 * (1.0 - self.contamination) if mask.sum() > 1 else 100.0
            thr = float(np.nanpercentile(scores_norm, perc))
        else:
            scores_norm = np.full(n, np.nan, dtype=float)
            thr = 1.0

        self.threshold_score_norm_ = thr
        self.scores_norm_ = scores_norm

        resultados = []
        self.anomalias_detectadas = []
        self.score_history = []
        for i in range(n):
            if np.isnan(scores_norm[i]):
                es_anomalia = False
                conf = 0.0
            else:
                es_anomalia = scores_norm[i] >= thr
                conf = float(scores_norm[i])
            res = {
                "timestamp": pd.to_datetime(ts[i]),
                "intensity": float(intens[i]),
                "expected": np.nan,
                "score": (float(scores_norm[i]) if not np.isnan(scores_norm[i]) else np.nan),
                "es_anomalia": bool(es_anomalia),
                "confianza": conf,
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
            "threshold_score_norm": self.threshold_score_norm_,
            "rcf_cobertura_pct": (
                float(100.0 * np.mean(~np.isnan(self.scores_norm_)))
                if self.scores_norm_ is not None else None
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

# Estados MAD extra
if "mad_floor" not in st.session_state:
    st.session_state.mad_floor = 1.5  # recomendación práctica

if "min_obs_per_bucket" not in st.session_state:
    st.session_state.min_obs_per_bucket = 7  # ~1 ciclo semanal por bucket

# Estados para RCF
if "rcf_n_trees" not in st.session_state:
    st.session_state.rcf_n_trees = 100

if "rcf_tree_size" not in st.session_state:
    st.session_state.rcf_tree_size = 256

if "rcf_shingle" not in st.session_state:
    st.session_state.rcf_shingle = 1

if "contamination_rcf" not in st.session_state:
    st.session_state.contamination_rcf = 0.01

# Post-regla de segmentos (MAD) — parámetros UI
if "seg_min_consec" not in st.session_state:
    st.session_state.seg_min_consec = 5  # minutos consecutivos mínimos
if "seg_tolerancia" not in st.session_state:
    st.session_state.seg_tolerancia = 1  # huecos permitidos dentro del segmento

# ============================================================================
# CABECERA
# ============================================================================

st.title("🚗 Detector de Anomalías en Tráfico")
st.markdown(
    """
Compara tres algoritmos de detección de anomalías:
- **MAD estacional (minuto + día de la semana)**.  
- **Isolation Forest** (modelo basado en árboles de aislamiento).  
- **Random Cut Forest** (bosque de cortes aleatorios con score de codisp).
"""
)

# ============================================================================
# UTILS: POST-REGLA POR SEGMENTOS (para MAD) — versión robusta
# ============================================================================

def _filtrar_por_segmentos(df_res: pd.DataFrame, min_consec=5, tolerancia=1):
    """
    Morfología 1D: (1) cierra huecos pequeños dentro de runs de 1s (<= tolerancia),
    (2) descarta segmentos cuya longitud total < min_consec.
    No expande segmentos más allá de lo debido y no marca como anómalos los gaps no cerrados.
    """
    if df_res.empty:
        return df_res

    df = df_res.copy().sort_values("timestamp").reset_index(drop=True)
    if "es_anomalia" not in df.columns:
        return df

    b = df["es_anomalia"].astype(bool).to_numpy()
    n = len(b)
    if n == 0:
        df["es_anomalia"] = b
        return df

    # 1) Cerrar huecos pequeños si están rodeados por 1s
    i = 0
    while i < n:
        if b[i]:
            j = i
            while j < n and b[j]:
                j += 1
            # gap entre j..k-1
            k = j
            while k < n and not b[k]:
                k += 1
            gap_len = k - j
            if gap_len > 0 and gap_len <= tolerancia and k < n:
                # Rellenar gap
                b[j:k] = True
                i = j
                continue
            i = j
        else:
            i += 1

    # 2) Mantener solo runs de 1s con longitud >= min_consec
    keep = np.zeros(n, dtype=bool)
    i = 0
    while i < n:
        if b[i]:
            j = i
            while j < n and b[j]:
                j += 1
            if (j - i) >= min_consec:
                keep[i:j] = True
            i = j
        else:
            i += 1

    df["es_anomalia"] = keep
    return df

# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    st.header("⚙️ Configuración")

    # Algoritmo
    st.subheader("0️⃣ Algoritmo")
    algoritmos_lista = ["MAD (Ventana deslizante)", "Isolation Forest", "Random Cut Forest"]
    try:
        idx_alg = algoritmos_lista.index(st.session_state.algoritmo)
    except ValueError:
        idx_alg = 0

    algoritmo = st.selectbox(
        "Método de detección:",
        algoritmos_lista,
        index=idx_alg,
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

        # Ejemplos 120 días si los añadiste
        "Accidente (4 eventos, 120 días)",
        "Evento Estadio (3 eventos, 120 días)",
        "Puente/Festivo (120 días)",
        "Desvío Temporal (2 semanas, 120 días)",
        "Corte Nocturno por Obras (120 días)",
        "Sensor Defectuoso (120 días)",
    ]

    dataset_seleccionado = st.selectbox("Dataset:", datasets_disponibles)

    archivo_map = {
        "Tráfico Normal (30 días)": "datos_trafico/trafico_normal.csv",
        "Con Incidencias (3 eventos)": "datos_trafico/trafico_con_incidencias.csv",
        "Cambio Gradual (Obra)": "datos_trafico/trafico_cambio_gradual.csv",
        "Ruido Alto (Sensores malos)": "datos_trafico/trafico_ruido_alto.csv",
        "Últimas 24 horas + Anomalía": "datos_trafico/trafico_ultimas_24h.csv",

        # Rutas a 120 días
        "Accidente (4 eventos, 120 días)": "datos_trafico/trafico_accidente_4eventos_120d.csv",
        "Evento Estadio (3 eventos, 120 días)": "datos_trafico/trafico_evento_estadio_3eventos_120d.csv",
        "Puente/Festivo (120 días)": "datos_trafico/trafico_puente_festivo_120d.csv",
        "Desvío Temporal (2 semanas, 120 días)": "datos_trafico/trafico_desvio_semana_120d.csv",
        "Corte Nocturno por Obras (120 días)": "datos_trafico/trafico_corte_nocturno_120d.csv",
        "Sensor Defectuoso (120 días)": "datos_trafico/trafico_sensor_defectuoso_120d.csv",
    }

    # Cache de carga por ruta (no aplica a file_uploader)
    @st.cache_data(show_spinner=False)
    def _load_csv_path(path: str) -> pd.DataFrame:
        df_ = pd.read_csv(path)
        df_["timestamp"] = pd.to_datetime(df_["timestamp"])
        return df_.sort_values("timestamp").reset_index(drop=True)

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
                df = _load_csv_path(archivo_usar)
            else:
                if archivo_usar is None:
                    st.warning("⚠️ Selecciona un archivo CSV para cargar.")
                    df = None
                else:
                    df = pd.read_csv(archivo_usar)
                    df["timestamp"] = pd.to_datetime(df["timestamp"])
                    df = df.sort_values("timestamp").reset_index(drop=True)

            if df is not None:
                st.session_state.df_cargado = df

                # Crear detector según algoritmo
                if algoritmo.startswith("MAD"):
                    st.session_state.detector = TrafficAnomalyDetectorMAD(
                        window_days=st.session_state.window_days,
                        threshold=st.session_state.threshold_actual,
                        mad_floor=st.session_state.mad_floor,
                        min_obs_per_bucket=st.session_state.min_obs_per_bucket,
                    )
                    with st.spinner("Entrenando MAD estacional (dow+minuto)…"):
                        stats_base = st.session_state.detector.cargar_historico(df)
                    with st.spinner("Calculando scores (MAD)…"):
                        resultados = st.session_state.detector.procesar_lote(
                            df, threshold=st.session_state.threshold_actual
                        )
                    df_res = pd.DataFrame(resultados)
                    if not df_res.empty:
                        df_res["timestamp"] = pd.to_datetime(df_res["timestamp"])
                        df_res = _filtrar_por_segmentos(
                            df_res,
                            min_consec=st.session_state.seg_min_consec,
                            tolerancia=st.session_state.seg_tolerancia
                        )
                        # Guardar back en los estados del detector
                        st.session_state.detector.anomalias_detectadas = [
                            r for r in df_res.to_dict(orient="records") if r["es_anomalia"]
                        ]
                        st.session_state.detector.score_history = df_res.to_dict(orient="records")
                        st.session_state.resultados = df_res.to_dict(orient="records")
                    else:
                        st.session_state.resultados = resultados

                    st.success(
                        "MAD estacional (dow+minuto) entrenado con "
                        f"{stats_base['puntos']} puntos — buckets válidos ≈ {stats_base['buckets_validos_pct']:.1f}% — "
                        f"MAD mediano global ≈ {stats_base['mad_mediano_global']:.2f}"
                    )

                elif algoritmo.startswith("Isolation"):
                    st.session_state.detector = TrafficAnomalyDetectorIForest(
                        contamination=st.session_state.contamination_iforest
                    )
                    with st.spinner("Entrenando Isolation Forest..."):
                        stats_base = st.session_state.detector.cargar_historico(df)
                    with st.spinner("Calculando scores (IForest)..."):
                        st.session_state.resultados = st.session_state.detector.procesar_lote(df)
                    st.success(
                        f"Isolation Forest entrenado con {stats_base['puntos']} puntos, "
                        f"contamination={st.session_state.contamination_iforest:.3f}"
                    )
                else:
                    # Random Cut Forest
                    if not RRCF_AVAILABLE:
                        st.session_state.detector = None
                        st.session_state.resultados = []
                        st.error("❌ RCF no está disponible. Instala 'rrcf' o 'rrcf2'.")
                        with st.expander("Detalles del error de importación"):
                            st.code(RRCF_IMPORT_ERROR or "Sin detalles", language="text")
                    else:
                        st.session_state.detector = TrafficAnomalyDetectorRCF(
                            n_trees=st.session_state.rcf_n_trees,
                            tree_size=st.session_state.rcf_tree_size,
                            shingle_size=st.session_state.rcf_shingle,
                            contamination=st.session_state.contamination_rcf,
                        )
                        with st.spinner(f"Entrenando Random Cut Forest (backend: {RRCF_BACKEND})..."):
                            stats_base = st.session_state.detector.cargar_historico(df)
                        with st.spinner("Calculando scores (RCF)..."):
                            st.session_state.resultados = st.session_state.detector.procesar_lote(df)
                        st.success(
                            f"Random Cut Forest entrenado con {stats_base['puntos']} puntos, "
                            f"árboles={st.session_state.rcf_n_trees}, tamaño árbol={st.session_state.rcf_tree_size}, "
                            f"shingle={st.session_state.rcf_shingle}, contamination={st.session_state.contamination_rcf:.3f}"
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
            max_value=120,
            value=st.session_state.window_days,
            step=7,
        )
        st.session_state.window_days = window_days

        threshold = st.slider(
            "Threshold (MADs):",
            min_value=1.5,
            max_value=7.0,
            value=st.session_state.threshold_actual,
            step=0.1,
        )
        st.session_state.threshold_actual = threshold

        # NUEVOS: mad_floor y min_obs_per_bucket
        mad_floor = st.slider(
            "Suelo de MAD (mad_floor):",
            min_value=0.0,
            max_value=5.0,
            value=st.session_state.mad_floor,
            step=0.5,
            help="MAD mínimo por bucket. Sube si ves puntitos sueltos o madrugada nerviosa."
        )
        st.session_state.mad_floor = mad_floor

        min_obs = st.slider(
            "Observaciones mínimas por bucket (dow, minuto):",
            min_value=1,
            max_value=60,
            value=st.session_state.min_obs_per_bucket,
            step=1,
            help="Si un bucket tiene menos observaciones en la ventana, se usa el fallback por minuto del día."
        )
        st.session_state.min_obs_per_bucket = min_obs

        # Post-regla de segmentos (MAD)
        st.markdown("**Post-regla de segmentos**")
        seg_min = st.slider(
            "Mínimo de minutos consecutivos (min_consec):",
            min_value=1, max_value=60,
            value=st.session_state.seg_min_consec, step=1,
            help="Longitud mínima de un segmento para considerarlo anomalía."
        )
        st.session_state.seg_min_consec = seg_min
        seg_tol = st.slider(
            "Huecos permitidos dentro del segmento (tolerancia):",
            min_value=0, max_value=10,
            value=st.session_state.seg_tolerancia, step=1,
            help="Número de minutos no anómalos que se pueden cerrar dentro de un segmento."
        )
        st.session_state.seg_tolerancia = seg_tol

    elif algoritmo.startswith("Isolation"):
        contamination = st.slider(
            "Contamination (proporción esperada de anomalías):",
            min_value=0.001,
            max_value=0.1,
            value=st.session_state.contamination_iforest,
            step=0.001,
        )
        st.session_state.contamination_iforest = contamination

    else:
        # Random Cut Forest
        n_trees = st.slider(
            "Nº de árboles (RCF):",
            min_value=20,
            max_value=300,
            value=st.session_state.rcf_n_trees,
            step=10,
            help="Más árboles = mejor estabilidad del score, pero más lento.",
        )
        st.session_state.rcf_n_trees = n_trees

        tree_size = st.slider(
            "Tamaño del árbol (RCF):",
            min_value=64,
            max_value=1024,
            value=st.session_state.rcf_tree_size,
            step=64,
            help="Número máximo de puntos por árbol (submuestreo por árbol).",
        )
        st.session_state.rcf_tree_size = tree_size

        shingle = st.slider(
            "Shingle size (contexto temporal):",
            min_value=1,
            max_value=10,
            value=st.session_state.rcf_shingle,
            step=1,
            help="Usa ventanas de este tamaño para captar patrones temporales.",
        )
        st.session_state.rcf_shingle = shingle

        contamination_rcf = st.slider(
            "Contamination (proporción esperada de anomalías):",
            min_value=0.001,
            max_value=0.1,
            value=st.session_state.contamination_rcf,
            step=0.001,
        )
        st.session_state.contamination_rcf = contamination_rcf

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
                    mad_floor=st.session_state.mad_floor,
                    min_obs_per_bucket=st.session_state.min_obs_per_bucket,
                )
                with st.spinner("Entrenando MAD estacional (dow+minuto)…"):
                    stats_base = st.session_state.detector.cargar_historico(df)
                with st.spinner("Calculando scores (MAD)…"):
                    resultados = st.session_state.detector.procesar_lote(
                        df, threshold=st.session_state.threshold_actual
                    )

                # POST-REGLA: segmentos con parámetros de la UI
                df_res = pd.DataFrame(resultados)
                if not df_res.empty:
                    df_res["timestamp"] = pd.to_datetime(df_res["timestamp"])
                    df_res = _filtrar_por_segmentos(
                        df_res,
                        min_consec=st.session_state.seg_min_consec,
                        tolerancia=st.session_state.seg_tolerancia
                    )
                    st.session_state.detector.anomalias_detectadas = [
                        r for r in df_res.to_dict(orient="records") if r["es_anomalia"]
                    ]
                    st.session_state.detector.score_history = df_res.to_dict(orient="records")
                    st.session_state.resultados = df_res.to_dict(orient="records")
                else:
                    st.session_state.resultados = resultados

                st.success(
                    "MAD estacional (dow+minuto) recalculado — "
                    f"puntos={stats_base['puntos']}, buckets válidos ≈ {stats_base['buckets_validos_pct']:.1f}%, "
                    f"MAD mediano global ≈ {stats_base['mad_mediano_global']:.2f}"
                )
            elif algoritmo.startswith("Isolation"):
                st.session_state.detector = TrafficAnomalyDetectorIForest(
                    contamination=st.session_state.contamination_iforest
                )
                with st.spinner("Entrenando Isolation Forest..."):
                    stats_base = st.session_state.detector.cargar_historico(df)
                with st.spinner("Calculando scores (IForest)..."):
                    st.session_state.resultados = st.session_state.detector.procesar_lote(df)
                st.success(
                    f"Isolation Forest recalculado (puntos={stats_base['puntos']}, "
                    f"contamination={st.session_state.contamination_iforest:.3f})"
                )
            else:
                if not RRCF_AVAILABLE:
                    st.session_state.detector = None
                    st.session_state.resultados = []
                    st.error("❌ RCF no está disponible. Instala 'rrcf' o 'rrcf2'.")
                    with st.expander("Detalles del error de importación"):
                        st.code(RRCF_IMPORT_ERROR or "Sin detalles", language="text")
                else:
                    st.session_state.detector = TrafficAnomalyDetectorRCF(
                        n_trees=st.session_state.rcf_n_trees,
                        tree_size=st.session_state.rcf_tree_size,
                        shingle_size=st.session_state.rcf_shingle,
                        contamination=st.session_state.contamination_rcf,
                    )
                    with st.spinner(f"Entrenando Random Cut Forest (backend: {RRCF_BACKEND})..."):
                        stats_base = st.session_state.detector.cargar_historico(df)
                    with st.spinner("Calculando scores (RCF)…"):
                        st.session_state.resultados = st.session_state.detector.procesar_lote(df)
                    st.success(
                        f"Random Cut Forest recalculado (puntos={stats_base['puntos']}, "
                        f"árboles={st.session_state.rcf_n_trees}, tamaño árbol={st.session_state.rcf_tree_size}, "
                        f"shingle={st.session_state.rcf_shingle}, contamination={st.session_state.contamination_rcf:.3f})"
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

        if st.session_state.algoritmo.startswith("Random Cut Forest"):
            st.caption(f"RCF backend: {RRCF_BACKEND or 'n/d'}")

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

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["📊 Gráficos", "🔴 Anomalías", "📈 Análisis", "ℹ️ Información", "📘 Guía del algoritmo"]
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

            # Toggle para dibujar baseline esperada en MAD
            if isinstance(detector, TrafficAnomalyDetectorMAD):
                show_expected = st.checkbox(
                    "Mostrar baseline esperada (mediana estacional)", value=False
                )
                if show_expected and "expected" in df_res.columns:
                    fig.add_trace(
                        go.Scatter(
                            x=df_res["timestamp"],
                            y=df_res["expected"],
                            name="Esperado (mediana estacional)",
                            mode="lines",
                            line=dict(color="green", width=1, dash="dot"),
                            opacity=0.6,
                        )
                    )

            fig.update_layout(
                title=f"Intensidad - Algoritmo: {st.session_state.algoritmo}",
                xaxis_title="Tiempo",
                yaxis_title="Intensidad (veh/min)",
                hovermode="x unified",
                height=500,
                template="plotly_white",
            )
            st.plotly_chart(fig, width="stretch")

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
                y_title = "Score (MADs estacionales)"
            elif isinstance(detector, TrafficAnomalyDetectorRCF):
                thr = getattr(detector, "threshold_score_norm_", None)
                if thr is not None:
                    fig2.add_hline(
                        y=thr,
                        line_dash="dash",
                        line_color="red",
                        annotation_text=f"Umbral (1 - contamination) = {thr:.2f}",
                        annotation_position="right",
                    )
                y_title = "Score normalizado (0 normal, 1 muy raro) — RCF"
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
            st.plotly_chart(fig2, width="stretch")

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
                width="content",
                hide_index=True,
            )
            # Exportar anomalías
            csv_anom = df_anom.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Descargar anomalías (CSV)",
                data=csv_anom,
                file_name="anomalies.csv",
                mime="text/csv",
            )
        else:
            st.info("No se han detectado anomalías.")

        # Exportar todos los scores (si existen)
        if not df_res.empty:
            csv_scores = df_res.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Descargar scores completos (CSV)",
                data=csv_scores,
                file_name="scores.csv",
                mime="text/csv",
            )

    # ---------- TAB 3: ANÁLISIS ----------
    with tab3:
        st.subheader("Análisis")

        if isinstance(detector, TrafficAnomalyDetectorMAD):
            stats = detector.get_estadisticas()
            col1, col2 = st.columns(2)
            with col1:
                st.metric(
                    "Mediana baseline (global estacional)",
                    f"{(stats['baseline_mediana'] or np.nan):.1f}"
                )
                st.metric(
                    "MAD mediano (global estacional)",
                    f"{(stats['baseline_mad'] or np.nan):.2f}"
                )
            with col2:
                st.metric("Threshold", f"{st.session_state.threshold_actual:.1f} MADs")
                st.metric("Ventana", f"{st.session_state.window_days} días")

            st.markdown("### Heatmap de tasa de anomalías (dow × minuto)")
            if not df_res.empty:
                df_hm = df_res.copy()
                df_hm["dow"] = df_hm["timestamp"].dt.weekday
                df_hm["minute"] = df_hm["timestamp"].dt.hour*60 + df_hm["timestamp"].dt.minute
                rate = (df_hm.groupby(["dow","minute"])["es_anomalia"]
                              .mean()
                              .unstack(0)  # columnas = dow
                              .fillna(0.0))
                fig_hm = px.imshow(
                    rate.values.T,
                    aspect="auto",
                    origin="lower",
                    labels=dict(x="Minuto del día (0..1439)", y="Día semana (0=L..6=D)", color="Tasa anómala"),
                    x=rate.index, y=list(range(7)),
                    color_continuous_scale="Viridis",
                )
                fig_hm.update_layout(height=300)
                st.plotly_chart(fig_hm, width="stretch")

                with st.expander("¿Qué aporta el heatmap y cómo interpretarlo?"):
                    st.markdown(
                        """
**¿Qué es?**  
Un mapa de calor que muestra, para cada **día de la semana (0=Lunes..6=Domingo)** y cada **minuto del día (0..1439)**, la **proporción de puntos** que el MAD estacional ha marcado como anómalos.

**¿Para qué sirve?**  
- Detecta **patrones sistemáticos** de falsas alarmas (franjas verticales cada mañana/tarde ⇒ threshold o `mad_floor` demasiado bajos).  
- Destaca **zonas localizadas** donde realmente hay eventos (manchas aisladas y no repetitivas).

**Cómo leerlo:**
- **Franjas amplias** y repetidas ⇒ el umbral es aún laxo para ese intervalo. Sube **Threshold** (p. ej., 4.0→4.5) o aumenta **mad_floor** (p. ej., 1.5→2.0).  
- **Manchas pequeñas** y concretas ⇒ eventos **reales** (accidentes, spikes, cortes), buen comportamiento.  
- **Zonas uniformemente azules (≈0%)** ⇒ normalidad estable para ese (dow, minuto).
"""
                    )
            else:
                st.info("No hay resultados para construir el heatmap.")

        elif isinstance(detector, TrafficAnomalyDetectorRCF):
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Árboles", f"{st.session_state.rcf_n_trees}")
                st.metric("Tamaño árbol", f"{st.session_state.rcf_tree_size}")
            with col2:
                st.metric("Shingle size", f"{st.session_state.rcf_shingle}")
                st.metric("Contamination", f"{st.session_state.contamination_rcf:.3f}")
            st.caption(f"RCF backend: {RRCF_BACKEND or 'n/d'}")
            # Cobertura
            stats = detector.get_estadisticas()
            cov = stats.get("rcf_cobertura_pct")
            if cov is not None:
                st.metric("Cobertura de score", f"{cov:.1f}%")
                if cov < 95.0:
                    st.info(
                        "Cobertura < 95%. Considera aumentar 'Nº de árboles' o 'Tamaño del árbol' para que más puntos "
                        "entren en los árboles y tengan score."
                    )
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
**MAD estacional (minuto del día + día de la semana)**

- Calcula una baseline específica para cada minuto del día y tipo de día (L–D) usando una ventana retrospectiva.
- El score compara cada punto contra su homólogo histórico (mismo minuto y día), en MADs.
- Evita que la noche arrastre el baseline de todo el día y reduce falsos positivos en picos normales.
"""
            )
        elif isinstance(detector, TrafficAnomalyDetectorRCF):
            st.markdown(
                """
**Random Cut Forest (RCF)**

- Bosque de cortes aleatorios; score de rareza (*codisp*) normalizado.
- Umbral por percentil usando *contamination*.
- *Shingle* opcional para capturar forma temporal.
"""
            )
        else:
            st.markdown(
                """
**Isolation Forest**

- Aísla puntos “raros” en árboles aleatorios.
- *Contamination* fija la proporción esperada de anomalías.
"""
            )

   # ---------- TAB 5: GUÍA DEL ALGORITMO ----------
with tab5:
    st.subheader("Guía del algoritmo seleccionado")

    if isinstance(detector, TrafficAnomalyDetectorMAD):
        st.markdown("### ¿Qué es MAD estacional?")
        st.markdown(
            "Comparas cada punto con su “normal” del **mismo minuto del día** y "
            "**mismo tipo de día (L–D)**, dentro de una ventana de varias semanas."
        )
        st.markdown("**Score:**")
        st.latex(
            r"\text{score}(t) = \frac{|x_t - \text{mediana}_{\text{dow,min}}|}"
            r"{\max(\text{MAD}_{\text{dow,min}}, \varepsilon)}"
        )
        st.markdown(
            "- \\(\\varepsilon\\) evita divisiones por cero (suelo de MAD).  \n"
            "- Umbral en **MADs** (p. ej., 3.5)."
        )
        st.markdown("### Consejos")
        st.markdown(
            "- **Ventana**: 42–56 días.  \n"
            "- **Threshold**: 3.5–4.5 según sensibilidad.  \n"
            "- **Suelo (mad_floor)**: 1.5–2.0 si hay minutos muy estables.  \n"
            "- **Segmentos**: agrupa anomalías si hay ≥5 minutos consecutivos (limpia puntitos sueltos)."
        )

    elif isinstance(detector, TrafficAnomalyDetectorIForest):
        st.markdown("### Isolation Forest (resumen)")
        st.markdown(
            "Aíslas observaciones con cortes aleatorios. Si un punto se aísla rápido, es raro."
        )
        st.markdown(
            "- Umbral indirecto: `contamination` (proporción esperada de anomalías).  \n"
            "- Ideal con múltiples variables."
        )

    elif isinstance(detector, TrafficAnomalyDetectorRCF):
        st.markdown("### Random Cut Forest (resumen)")
        st.markdown(
            "Mide cuánto “rompe” un punto la estructura del conjunto (score **codisp**)."
        )
        st.markdown(
            "- Umbral por percentil (1 - `contamination`).  \n"
            "- `shingle_size` para forma temporal."
        )

    else:
        # Fallback: por si el detector no matchea ninguna clase (no debería pasar)
        st.info("Selecciona un algoritmo y carga un dataset para ver la guía.")