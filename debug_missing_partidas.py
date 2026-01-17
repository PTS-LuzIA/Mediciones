"""Debug de partidas faltantes"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.parser.pdf_extractor import PDFExtractor
from src.parser.line_classifier import LineClassifier

pdf_path = "data/uploads/20251124_161558_PE_PRE_R2_RAMPA_PORTAL.pdf"

extractor = PDFExtractor(pdf_path)
datos = extractor.extraer_todo()
lineas = datos['all_lines']

# Buscar y clasificar las líneas problemáticas
partidas_buscar = ["01.17", "01.18", "02.01", "03.01"]

print("="*80)
print("BÚSQUEDA Y CLASIFICACIÓN DE PARTIDAS PROBLEMÁTICAS")
print("="*80)

for partida_codigo in partidas_buscar:
    print(f"\n{'='*80}")
    print(f"BUSCANDO: {partida_codigo}")
    print(f"{'='*80}")

    for i, linea in enumerate(lineas):
        if partida_codigo in linea:
            # Mostrar contexto
            start = max(0, i-2)
            end = min(len(lineas), i+10)

            print(f"\nEncontrada en línea {i}:")
            print("-"*80)

            for j in range(start, end):
                marca = " >>> " if j == i else "     "
                print(f"{marca}{j:3d}: {lineas[j]}")

                # Clasificar esta línea
                if j == i:
                    clasificacion = LineClassifier.clasificar(lineas[j])
                    print(f"\n     CLASIFICACIÓN: {clasificacion['tipo'].value}")
                    if clasificacion['datos']:
                        print(f"     DATOS: {clasificacion['datos']}")
                    print()
            break
    else:
        print(f"❌ NO ENCONTRADA EN EL PDF")
