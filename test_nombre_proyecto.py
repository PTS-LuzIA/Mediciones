"""Test de detección de nombre del proyecto"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.parser.partida_parser import PartidaParser

pdf_path = "data/uploads/20251124_161558_PE_PRE_R2_RAMPA_PORTAL.pdf"

parser = PartidaParser(pdf_path)

# Extraer líneas
datos_pdf = parser.extractor.extraer_todo()
lineas = datos_pdf['all_lines']

print("PRIMERAS 10 LÍNEAS DEL PDF:")
print("="*80)
for i, linea in enumerate(lineas[:10], 1):
    print(f"{i:2d}: {linea}")

print(f"\n{'='*80}")
print("DETECTANDO NOMBRE DEL PROYECTO:")
print("="*80)

parser._detectar_nombre_proyecto(lineas)

print(f"\nNombre detectado: {parser.estructura['nombre']}")
print(f"Longitud: {len(parser.estructura['nombre'])} caracteres")
