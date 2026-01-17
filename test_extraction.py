"""
Script para analizar qué líneas del PDF no están siendo clasificadas como partidas
"""
import sys
import re
from pathlib import Path

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.parser.pdf_extractor import PDFExtractor
from src.parser.line_classifier import LineClassifier, TipoLinea

def analizar_pdf(pdf_path):
    """Analiza el PDF y muestra líneas no clasificadas"""

    extractor = PDFExtractor(pdf_path)
    datos = extractor.extraer_todo()
    lineas = datos['all_lines']

    print(f"📄 Analizando: {pdf_path}")
    print(f"📝 Total líneas: {len(lineas)}\n")

    # Clasificar todas las líneas
    clasificaciones = LineClassifier.clasificar_bloque(lineas)

    # Contadores
    tipos_count = {}
    for item in clasificaciones:
        tipo = item['tipo']
        tipos_count[tipo.value] = tipos_count.get(tipo.value, 0) + 1

    print("=== ESTADÍSTICAS DE CLASIFICACIÓN ===")
    for tipo, count in sorted(tipos_count.items()):
        print(f"  {tipo:25s}: {count:4d}")

    print("\n=== LÍNEAS NO CLASIFICADAS (IGNORADAS) ===\n")

    # Mostrar líneas ignoradas que parecen partidas
    # (tienen letras, números y posiblemente unidades)
    patron_sospechoso = re.compile(r'^[A-Z0-9]', re.IGNORECASE)

    ignoradas_sospechosas = []
    for item in clasificaciones:
        if item['tipo'] == TipoLinea.IGNORAR:
            linea = item['linea']
            # Si empieza con letra o número mayúscula, podría ser partida
            if patron_sospechoso.match(linea) and len(linea) > 10:
                ignoradas_sospechosas.append(linea)

    print(f"Total líneas ignoradas que parecen partidas: {len(ignoradas_sospechosas)}\n")

    # Mostrar las primeras 30
    for i, linea in enumerate(ignoradas_sospechosas[:30], 1):
        print(f"{i:3d}. {linea}")

    if len(ignoradas_sospechosas) > 30:
        print(f"\n... y {len(ignoradas_sospechosas) - 30} más")

    # Ahora buscar específicamente en C08.01
    print("\n\n=== ANÁLISIS DE C08.01 CALLE TENERIFE ===\n")

    en_c08_01 = False
    lineas_c08_01 = []

    for item in clasificaciones:
        linea = item['linea']
        tipo = item['tipo']

        # Detectar inicio de C08.01
        if 'C08.01' in linea and 'TENERIFE' in linea.upper():
            en_c08_01 = True
            print(f"✓ Encontrado inicio de C08.01\n")

        # Detectar fin (siguiente subcapítulo o total)
        if en_c08_01 and ('C08.02' in linea or 'TOTAL SUBCAPÍTULO C08.01' in linea):
            en_c08_01 = False

        if en_c08_01:
            lineas_c08_01.append((linea, tipo))

    # Contar partidas en C08.01
    partidas_c08_01 = sum(1 for _, tipo in lineas_c08_01 if tipo == TipoLinea.PARTIDA_HEADER)
    ignoradas_c08_01 = [linea for linea, tipo in lineas_c08_01 if tipo == TipoLinea.IGNORAR and patron_sospechoso.match(linea)]

    print(f"Partidas detectadas en C08.01: {partidas_c08_01}")
    print(f"Líneas ignoradas sospechosas en C08.01: {len(ignoradas_c08_01)}\n")

    if ignoradas_c08_01:
        print("Líneas sospechosas en C08.01:")
        for i, linea in enumerate(ignoradas_c08_01[:15], 1):
            print(f"  {i:2d}. {linea}")

    # Buscar patrones de unidades en las líneas ignoradas
    print("\n\n=== ANÁLISIS DE PATRONES ===\n")

    # Buscar todas las posibles unidades en líneas ignoradas
    unidades_encontradas = set()
    patron_unidad = re.compile(r'\b(m[2-3]?|M[2-3]?|ml|Ml|ML|ud|Ud|UD|pa|Pa|PA|m\.|u\.|kg|Kg|KG|t|T|h|H)\b')

    for linea in ignoradas_sospechosas[:50]:
        matches = patron_unidad.findall(linea)
        unidades_encontradas.update(matches)

    if unidades_encontradas:
        print(f"Unidades encontradas en líneas ignoradas: {sorted(unidades_encontradas)}")

    # Mostrar ejemplos de códigos que empiezan las líneas ignoradas
    print("\nCódigos al inicio de líneas ignoradas (primeros 20):")
    patron_codigo = re.compile(r'^([A-Z0-9][A-Z0-9\.\s_]{0,15}?)\s+')
    codigos = set()

    for linea in ignoradas_sospechosas[:20]:
        match = patron_codigo.match(linea)
        if match:
            codigo = match.group(1).strip()
            if len(codigo) > 1:
                codigos.add(codigo)
                print(f"  - {codigo:20s} | {linea[:60]}...")

    return clasificaciones, ignoradas_sospechosas


if __name__ == "__main__":
    pdf_path = "data/uploads/20251124_101444_PROYECTO CALYPOFADO_extract.pdf"

    if not Path(pdf_path).exists():
        pdf_path = "ejemplo/PROYECTO CALYPOFADO_extract.pdf"

    if Path(pdf_path).exists():
        analizar_pdf(pdf_path)
    else:
        print("❌ No se encuentra el PDF")
