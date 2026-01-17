"""Extraer texto del PDF del proyecto 14"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.parser.pdf_extractor import PDFExtractor

pdf_path = "data/uploads/20251124_161558_PE_PRE_R2_RAMPA_PORTAL.pdf"

extractor = PDFExtractor(pdf_path)
datos = extractor.extraer_todo()
lineas = datos['all_lines']

print(f"Total de líneas: {len(lineas)}\n")
print("="*80)
print("PRIMERAS 50 LÍNEAS (para ver nombre del proyecto):")
print("="*80)
for i, linea in enumerate(lineas[:50], 1):
    print(f"{i:3d}: {linea}")

print(f"\n{'='*80}")
print("LÍNEAS ALREDEDOR DE '01.16' (buscando 01.17 y 01.18):")
print("="*80)

# Buscar 01.16 y mostrar contexto
for i, linea in enumerate(lineas):
    if "01.16" in linea:
        start = max(0, i-2)
        end = min(len(lineas), i+15)
        for j in range(start, end):
            marca = " >>> " if j == i else "     "
            print(f"{marca}{j:3d}: {lineas[j]}")
        break

print(f"\n{'='*80}")
print("LÍNEAS DEL CAPÍTULO 02:")
print("="*80)

# Buscar capítulo 02
for i, linea in enumerate(lineas):
    if "CAPÍTULO" in linea and "02" in linea:
        start = i
        end = min(len(lineas), i+30)
        for j in range(start, end):
            print(f"{j:3d}: {lineas[j]}")
        break

print(f"\n{'='*80}")
print("LÍNEAS DEL CAPÍTULO 03:")
print("="*80)

# Buscar capítulo 03
for i, linea in enumerate(lineas):
    if "CAPÍTULO" in linea and "03" in linea:
        start = i
        end = min(len(lineas), i+30)
        for j in range(start, end):
            print(f"{j:3d}: {lineas[j]}")
        break
