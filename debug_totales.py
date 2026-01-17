"""Debug de líneas TOTAL"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.parser.pdf_extractor import PDFExtractor
from src.parser.line_classifier import LineClassifier

pdf_path = "data/uploads/20251124_161558_PE_PRE_R2_RAMPA_PORTAL.pdf"

extractor = PDFExtractor(pdf_path)
datos = extractor.extraer_todo()
lineas = datos['all_lines']

clasificaciones = LineClassifier.clasificar_bloque(lineas)

print("="*80)
print("SECUENCIA ALREDEDOR DE 01.18:")
print("="*80)

for i, item in enumerate(clasificaciones):
    if item['linea'] and '01.18' in item['linea']:
        # Mostrar contexto: 3 antes y 5 después
        start = max(0, i-3)
        end = min(len(clasificaciones), i+6)

        for j in range(start, end):
            marca = ">>>" if j == i else "   "
            tipo = clasificaciones[j]['tipo'].value
            linea = clasificaciones[j]['linea'][:60]
            print(f"{marca} {j:3d} | {tipo:20s} | {linea}")
        break

print(f"\n{'='*80}")
print("SECUENCIA ALREDEDOR DE 02.01:")
print("="*80)

for i, item in enumerate(clasificaciones):
    if item['linea'] and '02.01' in item['linea']:
        start = max(0, i-3)
        end = min(len(clasificaciones), i+6)

        for j in range(start, end):
            marca = ">>>" if j == i else "   "
            tipo = clasificaciones[j]['tipo'].value
            linea = clasificaciones[j]['linea'][:60]
            print(f"{marca} {j:3d} | {tipo:20s} | {linea}")
        break

print(f"\n{'='*80}")
print("TODAS LAS LÍNEAS 'TOTAL':")
print("="*80)

for i, item in enumerate(clasificaciones):
    if item['tipo'].value == 'total':
        print(f"{i:3d} | TOTAL | {item['linea']}")
