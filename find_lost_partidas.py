"""
Encontrar las 11 partidas que se detectan pero no se guardan en la estructura
"""
import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.parser.pdf_extractor import PDFExtractor
from src.parser.line_classifier import LineClassifier, TipoLinea

pdf_path = "data/uploads/20251124_101444_PROYECTO CALYPOFADO_extract.pdf"
if not Path(pdf_path).exists():
    pdf_path = "ejemplo/PROYECTO CALYPOFADO_extract.pdf"

print("=== RASTREANDO PARTIDAS PERDIDAS ===\n")

# Extraer y clasificar
extractor = PDFExtractor(pdf_path)
datos = extractor.extraer_todo()
lineas = datos['all_lines']

clasificaciones = LineClassifier.clasificar_bloque(lineas)

# Contar PARTIDA_HEADER
headers_count = sum(1 for c in clasificaciones if c['tipo'] == TipoLinea.PARTIDA_HEADER)
datos_count = sum(1 for c in clasificaciones if c['tipo'] == TipoLinea.PARTIDA_DATOS)

print(f"PARTIDA_HEADER detectados: {headers_count}")
print(f"PARTIDA_DATOS detectados: {datos_count}")

# Agrupar partidas con el método de LineClassifier
partidas_agrupadas = LineClassifier.agrupar_partidas(clasificaciones)
print(f"Partidas AGRUPADAS: {len(partidas_agrupadas)}\n")

# Verificar cuántas tienen datos completos
partidas_con_datos = [p for p in partidas_agrupadas if p.get('importe_str')]
partidas_sin_datos = [p for p in partidas_agrupadas if not p.get('importe_str')]

print(f"Partidas con datos completos (importe_str): {len(partidas_con_datos)}")
print(f"Partidas SIN datos completos: {len(partidas_sin_datos)}\n")

if partidas_sin_datos:
    print("=== PARTIDAS SIN DATOS ===\n")
    for i, p in enumerate(partidas_sin_datos[:15], 1):
        print(f"{i:2d}. {p['codigo']:15s} | {p['resumen'][:60]}")

# Ahora parsear con PartidaParser y ver qué pasa
print("\n\n=== PARSEANDO CON PartidaParser ===\n")

from src.parser.partida_parser import PartidaParser

parser = PartidaParser(pdf_path)
resultado = parser.parsear()

print(f"Partidas en estructura final: {resultado['estadisticas']['partidas']}")

# Listar todas las partidas de la estructura
todas_partidas = parser.obtener_todas_partidas()
print(f"Partidas en método obtener_todas_partidas(): {len(todas_partidas)}")

# Ahora comparar: qué partidas de partidas_agrupadas NO están en todas_partidas
codigos_guardados = {p['codigo'] for p in todas_partidas}
codigos_detectados = {p['codigo'] for p in partidas_con_datos}

codigos_perdidos = codigos_detectados - codigos_guardados

print(f"\nCódigos perdidos: {len(codigos_perdidos)}")

if codigos_perdidos:
    print("\n=== PARTIDAS PERDIDAS ===\n")
    for codigo in sorted(codigos_perdidos):
        partida = next((p for p in partidas_con_datos if p['codigo'] == codigo), None)
        if partida:
            print(f"❌ {codigo:15s} | {partida.get('unidad', 'N/A'):5s} | {partida['resumen'][:50]}")

    # Buscar en qué contexto aparecen estas partidas
    print("\n\n=== CONTEXTO DE PARTIDAS PERDIDAS ===\n")

    en_capitulo = None
    en_subcapitulo = None
    en_apartado = None

    for item in clasificaciones:
        tipo = item['tipo']
        linea = item['linea']

        if tipo == TipoLinea.CAPITULO:
            en_capitulo = item['datos']['codigo']
            en_subcapitulo = None
            en_apartado = None

        elif tipo == TipoLinea.SUBCAPITULO:
            en_subcapitulo = item['datos']['codigo']
            en_apartado = None

        elif tipo == TipoLinea.APARTADO:
            en_apartado = item['datos']['codigo']

        elif tipo == TipoLinea.PARTIDA_HEADER:
            codigo = item['datos']['codigo']
            if codigo in codigos_perdidos:
                print(f"\nPartida perdida: {codigo}")
                print(f"  Capítulo: {en_capitulo}")
                print(f"  Subcapítulo: {en_subcapitulo}")
                print(f"  Apartado: {en_apartado}")
                print(f"  Línea: {linea[:70]}")

                # Mostrar líneas alrededor
                idx = next((i for i, c in enumerate(clasificaciones) if c['linea'] == linea), None)
                if idx:
                    print(f"\n  Líneas anteriores:")
                    for i in range(max(0, idx-3), idx):
                        print(f"    {clasificaciones[i]['tipo'].value:20s} | {clasificaciones[i]['linea'][:60]}")
