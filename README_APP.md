# 📐 MVP Mediciones - Aplicación Web Completa

Sistema completo con interfaz web para extraer, procesar y exportar mediciones desde PDFs de presupuestos de obra.

## 🎯 Arquitectura

El sistema está compuesto por dos servicios principales:

```
┌─────────────────────────────────────────────────┐
│  APLICACIÓN WEB (Puerto 3012)                   │
│  - Interfaz de usuario                          │
│  - Subida de PDFs (drag & drop)                 │
│  - Visualización de proyectos                   │
│  - Navegación por estructura jerárquica         │
└─────────────────┬───────────────────────────────┘
                  │
                  │ HTTP Requests
                  ↓
┌─────────────────────────────────────────────────┐
│  API BACKEND (Puerto 3013)                      │
│  - Procesamiento de PDFs                        │
│  - Base de datos SQLite                         │
│  - Exportación (CSV, Excel, XML, BC3)           │
│  - Documentación Swagger                        │
└─────────────────────────────────────────────────┘
```

## 🚀 Inicio Rápido

### 1. Iniciar el sistema

```bash
./start.sh
```

El script automáticamente:
- ✅ Verifica LLM Server (puerto 8080) y ofrece iniciarlo
- ✅ Crea entorno virtual Python
- ✅ Instala dependencias
- ✅ Verifica puertos (3012 y 3013)
- ✅ Inicia API Backend (3013)
- ✅ Inicia Aplicación Web (3012)
- ✅ Muestra resumen y logs en tiempo real

### 2. Acceder a la aplicación

Abre tu navegador en:

**🌐 Aplicación Web**
```
http://localhost:3012
```

**📚 API Documentación (Swagger)**
```
http://localhost:3013/docs
```

### 3. Detener el sistema

```bash
./stop.sh
```

O presiona `Ctrl+C` en la terminal donde está corriendo.

## 📱 Uso de la Aplicación Web

### Subir un PDF

1. Accede a http://localhost:3012
2. Arrastra un PDF de presupuesto o haz click para seleccionar
3. Click en "Procesar PDF"
4. Espera mientras se procesa (unos segundos)
5. Serás redirigido al proyecto creado

### Ver Proyectos

1. Click en "📋 Proyectos" en el menú
2. Ver lista de todos los proyectos procesados
3. Click en "Ver Detalle" para ver estructura completa

### Exportar Datos

En la página de detalle de un proyecto:
- **📄 Exportar CSV**: Lista plana de partidas
- **📊 Exportar Excel**: Estructura con dos hojas (Resumen + Partidas)
- **📋 Exportar XML**: Estructura jerárquica completa
- **🏗️ Exportar BC3**: Formato FIEBDC-3 estándar español

## 🔧 Estructura del Proyecto

```
Mediciones/
├── src/
│   ├── app/                      # 🌐 Aplicación Web (Puerto 3012)
│   │   ├── main.py              # FastAPI app frontend
│   │   └── templates/
│   │       ├── base.html        # Plantilla base
│   │       ├── index.html       # Página principal (subir PDF)
│   │       ├── proyectos.html   # Lista de proyectos
│   │       └── proyecto_detalle.html  # Detalle de proyecto
│   │
│   ├── api/                      # 🔌 API Backend (Puerto 3013)
│   │   └── main.py              # FastAPI REST API
│   │
│   ├── parser/
│   │   ├── pdf_extractor.py     # Extracción de texto desde PDF
│   │   ├── line_classifier.py   # Clasificación de líneas
│   │   └── partida_parser.py    # Parser principal
│   │
│   ├── models/
│   │   └── db_models.py         # Modelos SQLAlchemy
│   │
│   ├── exporters/
│   │   ├── csv_exporter.py
│   │   ├── excel_exporter.py
│   │   ├── xml_exporter.py
│   │   └── bc3_exporter.py      # Formato FIEBDC-3
│   │
│   └── utils/
│       └── normalizer.py        # Normalización de datos
│
├── data/
│   ├── uploads/                 # PDFs subidos
│   ├── exports/                 # Archivos exportados
│   └── mediciones.db           # Base de datos SQLite
│
├── logs/
│   ├── api.log                  # Logs de API
│   └── app.log                  # Logs de App
│
├── start.sh                     # 🚀 Script de inicio
├── stop.sh                      # 🛑 Script de parada
└── requirements.txt
```

## 🌐 Endpoints de la API

### API Backend (Puerto 3013)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/` | Información de la API |
| GET | `/health` | Health check |
| POST | `/upload` | Subir y procesar PDF |
| GET | `/proyectos` | Listar todos los proyectos |
| GET | `/proyectos/{id}` | Obtener proyecto específico |
| GET | `/exportar/{id}/{formato}` | Exportar (csv/excel/xml/bc3) |
| DELETE | `/proyectos/{id}` | Eliminar proyecto |

### Aplicación Web (Puerto 3012)

| Ruta | Descripción |
|------|-------------|
| `/` | Página principal - Subir PDF |
| `/proyectos` | Lista de proyectos procesados |
| `/proyecto/{id}` | Detalle de proyecto |
| `/health` | Health check |

## 📊 Formatos de Exportación

### CSV
Lista plana con todas las partidas:
```csv
capitulo,subcapitulo,apartado,codigo,unidad,resumen,descripcion,cantidad,precio,importe
```

### Excel (.xlsx)
Dos hojas:
- **Resumen**: Estructura jerárquica con totales
- **Partidas**: Todas las partidas con filtros automáticos

### XML
Estructura jerárquica completa en formato XML estándar

### BC3/FIEBDC-3
Formato estándar español para presupuestos, compatible con software profesional de mediciones

## 🔍 Características de la Interfaz

### Página Principal
- ✅ Drag & drop de archivos PDF
- ✅ Indicador de archivo seleccionado (nombre y tamaño)
- ✅ Procesamiento con loading spinner
- ✅ Redirección automática al proyecto creado

### Lista de Proyectos
- ✅ Tabla con todos los proyectos
- ✅ Información: ID, nombre, capítulos, partidas, fecha
- ✅ Estadísticas generales (totales)
- ✅ Búsqueda y filtrado

### Detalle de Proyecto
- ✅ Estadísticas del proyecto
- ✅ Botones de exportación en todos los formatos
- ✅ Estructura jerárquica navegable
- ✅ Visualización de partidas por capítulo/subcapítulo
- ✅ Información de archivo origen

## 🎨 Diseño

- **Framework CSS**: Diseño custom con gradientes modernos
- **Colores**: Gradiente púrpura (#667eea → #764ba2)
- **Responsive**: Adaptable a diferentes tamaños de pantalla
- **Iconos**: Emojis nativos para mejor compatibilidad
- **UX**: Drag & drop, loading states, feedback visual

## 🛠️ Variables de Entorno

Crear archivo `.env` basado en `.env.example`:

```bash
# Puerto de la API Backend
API_PORT=3013

# Puerto de la App Web
APP_PORT=3012

# Puertos del LLM Server
LLM_GATEWAY_PORT=8080
LLM_GATEWAY_URL=http://localhost:8080

# Base de datos
DATABASE_PATH=data/mediciones.db

# Directorios
UPLOAD_DIR=data/uploads
EXPORT_DIR=data/exports
LOG_DIR=logs
```

## 🐛 Troubleshooting

### Puerto ocupado

```bash
# Ver qué proceso usa el puerto
lsof -i :3012
lsof -i :3013

# Matar proceso
./stop.sh
```

### Error al subir PDF

- Verificar que el PDF no esté cifrado
- Asegurar que el PDF contiene texto extraíble (no imágenes escaneadas)
- Revisar logs: `tail -f logs/api.log`

### App no carga

- Verificar que la API esté corriendo: http://localhost:3013/health
- Revisar logs: `tail -f logs/app.log`

### Dependencias

```bash
# Reinstalar dependencias
source venv/bin/activate
pip install --upgrade -r requirements.txt
```

## 📝 Logs

Los logs se guardan en tiempo real:

```bash
# Ver logs de la API
tail -f logs/api.log

# Ver logs de la App
tail -f logs/app.log

# Ver ambos
tail -f logs/*.log
```

## 🔐 Seguridad

- ✅ Validación de tipo de archivo (solo PDF)
- ✅ Sin ejecución de código del PDF
- ✅ CORS configurado para localhost
- ✅ Timeouts en uploads (5 minutos)
- ✅ Sanitización de nombres de archivo

## 🚧 Mejoras Futuras

- [ ] Autenticación de usuarios
- [ ] Comparación de presupuestos
- [ ] Búsqueda de partidas
- [ ] Edición de partidas
- [ ] Importación desde BC3
- [ ] OCR para PDFs escaneados
- [ ] Cálculo automático de totales
- [ ] Exportación a Presto

## 📄 Licencia

MIT

## 👤 Autor

Desarrollado para el análisis de mediciones de obras de construcción.

---

**Versión:** 2.0.0 (Con interfaz web completa)
**Última actualización:** 2025-01-23
