"""
Debuggear el flujo del parser con logs detallados
"""
import sys
from pathlib import Path
import logging

sys.path.insert(0, str(Path(__file__).parent / 'src'))

# Configurar logging detallado
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)-8s | %(message)s'
)

from src.parser.partida_parser import PartidaParser

pdf_path = "data/uploads/20251124_111644_PE_PRE_R2_RAMPA_PORTAL.pdf"

print("=== PARSEANDO CON LOGS DETALLADOS ===\n")

parser = PartidaParser(pdf_path)

# Modificar temporalmente el parser para agregar logs
original_construir = parser._construir_estructura

def construir_con_logs(clasificaciones):
    capitulo_actual = None
    subcapitulo_actual = None
    apartado_actual = None
    partida_actual = None

    for idx, item in enumerate(clasificaciones):
        tipo = item['tipo']

        if 'CAPITULO' in tipo.value.upper():
            print(f"\n{idx:3d} | {tipo.value:20s} | {item['linea'][:60]}")
            capitulo_actual = item['datos']['codigo']
            subcapitulo_actual = None
            print(f"       → capitulo_actual = {capitulo_actual}")

        elif 'PARTIDA_HEADER' in tipo.value.upper():
            codigo = item['datos']['codigo']
            if codigo in ['01.01', '01.02', '01.04']:
                print(f"\n{idx:3d} | {tipo.value:20s} | {codigo}")
                print(f"       → capitulo_actual = {capitulo_actual}")
                print(f"       → subcapitulo_actual = {subcapitulo_actual}")
                print(f"       → partida_actual antes = {partida_actual is not None}")
            partida_actual = codigo

        elif 'PARTIDA_DATOS' in tipo.value.upper():
            if partida_actual in ['01.01', '01.02', '01.04']:
                print(f"{idx:3d} | {tipo.value:20s} | {item['datos']}")
                print(f"       → partida_actual = {partida_actual}")

    # Llamar al método original
    return original_construir(clasificaciones)

parser._construir_estructura = construir_con_logs

resultado = parser.parsear()

print(f"\n\n=== RESULTADO FINAL ===")
print(f"Partidas extraídas: {resultado['estadisticas']['partidas']}")
