"""
Debug: Buscar la línea exacta de P:A:REPARACIONES FÁBRICAS
"""
import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.parser.pdf_extractor import PDFExtractor
from src.parser.line_classifier import LineClassifier, TipoLinea

pdf_path = "data/uploads/20251124_104742_PROYECTO CALLE ARENAL_extract.pdf"

extractor = PDFExtractor(pdf_path)
datos = extractor.extraer_todo()
lineas = datos['all_lines']

print("=== BUSCANDO LÍNEA CON P:A: ===\n")

# Buscar líneas que contengan "P:A:" o "REPARACIONES"
for i, linea in enumerate(lineas):
    if 'P:A:' in linea or 'REPARACION' in linea.upper():
        print(f"Línea {i}: {repr(linea)}")

        # Mostrar contexto
        print("\nContexto:")
        for j in range(max(0, i-2), min(len(lineas), i+3)):
            marca = ">>>" if j == i else "   "
            print(f"{marca} {j:3d}: {repr(lineas[j])}")
        print()

print("\n=== TESTEANDO PATRÓN ACTUAL ===\n")

# Patrón actual
PATRON_PARTIDA = re.compile(r'^([A-Z0-9][A-Z0-9\.\s_]+?)\s+(m[2-3]?|M[2-3]?|Ml|ml|M|m\.|ud|Ud|UD|[Pp][\.:][Aa][\.::]?|pa|Pa|u)\s+(.+)', re.IGNORECASE)

# Testar líneas sospechosas
lineas_test = [
    "03.02.02 P:A:REPARACIONES FÁBRICAS",
    "03.02.02   P:A:REPARACIONES FÁBRICAS",
    "03.02.02 P:A: REPARACIONES FÁBRICAS",
]

for linea_test in lineas_test:
    match = PATRON_PARTIDA.match(linea_test)
    if match:
        print(f"✓ MATCH: {repr(linea_test)}")
        print(f"  Código: {match.group(1)}")
        print(f"  Unidad: {match.group(2)}")
        print(f"  Resumen: {match.group(3)}")
    else:
        print(f"✗ NO MATCH: {repr(linea_test)}")
    print()

print("\n=== CLASIFICANDO LÍNEAS DEL SUBCAPÍTULO 03.02 ===\n")

clasificaciones = LineClassifier.clasificar_bloque(lineas)

en_subcap_0302 = False
for item in clasificaciones:
    tipo = item['tipo']
    linea = item['linea']

    if tipo == TipoLinea.SUBCAPITULO and '03.02' in item['datos']['codigo']:
        en_subcap_0302 = True
        print(f"\n>>> INICIO SUBCAPÍTULO 03.02 <<<\n")

    if en_subcap_0302:
        if tipo == TipoLinea.SUBCAPITULO and '03.02' not in item['datos']['codigo']:
            print(f"\n>>> FIN SUBCAPÍTULO 03.02 <<<\n")
            break

        print(f"{tipo.value:25s} | {linea[:70]}")

        if tipo == TipoLinea.PARTIDA_HEADER:
            print(f"  → Código: {item['datos']['codigo']}, Unidad: {item['datos']['unidad']}")
