#!/usr/bin/env python3
"""
Script para probar que el endpoint revisar-elemento usa el ID correcto
"""
import sys
sys.path.insert(0, 'src')

from models.hybrid_db_manager import HybridDatabaseManager
from models.hybrid_models import HybridSubcapitulo

# Conectar a BD
db = HybridDatabaseManager()

# Obtener el proyecto 4
proyecto = db.obtener_proyecto(4)

if not proyecto:
    print("❌ No se encontró el proyecto 4")
    sys.exit(1)

print(f"📋 Proyecto: {proyecto.nombre}\n")

# Listar todos los subcapítulos con su ID
print("SUBCAPÍTULOS DEL PROYECTO 4:")
print("=" * 80)

for cap in proyecto.capitulos:
    print(f"\nCapítulo {cap.codigo} - {cap.nombre} (ID: {cap.id})")
    for sub in cap.subcapitulos:
        if not sub.parent_id:  # Solo nivel 1
            print(f"  └─ Subcapítulo {sub.codigo} - {sub.nombre}")
            print(f"     ID: {sub.id}")
            print(f"     Estado: {sub.estado_validacion.value}")
            print(f"     Total IA: {sub.total_ia:.2f} €")
            print(f"     Total Local: {sub.total_local:.2f} €")

            # Simular lo que haría el endpoint
            print(f"     📤 Si haces click en 'Revisar con IA':")
            print(f"        URL: /hybrid-revisar-elemento/{proyecto.id}?elemento_tipo=subcapitulo&elemento_id={sub.id}")
            print(f"        Se buscaría: Subcapitulo.id == {sub.id}")

            # Verificar que se obtendría el correcto
            test_elemento = db.session.query(HybridSubcapitulo).filter_by(id=sub.id).first()
            if test_elemento:
                print(f"        ✓ Se obtendría: {test_elemento.codigo} - {test_elemento.nombre}")
                print(f"        ✓ Se enviaría al LLM: capitulo={cap.codigo}, subcapitulos_filtrados=['{test_elemento.codigo}']")
            else:
                print(f"        ❌ ERROR: No se encuentra subcapítulo con ID {sub.id}")

            print()
