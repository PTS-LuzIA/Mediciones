"""
Debug detallado del parseo
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.parser.partida_parser import PartidaParser

pdf_path = "data/uploads/20251124_111644_PE_PRE_R2_RAMPA_PORTAL.pdf"

parser = PartidaParser(pdf_path)
resultado = parser.parsear()

print("=== ESTRUCTURA EXTRAÍDA ===\n")
print(f"Capítulos: {len(resultado['estructura']['capitulos'])}")

for i, cap in enumerate(resultado['estructura']['capitulos'], 1):
    print(f"\nCap {i}: {cap['codigo']} - {cap['nombre'][:50]}")
    print(f"  Subcapítulos: {len(cap['subcapitulos'])}")
    print(f"  Partidas directas: {len(cap.get('partidas', []))}")

    for sub in cap['subcapitulos']:
        print(f"    Sub: {sub['codigo']} - {sub['nombre'][:40]}")
        print(f"      Partidas: {len(sub['partidas'])}")

        for p in sub['partidas'][:3]:  # Primeras 3
            print(f"        • {p['codigo']}: {p['resumen'][:30]}... | Cant={p['cantidad']}, Prec={p['precio']}, Imp={p['importe']}")
