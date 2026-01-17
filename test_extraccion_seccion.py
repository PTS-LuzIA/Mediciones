#!/usr/bin/env python3
"""
Script de prueba para verificar la extracción de sección específica del PDF
usando LineClassifier y el método extraer_texto_seccion del PartidaExtractionAgent
"""

import sys
from pathlib import Path
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)
logger = logging.getLogger(__name__)

# Añadir src al path
src_dir = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_dir))

from parser.pdf_extractor import PDFExtractor
from parser.line_classifier import LineClassifier, TipoLinea


def test_extraccion_seccion(pdf_path: str, capitulo_codigo: str, subcapitulos_filtrados: list = None):
    """
    Prueba la extracción de una sección específica del PDF

    Args:
        pdf_path: Ruta al PDF
        capitulo_codigo: Código del capítulo (ej: '01')
        subcapitulos_filtrados: Lista de códigos de subcapítulos (ej: ['01.01'])
    """
    print("=" * 80)
    print(f"TEST: Extracción de sección del PDF")
    print("=" * 80)
    print(f"PDF: {pdf_path}")
    print(f"Capítulo: {capitulo_codigo}")
    print(f"Subcapítulos filtrados: {subcapitulos_filtrados}")
    print("=" * 80)
    print()

    # 1. Extraer todas las líneas del PDF
    print("📄 PASO 1: Extrayendo líneas del PDF...")
    extractor = PDFExtractor(pdf_path)
    datos = extractor.extraer_todo()
    lineas = datos['all_lines']
    print(f"   ✓ Extraídas {len(lineas)} líneas")
    print()

    # 2. Clasificar líneas
    print("🏷️  PASO 2: Clasificando líneas...")
    clasificaciones = LineClassifier.clasificar_bloque(lineas)
    print(f"   ✓ Clasificadas {len(clasificaciones)} líneas")
    print()

    # 3. Analizar clasificaciones (primeras 500 líneas para debug)
    print("🔍 PASO 3: Analizando clasificaciones...")
    capitulos_encontrados = []
    subcapitulos_encontrados = []
    apartados_encontrados = []

    for i, clasificacion in enumerate(clasificaciones[:500]):
        tipo = clasificacion['tipo'].value if hasattr(clasificacion['tipo'], 'value') else clasificacion['tipo']
        datos = clasificacion.get('datos', {})
        codigo = datos.get('codigo', '') if datos else ''

        if tipo == 'capitulo' and codigo:
            capitulos_encontrados.append(codigo)
        elif tipo == 'subcapitulo' and codigo:
            subcapitulos_encontrados.append(codigo)
        elif tipo == 'apartado' and codigo:
            apartados_encontrados.append(codigo)

    print(f"   📋 Capítulos encontrados (primeros 500 líneas): {capitulos_encontrados[:15]}")
    print(f"   📋 Subcapítulos encontrados (primeros 500 líneas): {subcapitulos_encontrados[:15]}")
    print(f"   📋 Apartados encontrados (primeros 500 líneas): {apartados_encontrados[:15]}")
    print()

    # 4. Filtrar sección específica (replicando lógica de partida_extraction_agent.py)
    print(f"🎯 PASO 4: Filtrando sección: Capítulo {capitulo_codigo}, Subcaps {subcapitulos_filtrados}...")
    lineas_seccion = []
    dentro_capitulo = False
    dentro_subcapitulo_correcto = False

    for i, clasificacion in enumerate(clasificaciones):
        tipo = clasificacion['tipo'].value if hasattr(clasificacion['tipo'], 'value') else clasificacion['tipo']
        datos = clasificacion.get('datos', {})
        codigo = datos.get('codigo', '') if datos else ''
        linea = clasificacion.get('linea', '')

        # Detectar inicio del capítulo
        if tipo == 'capitulo' and codigo == capitulo_codigo:
            dentro_capitulo = True
            lineas_seccion.append(linea)
            print(f"   ✓ Encontrado inicio capítulo {codigo} (línea {i})")
            continue

        # Detectar fin del capítulo (siguiente capítulo)
        if dentro_capitulo and tipo == 'capitulo' and codigo != capitulo_codigo:
            print(f"   ⏹️  Fin capítulo (encontrado siguiente: {codigo}, línea {i})")
            break

        # Si estamos dentro del capítulo
        if dentro_capitulo:
            # Si hay filtro de subcapítulos específicos
            if subcapitulos_filtrados:
                # Detectar inicio de subcapítulo/apartado filtrado
                if (tipo in ['subcapitulo', 'apartado']) and codigo in subcapitulos_filtrados:
                    dentro_subcapitulo_correcto = True
                    lineas_seccion.append(linea)
                    print(f"   ✓ Encontrado inicio {tipo} {codigo} (línea {i})")
                    continue
                elif tipo in ['subcapitulo', 'apartado'] and codigo:
                    # Mostrar subcapítulos que no coinciden (primeros 5)
                    if len([x for x in [codigo] if x not in subcapitulos_filtrados]) <= 5:
                        print(f"   ⊘ {tipo.capitalize()} encontrado pero no coincide: '{codigo}' (línea {i})")

                # Detectar fin de subcapítulo/apartado filtrado
                if dentro_subcapitulo_correcto and tipo in ['subcapitulo', 'apartado'] and codigo not in subcapitulos_filtrados:
                    nivel_actual = len(subcapitulos_filtrados[0].split('.'))
                    nivel_nuevo = len(codigo.split('.'))
                    if nivel_nuevo <= nivel_actual:
                        dentro_subcapitulo_correcto = False
                        print(f"   ⏹️  Fin subcapítulo (encontrado siguiente: {codigo}, línea {i})")
                        continue

                # Capturar solo si estamos en subcapítulo correcto
                if dentro_subcapitulo_correcto:
                    lineas_seccion.append(linea)
            else:
                # Sin filtro: capturar todo el capítulo
                lineas_seccion.append(linea)

    print()
    print("=" * 80)
    print("📊 RESULTADOS:")
    print("=" * 80)
    print(f"Líneas extraídas de la sección: {len(lineas_seccion)}")

    if lineas_seccion:
        texto_seccion = ' '.join(lineas_seccion)
        num_chars = len(texto_seccion)
        estimated_tokens = int(num_chars * 0.37)

        print(f"Caracteres: {num_chars:,}")
        print(f"Tokens estimados: {estimated_tokens:,}")
        print()
        print("📝 PRIMERAS 20 LÍNEAS DE LA SECCIÓN:")
        print("-" * 80)
        for i, linea in enumerate(lineas_seccion[:20], 1):
            linea_corta = linea[:100] + "..." if len(linea) > 100 else linea
            print(f"{i:3d}. {linea_corta}")

        if len(lineas_seccion) > 20:
            print(f"\n... ({len(lineas_seccion) - 20} líneas más)")

        print()
        print("📝 ÚLTIMAS 10 LÍNEAS DE LA SECCIÓN:")
        print("-" * 80)
        for i, linea in enumerate(lineas_seccion[-10:], len(lineas_seccion) - 9):
            linea_corta = linea[:100] + "..." if len(linea) > 100 else linea
            print(f"{i:3d}. {linea_corta}")

        return True
    else:
        print("❌ ERROR: No se extrajo ninguna línea de la sección")
        print()
        print("DIAGNÓSTICO:")
        print(f"  - ¿Se encontró el capítulo {capitulo_codigo}? {'SÍ' if dentro_capitulo else 'NO'}")
        if subcapitulos_filtrados:
            print(f"  - ¿Se encontró algún subcapítulo de {subcapitulos_filtrados}? {'SÍ' if dentro_subcapitulo_correcto else 'NO'}")
        print()
        print("SUGERENCIAS:")
        print("  1. Verifica que el código del capítulo/subcapítulo sea correcto")
        print("  2. Revisa los códigos encontrados en el PASO 3")
        print("  3. Comprueba que el PDF contiene la sección solicitada")

        return False


if __name__ == "__main__":
    # Buscar el PDF más reciente en la carpeta data/uploads
    from pathlib import Path
    import os

    uploads_dir = Path(__file__).parent / 'data' / 'uploads'

    if uploads_dir.exists():
        pdf_files = list(uploads_dir.glob('*.pdf'))
        if pdf_files:
            # Obtener el PDF más reciente
            pdf_path = max(pdf_files, key=os.path.getmtime)
            print(f"\n🔍 PDF encontrado: {pdf_path.name}\n")

            # TEST 1: Capítulo 01 completo
            print("\n" + "="*80)
            print("TEST 1: Extrayendo CAPÍTULO 01 completo")
            print("="*80)
            test_extraccion_seccion(
                pdf_path=str(pdf_path),
                capitulo_codigo='01',
                subcapitulos_filtrados=None
            )

            print("\n\n")

            # TEST 2: Solo subcapítulo 01.01
            print("\n" + "="*80)
            print("TEST 2: Extrayendo solo SUBCAPÍTULO 01.01")
            print("="*80)
            test_extraccion_seccion(
                pdf_path=str(pdf_path),
                capitulo_codigo='01',
                subcapitulos_filtrados=['01.01']
            )

            print("\n\n")

            # TEST 3: Solo subcapítulo 01.02
            print("\n" + "="*80)
            print("TEST 3: Extrayendo solo SUBCAPÍTULO 01.02")
            print("="*80)
            test_extraccion_seccion(
                pdf_path=str(pdf_path),
                capitulo_codigo='01',
                subcapitulos_filtrados=['01.02']
            )

        else:
            print("❌ No se encontraron archivos PDF en data/uploads/")
    else:
        print("❌ No existe la carpeta data/uploads/")
