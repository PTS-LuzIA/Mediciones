"""
Script para encontrar TODAS las unidades en líneas que parecen partidas pero no se detectan
"""
import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.parser.pdf_extractor import PDFExtractor

# Patrón similar al PATRON_PARTIDA pero más flexible para capturar la unidad
patron_partida_flexible = re.compile(
    r'^([A-Z][A-Z0-9\.\s_]{2,15}?)\s+([a-zA-Z0-9\.]+?)\s+([A-ZÁÉÍÓÚÑ\s])',
    re.IGNORECASE
)

pdf_path = "data/uploads/20251124_101444_PROYECTO CALYPOFADO_extract.pdf"
if not Path(pdf_path).exists():
    pdf_path = "ejemplo/PROYECTO CALYPOFADO_extract.pdf"

extractor = PDFExtractor(pdf_path)
datos = extractor.extraer_todo()
lineas = datos['all_lines']

print("=== BUSCANDO LÍNEAS CON FORMATO DE PARTIDA ===\n")

unidades_encontradas = {}
ejemplos = []

for linea in lineas:
    match = patron_partida_flexible.match(linea)
    if match:
        codigo = match.group(1).strip()
        unidad = match.group(2).strip()
        resumen_inicio = match.group(3)

        # Filtrar líneas de título
        if len(codigo) >= 3 and len(unidad) <= 5:
            if unidad not in unidades_encontradas:
                unidades_encontradas[unidad] = []

            unidades_encontradas[unidad].append(linea)

print("UNIDADES ENCONTRADAS EN EL PDF:")
print("-" * 80)

for unidad in sorted(unidades_encontradas.keys()):
    count = len(unidades_encontradas[unidad])
    print(f"\n{unidad:10s} ({count} apariciones)")
    # Mostrar primeros 3 ejemplos
    for ejemplo in unidades_encontradas[unidad][:3]:
        print(f"   {ejemplo[:75]}")

# Ahora verificar cuáles NO están en el patrón actual
patron_actual = re.compile(r'^(m[2-3]?|M[2-3]?|Ml|ml|M|m\.|ud|Ud|pa|Pa)$', re.IGNORECASE)

print("\n\n=== UNIDADES QUE FALTAN EN EL PATRÓN ===\n")

unidades_faltantes = []
for unidad in sorted(unidades_encontradas.keys()):
    if not patron_actual.match(unidad):
        unidades_faltantes.append(unidad)
        count = len(unidades_encontradas[unidad])
        print(f"❌ {unidad:10s} ({count} partidas)")
        print(f"   Ejemplo: {unidades_encontradas[unidad][0][:70]}...")

print(f"\n\nTotal unidades faltantes: {len(unidades_faltantes)}")
print(f"Unidades a añadir al patrón: {' | '.join(unidades_faltantes)}")
