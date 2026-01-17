#!/usr/bin/env python3
"""
Script de depuración para verificar discrepancias en capítulo 01.01
"""
import sys
sys.path.insert(0, 'src')

from models.hybrid_db_manager import HybridDatabaseManager
from models.hybrid_models import HybridCapitulo, HybridSubcapitulo

# Conectar a BD
db = HybridDatabaseManager()

# Obtener el proyecto 4 específicamente
proyecto = db.obtener_proyecto(4)

if not proyecto:
    print("❌ No se encontró el proyecto 4")
    sys.exit(1)
print(f"📋 Proyecto: {proyecto.nombre}")
print(f"   ID: {proyecto.id}")
print()

# Buscar capítulo 01.01
capitulo_01 = None
subcap_01_01 = None

for cap in proyecto.capitulos:
    print(f"🔍 Capítulo: {cap.codigo} - {cap.nombre}")
    print(f"   Total IA: {cap.total_ia:.2f} €")
    print(f"   Total Local: {cap.total_local:.2f} €")
    print(f"   Diferencia: {abs(cap.total_ia - cap.total_local):.4f} €")
    print(f"   Estado: {cap.estado_validacion.value}")
    print(f"   Necesita revisión: {cap.necesita_revision_ia}")
    print()

    if cap.codigo == "01":
        capitulo_01 = cap

    for sub in cap.subcapitulos:
        if not sub.parent_id:  # Solo nivel 1
            print(f"  └─ Subcapítulo: {sub.codigo} - {sub.nombre}")
            print(f"     Total IA: {sub.total_ia:.2f} €")
            print(f"     Total Local: {sub.total_local:.2f} €")
            print(f"     Diferencia: {abs(sub.total_ia - sub.total_local):.4f} €")
            print(f"     Diferencia % almacenada: {sub.diferencia_porcentaje}")
            print(f"     Diferencia € almacenada: {sub.diferencia_euros}")
            print(f"     Estado: {sub.estado_validacion.value}")
            print(f"     Necesita revisión: {sub.necesita_revision_ia}")
            print(f"     Num partidas IA: {sub.num_partidas_ia}")
            print(f"     Num partidas Local: {sub.num_partidas_local}")
            print(f"     Tiene partidas directas: {len(sub.partidas)}")
            print(f"     Tiene apartados: {len(sub.apartados)}")
            print(f"     Tiene hijos: {len(sub.subcapitulos_hijos)}")

            if sub.codigo == "01.01":
                subcap_01_01 = sub

                # Verificar partidas
                print(f"\n     🔍 PARTIDAS DEL SUBCAPÍTULO 01.01:")
                total_manual = 0.0
                for partida in sub.partidas:
                    print(f"        - {partida.codigo}: {partida.importe:.2f} €")
                    total_manual += partida.importe

                print(f"\n     📊 TOTAL MANUAL (suma partidas): {total_manual:.2f} €")
                print(f"     📊 TOTAL LOCAL (BD): {sub.total_local:.2f} €")
                print(f"     📊 TOTAL IA (BD): {sub.total_ia:.2f} €")
                print(f"     📊 Diferencia manual vs IA: {abs(total_manual - sub.total_ia):.4f} €")
                print(f"     📊 Diferencia local vs IA: {abs(sub.total_local - sub.total_ia):.4f} €")

            print()

print("\n" + "="*80)
print("RESUMEN DEL PROBLEMA")
print("="*80)

if subcap_01_01:
    diff = abs(subcap_01_01.total_ia - subcap_01_01.total_local)
    print(f"Subcapítulo 01.01:")
    print(f"  Total IA: {subcap_01_01.total_ia:.10f} €")
    print(f"  Total Local: {subcap_01_01.total_local:.10f} €")
    print(f"  Diferencia absoluta: {diff:.10f} €")
    print(f"  ¿Diferencia < 0.01€?: {diff < 0.01}")
    print(f"  Estado actual: {subcap_01_01.estado_validacion.value}")
    print(f"  ¿Debería estar VALIDADO?: {diff < 0.01}")

    if diff < 0.01 and subcap_01_01.estado_validacion.value == "discrepancia":
        print("\n⚠️  PROBLEMA DETECTADO:")
        print("    La diferencia es < 0.01€ pero el estado es DISCREPANCIA")
        print("    Esto indica que el método _validar_elemento() no se ejecutó")
        print("    correctamente o los totales se recalcularon DESPUÉS de la validación.")
else:
    print("❌ No se encontró el subcapítulo 01.01")
