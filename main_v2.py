#!/usr/bin/env python3
"""
Sistema de Mediciones V2 - Multi-formato con detección automática
=================================================================

CARACTERÍSTICAS V2:
- Detecta automáticamente layout (1 o 2 columnas)
- Detecta automáticamente tipo de mediciones (con/sin tabla auxiliar)
- Almacena mediciones parciales completas
- Validación de sumas (parciales vs total)
- Exportadores mejorados con mediciones expandidas

DIFERENCIAS CON V1:
- V1: Optimizado para formato específico
- V2: Soporte multi-formato universal

USO:
    python main_v2.py procesar <pdf_path>
    python main_v2.py procesar <pdf_path> --exportar excel csv
    python main_v2.py listar
    python main_v2.py validar <proyecto_id>

"""

import sys
from pathlib import Path
import argparse
import logging

# Agregar src al path
sys.path.append(str(Path(__file__).parent / 'src'))

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def procesar_pdf(pdf_path: str, guardar_db: bool = True, exportar_formatos: list = None):
    """
    Procesa un PDF de mediciones con el Sistema V2

    Args:
        pdf_path: ruta al PDF
        guardar_db: guardar en base de datos PostgreSQL (mediciones_db)
        exportar_formatos: lista de formatos a exportar ['csv', 'excel', 'xml', 'bc3']
    """
    from parser_v2.partida_parser_v2 import PartidaParserV2
    from models_v2.db_manager_v2 import DatabaseManagerV2

    print(f"\n{'='*80}")
    print(f"SISTEMA V2 - PROCESANDO: {pdf_path}")
    print(f"{'='*80}\n")

    # Parsear PDF
    parser = PartidaParserV2(pdf_path)
    resultado = parser.parsear()

    # Imprimir resumen
    parser.imprimir_resumen(resultado['estructura'], resultado['estadisticas'])

    # Guardar en base de datos
    proyecto_id = None
    if guardar_db:
        print("[Base de Datos PostgreSQL]")
        with DatabaseManagerV2() as db:
            proyecto = db.guardar_estructura(
                resultado['estructura'],
                resultado['metadata'],
                pdf_path
            )
            proyecto_id = proyecto.id

            print(f"✓ Guardado en PostgreSQL con ID: {proyecto_id}")
            print(f"✓ Presupuesto total: {proyecto.presupuesto_total:,.2f} €\n")

    # TODO: Exportar formatos
    if exportar_formatos:
        print("[Exportando]")
        print("⚠️  Exportadores V2 en desarrollo\n")

    print(f"{'='*80}")
    print("PROCESAMIENTO COMPLETADO (V2)")
    print(f"{'='*80}\n")

    return proyecto_id, resultado['estadisticas']


def listar_proyectos():
    """Lista todos los proyectos en la base de datos V2"""
    from models_v2.db_manager_v2 import DatabaseManagerV2

    print(f"\n{'='*80}")
    print("PROYECTOS EN BASE DE DATOS V2 (PostgreSQL)")
    print(f"{'='*80}\n")

    with DatabaseManagerV2() as db:
        proyectos = db.listar_proyectos()

        if not proyectos:
            print("No hay proyectos en la base de datos V2.\n")
            return

        for p in proyectos:
            print(f"ID: {p.id}")
            print(f"  Nombre: {p.nombre}")
            print(f"  Fecha: {p.fecha_creacion.strftime('%Y-%m-%d %H:%M') if p.fecha_creacion else 'N/A'}")
            print(f"  Layout: {p.layout_detectado}")
            print(f"  Mediciones auxiliares: {'Sí' if p.tiene_mediciones_auxiliares else 'No'}")
            print(f"  Presupuesto: {p.presupuesto_total:,.2f} €")
            print(f"  Capítulos: {len(p.capitulos)}")
            print("")


def validar_proyecto(proyecto_id: int):
    """
    Valida mediciones parciales de un proyecto

    Args:
        proyecto_id: ID del proyecto a validar
    """
    from models_v2.db_manager_v2 import DatabaseManagerV2

    print(f"\n{'='*80}")
    print(f"VALIDACIÓN DE MEDICIONES - PROYECTO {proyecto_id}")
    print(f"{'='*80}\n")

    with DatabaseManagerV2() as db:
        resultado = db.validar_mediciones_proyecto(proyecto_id)

        if 'error' in resultado:
            print(f"Error: {resultado['error']}\n")
            return

        print(f"Total partidas: {resultado['total_partidas']}")
        print(f"Partidas con mediciones auxiliares: {resultado['partidas_con_mediciones']}")
        print(f"Partidas válidas: {resultado['partidas_validas']}")
        print(f"Partidas inválidas: {resultado['partidas_invalidas']}\n")

        if resultado['partidas_invalidas'] > 0:
            print("⚠️  PARTIDAS CON ERRORES:")
            print("="*80)
            for p in resultado['detalles_invalidas']:
                print(f"\nCódigo: {p['codigo']}")
                print(f"  Cantidad total: {p['cantidad_total']:.2f}")
                print(f"  Suma parciales: {p['suma_parciales']:.2f}")
                print(f"  Diferencia: {p['diferencia']:.2f}")
        else:
            print("✓ Todas las mediciones son válidas\n")


def main():
    parser = argparse.ArgumentParser(
        description='Sistema de Mediciones V2 - Multi-formato con auto-detección',
        epilog='Sistema V2: Soporta 1/2 columnas + con/sin mediciones auxiliares'
    )

    subparsers = parser.add_subparsers(dest='comando', help='Comandos disponibles')

    # Comando: procesar
    parser_procesar = subparsers.add_parser('procesar', help='Procesar un PDF (V2)')
    parser_procesar.add_argument('pdf', help='Ruta al archivo PDF')
    parser_procesar.add_argument(
        '--no-db',
        action='store_true',
        help='No guardar en base de datos'
    )
    parser_procesar.add_argument(
        '--exportar',
        nargs='+',
        choices=['csv', 'excel', 'xml', 'bc3'],
        help='Formatos a exportar'
    )

    # Comando: listar
    subparsers.add_parser('listar', help='Listar proyectos en BD V2')

    # Comando: validar
    parser_validar = subparsers.add_parser('validar', help='Validar mediciones de un proyecto')
    parser_validar.add_argument('proyecto_id', type=int, help='ID del proyecto a validar')

    args = parser.parse_args()

    if args.comando == 'procesar':
        if not Path(args.pdf).exists():
            print(f"Error: Archivo no encontrado: {args.pdf}")
            sys.exit(1)

        procesar_pdf(
            args.pdf,
            guardar_db=not args.no_db,
            exportar_formatos=args.exportar
        )

    elif args.comando == 'listar':
        listar_proyectos()

    elif args.comando == 'validar':
        validar_proyecto(args.proyecto_id)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
