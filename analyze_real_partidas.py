"""
Análisis preciso: detectar partidas que tienen números al final (cantidad, precio, importe)
"""
import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.parser.pdf_extractor import PDFExtractor
from src.parser.line_classifier import LineClassifier, TipoLinea

pdf_path = "data/uploads/20251124_101444_PROYECTO CALYPOFADO_extract.pdf"
if not Path(pdf_path).exists():
    pdf_path = "ejemplo/PROYECTO CALYPOFADO_extract.pdf"

extractor = PDFExtractor(pdf_path)
datos = extractor.extraer_todo()
lineas = datos['all_lines']

# Buscar patrones: línea con código + unidad, seguida en algún momento por 3 números
patron_numeros = re.compile(r'(\d{1,3}(?:\.\d{3})*,\d{2})\s+(\d{1,3}(?:\.\d{3})*,\d{2})\s+(\d{1,3}(?:\.\d{3})*,\d{2})\s*$')

# Encontrar líneas con números
lineas_con_numeros_idx = []
for i, linea in enumerate(lineas):
    if patron_numeros.search(linea):
        lineas_con_numeros_idx.append(i)

print(f"=== ANÁLISIS DE PARTIDAS REALES ===\n")
print(f"Líneas con 3 números (cantidad/precio/importe): {len(lineas_con_numeros_idx)}\n")

# Para cada línea con números, buscar el header de partida hacia atrás
patron_partida_actual = re.compile(r'^([A-Z][A-Z0-9\.\s_]+?)\s+(m[2-3]?|M[2-3]?|Ml|ml|M|m\.|ud|Ud|pa|Pa)\s+(.+)', re.IGNORECASE)

partidas_detectadas = []
partidas_no_detectadas = []

for idx_numeros in lineas_con_numeros_idx:
    # Buscar hacia atrás hasta 10 líneas
    header_encontrado = None
    for i in range(max(0, idx_numeros - 10), idx_numeros):
        linea = lineas[i]

        # Intentar match con patrón actual
        match = patron_partida_actual.match(linea)
        if match:
            header_encontrado = {
                'linea': linea,
                'codigo': match.group(1).strip(),
                'unidad': match.group(2).strip(),
                'resumen': match.group(3).strip(),
                'detectado': True
            }
            break

        # Si no match, pero parece ser un código (empieza con letra mayúscula + espacio + algo corto)
        match_flexible = re.match(r'^([A-Z][A-Z0-9\.\s_]{2,15}?)\s+([a-zA-Z0-9\.]{1,6})\s+([A-ZÁÉÍÓÚÑ].*)', linea, re.IGNORECASE)
        if match_flexible and not header_encontrado:
            codigo = match_flexible.group(1).strip()
            unidad = match_flexible.group(2).strip()
            resumen = match_flexible.group(3).strip()

            # Filtrar palabras comunes que NO son unidades
            palabras_comunes = {'de', 'en', 'con', 'para', 'por', 'bajo', 'sobre', 'entre', 'y', 'o', 'a', 'el', 'la', 'los', 'las', 'del', 'al'}

            if len(codigo) >= 3 and unidad.lower() not in palabras_comunes:
                header_encontrado = {
                    'linea': linea,
                    'codigo': codigo,
                    'unidad': unidad,
                    'resumen': resumen,
                    'detectado': False
                }

    if header_encontrado:
        if header_encontrado['detectado']:
            partidas_detectadas.append(header_encontrado)
        else:
            partidas_no_detectadas.append(header_encontrado)

print(f"Partidas DETECTADAS por patrón actual: {len(partidas_detectadas)}")
print(f"Partidas NO DETECTADAS: {len(partidas_no_detectadas)}\n")

if partidas_no_detectadas:
    print("=== PARTIDAS NO DETECTADAS ===\n")

    # Agrupar por unidad
    unidades_faltantes = {}
    for partida in partidas_no_detectadas:
        unidad = partida['unidad']
        if unidad not in unidades_faltantes:
            unidades_faltantes[unidad] = []
        unidades_faltantes[unidad].append(partida)

    for unidad in sorted(unidades_faltantes.keys()):
        partidas = unidades_faltantes[unidad]
        print(f"\nUnidad: '{unidad}' ({len(partidas)} partidas)")
        for p in partidas[:5]:  # Mostrar primeras 5
            print(f"  {p['codigo']:15s} | {p['unidad']:10s} | {p['resumen'][:50]}")

    print(f"\n\nUnidades a añadir al patrón:")
    unidades_reales = [u for u in unidades_faltantes.keys() if len(u) <= 3]
    print(f"  {' | '.join(sorted(unidades_reales))}")

# También verificar si hay partidas en el proyecto json
print("\n\n=== COMPARACIÓN CON EXTRACCIÓN GUARDADA ===\n")
import json
proyecto_json = Path("/tmp/proyecto.json")
if proyecto_json.exists():
    with open(proyecto_json) as f:
        proyecto = json.load(f)

    total_partidas_json = 0
    for cap in proyecto['capitulos']:
        for sub in cap['subcapitulos']:
            total_partidas_json += len(sub['partidas'])
            for apt in sub['apartados']:
                total_partidas_json += len(apt['partidas'])

    print(f"Partidas en /tmp/proyecto.json: {total_partidas_json}")
    print(f"Líneas con números en PDF: {len(lineas_con_numeros_idx)}")
    print(f"Diferencia: {len(lineas_con_numeros_idx) - total_partidas_json} partidas faltantes")
