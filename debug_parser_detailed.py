"""Debug detallado del parser"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.parser.partida_parser import PartidaParser
from src.parser.line_classifier import LineClassifier

pdf_path = "data/uploads/20251124_161558_PE_PRE_R2_RAMPA_PORTAL.pdf"

parser = PartidaParser(pdf_path)

# Extraer y clasificar
datos_pdf = parser.extractor.extraer_todo()
lineas = datos_pdf['all_lines']

clasificaciones = LineClassifier.clasificar_bloque(lineas)

# Filtrar y mostrar solo partidas
print("="*80)
print("PARTIDAS DETECTADAS EN EL CLASIFICADOR:")
print("="*80)

partidas_count = 0
for i, item in enumerate(clasificaciones):
    if item['tipo'].value == 'partida_header':
        partidas_count += 1
        datos = item['datos']
        print(f"{partidas_count:2d}. {datos['codigo']:8s} | {datos['unidad']:3s} | {datos['resumen'][:50]}")

print(f"\nTotal partidas detectadas: {partidas_count}")

# Ahora parsear completo
print(f"\n{'='*80}")
print("PARSEANDO ESTRUCTURA COMPLETA...")
print("="*80)

resultado = parser.parsear()
estructura = resultado['estructura']

print(f"\nEstadísticas del parseo:")
print(f"  Partidas en estadísticas: {resultado['estadisticas']['partidas']}")

print(f"\nEstructura de capítulos:")
for cap in estructura['capitulos']:
    total_partidas_cap = 0
    for sub in cap['subcapitulos']:
        total_partidas_cap += len(sub['partidas'])

    print(f"  {cap['codigo']}: {cap['nombre']}")
    print(f"    Subcapítulos: {len(cap['subcapitulos'])}, Partidas: {total_partidas_cap}")

print(f"\n{'='*80}")
print("DETALLE DE CAPÍTULOS 01, 02, 03:")
print("="*80)

for codigo_cap in ['01', '02', '03']:
    cap = next((c for c in estructura['capitulos'] if c['codigo'] == codigo_cap), None)
    if cap:
        print(f"\nCAPÍTULO {codigo_cap}: {cap['nombre']}")
        for sub in cap['subcapitulos']:
            print(f"  SUBCAPÍTULO {sub['codigo']}: {sub['nombre']}")
            for p in sub['partidas']:
                print(f"    • {p['codigo']} | {p['unidad']} | {p['resumen'][:50]}")
    else:
        print(f"\n❌ CAPÍTULO {codigo_cap} NO ENCONTRADO")
