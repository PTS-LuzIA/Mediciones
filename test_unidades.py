"""Test de unidades no reconocidas"""
import sys
from pathlib import Path
import re

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.parser.line_classifier import LineClassifier

# Líneas de prueba
test_lines = [
    "01.17 m PASAMANOS ACERO INOXIDABLE ACCESIBLE DOBLE 50 mm",
    "01.18 uf IMPLANTACIÓN EQUIPO AUTOMATIZACIÓN APERTURA PUERTA",
    "02.01 ud SEGURIDAD Y SALUD",
    "03.01 ud ENSAYO HORM. FORJADOS <1000 m2",
]

print("="*80)
print("TEST DE CLASIFICACIÓN DE PARTIDAS")
print("="*80)

for linea in test_lines:
    clasificacion = LineClassifier.clasificar(linea)
    tipo = clasificacion['tipo'].value
    datos = clasificacion['datos']

    print(f"\nLínea: {linea}")
    print(f"Tipo: {tipo}")
    if datos:
        print(f"Datos: {datos}")
    else:
        print(f"❌ NO DETECTADA")

# Mostrar el patrón actual
print("\n" + "="*80)
print("PATRÓN ACTUAL:")
print("="*80)
print(LineClassifier.PATRON_PARTIDA.pattern)

# Test directo del patrón
print("\n" + "="*80)
print("TEST DIRECTO DEL REGEX:")
print("="*80)

for linea in test_lines:
    match = LineClassifier.PATRON_PARTIDA.match(linea)
    if match:
        print(f"\n✓ {linea}")
        print(f"  Código: '{match.group(1)}'")
        print(f"  Unidad: '{match.group(2)}'")
        print(f"  Resumen: '{match.group(3)}'")
    else:
        print(f"\n❌ {linea}")
        print("  NO MATCHEA")
