"""Debug del proyecto 1 - partidas problemáticas"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.parser.pdf_extractor import PDFExtractor
from src.parser.line_classifier import LineClassifier

# Usar el PDF más reciente de CALYPOFADO
pdf_path = "data/uploads/20251124_104805_PROYECTO CALYPOFADO_extract.pdf"

extractor = PDFExtractor(pdf_path)
datos = extractor.extraer_todo()
lineas = datos['all_lines']

print(f"Total líneas: {len(lineas)}\n")

# Buscar RETIRADA001
print("="*80)
print("BUSCANDO: RETIRADA001")
print("="*80)

for i, linea in enumerate(lineas):
    if "RETIRADA001" in linea:
        start = max(0, i-2)
        end = min(len(lineas), i+8)

        print(f"\nEncontrada en línea {i}:")
        for j in range(start, end):
            marca = ">>>" if j == i else "   "
            print(f"{marca} {j:3d}: {lineas[j]}")

        # Clasificar esta sección
        print("\nCLASIFICACIÓN:")
        for j in range(start, end):
            clasificacion = LineClassifier.clasificar(lineas[j], {'partida_activa': True if j > i else False})
            tipo = clasificacion['tipo'].value
            print(f"    {j:3d} | {tipo:20s} | {lineas[j][:60]}")
        break

# Buscar U11SAM020
print(f"\n{'='*80}")
print("BUSCANDO: U11SAM020 (primera aparición)")
print("="*80)

for i, linea in enumerate(lineas):
    if "U11SAM020" in linea:
        start = max(0, i-2)
        end = min(len(lineas), i+8)

        print(f"\nEncontrada en línea {i}:")
        for j in range(start, end):
            marca = ">>>" if j == i else "   "
            print(f"{marca} {j:3d}: {lineas[j]}")

        # Clasificar esta sección
        print("\nCLASIFICACIÓN:")
        for j in range(start, end):
            clasificacion = LineClassifier.clasificar(lineas[j], {'partida_activa': True if j > i else False})
            tipo = clasificacion['tipo'].value
            print(f"    {j:3d} | {tipo:20s} | {lineas[j][:60]}")
        break
