"""Lista todos los proyectos en la base de datos"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.models.db_models import Proyecto, DatabaseManager

db_manager = DatabaseManager('data/mediciones.db')
db = db_manager.session

proyectos = db.query(Proyecto).order_by(Proyecto.id.desc()).all()

print(f"\n📊 Total de proyectos: {len(proyectos)}\n")
print("="*80)

for p in proyectos:
    print(f"\nID: {p.id}")
    print(f"Nombre: {p.nombre[:100]}")
    print(f"Archivo: {p.archivo_origen}")
    print(f"Fecha: {p.fecha_creacion}")
    print("-"*80)

db_manager.cerrar()
