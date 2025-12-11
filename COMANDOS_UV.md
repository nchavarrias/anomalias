# ⚡ Comandos UV - Referencia Rápida

## 🚀 Inicio Rápido (Una línea por paso)

```bash
# 1. Instalar UV (si no lo tienes)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Crear venv
uv venv

# 3. Activar venv
source .venv/bin/activate          # macOS/Linux
.venv\Scripts\activate              # Windows

# 4. Instalar dependencias
uv sync

# 5. Ejecutar app
uv run streamlit run app_streamlit.py
```

---

## 📦 Comandos de Instalación

```bash
# Instalar todas las dependencias
uv sync

# Instalar + crear lock file
uv sync --frozen

# Instalar paquete nuevo
uv add streamlit

# Instalar múltiples paquetes
uv add pandas numpy scipy

# Instalar versión específica
uv add streamlit==1.28.0

# Instalar rango de versiones
uv add "streamlit>=1.28,<2.0"

# Instalar desde archivo
uv pip install -r requirements.txt

# Instalar en modo desarrollo
uv add -e .
```

---

## 🔄 Actualizar Dependencias

```bash
# Actualizar un paquete específico
uv add streamlit --upgrade

# Actualizar todos los paquetes
uv add --upgrade

# Actualizar lock file sin instalar
uv lock --upgrade

# Actualizar versión mínima de Python
uv sync --python 3.11
```

---

## 🗑️ Remover Paquetes

```bash
# Remover paquete
uv remove streamlit

# Remover múltiples paquetes
uv remove pandas numpy scipy
```

---

## 📋 Ver Información

```bash
# Listar paquetes instalados
uv pip list

# Mostrar versión
uv --version

# Ver árbol de dependencias
uv pip freeze

# Información de un paquete
uv pip show streamlit

# Ver compatibilidad de Python
uv python list
```

---

## 🏃 Ejecutar Comandos

```bash
# Ejecutar script Python
uv run python script.py

# Ejecutar Streamlit (forma corta)
uv run streamlit run app_streamlit.py

# Ejecutar comando pip
uv run python -m pip list

# Ejecutar en python shell
uv run python

# Ejecutar con argumentos
uv run python script.py --arg1 value1
```

---

## 🔧 Entorno Virtual

```bash
# Crear venv
uv venv

# Crear venv con Python específico
uv venv --python 3.11

# Crear venv con nombre personalizado
uv venv mi-venv

# Activar venv (macOS/Linux)
source .venv/bin/activate

# Activar venv (Windows)
.venv\Scripts\activate

# Desactivar venv
deactivate

# Eliminar venv
rm -rf .venv                    # macOS/Linux
rmdir /s .venv                  # Windows
```

---

## 🔐 Lock File

```bash
# Crear/actualizar lock file
uv lock

# Actualizar lock file con últimas versiones
uv lock --upgrade

# Lock file sin instalar
uv lock --frozen
```

---

## 📦 Gestión de Proyectos

```bash
# Inicializar proyecto nuevo
uv init

# Inicializar con nombre específico
uv init mi-proyecto

# Sincronizar estado del proyecto
uv sync

# Compilar/construir proyecto
uv build

# Ver información del proyecto
uv tree
```

---

## 🎯 Comandos Avanzados

```bash
# Mostrar cache
uv cache show

# Limpiar cache
uv cache clean

# Reinstalar todo (limpio)
uv cache clean && uv sync

# Compilar dependencias
uv pip compile

# Mostrar cambios que haría
uv sync --dry-run
```

---

## 🐛 Troubleshooting

```bash
# Verificar instalación
uv --version

# Verificar entorno
uv python list

# Diagnosticar problemas
uv --help

# Verbose output (más detalles)
uv sync --verbose

# Very verbose
uv sync -vv
```

---

## ⚡ Atajos Útiles

```bash
# Instalación rápida (una línea)
uv venv && source .venv/bin/activate && uv sync

# Ejecutar sin entorno activo
uv run streamlit run app_streamlit.py

# Crear + instalar + ejecutar (desarrollo rápido)
uv venv && source .venv/bin/activate && uv sync && uv run streamlit run app.py
```

---

## 📊 Comparativa UV vs PIP

### Con UV (Recomendado)
```bash
uv venv
source .venv/bin/activate
uv sync
uv run streamlit run app.py
```

### Con PIP (Antiguo)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

**UV es 10-100x más rápido** ⚡

---

## 🎓 Casos de Uso Comunes

### Caso 1: Instalar dependencias por primera vez
```bash
uv venv
source .venv/bin/activate
uv sync
```

### Caso 2: Agregar nueva dependencia
```bash
uv add matplotlib
```

### Caso 3: Ejecutar sin activar venv
```bash
uv run streamlit run app.py
```

### Caso 4: Actualizar todas las dependencias
```bash
uv lock --upgrade
uv sync
```

### Caso 5: Crear entorno limpio
```bash
rm -rf .venv uv.lock
uv venv
uv sync
```

### Caso 6: Instalar versión específica
```bash
uv add streamlit==1.28.0
```

### Caso 7: Ver qué cambiaría
```bash
uv sync --dry-run
```

### Caso 8: Limpiar todo y empezar
```bash
uv cache clean
uv sync --force-reinstall
```

---

## 🚀 TL;DR (El Resumen)

| Necesitas | Comando |
|-----------|---------|
| **Crear proyecto** | `uv init` |
| **Crear venv** | `uv venv` |
| **Activar venv** | `source .venv/bin/activate` |
| **Instalar deps** | `uv sync` |
| **Agregar paquete** | `uv add streamlit` |
| **Ejecutar app** | `uv run streamlit run app.py` |
| **Actualizar todo** | `uv lock --upgrade && uv sync` |
| **Ver instalado** | `uv pip list` |
| **Remover pkg** | `uv remove streamlit` |
| **Limpiar** | `uv cache clean` |

---

**¡Eso es todo! Ahora eres experto en UV** 🚀
