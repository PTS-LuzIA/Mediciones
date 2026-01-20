#!/usr/bin/env python3
"""
Test del sistema de guardado progresivo por fases
==================================================

Verifica que cada fase guarda correctamente en BD
"""

import sys
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from models_v2.db_manager_v2 import DatabaseManagerV2


def test_fases_progresivas():
    """Test del guardado progresivo"""

    print("\n" + "="*60)
    print("TEST: Guardado Progresivo por Fases")
    print("="*60)

    with DatabaseManagerV2() as db:
        # Obtener el último proyecto
        proyectos = db.listar_proyectos()

        if not proyectos:
            print("❌ No hay proyectos en BD para testear")
            return

        proyecto = proyectos[0]

        print(f"\n📁 Proyecto: {proyecto.nombre}")
        print(f"   ID: {proyecto.id}")
        print(f"   Layout: {proyecto.layout_detectado}")
        print(f"   Total: {proyecto.presupuesto_total:,.2f} €")

        # Contar elementos
        num_capitulos = len(proyecto.capitulos)
        num_subcapitulos = sum(len(cap.subcapitulos) for cap in proyecto.capitulos)
        num_partidas = sum(
            len(sub.partidas)
            for cap in proyecto.capitulos
            for sub in cap.subcapitulos
        )

        print(f"\n📊 Estructura:")
        print(f"   - Capítulos: {num_capitulos}")
        print(f"   - Subcapítulos: {num_subcapitulos}")
        print(f"   - Partidas: {num_partidas}")

        # Verificar datos de cada capítulo
        print(f"\n📂 Detalle de capítulos:")
        for cap in proyecto.capitulos:
            print(f"   CAP {cap.codigo}: {cap.nombre[:50]}")
            print(f"      Total: {cap.total:,.2f} €")
            print(f"      Subcapítulos: {len(cap.subcapitulos)}")

            # Contar partidas del capítulo
            partidas_cap = sum(len(sub.partidas) for sub in cap.subcapitulos)
            print(f"      Partidas: {partidas_cap}")

        # Verificar que los datos están completos
        print(f"\n✅ Verificación:")

        if num_capitulos > 0:
            print(f"   ✓ Fase 1: Capítulos guardados ({num_capitulos})")
        else:
            print(f"   ✗ Fase 1: No hay capítulos")

        if num_subcapitulos > 0:
            print(f"   ✓ Fase 1: Subcapítulos guardados ({num_subcapitulos})")
        else:
            print(f"   ✗ Fase 1: No hay subcapítulos")

        if num_partidas > 0:
            print(f"   ✓ Fase 2: Partidas guardadas ({num_partidas})")
        else:
            print(f"   ✗ Fase 2: No hay partidas")

        if proyecto.presupuesto_total > 0:
            print(f"   ✓ Fase 3: Total calculado ({proyecto.presupuesto_total:,.2f} €)")
        else:
            print(f"   ⚠ Fase 3: Total es 0")

        print("\n" + "="*60)


if __name__ == "__main__":
    test_fases_progresivas()
