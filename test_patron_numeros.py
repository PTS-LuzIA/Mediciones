"""Test del patrón de números finales"""
import sys
from pathlib import Path
import re

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.parser.line_classifier import LineClassifier

# Líneas problemáticas
test_lines = [
    "1 1",
    "1 530,00 530,00",
    "1 1,00",
    "1,00 400,00 400,00",
    "2 2,49 4,98",
    "4,98 148,26 738,33",
]

print("="*80)
print("TEST DE PATRÓN DE NÚMEROS FINALES")
print("="*80)
print(f"\nPatrón actual:")
print(LineClassifier.PATRON_NUMEROS_FINAL.pattern)
print()

for linea in test_lines:
    match = LineClassifier.PATRON_NUMEROS_FINAL.search(linea)
    clasificacion = LineClassifier.clasificar(linea, {'partida_activa': True})

    print(f"Línea: '{linea}'")
    if match:
        print(f"  ✓ MATCH:")
        print(f"    Grupo 1 (cantidad): {match.group(1)}")
        print(f"    Grupo 2 (precio): {match.group(2)}")
        print(f"    Grupo 3 (importe): {match.group(3)}")
    else:
        print(f"  ❌ NO MATCH")

    print(f"  Clasificación: {clasificacion['tipo'].value}")
    print()
