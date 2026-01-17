# Scripts de Gestión - MVP Mediciones

Scripts para iniciar, detener y verificar el estado del sistema MVP Mediciones.

## Scripts Disponibles

### 🚀 start.sh - Iniciar el Sistema

Inicia todos los servicios del MVP Mediciones:
- API Backend (puerto 3013)
- Aplicación Web (puerto 3012)

```bash
./start.sh
```

**Características:**
- ✅ Verifica automáticamente el LLM Server
- ✅ Configura el entorno virtual Python
- ✅ Detecta servicios ya corriendo y da opciones:
  1. Reiniciar servicios
  2. Mantener servicios existentes
  3. Cancelar
- ✅ Verifica que los servicios inicien correctamente
- ✅ Muestra logs en tiempo real (Ctrl+C para detener)

**Logs:**
- API: `logs/api.log`
- App: `logs/app.log`

---

### 🛑 stop.sh - Detener el Sistema

Detiene todos los servicios corriendo:

```bash
./stop.sh
```

**Características:**
- ✅ Intenta detener servicios gracefully por PID
- ✅ Si falla, fuerza el cierre por puerto
- ✅ Limpia archivos PID
- ✅ Muestra resumen de servicios detenidos

---

### 📊 status.sh - Verificar Estado

Verifica el estado de todos los servicios:

```bash
./status.sh
```

**Muestra:**
- Estado de API Backend (con health check)
- Estado de Aplicación Web (con health check)
- Estado de servicios LLM opcionales:
  - LiteLLM Gateway (puerto 8080)
  - Llama Server / Qwen (puerto 8081)
  - BGE-M3 Embeddings (puerto 8082)
  - Ollama (puerto 11434)

---

## Flujo de Trabajo Típico

### Primera vez / Inicio limpio

```bash
# 1. Iniciar el sistema
./start.sh

# El script:
# - Verifica LLM Server (opcional)
# - Configura entorno virtual
# - Inicia API y App
# - Muestra logs
```

### Verificar estado

```bash
./status.sh
```

### Detener el sistema

```bash
# Opción 1: Ctrl+C si start.sh está mostrando logs

# Opción 2: Desde otra terminal
./stop.sh
```

### Reiniciar servicios

```bash
# Si hay problemas, reinicia completamente
./stop.sh
./start.sh
```

---

## Puertos Utilizados

| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| API Backend | 3013 | API REST con FastAPI |
| Aplicación Web | 3012 | Interfaz web con Jinja2 |
| LiteLLM Gateway | 8080 | Gateway unificado LLM (opcional) |
| Llama Server | 8081 | Qwen 2.5 7B (opcional) |
| BGE-M3 | 8082 | Embeddings (opcional) |
| Ollama | 11434 | Vision models (opcional) |

---

## Endpoints Principales

### API Backend (http://localhost:3013)

- `GET /` - Info de la API
- `GET /health` - Health check
- `POST /upload` - Subir PDF para procesar
- `GET /proyectos` - Listar proyectos
- `GET /proyectos/{id}` - Obtener proyecto
- `GET /exportar/{id}/{formato}` - Exportar proyecto (csv, excel, xml, bc3)
- `DELETE /proyectos/{id}` - Eliminar proyecto
- `GET /docs` - Documentación Swagger

### Aplicación Web (http://localhost:3012)

- `GET /` - Página principal
- `GET /proyectos` - Lista de proyectos
- `GET /proyecto/{id}` - Detalle de proyecto
- `POST /upload` - Subir PDF
- `GET /health` - Health check

---

## Resolución de Problemas

### Puerto ya en uso

```bash
# Ver qué está usando el puerto
lsof -i:3013
lsof -i:3012

# El script start.sh te dará opciones automáticamente
./start.sh
# Opción 1: Reiniciar servicios
# Opción 2: Mantener servicios corriendo
```

### Servicio no inicia

```bash
# Verificar logs
tail -f logs/api.log
tail -f logs/app.log

# Verificar dependencias
source venv/bin/activate
pip install -r requirements.txt
```

### Limpiar todo y empezar de nuevo

```bash
# Detener servicios
./stop.sh

# Limpiar procesos huérfanos
pkill -f "uvicorn src.api.main"
pkill -f "uvicorn src.app.main"

# Limpiar PIDs
rm -f logs/*.pid

# Iniciar de nuevo
./start.sh
```

---

## Estructura de Directorios

```
MVP Mediciones/
├── start.sh          # Iniciar sistema
├── stop.sh           # Detener sistema
├── status.sh         # Verificar estado
├── logs/
│   ├── api.log       # Logs de API
│   ├── app.log       # Logs de App
│   ├── api.pid       # PID de API
│   └── app.pid       # PID de App
├── data/
│   ├── uploads/      # PDFs subidos
│   └── exports/      # Archivos exportados
└── src/
    ├── api/          # Código API
    └── app/          # Código App
```

---

## Notas

- Los scripts requieren Bash (macOS/Linux)
- Se requiere Python 3.8+
- El LLM Server es opcional pero recomendado para funcionalidades avanzadas
- Los logs se rotan automáticamente al reiniciar servicios
- Los PIDs se limpian automáticamente al detener servicios
