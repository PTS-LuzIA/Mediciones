# 📚 Ejemplos de Uso - MVP Mediciones

## 🚀 Inicio Rápido

### 1. Procesar PDF de ejemplo (línea de comandos)

```bash
# Procesar y exportar en todos los formatos
./main.py ejemplo

# Solo procesar sin exportar
./main.py procesar ejemplo/PROYECTO\ CALYPOFADO_extract.pdf

# Procesar y exportar solo CSV y Excel
./main.py procesar ejemplo/PROYECTO\ CALYPOFADO_extract.pdf --exportar csv excel

# Procesar sin guardar en BD
./main.py procesar ejemplo/PROYECTO\ CALYPOFADO_extract.pdf --no-db

# Listar proyectos en BD
./main.py listar
```

### 2. Usar la API REST

**Iniciar servidor:**
```bash
./start.sh
```

**Subir PDF:**
```bash
curl -X POST http://localhost:3012/upload \
  -F "file=@ejemplo/PROYECTO CALYPOFADO_extract.pdf" \
  | jq
```

**Listar proyectos:**
```bash
curl http://localhost:3012/proyectos | jq
```

**Obtener proyecto específico:**
```bash
curl http://localhost:3012/proyectos/1 | jq
```

**Exportar a CSV:**
```bash
curl -O http://localhost:3012/exportar/1/csv
```

**Exportar a Excel:**
```bash
curl -O http://localhost:3012/exportar/1/excel
```

**Exportar a XML:**
```bash
curl -O http://localhost:3012/exportar/1/xml
```

**Exportar a BC3:**
```bash
curl -O http://localhost:3012/exportar/1/bc3
```

**Eliminar proyecto:**
```bash
curl -X DELETE http://localhost:3012/proyectos/1
```

## 🐍 Uso desde Python

### Ejemplo 1: Parser básico

```python
from src.parser.partida_parser import PartidaParser

# Parsear PDF
parser = PartidaParser('ejemplo/PROYECTO CALYPOFADO_extract.pdf')
resultado = parser.parsear()

# Ver estadísticas
print(f"Partidas: {resultado['estadisticas']['partidas']}")
print(f"Capítulos: {resultado['estadisticas']['capitulos']}")

# Obtener todas las partidas
partidas = parser.obtener_todas_partidas()
print(f"\nPrimera partida:")
print(f"  Código: {partidas[0]['codigo']}")
print(f"  Resumen: {partidas[0]['resumen']}")
print(f"  Importe: {partidas[0]['importe']}")
```

### Ejemplo 2: Guardar en base de datos

```python
from src.parser.partida_parser import PartidaParser
from src.models.db_models import DatabaseManager

# Parsear
parser = PartidaParser('mi_presupuesto.pdf')
resultado = parser.parsear()

# Guardar
db = DatabaseManager()
proyecto = db.guardar_estructura(resultado['estructura'])
total = db.calcular_totales(proyecto.id)

print(f"Proyecto ID: {proyecto.id}")
print(f"Total: {total:,.2f} €")

db.cerrar()
```

### Ejemplo 3: Exportar a múltiples formatos

```python
from src.parser.partida_parser import PartidaParser
from src.exporters.csv_exporter import CSVExporter
from src.exporters.excel_exporter import ExcelExporter
from src.exporters.xml_exporter import XMLExporter
from src.exporters.bc3_exporter import BC3Exporter

# Parsear
parser = PartidaParser('mi_presupuesto.pdf')
resultado = parser.parsear()

estructura = resultado['estructura']
partidas = parser.obtener_todas_partidas()

# Exportar
CSVExporter.exportar(partidas, 'salida.csv')
ExcelExporter.exportar_multihojas(estructura, 'salida.xlsx')
XMLExporter.exportar(estructura, 'salida.xml')
BC3Exporter.exportar(estructura, 'salida.bc3')

print("✓ Archivos exportados")
```

### Ejemplo 4: Validar importes

```python
from src.parser.partida_parser import PartidaParser
from src.utils.normalizer import Normalizer

parser = PartidaParser('presupuesto.pdf')
resultado = parser.parsear()

partidas = parser.obtener_todas_partidas()

print("Validando importes...")
for partida in partidas:
    es_valido = Normalizer.validar_importe(
        partida['cantidad'],
        partida['precio'],
        partida['importe']
    )

    if not es_valido:
        print(f"⚠ {partida['codigo']}: importe no coincide")
```

### Ejemplo 5: Filtrar partidas

```python
from src.parser.partida_parser import PartidaParser

parser = PartidaParser('presupuesto.pdf')
resultado = parser.parsear()

partidas = parser.obtener_todas_partidas()

# Filtrar partidas de demolición
partidas_demolicion = [
    p for p in partidas
    if 'DEMOLICIÓN' in p['resumen'].upper()
]

print(f"Partidas de demolición: {len(partidas_demolicion)}")

# Calcular total de demoliciones
total = sum(p['importe'] for p in partidas_demolicion)
print(f"Total demoliciones: {total:,.2f} €")
```

### Ejemplo 6: Leer desde base de datos

```python
from src.models.db_models import DatabaseManager

db = DatabaseManager()

# Listar proyectos
proyectos = db.listar_proyectos()
for p in proyectos:
    print(f"{p.id}. {p.nombre} - {p.presupuesto_total:,.2f} €")

# Obtener proyecto específico
proyecto = db.obtener_proyecto(1)

# Recorrer estructura
for capitulo in proyecto.capitulos:
    print(f"\n{capitulo.codigo} - {capitulo.nombre}")

    for subcapitulo in capitulo.subcapitulos:
        print(f"  {subcapitulo.codigo} - {subcapitulo.nombre}")
        print(f"    Partidas: {len(subcapitulo.partidas)}")
        print(f"    Total: {subcapitulo.total:,.2f} €")

db.cerrar()
```

## 🧪 Tests de Componentes

### Test del extractor de PDF:
```bash
python src/parser/pdf_extractor.py
```

### Test del clasificador de líneas:
```bash
python src/parser/line_classifier.py
```

### Test del normalizador:
```bash
python src/utils/normalizer.py
```

### Test del parser completo:
```bash
python src/parser/partida_parser.py
```

### Test de exportadores:
```bash
python src/exporters/csv_exporter.py
python src/exporters/excel_exporter.py
python src/exporters/xml_exporter.py
python src/exporters/bc3_exporter.py
```

## 📊 Análisis de Resultados

### Ejemplo: Análisis con Pandas

```python
import pandas as pd
from src.parser.partida_parser import PartidaParser

# Parsear
parser = PartidaParser('presupuesto.pdf')
resultado = parser.parsear()
partidas = parser.obtener_todas_partidas()

# Convertir a DataFrame
df = pd.DataFrame(partidas)

# Estadísticas
print("\n=== ESTADÍSTICAS ===")
print(f"Total partidas: {len(df)}")
print(f"Total presupuesto: {df['importe'].sum():,.2f} €")
print(f"Precio medio: {df['precio'].mean():.2f} €")
print(f"Cantidad media: {df['cantidad'].mean():.2f}")

# Partidas más caras
print("\n=== TOP 10 PARTIDAS MÁS CARAS ===")
top10 = df.nlargest(10, 'importe')[['codigo', 'resumen', 'importe']]
print(top10.to_string(index=False))

# Agrupar por capítulo
print("\n=== TOTALES POR CAPÍTULO ===")
por_capitulo = df.groupby('capitulo')['importe'].sum().sort_values(ascending=False)
print(por_capitulo)

# Exportar análisis
df.to_excel('analisis_completo.xlsx', index=False)
print("\n✓ Análisis exportado a analisis_completo.xlsx")
```

## 🔌 Integración con otras herramientas

### Con Requests (Python):

```python
import requests
import json

API_URL = "http://localhost:3012"

# Subir PDF
with open('mi_presupuesto.pdf', 'rb') as f:
    files = {'file': f}
    response = requests.post(f"{API_URL}/upload", files=files)
    resultado = response.json()

proyecto_id = resultado['proyecto_id']
print(f"Proyecto creado: {proyecto_id}")

# Listar proyectos
response = requests.get(f"{API_URL}/proyectos")
proyectos = response.json()
for p in proyectos:
    print(f"{p['id']}. {p['nombre']}")

# Descargar Excel
response = requests.get(f"{API_URL}/exportar/{proyecto_id}/excel")
with open('presupuesto.xlsx', 'wb') as f:
    f.write(response.content)
print("✓ Excel descargado")
```

### Con JavaScript (Node.js):

```javascript
const FormData = require('form-data');
const fs = require('fs');
const axios = require('axios');

const API_URL = 'http://localhost:3012';

// Subir PDF
async function uploadPDF(filePath) {
  const form = new FormData();
  form.append('file', fs.createReadStream(filePath));

  const response = await axios.post(`${API_URL}/upload`, form, {
    headers: form.getHeaders()
  });

  return response.data;
}

// Listar proyectos
async function listProjects() {
  const response = await axios.get(`${API_URL}/proyectos`);
  return response.data;
}

// Uso
(async () => {
  const result = await uploadPDF('presupuesto.pdf');
  console.log(`Proyecto ID: ${result.proyecto_id}`);

  const projects = await listProjects();
  console.log(`Total proyectos: ${projects.length}`);
})();
```

## 🎯 Casos de Uso Avanzados

### 1. Comparar dos presupuestos

```python
from src.parser.partida_parser import PartidaParser
import pandas as pd

# Parsear ambos
p1 = PartidaParser('presupuesto_original.pdf')
r1 = p1.parsear()
partidas1 = pd.DataFrame(p1.obtener_todas_partidas())

p2 = PartidaParser('presupuesto_reformado.pdf')
r2 = p2.parsear()
partidas2 = pd.DataFrame(p2.obtener_todas_partidas())

# Comparar totales
total1 = partidas1['importe'].sum()
total2 = partidas2['importe'].sum()
diferencia = total2 - total1
porcentaje = (diferencia / total1) * 100

print(f"Original: {total1:,.2f} €")
print(f"Reformado: {total2:,.2f} €")
print(f"Diferencia: {diferencia:,.2f} € ({porcentaje:+.2f}%)")
```

### 2. Generar informe HTML

```python
from src.parser.partida_parser import PartidaParser
import pandas as pd

parser = PartidaParser('presupuesto.pdf')
resultado = parser.parsear()
df = pd.DataFrame(parser.obtener_todas_partidas())

# Generar HTML
html = f"""
<html>
<head><title>Informe Presupuesto</title></head>
<body>
  <h1>Informe de Presupuesto</h1>
  <p>Total Partidas: {len(df)}</p>
  <p>Total Presupuesto: {df['importe'].sum():,.2f} €</p>
  {df.to_html(index=False)}
</body>
</html>
"""

with open('informe.html', 'w') as f:
    f.write(html)

print("✓ Informe generado: informe.html")
```

---

**¿Más ejemplos?** Consulta el [README.md](README.md) para documentación completa.
