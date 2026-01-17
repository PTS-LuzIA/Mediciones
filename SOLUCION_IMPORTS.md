# Solución de Problemas de Imports

## Problema Original

Al ejecutar `./start.sh`, se producía el siguiente error:

```
ImportError: attempted relative import beyond top-level package
File "src/parser/partida_parser.py", line 10, in <module>
    from ..utils.normalizer import Normalizer
```

## Causa Raíz

El problema ocurría porque Python estaba ejecutando los módulos en diferentes contextos:
- Cuando se ejecutaba desde `src/api/` los imports relativos (`..utils`) fallaban
- El directorio `src` no estaba en el PYTHONPATH correctamente

## Solución Implementada

### 1. Modificación de `src/parser/partida_parser.py`

Añadido sistema de fallback para imports:

```python
try:
    # Intenta imports relativos (cuando se usa como paquete)
    from .pdf_extractor import PDFExtractor
    from .line_classifier import LineClassifier, TipoLinea
    from ..utils.normalizer import Normalizer
except ImportError:
    # Fallback a imports absolutos (cuando se ejecuta directamente)
    import sys
    from pathlib import Path
    parent_dir = str(Path(__file__).parent.parent)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    from parser.pdf_extractor import PDFExtractor
    from parser.line_classifier import LineClassifier, TipoLinea
    from utils.normalizer import Normalizer
```

### 2. Modificación de `src/api/main.py`

Mejorado el setup del path:

```python
import sys
from pathlib import Path
# Agregar el directorio src al path
src_path = str(Path(__file__).parent.parent)
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from parser.partida_parser import PartidaParser
from models.db_models import DatabaseManager
# ... resto de imports
```

### 3. Modificación de `start.sh`

Cambiado el método de ejecución de la API:

**ANTES:**
```bash
cd src/api && python3 main.py 2>&1 | tee ../../logs/api.log
```

**DESPUÉS:**
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
python3 -m uvicorn src.api.main:app --host 0.0.0.0 --port $API_PORT 2>&1 | tee logs/api.log
```

Ventajas del nuevo método:
- Ejecuta desde la raíz del proyecto (no cambia directorio)
- Usa formato de módulo de uvicorn (`src.api.main:app`)
- Establece PYTHONPATH correctamente
- Mantiene logs en ubicación correcta

## Verificación

Se creó `test_parser.py` para verificar que todo funciona:

```bash
python3 test_parser.py
```

### Resultado del Test

```
✓ Capítulos: 2
✓ Subcapítulos: 8
✓ Apartados: 2
✓ Partidas: 102
✓ Partidas válidas: 102
```

## Archivos Modificados

1. `src/parser/partida_parser.py` - Líneas 9-23
2. `src/api/main.py` - Líneas 17-21
3. `start.sh` - Líneas 191-192

## Ejecución

Ahora la aplicación se puede ejecutar correctamente con:

```bash
./start.sh
```

La API estará disponible en:
- **API**: http://localhost:3012
- **Docs**: http://localhost:3012/docs
- **Health**: http://localhost:3012/health

## Notas Técnicas

- Los imports relativos (`from .modulo import Clase`) funcionan cuando Python trata el código como un paquete
- Los imports absolutos (`from modulo import Clase`) requieren que el directorio padre esté en `sys.path`
- Usar `python3 -m uvicorn` en lugar de `python3 script.py` mantiene el contexto de paquete correcto
- PYTHONPATH permite que Python encuentre los módulos desde la raíz del proyecto
