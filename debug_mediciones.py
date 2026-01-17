"""
Analizar la estructura de mediciones parciales vs totales en proyecto 12
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.parser.pdf_extractor import PDFExtractor
from src.parser.line_classifier import LineClassifier, TipoLinea

pdf_path = "data/uploads/20251124_111644_PE_PRE_R2_RAMPA_PORTAL.pdf"

extractor = PDFExtractor(pdf_path)
datos = extractor.extraer_todo()
lineas = datos['all_lines']

print("=== BUSCANDO PARTIDA 01.04 ===\n")

# Buscar la partida 01.04
for i, linea in enumerate(lineas):
    if '01.04' in linea and 'DEMOLICIÓN' in linea.upper():
        print(f"Encontrada partida 01.04 en línea {i}:")
        print(f"  {repr(linea)}\n")

        # Mostrar las siguientes 30 líneas para ver la estructura
        print("Líneas siguientes:")
        print("-" * 80)
        for j in range(i, min(i + 30, len(lineas))):
            print(f"{j:3d}: {lineas[j]}")
        print("-" * 80)
        break

print("\n=== CLASIFICANDO LÍNEAS DE 01.04 ===\n")

clasificaciones = LineClassifier.clasificar_bloque(lineas)

en_0104 = False
partida_0104_header_idx = None

for idx, item in enumerate(clasificaciones):
    tipo = item['tipo']
    linea = item['linea']

    if tipo == TipoLinea.PARTIDA_HEADER and '01.04' in item['datos']['codigo']:
        en_0104 = True
        partida_0104_header_idx = idx
        print(f">>> INICIO PARTIDA 01.04 (índice {idx}) <<<\n")

    if en_0104:
        # Mostrar hasta encontrar la siguiente partida
        if tipo == TipoLinea.PARTIDA_HEADER and '01.04' not in item['datos']['codigo']:
            print(f"\n>>> FIN PARTIDA 01.04 (siguiente partida en índice {idx}) <<<\n")
            break

        print(f"{tipo.value:25s} | {linea[:70]}")

        if tipo == TipoLinea.PARTIDA_DATOS:
            print(f"  → Datos capturados: {item['datos']}")
