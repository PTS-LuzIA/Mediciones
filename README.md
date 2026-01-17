# 📐 MVP Mediciones - Extractor de Presupuestos de Construcción

Sistema completo para extraer, procesar y exportar mediciones desde PDFs de presupuestos de obra.

## 🚀 Características

- ✅ **Extracción inteligente** de PDFs con estructura jerárquica (Capítulos → Subcapítulos → Apartados → Partidas)
- ✅ **Base de datos SQLite** para almacenamiento persistente
- ✅ **Exportación múltiple**: CSV, Excel, XML y BC3/FIEBDC-3
- ✅ **API REST** con FastAPI para integración
- ✅ **Validación automática** de importes y cantidades
- ✅ **100% local** sin dependencias cloud

## 📁 Estructura del Proyecto

```
Mediciones/
├── src/
│   ├── parser/
│   │   ├── pdf_extractor.py      # Extracción de texto desde PDF
│   │   ├── line_classifier.py    # Clasificación de líneas
│   │   └── partida_parser.py     # Parser principal
│   ├── models/
│   │   └── db_models.py          # Modelos SQLAlchemy
│   ├── exporters/
│   │   ├── csv_exporter.py
│   │   ├── excel_exporter.py
│   │   ├── xml_exporter.py
│   │   └── bc3_exporter.py       # Formato FIEBDC-3
│   ├── utils/
│   │   └── normalizer.py         # Normalización de datos
│   └── api/
│       └── main.py               # API FastAPI
├── data/
│   ├── uploads/                  # PDFs subidos
│   ├── exports/                  # Archivos exportados
│   └── mediciones.db            # Base de datos SQLite
├── ejemplo/
│   └── PROYECTO CALYPOFADO_extract.pdf
├── logs/
│   └── api.log
├── start.sh                      # Script de inicio automático
├── requirements.txt
└── README.md
```

## 🔧 Instalación

### Requisitos previos

- Python 3.9+
- macOS (configurado para Mac, adaptable a Linux/Windows)

### Pasos

1. **Clonar/ubicarse en el directorio:**
   ```bash
   cd /Volumes/DATOS_IA/G_Drive_LuzIA/IA/Proyectos/MVP/Mediciones
   ```

2. **Ejecutar script de inicio:**
   ```bash
   ./start.sh
   ```

   El script automáticamente:
   - Crea entorno virtual Python
   - Instala dependencias
   - Verifica puertos (3012 para API, 8080 para LLM Server)
   - Ofrece iniciar LLM Server si no está corriendo
   - Inicia la API

### Instalación manual (alternativa)

```bash
# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Iniciar API
cd src/api
python main.py
```

## 📖 Uso

### 1. Mediante API REST

**Iniciar servidor:**
```bash
./start.sh
```

**Endpoints disponibles:**

- `GET /` - Información general
- `GET /health` - Health check
- `POST /upload` - Subir y procesar PDF
- `GET /proyectos` - Listar proyectos
- `GET /proyectos/{id}` - Obtener proyecto específico
- `GET /exportar/{id}/{formato}` - Exportar (csv/excel/xml/bc3)
- `DELETE /proyectos/{id}` - Eliminar proyecto

**Documentación interactiva:**
```
http://localhost:3012/docs
```

**Ejemplo con curl:**
```bash
# Subir PDF
curl -X POST http://localhost:3012/upload \
  -F "file=@ejemplo/PROYECTO CALYPOFADO_extract.pdf"

# Listar proyectos
curl http://localhost:3012/proyectos

# Exportar a Excel
curl -O http://localhost:3012/exportar/1/excel
```

### 2. Uso directo de módulos Python

**Parser completo:**
```python
from src.parser.partida_parser import PartidaParser

parser = PartidaParser('ejemplo/PROYECTO CALYPOFADO_extract.pdf')
resultado = parser.parsear()

print(f"Partidas extraídas: {resultado['estadisticas']['partidas']}")
```

**Exportar a CSV:**
```python
from src.exporters.csv_exporter import CSVExporter

partidas = parser.obtener_todas_partidas()
CSVExporter.exportar(partidas, 'salida.csv')
```

**Guardar en base de datos:**
```python
from src.models.db_models import DatabaseManager

db = DatabaseManager()
proyecto = db.guardar_estructura(resultado['estructura'])
db.calcular_totales(proyecto.id)
```

## 🧪 Tests

Cada módulo incluye tests integrados:

```bash
# Test extractor PDF
python src/parser/pdf_extractor.py

# Test clasificador
python src/parser/line_classifier.py

# Test normalizador
python src/utils/normalizer.py

# Test parser completo
python src/parser/partida_parser.py

# Test exportadores
python src/exporters/csv_exporter.py
python src/exporters/excel_exporter.py
python src/exporters/xml_exporter.py
python src/exporters/bc3_exporter.py
```

## 📊 Formatos de Exportación

### CSV
Lista plana de todas las partidas con columnas:
```
capitulo,subcapitulo,apartado,codigo,unidad,resumen,descripcion,cantidad,precio,importe
```

### Excel (.xlsx)
Dos hojas:
- **Resumen**: Estructura jerárquica
- **Partidas**: Todas las partidas con filtros

### XML
Estructura jerárquica completa en formato XML estándar.

### BC3/FIEBDC-3
Formato estándar español para presupuestos de construcción, compatible con software de mediciones profesional.

## 🔍 Estructura de Datos Extraída

```json
{
  "estructura": {
    "nombre": "Proyecto",
    "capitulos": [
      {
        "codigo": "C01",
        "nombre": "ACTUACIONES EN CALYPO FADO",
        "subcapitulos": [
          {
            "codigo": "C08.01",
            "nombre": "CALLE TENERIFE",
            "partidas": [
              {
                "codigo": "DEM06",
                "unidad": "m",
                "resumen": "CORTE PAVIMENTO EXISTENTE",
                "descripcion": "Corte de pavimento de aglomerado...",
                "cantidad": 630.0,
                "precio": 1.12,
                "importe": 705.60
              }
            ]
          }
        ]
      }
    ]
  },
  "estadisticas": {
    "lineas_totales": 1543,
    "capitulos": 2,
    "subcapitulos": 8,
    "apartados": 2,
    "partidas": 187,
    "partidas_validas": 185,
    "errores": []
  }
}
```

## 🛠️ Configuración LLM Server (Opcional)

El sistema puede integrarse con un LLM local para mejoras futuras.

**Ubicación esperada del LLM Server:**
```
/Volumes/DATOS_IA/G_Drive_LuzIA/IA/Proyectos/LLM-Server
```

**Puertos utilizados:**
- **8080**: LiteLLM Gateway (API unificada)
- **8081**: Llama Server (Qwen 2.5 7B - 128K context)
- **8082**: BGE-M3 (Embeddings)
- **11434**: Ollama (Vision models)

**Iniciar LLM Server:**
```bash
cd /Volumes/DATOS_IA/G_Drive_LuzIA/IA/Proyectos/LLM-Server
./start-native.sh
```

El script `start.sh` de Mediciones detecta automáticamente si el LLM Server está corriendo en el puerto 8080 y ofrece iniciarlo. Si no está disponible, el MVP funciona normalmente sin funciones de LLM.

## 📝 Logs

Los logs se guardan en:
```
logs/api.log
```

## 🐛 Troubleshooting

### Puerto 3012 ocupado
```bash
# Verificar qué proceso usa el puerto
lsof -i :3012

# Matar proceso
kill -9 $(lsof -t -i:3012)
```

### Errores de PDF
- Verificar que el PDF no esté cifrado
- Asegurar que el PDF contiene texto extraíble (no imágenes escaneadas)

### Errores de importes
El sistema valida que `cantidad × precio ≈ importe`. Los errores se reportan en `estadisticas.errores`.

## 🚧 Mejoras Futuras

- [ ] Integración con LLM local para OCR y corrección
- [ ] Interfaz web con React
- [ ] Reconocimiento de PDFs escaneados (OCR)
- [ ] Importación desde BC3
- [ ] Detección automática de totales
- [ ] Exportación a formato Presto

## 📄 Licencia

MIT

## 👤 Autor

Desarrollado para el análisis de mediciones de obras de construcción.

---

**Versión:** 1.0.0
**Última actualización:** 2025-01-23
