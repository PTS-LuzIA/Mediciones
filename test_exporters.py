#!/usr/bin/env python3
import sys
from pathlib import Path

src_path = Path(__file__).parent / 'src'
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from parser.pdf_extractor import PDFExtractor

pdf_path = '/Volumes/DATOS_IA/G_Drive_LuzIA/PRUEBAS/PLIEGOS/PRESUPUESTOS PARCIALES NAVAS DE TOLOSA.pdf'

extractor = PDFExtractor(pdf_path, detect_columns=True)
result = extractor.extraer_todo()

print(f"Total líneas: {len(result['all_lines'])}\n")
print("Primeras 30 líneas:\n")

for i, linea in enumerate(result['all_lines'][:30], 1):
    print(f"{i:3d}. {linea}")
