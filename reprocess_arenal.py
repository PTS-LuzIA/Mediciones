"""
Re-procesar directamente el PDF de CALLE ARENAL con el parser actualizado
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.parser.partida_parser import PartidaParser

pdf_path = "data/uploads/20251124_104742_PROYECTO CALLE ARENAL_extract.pdf"

print("=== RE-PROCESANDO CALLE ARENAL CON NUEVO CÓDIGO ===\n")

parser = PartidaParser(pdf_path)
resultado = parser.parsear()

print("\n=== VERIFICANDO SUBCAPÍTULO 03.02 ===\n")

for cap in resultado['estructura']['capitulos']:
    for sub in cap['subcapitulos']:
        if sub['codigo'] == '03.02':
            print(f"Subcapítulo: {sub['codigo']} - {sub['nombre']}")
            print(f"Partidas encontradas: {len(sub['partidas'])}")

            total_sub = sum(p['importe'] for p in sub['partidas'])
            formato_total = f'{total_sub:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
            print(f"Total: {formato_total} €")

            print("\nPartidas:")
            for i, p in enumerate(sub['partidas'], 1):
                formato_importe = f'{p["importe"]:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
                print(f"  {i}. {p['codigo']:15s} | {p['unidad']:5s} | {p['resumen'][:50]}")
                print(f"     Importe: {formato_importe} €")

            print("\n" + "="*80)
            if len(sub['partidas']) == 2:
                print("✓ ¡ÉXITO! Se detectaron 2 partidas (antes solo 1)")
                print("✓ El fix de P:A: funcionó correctamente")
            else:
                print(f"⚠ Se detectaron {len(sub['partidas'])} partidas (esperado: 2)")
            print("="*80)
