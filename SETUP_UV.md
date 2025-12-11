# 🚀 Configurar Proyecto con UV

## ¿Qué es UV?

**UV** es un gestor de paquetes Python extremadamente rápido, escrito en Rust.

- **10-100x más rápido** que pip
- Compatible 100% con pip
- Mejor resolución de dependencias
- Lock file automático
- Menor consumo de RAM

---

## 📦 Instalación de UV

### macOS / Linux
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Windows (PowerShell)
```powershell
powershell -ExecutionPolicy BypassUser -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Con pip (alternativa)
```bash
pip install uv
```

### Verificar instalación
```bash
uv --version
```

Expected output: `uv 0.x.x`

---

## 🎯 Configurar el Proyecto

### Opción 1: Proyecto Nuevo (con uv)

Si estás creando desde cero:

```bash
# Crear proyecto
uv init mi-proyecto
cd mi-proyecto

# Crear venv
uv venv

# Activar venv
source .venv/bin/activate    # macOS/Linux
.venv\Scripts\activate         # Windows

# Agregar dependencias
uv add streamlit pandas numpy plotly scipy
```

---

### Opción 2: Proyecto Existente (migrar de pip)

Si ya tienes un `requirements.txt`:

```bash
# 1. Crear venv
uv venv

# 2. Activar venv
source .venv/bin/activate    # macOS/Linux
.venv\Scripts\activate         # Windows

# 3. Instalar desde requirements.txt
uv pip install -r requirements.txt

# 4. Generar pyproject.toml
uv pip freeze > requirements.txt
```

---

### Opción 3: Crear pyproject.toml (RECOMENDADO)

Crea un archivo `pyproject.toml` en la raíz del proyecto:

```toml
[project]
name = "detector-anomalias"
version = "1.0.0"
description = "Detector de anomalías en tráfico con Streamlit"
requires-python = ">=3.8"
dependencies = [
    "streamlit>=1.28.0",
    "pandas>=2.0.0",
    "numpy>=1.24.0",
    "plotly>=5.17.0",
    "scipy>=1.11.0",
]

[tool.uv]
python-version = "3.11"

[build-system]
requires = ["setuptools", "wheel"]
build-backend = "setuptools.build_meta"
```

Luego:

```bash
# 1. Crear venv
uv venv

# 2. Activar venv
source .venv/bin/activate    # macOS/Linux
.venv\Scripts\activate         # Windows

# 3. Instalar dependencias
uv sync

# 4. Crear lock file
uv lock
```

---

## 📋 Comandos Principales de UV

### Crear y Activar Entorno

```bash
# Crear venv
uv venv

# Activar (macOS/Linux)
source .venv/bin/activate

# Activar (Windows)
.venv\Scripts\activate

# Desactivar
deactivate
```

### Instalar Paquetes

```bash
# Instalar paquete único
uv add streamlit

# Instalar múltiples
uv add pandas numpy scipy

# Instalar versión específica
uv add streamlit==1.28.0

# Instalar desde requirements.txt
uv pip install -r requirements.txt

# Instalar todas las dependencias del proyecto
uv sync
```

### Actualizar Paquetes

```bash
# Actualizar paquete
uv add streamlit --upgrade

# Actualizar todo
uv add --upgrade

# Actualizar lock file
uv lock --upgrade
```

### Remover Paquetes

```bash
# Remover un paquete
uv remove streamlit
```

### Ver Dependencias

```bash
# Listar paquetes instalados
uv pip list

# Ver árbol de dependencias
uv pip freeze
```

### Ejecutar Comandos

```bash
# Ejecutar script Python
uv run python script.py

# Ejecutar Streamlit
uv run streamlit run app_streamlit.py

# Ejecutar comando sin activar venv
uv run python -m pip list
```

---

## 🏗️ Estructura del Proyecto con UV

```
detector-anomalias/
├── pyproject.toml              ← Configuración del proyecto
├── uv.lock                     ← Lock file (auto-generado)
├── .venv/                      ← Entorno virtual
├── app_streamlit.py
├── datos_trafico/
│   ├── trafico_normal.csv
│   ├── trafico_con_incidencias.csv
│   ├── trafico_cambio_gradual.csv
│   ├── trafico_ruido_alto.csv
│   └── trafico_ultimas_24h.csv
├── README.md
└── INICIO_RAPIDO.md
```

---

## ⚡ Flujo Completo: De Cero a Ejecutar

### 1. Crear el Proyecto

```bash
# Crear carpeta
mkdir detector-anomalias
cd detector-anomalias

# Inicializar proyecto
uv init

# Crear venv
uv venv

# Activar venv
source .venv/bin/activate    # macOS/Linux
.venv\Scripts\activate         # Windows
```

### 2. Configurar pyproject.toml

```bash
# Copiar el contenido de la sección anterior
# O crear manualmente con tu editor
```

### 3. Instalar Dependencias

```bash
# Instalar todas
uv sync

# Crear lock file
uv lock
```

### 4. Verificar Instalación

```bash
uv pip list
```

Expected output:
```
streamlit        1.28.x
pandas          2.0.x
numpy           1.24.x
plotly          5.17.x
scipy           1.11.x
```

### 5. Ejecutar la App

```bash
uv run streamlit run app_streamlit.py
```

O activar primero y luego ejecutar normalmente:

```bash
streamlit run app_streamlit.py
```

---

## 🔄 Migrar de pip a UV

Si ya tienes `requirements.txt`:

### Paso 1: Crear pyproject.toml

```bash
# Copiar dependencias a pyproject.toml
# (ver sección anterior)
```

### Paso 2: Crear venv con UV

```bash
uv venv
source .venv/bin/activate    # macOS/Linux
.venv\Scripts\activate         # Windows
```

### Paso 3: Sincronizar

```bash
uv sync
```

### Paso 4: Generar Lock File

```bash
uv lock
```

### Paso 5: Guardar en Git

```bash
git add pyproject.toml uv.lock
git commit -m "Migrado a UV"
```

---

## 📊 UV vs PIP

| Aspecto | UV | PIP |
|---------|-----|-----|
| Velocidad | 10-100x más rápido | Línea base |
| Resolución de deps | Excelente | Bueno |
| Lock file | Automático (uv.lock) | Manual (poetry, pipenv) |
| RAM | Bajo | Normal |
| Python version | Gestiona automáticamente | Manual |
| Reproducibilidad | Muy alta | Media |
| Compatible | Sí, 100% | N/A |

---

## 🎓 Ejemplos Prácticos

### Ejemplo 1: Instalar todas las dependencias

```bash
# Una línea
uv sync

# vs pip (múltiples líneas)
pip install -r requirements.txt
```

### Ejemplo 2: Ejecutar Streamlit

```bash
# Sin activar venv (UV lo hace automáticamente)
uv run streamlit run app_streamlit.py

# vs pip (hay que activar venv primero)
source .venv/bin/activate
streamlit run app_streamlit.py
```

### Ejemplo 3: Agregar nueva dependencia

```bash
# Agregar y actualizar lock file automáticamente
uv add matplotlib

# vs pip (hay que actualizar requirements.txt manualmente)
pip install matplotlib
pip freeze > requirements.txt
```

### Ejemplo 4: Actualizar dependencia específica

```bash
# Actualizar streamlit
uv add streamlit --upgrade

# Actualizar todo el proyecto
uv add --upgrade

# vs pip
pip install --upgrade streamlit
pip freeze > requirements.txt
```

---

## 🚨 Troubleshooting

### Error: "command not found: uv"

**Solución**: Asegúrate de que UV está en el PATH

```bash
# macOS/Linux
echo $PATH | grep -q "\.cargo/bin" || echo "Add ~/.cargo/bin to PATH"

# Windows
# Reinicia la terminal después de instalar
```

### Error: "No virtual environment active"

**Solución**: Activa el venv

```bash
source .venv/bin/activate    # macOS/Linux
.venv\Scripts\activate         # Windows
```

### Error: "uv.lock outdated"

**Solución**: Actualiza el lock file

```bash
uv lock --upgrade
```

### Error: "Python version mismatch"

**Solución**: Especifica la versión en pyproject.toml

```toml
[tool.uv]
python-version = "3.11"  # Cambiar según tu versión
```

---

## 📚 Archivo completo pyproject.toml para el proyecto

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "detector-anomalias"
version = "1.0.0"
description = "Detector de anomalías en tráfico con MAD Ventana Móvil"
readme = "README.md"
requires-python = ">=3.8"
license = {text = "MIT"}
authors = [
    {name = "Tu Nombre", email = "tu.email@example.com"},
]
keywords = [
    "anomaly-detection",
    "traffic",
    "mad",
    "streamlit",
    "data-analysis"
]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]
dependencies = [
    "streamlit>=1.28.0",
    "pandas>=2.0.0",
    "numpy>=1.24.0",
    "plotly>=5.17.0",
    "scipy>=1.11.0",
]

[project.urls]
Homepage = "https://github.com/tuusuario/detector-anomalias"
Repository = "https://github.com/tuusuario/detector-anomalias"
Issues = "https://github.com/tuusuario/detector-anomalias/issues"

[tool.uv]
python-version = "3.11"
python-versions = ">=3.8"

[tool.black]
line-length = 100
target-version = ["py311"]

[tool.isort]
profile = "black"
line_length = 100

[tool.pylint]
max-line-length = 100

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false
```

---

## 🎯 Inicio Rápido con UV (Simplificado)

```bash
# 1. Crear proyecto
mkdir detector-anomalias
cd detector-anomalias

# 2. Crear venv
uv venv

# 3. Activar
source .venv/bin/activate    # macOS/Linux
.venv\Scripts\activate         # Windows

# 4. Instalar dependencias
uv add streamlit pandas numpy plotly scipy

# 5. Ejecutar app
uv run streamlit run app_streamlit.py
```

---

## 📖 Enlaces Útiles

- **Documentación UV**: https://docs.astral.sh/uv/
- **GitHub UV**: https://github.com/astral-sh/uv
- **Comparativa PEP 723**: https://peps.python.org/pep-0723/

---

## ✅ Resumen: UV vs PIP para tu proyecto

| Tarea | UV | PIP |
|------|-----|-----|
| Instalar dependencias | `uv sync` | `pip install -r requirements.txt` |
| Ejecutar app | `uv run streamlit run ...` | Activar venv + streamlit run |
| Agregar paquete | `uv add streamlit` | `pip install streamlit` + freeze |
| Actualizar todo | `uv add --upgrade` | `pip install --upgrade -r requirements.txt` |
| Lock file | Automático | Manual |
| Velocidad | 10-100x más rápido | Línea base |

**Recomendación**: Usa UV para nuevos proyectos o migra proyectos existentes. Es el futuro de Python packaging.

---

## 🚀 Una Línea Final

```bash
# Con UV (recomendado)
uv venv && source .venv/bin/activate && uv sync && uv run streamlit run app_streamlit.py

# vs Con PIP (antiguo)
python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && streamlit run app_streamlit.py
```

UV es 10-100x más rápido. ¡Usa UV! 🚀
