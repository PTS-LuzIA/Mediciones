# 🔧 Guía de Instalación - MVP Mediciones

## Requisitos del Sistema

- **Sistema Operativo**: macOS 10.15+ (adaptable a Linux/Windows)
- **Python**: 3.9 o superior
- **Espacio en disco**: Mínimo 500 MB
- **RAM**: Mínimo 2 GB

## Instalación Paso a Paso

### 1. Verificar Python

```bash
python3 --version
```

Debe mostrar Python 3.9 o superior.

### 2. Clonar o Ubicarse en el Directorio

```bash
cd /Volumes/DATOS_IA/G_Drive_LuzIA/IA/Proyectos/MVP/Mediciones
```

### 3. Dar Permisos de Ejecución

```bash
chmod +x start.sh main.py
```

### 4. Iniciar la Aplicación

```bash
./start.sh
```

El script automáticamente:
- ✅ Creará el entorno virtual Python
- ✅ Instalará todas las dependencias
- ✅ Verificará puertos disponibles
- ✅ Iniciará la API en puerto 3012

### 5. Verificar Instalación

Abre en tu navegador:
```
http://localhost:3012/docs
```

Deberías ver la documentación interactiva de la API (Swagger UI).

## Instalación Manual (Alternativa)

Si `start.sh` falla, instala manualmente:

```bash
# 1. Crear entorno virtual
python3 -m venv venv

# 2. Activar entorno
source venv/bin/activate

# 3. Actualizar pip
pip install --upgrade pip

# 4. Instalar dependencias
pip install -r requirements.txt

# 5. Iniciar API
cd src/api
python main.py
```

## Verificación de Componentes

### Test de Módulos

```bash
# Activar entorno
source venv/bin/activate

# Test extractor PDF
python src/parser/pdf_extractor.py

# Test parser completo
python src/parser/partida_parser.py

# Test normalizador
python src/utils/normalizer.py
```

### Procesar PDF de Ejemplo

```bash
./main.py ejemplo
```

Si todo está correcto, verás:
```
✓ Parseo completado: X partidas extraídas
✓ Guardado en BD con ID: 1
✓ CSV: data/exports/PROYECTO CALYPOFADO_extract.csv
✓ Excel: data/exports/PROYECTO CALYPOFADO_extract.xlsx
✓ XML: data/exports/PROYECTO CALYPOFADO_extract.xml
✓ BC3: data/exports/PROYECTO CALYPOFADO_extract.bc3
```

## Solución de Problemas

### Error: "python3: command not found"

Instala Python 3:
```bash
# macOS con Homebrew
brew install python@3.11
```

### Error: "Permission denied: start.sh"

```bash
chmod +x start.sh
```

### Error: "Port 3012 already in use"

Mata el proceso:
```bash
kill -9 $(lsof -t -i:3012)
```

O edita `start.sh` y cambia `API_PORT=3012` por otro puerto.

### Error instalando pdfplumber

```bash
# macOS: instalar dependencias del sistema
brew install poppler

# Reinstalar
pip install --force-reinstall pdfplumber
```

### Error de memoria al procesar PDFs grandes

Aumenta límite de memoria:
```bash
export PYTHONMALLOC=malloc
python main.py procesar archivo_grande.pdf
```

## Configuración del LLM Server (Opcional)

El sistema busca un LLM Server en:
```
/Volumes/DATOS_IA/G_Drive_LuzIA/IA/Proyectos/LLM-Server
```

Si no existe o no está corriendo, el sistema funciona normalmente sin funciones de LLM.

Para habilitar LLM en futuras versiones:
1. Inicia tu servidor LLM en puerto 8000
2. El script `start.sh` lo detectará automáticamente

## Estructura de Archivos Creados

Después de la instalación:

```
Mediciones/
├── venv/                   # Entorno virtual (creado)
├── data/
│   ├── uploads/           # PDFs subidos
│   ├── exports/           # Archivos exportados
│   └── mediciones.db     # Base de datos SQLite
├── logs/
│   └── api.log           # Logs de la API
└── ...
```

## Desinstalación

```bash
# Desactivar entorno virtual
deactivate

# Eliminar entorno virtual
rm -rf venv

# Eliminar datos (opcional)
rm -rf data logs

# Desinstalar dependencias del sistema (opcional)
# brew uninstall poppler  # si fue instalado
```

## Próximos Pasos

1. Lee el [README.md](README.md) para documentación completa
2. Revisa [EJEMPLOS.md](EJEMPLOS.md) para ejemplos de uso
3. Prueba la API en `http://localhost:3012/docs`
4. Procesa tu primer PDF con `./main.py procesar mi_presupuesto.pdf`

---

**¿Problemas?** Consulta los logs en `logs/api.log`
