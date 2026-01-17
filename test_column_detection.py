#!/usr/bin/env python3
"""
Script de prueba para la detección de columnas en PDFs.
Útil para verificar que el sistema detecta y procesa correctamente layouts de múltiples columnas.
"""

import sys
from pathlib import Path

# Añadir src al path
src_path = Path(__file__).parent / 'src'
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from parser.pdf_extractor import PDFExtractor
from parser.column_detector import ColumnDetector
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)


def test_pdf(pdf_path: str, visualizar_lineas: int = 20):
    """
    Prueba la extracción de un PDF con detección de columnas

    Args:
        pdf_path: Ruta al PDF
        visualizar_lineas: Número de líneas a mostrar
    """
    print("=" * 80)
    print(f"TEST DE DETECCIÓN DE COLUMNAS")
    print("=" * 80)
    print(f"\nPDF: {pdf_path}\n")

    if not Path(pdf_path).exists():
        print(f"❌ Error: El archivo no existe: {pdf_path}")
        return

    # Extraer con detección de columnas
    print("🔍 Extrayendo con detección de columnas activada...")
    print("-" * 80)

    extractor = PDFExtractor(pdf_path, detect_columns=True)
    resultado = extractor.extraer_todo()

    # Mostrar información del PDF
    print(f"\n📄 Información del PDF:")
    print(f"   Archivo: {resultado['metadata']['archivo']}")
    print(f"   Páginas: {resultado['metadata']['num_paginas']}")
    print(f"   Líneas totales: {len(resultado['all_lines'])}")

    # Mostrar información de layout
    layout_summary = resultado.get('layout_summary', {})
    if layout_summary.get('paginas_multicolumna', 0) > 0:
        print(f"\n⚡ Layout de Múltiples Columnas:")
        print(f"   Páginas con múltiples columnas: {layout_summary['paginas_multicolumna']}")
        print(f"   Máximo de columnas detectadas: {layout_summary['total_columnas']}")
    else:
        print(f"\n📝 Layout: Columna simple (vertical tradicional)")

    # Detalles por página
    print(f"\n📑 Detalle por Página:")
    print("-" * 80)
    for page_data in resultado['pages']:
        layout = page_data.get('layout')
        if layout:
            print(f"   Página {page_data['num']}:")
            print(f"      • Tipo: {layout.get('tipo', 'N/A')}")
            print(f"      • Columnas: {layout.get('num_columnas', 1)}")
            print(f"      • Orientación: {layout.get('orientacion', 'N/A')}")

            # Detalles de columnas
            if layout.get('num_columnas', 0) > 1:
                for col in layout.get('columnas', []):
                    print(f"         - Columna {col['num']}: X=[{col['x_min']:.1f}, {col['x_max']:.1f}], Ancho={col['ancho']:.1f} pts")

    # Mostrar primeras líneas extraídas
    print(f"\n📝 Primeras {visualizar_lineas} líneas extraídas:")
    print("-" * 80)
    for i, linea in enumerate(resultado['all_lines'][:visualizar_lineas], 1):
        # Truncar líneas muy largas
        linea_display = linea if len(linea) <= 100 else linea[:97] + "..."
        print(f"{i:3d}. {linea_display}")

    if len(resultado['all_lines']) > visualizar_lineas:
        print(f"     ... y {len(resultado['all_lines']) - visualizar_lineas} líneas más")

    # Comparación con extracción sin detección de columnas
    print(f"\n🔄 Comparación: Sin detección de columnas")
    print("-" * 80)

    extractor_simple = PDFExtractor(pdf_path, detect_columns=False)
    resultado_simple = extractor_simple.extraer_todo()

    print(f"   Líneas extraídas (simple): {len(resultado_simple['all_lines'])}")
    print(f"   Líneas extraídas (columnas): {len(resultado['all_lines'])}")

    # Mostrar diferencia si hay
    if len(resultado['all_lines']) != len(resultado_simple['all_lines']):
        print(f"\n   ⚠️  Diferencia detectada: {abs(len(resultado['all_lines']) - len(resultado_simple['all_lines']))} líneas")

        print(f"\n   Primeras 10 líneas (modo simple):")
        for i, linea in enumerate(resultado_simple['all_lines'][:10], 1):
            linea_display = linea if len(linea) <= 80 else linea[:77] + "..."
            print(f"   {i:2d}. {linea_display}")

        print(f"\n   Primeras 10 líneas (con detección columnas):")
        for i, linea in enumerate(resultado['all_lines'][:10], 1):
            linea_display = linea if len(linea) <= 80 else linea[:77] + "..."
            print(f"   {i:2d}. {linea_display}")
    else:
        print("   ✓ Mismo número de líneas (probablemente PDF de columna simple)")

    print("\n" + "=" * 80)
    print("✓ Test completado")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description='Prueba la detección de columnas en PDFs de mediciones'
    )
    parser.add_argument(
        'pdf_path',
        help='Ruta al archivo PDF a analizar'
    )
    parser.add_argument(
        '-n', '--num-lines',
        type=int,
        default=20,
        help='Número de líneas a mostrar (default: 20)'
    )

    args = parser.parse_args()

    test_pdf(args.pdf_path, args.num_lines)
