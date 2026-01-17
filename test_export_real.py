"""Test de exportación con proyecto real"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from models.db_models import DatabaseManager
from exporters.excel_exporter import ExcelExporter
from exporters.csv_exporter import CSVExporter

# Inicializar DB
db = DatabaseManager()

# Obtener todos los proyectos
proyectos = db.listar_proyectos()

if not proyectos:
    print("❌ No hay proyectos en la base de datos")
    sys.exit(1)

print("="*80)
print("PROYECTOS DISPONIBLES:")
print("="*80)
for p in proyectos:
    print(f"  {p.id}: {p.nombre[:60]}...")

# Usar el primer proyecto
proyecto = proyectos[0]
print(f"\n{'='*80}")
print(f"EXPORTANDO PROYECTO: {proyecto.nombre[:60]}...")
print(f"{'='*80}")

# Obtener todas las partidas del proyecto
partidas_list = []

for capitulo in proyecto.capitulos:
    for subcapitulo in capitulo.subcapitulos:
        # Partidas directas del subcapítulo
        for partida in subcapitulo.partidas:
            partidas_list.append({
                'capitulo': capitulo.codigo,
                'subcapitulo': subcapitulo.codigo,
                'apartado': None,
                'codigo': partida.codigo,
                'unidad': partida.unidad,
                'resumen': partida.resumen,
                'descripcion': partida.descripcion or '',
                'cantidad': float(partida.cantidad) if partida.cantidad else 0.0,
                'precio': float(partida.precio) if partida.precio else 0.0,
                'importe': float(partida.importe) if partida.importe else 0.0
            })

        # Partidas de apartados
        for apartado in subcapitulo.apartados:
            for partida in apartado.partidas:
                partidas_list.append({
                    'capitulo': capitulo.codigo,
                    'subcapitulo': subcapitulo.codigo,
                    'apartado': apartado.codigo,
                    'codigo': partida.codigo,
                    'unidad': partida.unidad,
                    'resumen': partida.resumen,
                    'descripcion': partida.descripcion or '',
                    'cantidad': float(partida.cantidad) if partida.cantidad else 0.0,
                    'precio': float(partida.precio) if partida.precio else 0.0,
                    'importe': float(partida.importe) if partida.importe else 0.0
                })

print(f"\nTotal de partidas: {len(partidas_list)}")

if partidas_list:
    print("\n" + "="*80)
    print("EXPORTANDO...")
    print("="*80)

    # Exportar Excel
    excel_path = f"data/export_real_{proyecto.id}.xlsx"
    ExcelExporter.exportar(partidas_list, excel_path)
    print(f"✓ Excel: {excel_path}")

    # Exportar CSV
    csv_path = f"data/export_real_{proyecto.id}.csv"
    CSVExporter.exportar(partidas_list, csv_path)
    print(f"✓ CSV: {csv_path}")

    print("\n" + "="*80)
    print("PRIMERAS 3 PARTIDAS:")
    print("="*80)
    for i, p in enumerate(partidas_list[:3], 1):
        print(f"\n{i}. {p['codigo']} ({p['unidad']})")
        print(f"   Cap: {p['capitulo']} | Sub: {p['subcapitulo']}")
        print(f"   {p['resumen'][:50]}...")
        print(f"   Cantidad: {p['cantidad']} | Precio: {p['precio']} | Total: {p['importe']}")
else:
    print("❌ No hay partidas en este proyecto")

db.cerrar()
