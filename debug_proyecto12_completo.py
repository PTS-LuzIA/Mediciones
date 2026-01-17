"""
Debug completo del proyecto 12
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.parser.partida_parser import PartidaParser

pdf_path = "data/uploads/20251124_111644_PE_PRE_R2_RAMPA_PORTAL.pdf"

parser = PartidaParser(pdf_path)
resultado = parser.parsear()

print("=== PROYECTO 12 - ANÁLISIS COMPLETO ===\n")
print(f"Nombre detectado: {resultado['estructura']['nombre']}\n")

print(f"Total partidas: {resultado['estadisticas']['partidas']}\n")

for cap in resultado['estructura']['capitulos']:
    print(f"\nCAPÍTULO {cap['codigo']}: {cap['nombre']}")
    print(f"  Subcapítulos: {len(cap['subcapitulos'])}")
    print(f"  Partidas directas: {len(cap.get('partidas', []))}")

    if cap.get('partidas'):
        print("  ⚠ PARTIDAS DIRECTAS (deberían estar en subcapítulo):")
        for p in cap['partidas']:
            print(f"    • {p['codigo']}: {p['resumen'][:40]}")

    for sub in cap['subcapitulos']:
        print(f"\n  SUBCAPÍTULO {sub['codigo']}: {sub['nombre']}")
        print(f"    Partidas: {len(sub['partidas'])}")

        for i, p in enumerate(sub['partidas'], 1):
            print(f"      {i:2d}. {p['codigo']:10s} | Cant={p['cantidad']:6.2f} | Prec={p['precio']:8.2f} | Imp={p['importe']:10.2f}")

print("\n\n=== VERIFICAR PARTIDAS ESPECÍFICAS ===\n")

todas = parser.obtener_todas_partidas()

# 01.05
p_0105 = next((p for p in todas if '01.05' in p['codigo']), None)
if p_0105:
    print(f"01.05: {p_0105['resumen'][:50]}")
    print(f"  Cantidad={p_0105['cantidad']}, Precio={p_0105['precio']}, Importe={p_0105['importe']}")

# 01.06
p_0106 = next((p for p in todas if '01.06' in p['codigo']), None)
if p_0106:
    print(f"\n01.06: {p_0106['resumen'][:50]}")
    print(f"  Cantidad={p_0106['cantidad']}, Precio={p_0106['precio']}, Importe={p_0106['importe']}")
else:
    print("\n01.06: ✗ NO ENCONTRADA")

# 01.17
p_0117 = next((p for p in todas if '01.17' in p['codigo']), None)
if p_0117:
    print(f"\n01.17: {p_0117['resumen'][:50]}")
else:
    print("\n01.17: ✗ NO ENCONTRADA")

# 01.18
p_0118 = next((p for p in todas if '01.18' in p['codigo']), None)
if p_0118:
    print(f"\n01.18: {p_0118['resumen'][:50]}")
else:
    print("\n01.18: ✗ NO ENCONTRADA")

# Cap 2
print("\n\n=== CAPÍTULO 02 ===")
cap2 = next((c for c in resultado['estructura']['capitulos'] if c['codigo'] == '02'), None)
if cap2:
    print(f"Subcapítulos: {len(cap2['subcapitulos'])}")
    print(f"Partidas directas: {len(cap2.get('partidas', []))}")
