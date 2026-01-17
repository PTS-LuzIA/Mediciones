"""
Debug: ver exactamente qué se clasificó
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.parser.pdf_extractor import PDFExtractor
from src.parser.line_classifier import LineClassifier, TipoLinea

pdf_path = "data/uploads/20251124_104742_PROYECTO CALLE ARENAL_extract.pdf"

extractor = PDFExtractor(pdf_path)
datos = extractor.extraer_todo()
lineas = datos['all_lines']

clasificaciones = LineClassifier.clasificar_bloque(lineas)

print("=== CLASIFICACIONES EN 03.02 ===\n")

en_0302 = False
for item in clasificaciones:
    tipo = item['tipo']
    linea = item['linea']

    if tipo == TipoLinea.SUBCAPITULO and '03.02' in item['datos']['codigo']:
        en_0302 = True
        print(f">>> INICIO 03.02 <<<\n")

    if en_0302:
        if tipo == TipoLinea.SUBCAPITULO and '03.02' not in item['datos']['codigo']:
            print(f">>> FIN 03.02 <<<\n")
            break

        print(f"{tipo.value:25s} | {repr(linea[:70])}")

        if tipo == TipoLinea.PARTIDA_HEADER:
            datos = item['datos']
            print(f"  → Código: {repr(datos['codigo'])}")
            print(f"  → Unidad: {repr(datos['unidad'])}")
            print(f"  → Resumen: {repr(datos['resumen'])}")
            print()
