# Detección Automática de Columnas en PDFs

## Problema

Los presupuestos de construcción a menudo vienen en formato apaisado con **múltiples columnas** para aprovechar mejor el espacio. Cuando se extraen con herramientas estándar, el texto se mezcla incorrectamente.

### Ejemplo del Problema

**PDF Original (2 columnas):**
```
┌─────────────────────┬─────────────────────┐
│ CAPÍTULO 01         │ CAPÍTULO 02         │
│ DEMOLICIONES        │ CIMENTACIÓN         │
│                     │                     │
│ Partida A           │ Partida D           │
│ Partida B           │ Partida E           │
│ Partida C           │ Partida F           │
└─────────────────────┴─────────────────────┘
```

**Extracción incorrecta (sin detección de columnas):**
```
CAPÍTULO 01 CAPÍTULO 02
DEMOLICIONES CIMENTACIÓN
Partida A Partida D
Partida B Partida E
Partida C Partida F
```

**Extracción correcta (con detección de columnas):**
```
CAPÍTULO 01
DEMOLICIONES
Partida A
Partida B
Partida C
CAPÍTULO 02
CIMENTACIÓN
Partida D
Partida E
Partida F
```

---

## Solución Implementada

### 1. Detector de Columnas (`ColumnDetector`)

Analiza la distribución espacial de las palabras en el PDF para detectar automáticamente:
- Número de columnas
- Rangos X de cada columna
- Tipo de layout (vertical / apaisado)
- Orientación del documento

**Algoritmo:**
1. Extrae posiciones X de todas las palabras
2. Crea histograma de posiciones
3. Detecta gaps (espacios sin texto)
4. Define rangos de columnas basados en gaps
5. Agrupa palabras por columna
6. Ordena cada columna de arriba a abajo

### 2. Extractor Mejorado (`PDFExtractor`)

Integra el detector de columnas en el flujo de extracción:
- Activa automáticamente por defecto
- Se puede desactivar con `detect_columns=False`
- Procesa cada página individualmente
- Mantiene compatibilidad con PDFs de columna simple

---

## Uso

### Básico (Automático)

```python
from parser.pdf_extractor import PDFExtractor

# La detección de columnas está activada por defecto
extractor = PDFExtractor("presupuesto.pdf")
resultado = extractor.extraer_todo()

# Acceder a las líneas ordenadas correctamente
lineas = resultado['all_lines']

# Ver información de layout
layout_summary = resultado['layout_summary']
print(f"Páginas con múltiples columnas: {layout_summary['paginas_multicolumna']}")
```

### Desactivar Detección de Columnas

```python
# Para PDFs que sepas que son de columna simple
extractor = PDFExtractor("presupuesto.pdf", detect_columns=False)
resultado = extractor.extraer_todo()
```

### Análisis de Layout

```python
# Ver detalles de layout por página
for page in resultado['pages']:
    layout = page['layout']
    print(f"Página {page['num']}:")
    print(f"  - Columnas: {layout['num_columnas']}")
    print(f"  - Tipo: {layout['tipo']}")
    print(f"  - Orientación: {layout['orientacion']}")
```

### Script de Prueba

```bash
# Probar con un PDF específico
python test_column_detection.py ruta/al/presupuesto.pdf

# Ver más líneas
python test_column_detection.py ruta/al/presupuesto.pdf -n 50
```

---

## Configuración Avanzada

### Ajustar Parámetros del Detector

```python
from parser.column_detector import ColumnDetector
from parser.pdf_extractor import PDFExtractor

# Crear detector personalizado
detector = ColumnDetector(
    threshold_gap=50.0,        # Gap mínimo entre columnas (puntos)
    min_column_width=150.0     # Ancho mínimo de una columna (puntos)
)

# Usar en el extractor
extractor = PDFExtractor("presupuesto.pdf")
extractor.column_detector = detector
resultado = extractor.extraer_todo()
```

### Parámetros:

- **`threshold_gap`**: Espacio mínimo (en puntos PDF) para considerar separación entre columnas
  - Valor por defecto: `50.0`
  - Aumentar si detecta columnas donde no las hay
  - Disminuir si no detecta columnas que sí existen

- **`min_column_width`**: Ancho mínimo que debe tener una columna válida
  - Valor por defecto: `150.0`
  - Previene detección de columnas muy estrechas (encabezados, márgenes)

---

## Casos de Uso

### ✅ Funciona Correctamente Con:

1. **PDFs apaisados con 2 columnas** - Caso más común
2. **PDFs verticales con columna simple** - Se procesa normalmente
3. **PDFs con 3+ columnas** - Detecta y procesa todas
4. **Mezcla de layouts** - Páginas con columnas + páginas simples en el mismo PDF

### ⚠️  Limitaciones Conocidas:

1. **Columnas irregulares** - Si las columnas no están bien alineadas verticalmente
2. **Cambio de columnas a mitad de página** - Texto que cambia de columnas horizontalmente
3. **Tablas complejas** - Pueden confundirse con múltiples columnas

---

## Logs y Debugging

El sistema genera logs automáticos cuando detecta columnas:

```
INFO: Extrayendo 5 páginas de presupuesto.pdf
INFO:   Página 1: 2 columnas detectadas (apaisado)
INFO:   Página 3: 2 columnas detectadas (apaisado)
INFO: ⚡ Detectadas 2 página(s) con múltiples columnas (máx: 2 columnas)
INFO: ✓ Extraídas 1247 líneas
```

### Ver más detalles:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## Impacto en el Sistema

### Rendimiento

- **Overhead mínimo**: ~5-10% más lento que extracción simple
- **Sin dependencias adicionales**: Usa solo `pdfplumber` existente
- **Cache de palabras**: Cada página se procesa una sola vez

### Compatibilidad

- ✅ **100% compatible** con código existente
- ✅ Activo por defecto en nuevas extracciones
- ✅ No afecta PDFs de columna simple
- ✅ Retrocompatible con `detect_columns=False`

---

## Integración con el Parser

El sistema de parseo (`PartidaParser`) **automáticamente se beneficia** de la detección de columnas:

```python
from parser.partida_parser import PartidaParser

# El parser usa PDFExtractor internamente
parser = PartidaParser("presupuesto_2_columnas.pdf")
resultado = parser.parsear()

# Las partidas se extraen correctamente incluso con múltiples columnas
print(f"Partidas extraídas: {resultado['estadisticas']['partidas']}")
```

**No se requiere ningún cambio en el código existente.**

---

## Ejemplos de Salida

### PDF con 2 Columnas Detectadas

```
📄 Información del PDF:
   Archivo: presupuesto_apaisado.pdf
   Páginas: 15
   Líneas totales: 2847

⚡ Layout de Múltiples Columnas:
   Páginas con múltiples columnas: 12
   Máximo de columnas detectadas: 2

📑 Detalle por Página:
   Página 1:
      • Tipo: multicolumna
      • Columnas: 2
      • Orientación: apaisado
         - Columna 1: X=[72.0, 306.0], Ancho=234.0 pts
         - Columna 2: X=[318.0, 540.0], Ancho=222.0 pts
```

### Comparación con/sin Detección

```
🔄 Comparación: Sin detección de columnas
   Líneas extraídas (simple): 2847
   Líneas extraídas (columnas): 2847
   ✓ Mismo número de líneas

   Primeras 10 líneas (modo simple):
    1. CAPÍTULO C01 ACTUACIONES CAPÍTULO C02 DEMOLICIONES
    2. Partida A Descripción... Partida F Otra desc...

   Primeras 10 líneas (con detección columnas):
    1. CAPÍTULO C01 ACTUACIONES
    2. Partida A
    3. Descripción de la partida A...
    4. ...
    5. CAPÍTULO C02 DEMOLICIONES
    6. Partida F
```

---

## Troubleshooting

### Problema: Detecta columnas donde no las hay

**Solución:** Aumentar `threshold_gap`

```python
detector = ColumnDetector(threshold_gap=100.0)
```

### Problema: No detecta columnas que sí existen

**Solución 1:** Disminuir `threshold_gap`
```python
detector = ColumnDetector(threshold_gap=30.0)
```

**Solución 2:** Verificar con el script de prueba
```bash
python test_column_detection.py problema.pdf
```

### Problema: Columnas detectadas pero texto mezclado

**Causa:** Palabras en posiciones Y muy diferentes en cada columna

**Solución:** Este caso puede requerir ajuste manual o procesamiento con LLM

---

## Próximas Mejoras

### Planeadas:

1. ✨ **Detección de cambio de columnas horizontal** - Para textos que fluyen entre columnas
2. ✨ **Soporte para tablas multi-columna** - Reconocer tablas dentro de layouts de columnas
3. ✨ **Fallback con LLM** - Usar LLM para casos complejos que fallen con regex
4. ✨ **Visualización de columnas** - Generar imagen mostrando columnas detectadas

### En Consideración:

- Detección de rotación de texto
- Soporte para columnas con anchos variables
- Export de metadata de columnas en formatos de salida

---

## Referencias

- **Código fuente**: `src/parser/column_detector.py`
- **Integración**: `src/parser/pdf_extractor.py`
- **Tests**: `test_column_detection.py`
- **Biblioteca base**: [pdfplumber](https://github.com/jsvine/pdfplumber)
