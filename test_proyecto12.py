"""
Testar re-procesamiento del proyecto 12 con el fix de mediciones parciales
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.parser.partida_parser import PartidaParser

pdf_path = "data/uploads/20251124_111644_PE_PRE_R2_RAMPA_PORTAL.pdf"

print("=== RE-PROCESANDO PROYECTO 12 CON FIX DE MEDICIONES ===\n")

parser = PartidaParser(pdf_path)
resultado = parser.parsear()

parser.imprimir_resumen()

# Verificar partida 01.04
todas_partidas = parser.obtener_todas_partidas()

for p in todas_partidas:
    if '01.04' in p['codigo']:
        print("\n" + "="*80)
        print("VERIFICACIÓN PARTIDA 01.04")
        print("="*80)
        print(f"Código:      {p['codigo']}")
        print(f"Unidad:      {p['unidad']}")
        print(f"Resumen:     {p['resumen'][:60]}...")
        print(f"Cantidad:    {p['cantidad']}")
        print(f"Precio:      {p['precio']}")
        print(f"Importe:     {p['importe']}")
        print()

        # Validar que sean los valores correctos (totales, no parciales)
        if p['cantidad'] == 2.83 and p['precio'] == 8.04 and p['importe'] == 22.75:
            print("✓ ¡CORRECTO! Se capturaron los totales (2,83  8,04  22,75)")
            print("✓ No se capturaron las mediciones parciales (1  2,08  3,30  6,86)")
        else:
            print(f"✗ ERROR: Valores incorrectos")
            print(f"  Esperado: Cantidad=2.83, Precio=8.04, Importe=22.75")
            print(f"  Obtenido: Cantidad={p['cantidad']}, Precio={p['precio']}, Importe={p['importe']}")

        break
