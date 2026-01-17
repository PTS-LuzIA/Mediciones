"""Buscar partida 01.18"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.parser.pdf_extractor import PDFExtractor

pdf_path = "data/uploads/20251124_161558_PE_PRE_R2_RAMPA_PORTAL.pdf"

extractor = PDFExtractor(pdf_path)
datos = extractor.extraer_todo()
lineas = datos['all_lines']

# Buscar 01.17 y mostrar más contexto
for i, linea in enumerate(lineas):
    if "01.17" in linea:
        start = max(0, i-2)
        end = min(len(lineas), i+25)  # Mostrar 25 líneas después
        print(f"{'='*80}")
        print(f"LÍNEAS {start} A {end} (buscando 01.17 y 01.18):")
        print(f"{'='*80}\n")
        for j in range(start, end):
            marca = " >>> " if "01.17" in lineas[j] or "01.18" in lineas[j] else "     "
            print(f"{marca}{j:3d}: {lineas[j]}")
        break
