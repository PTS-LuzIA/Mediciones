#!/usr/bin/env python3
"""
Script principal para procesamiento local de PDFs de mediciones.
Uso sin necesidad de la API.
"""

import sys
from pathlib import Path
import argparse

# Agregar src al path
sys.path.append(str(Path(__file__).parent / 'src'))

from parser.partida_parser import PartidaParser
from models.db_models import DatabaseManager
from exporters.csv_exporter import CSVExporter
from exporters.excel_exporter import ExcelExporter
from exporters.xml_exporter import XMLExporter
from exporters.bc3_exporter import BC3Exporter


def procesar_pdf(pdf_path: str, guardar_db: bool = True, exportar_formatos: list = None):
    """
    Procesa un PDF de mediciones

    Args:
        pdf_path: ruta al PDF
        guardar_db: guardar en base de datos SQLite
        exportar_formatos: lista de formatos a exportar ['csv', 'excel', 'xml', 'bc3']
    """
    print(f"\n{'='*80}")
    print(f"PROCESANDO: {pdf_path}")
    print(f"{'='*80}\n")

    # Parsear PDF
    parser = PartidaParser(pdf_path)
    resultado = parser.parsear()
    parser.imprimir_resumen()

    estructura = resultado['estructura']
    estadisticas = resultado['estadisticas']

    # Guardar en base de datos
    proyecto_id = None
    if guardar_db:
        print("\n[Base de Datos]")
        db = DatabaseManager()
        proyecto = db.guardar_estructura(estructura)
        total = db.calcular_totales(proyecto.id)
        proyecto_id = proyecto.id

        print(f"✓ Guardado en BD con ID: {proyecto_id}")
        print(f"✓ Presupuesto total: {total:,.2f} €")
        db.cerrar()

    # Exportar
    if exportar_formatos:
        print("\n[Exportando]")
        base_name = Path(pdf_path).stem
        partidas = parser.obtener_todas_partidas()

        for formato in exportar_formatos:
            output_path = f"data/exports/{base_name}.{formato}"

            if formato == 'csv':
                CSVExporter.exportar(partidas, output_path)
                print(f"✓ CSV: {output_path}")

            elif formato == 'excel':
                ExcelExporter.exportar_multihojas(estructura, output_path)
                print(f"✓ Excel: {output_path}")

            elif formato == 'xml':
                XMLExporter.exportar(estructura, output_path)
                print(f"✓ XML: {output_path}")

            elif formato == 'bc3':
                BC3Exporter.exportar(estructura, output_path)
                print(f"✓ BC3: {output_path}")

    print(f"\n{'='*80}")
    print("PROCESAMIENTO COMPLETADO")
    print(f"{'='*80}\n")

    return proyecto_id, estadisticas


def listar_proyectos():
    """Lista todos los proyectos en la base de datos"""
    db = DatabaseManager()
    proyectos = db.listar_proyectos()

    if not proyectos:
        print("\nNo hay proyectos en la base de datos.\n")
        return

    print(f"\n{'='*80}")
    print("PROYECTOS EN BASE DE DATOS")
    print(f"{'='*80}\n")

    for p in proyectos:
        print(f"ID: {p.id}")
        print(f"  Nombre: {p.nombre}")
        print(f"  Fecha: {p.fecha_creacion.strftime('%Y-%m-%d %H:%M') if p.fecha_creacion else 'N/A'}")
        print(f"  Presupuesto: {p.presupuesto_total:,.2f} €")
        print(f"  Capítulos: {len(p.capitulos)}")
        print("")

    db.cerrar()


def main():
    parser = argparse.ArgumentParser(
        description='Sistema de Mediciones - Procesamiento local de PDFs'
    )

    subparsers = parser.add_subparsers(dest='comando', help='Comandos disponibles')

    # Comando: procesar
    parser_procesar = subparsers.add_parser('procesar', help='Procesar un PDF')
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
    subparsers.add_parser('listar', help='Listar proyectos en BD')

    # Comando: ejemplo
    subparsers.add_parser('ejemplo', help='Procesar PDF de ejemplo')

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

    elif args.comando == 'ejemplo':
        pdf_ejemplo = 'ejemplo/PROYECTO CALYPOFADO_extract.pdf'
        if not Path(pdf_ejemplo).exists():
            print(f"Error: PDF de ejemplo no encontrado: {pdf_ejemplo}")
            sys.exit(1)

        procesar_pdf(
            pdf_ejemplo,
            guardar_db=True,
            exportar_formatos=['csv', 'excel', 'xml', 'bc3']
        )

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
