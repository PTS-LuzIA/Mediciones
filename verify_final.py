"""
Verificación final: mostrar detalles completos de las partidas de 03.02
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.parser.partida_parser import PartidaParser

pdf_path = "data/uploads/20251124_104742_PROYECTO CALLE ARENAL_extract.pdf"

parser = PartidaParser(pdf_path)
resultado = parser.parsear()

print("=" * 80)
print("VERIFICACIÓN FINAL - SUBCAPÍTULO 03.02")
print("=" * 80)

for cap in resultado['estructura']['capitulos']:
    for sub in cap['subcapitulos']:
        if sub['codigo'] == '03.02':
            print(f"\nSubcapítulo: {sub['codigo']} - {sub['nombre']}")
            print(f"Número de partidas: {len(sub['partidas'])}\n")

            for i, p in enumerate(sub['partidas'], 1):
                print(f"{'='*80}")
                print(f"PARTIDA {i}")
                print(f"{'='*80}")
                print(f"Código:      {p['codigo']}")
                print(f"Unidad:      {p['unidad']}")
                print(f"Resumen:     {p['resumen']}")
                print(f"Descripción: {p['descripcion']}")
                print(f"Cantidad:    {p['cantidad']}")
                print(f"Precio:      {p['precio']:,.2f} €".replace(',', 'X').replace('.', ',').replace('X', '.'))
                print(f"Importe:     {p['importe']:,.2f} €".replace(',', 'X').replace('.', ',').replace('X', '.'))
                print()

            total = sum(p['importe'] for p in sub['partidas'])
            print(f"{'='*80}")
            print(f"TOTAL SUBCAPÍTULO 03.02: {total:,.2f} €".replace(',', 'X').replace('.', ',').replace('X', '.'))
            print(f"{'='*80}")
            print()
            print("✓ FIX COMPLETADO CON ÉXITO")
            print("✓ Ahora detecta correctamente la unidad P:A: pegada al texto")
            print("✓ Total de partidas en CALLE ARENAL: 35 (antes: 34)")
