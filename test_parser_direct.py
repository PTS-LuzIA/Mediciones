#!/usr/bin/env python3
"""
Test directo del parser con líneas extraídas
"""

import sys
from pathlib import Path

# Añadir src al path
src_path = Path(__file__).parent / 'src'
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from parser.pdf_extractor import PDFExtractor
from parser.partida_parser import PartidaParser
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

pdf_path = '/Volumes/DATOS_IA/G_Drive_LuzIA/PRUEBAS/PLIEGOS/PRESUPUESTOS PARCIALES NAVAS DE TOLOSA.pdf'

print("=" * 80)
print("TEST DIRECTO DEL PARSER")
print("=" * 80)

# Parsear con PartidaParser
print("\n1. Parseando PDF completo con PartidaParser...")
parser = PartidaParser(pdf_path)
estructura = parser.parsear()

print(f"\n2. RESULTADOS:")
print(f"   • Capítulos: {len(estructura.get('capitulos', []))}")
stats = parser.estadisticas
print(f"   • Líneas totales: {stats['lineas_totales']}")
print(f"   • Partidas encontradas: {stats['partidas']}")
print(f"   • Partidas válidas: {stats['partidas_validas']}")

if estructura.get('capitulos'):
    print(f"\n3. DETALLE DE CAPÍTULOS:")
    for cap in estructura['capitulos'][:3]:  # Solo primeros 3
        print(f"\n   CAPÍTULO: {cap.get('codigo', 'N/A')} - {cap.get('titulo', 'N/A')[:50]}")
        print(f"   Partidas: {len(cap.get('partidas', []))}")

        # Mostrar primeras partidas
        for partida in cap.get('partidas', [])[:3]:
            print(f"      • {partida.get('codigo', 'N/A')} - {partida.get('descripcion', 'N/A')[:60]}")
else:
    print("\n⚠️  No se encontraron capítulos")

print("\n" + "=" * 80)
