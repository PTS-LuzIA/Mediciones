#!/usr/bin/env python3
"""
Compara diferentes métodos de extracción para encontrar el mejor
"""

import sys
from pathlib import Path

# Añadir src al path
src_path = Path(__file__).parent / 'src'
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from parser.pdf_extractor import PDFExtractor
import logging

logging.basicConfig(level=logging.WARNING)

pdf_path = '/Volumes/DATOS_IA/G_Drive_LuzIA/PRUEBAS/PLIEGOS/PRESUPUESTOS PARCIALES NAVAS DE TOLOSA.pdf'

print("=" * 80)
print("COMPARACIÓN DE MÉTODOS DE EXTRACCIÓN")
print("=" * 80)

# Método 1: Simple (sin detección de columnas)
print("\n1. MÉTODO SIMPLE (extract_text)")
print("-" * 80)
extractor1 = PDFExtractor(pdf_path, detect_columns=False)
result1 = extractor1.extraer_todo()
print(f"Líneas totales: {len(result1['all_lines'])}")
print(f"\nPrimeras 15 líneas:")
for i, linea in enumerate(result1['all_lines'][3:18], 4):
    print(f"{i:3d}. {linea[:100]}")

# Método 2: Con detección de columnas
print("\n\n2. MÉTODO CON DETECCIÓN DE COLUMNAS")
print("-" * 80)
extractor2 = PDFExtractor(pdf_path, detect_columns=True)
result2 = extractor2.extraer_todo()
print(f"Líneas totales: {len(result2['all_lines'])}")
print(f"\nPrimeras 15 líneas:")
for i, linea in enumerate(result2['all_lines'][3:18], 4):
    print(f"{i:3d}. {linea[:100]}")

# Buscar líneas que empiecen con códigos de partida
print("\n\n3. ANÁLISIS: Líneas que parecen partidas (empiezan con código)")
print("-" * 80)

import re
partida_pattern = r'^[a-zA-Z0-9]{2,15}\s+(Ud|m|m2|m3|kg|t|h|l|pa)'

print("\nMÉTODO SIMPLE:")
count = 0
for i, linea in enumerate(result1['all_lines'][:100]):
    if re.match(partida_pattern, linea):
        print(f"{i:3d}. {linea[:120]}")
        count += 1
        if count >= 5:
            break

print("\nMÉTODO CON COLUMNAS:")
count = 0
for i, linea in enumerate(result2['all_lines'][:100]):
    if re.match(partida_pattern, linea):
        print(f"{i:3d}. {linea[:120]}")
        count += 1
        if count >= 5:
            break

print("\n" + "=" * 80)
