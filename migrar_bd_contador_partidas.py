#!/usr/bin/env python3
"""
Script de migración para agregar campos num_partidas_ia y num_partidas_local
a la base de datos híbrida existente.

Este script:
1. Hace backup de la BD actual
2. Agrega las nuevas columnas a las tablas existentes
3. Inicializa los valores en 0

Autor: Claude Code
Fecha: 2026-01-13
"""

import sqlite3
import shutil
import os
from datetime import datetime

# Rutas
DB_PATH = 'data/mediciones.db'
BACKUP_PATH = f'data/mediciones_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'


def hacer_backup():
    """Crea un backup de la base de datos"""
    if not os.path.exists(DB_PATH):
        print(f"❌ No se encontró la base de datos en {DB_PATH}")
        print("   No hay nada que migrar. La BD se creará automáticamente con las nuevas columnas.")
        return False

    print(f"📦 Creando backup en {BACKUP_PATH}...")
    shutil.copy2(DB_PATH, BACKUP_PATH)
    print(f"✓ Backup creado exitosamente")
    return True


def agregar_columnas():
    """Agrega las nuevas columnas a las tablas existentes"""
    if not os.path.exists(DB_PATH):
        print("ℹ️  No hay BD existente, se creará automáticamente con las nuevas columnas")
        return True

    print(f"\n🔧 Agregando nuevas columnas a {DB_PATH}...")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Verificar si las columnas ya existen
        cursor.execute("PRAGMA table_info(hybrid_capitulos)")
        columnas_capitulos = [col[1] for col in cursor.fetchall()]

        # Agregar columnas a hybrid_capitulos si no existen
        if 'num_partidas_ia' not in columnas_capitulos:
            print("  • Agregando num_partidas_ia a hybrid_capitulos...")
            cursor.execute("""
                ALTER TABLE hybrid_capitulos
                ADD COLUMN num_partidas_ia INTEGER DEFAULT 0
            """)
            print("    ✓ num_partidas_ia agregado")
        else:
            print("  ℹ️  num_partidas_ia ya existe en hybrid_capitulos")

        if 'num_partidas_local' not in columnas_capitulos:
            print("  • Agregando num_partidas_local a hybrid_capitulos...")
            cursor.execute("""
                ALTER TABLE hybrid_capitulos
                ADD COLUMN num_partidas_local INTEGER DEFAULT 0
            """)
            print("    ✓ num_partidas_local agregado")
        else:
            print("  ℹ️  num_partidas_local ya existe en hybrid_capitulos")

        # Verificar si las columnas ya existen en subcapitulos
        cursor.execute("PRAGMA table_info(hybrid_subcapitulos)")
        columnas_subcapitulos = [col[1] for col in cursor.fetchall()]

        # Agregar columnas a hybrid_subcapitulos si no existen
        if 'num_partidas_ia' not in columnas_subcapitulos:
            print("  • Agregando num_partidas_ia a hybrid_subcapitulos...")
            cursor.execute("""
                ALTER TABLE hybrid_subcapitulos
                ADD COLUMN num_partidas_ia INTEGER DEFAULT 0
            """)
            print("    ✓ num_partidas_ia agregado")
        else:
            print("  ℹ️  num_partidas_ia ya existe en hybrid_subcapitulos")

        if 'num_partidas_local' not in columnas_subcapitulos:
            print("  • Agregando num_partidas_local a hybrid_subcapitulos...")
            cursor.execute("""
                ALTER TABLE hybrid_subcapitulos
                ADD COLUMN num_partidas_local INTEGER DEFAULT 0
            """)
            print("    ✓ num_partidas_local agregado")
        else:
            print("  ℹ️  num_partidas_local ya existe en hybrid_subcapitulos")

        conn.commit()
        print("\n✅ Migración completada exitosamente")
        return True

    except sqlite3.Error as e:
        print(f"\n❌ Error durante la migración: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def mostrar_estadisticas():
    """Muestra estadísticas de la base de datos migrada"""
    if not os.path.exists(DB_PATH):
        return

    print(f"\n📊 Estadísticas de la BD migrada:")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Proyectos híbridos
        cursor.execute("SELECT COUNT(*) FROM hybrid_proyectos")
        num_proyectos = cursor.fetchone()[0]
        print(f"  • Proyectos híbridos: {num_proyectos}")

        # Capítulos
        cursor.execute("SELECT COUNT(*) FROM hybrid_capitulos")
        num_capitulos = cursor.fetchone()[0]
        print(f"  • Capítulos: {num_capitulos}")

        # Subcapítulos
        cursor.execute("SELECT COUNT(*) FROM hybrid_subcapitulos")
        num_subcapitulos = cursor.fetchone()[0]
        print(f"  • Subcapítulos: {num_subcapitulos}")

        # Partidas
        cursor.execute("SELECT COUNT(*) FROM hybrid_partidas")
        num_partidas = cursor.fetchone()[0]
        print(f"  • Partidas: {num_partidas}")

        print("\n💡 Nota:")
        print("  - Los proyectos existentes tendrán num_partidas_ia = 0 (por defecto)")
        print("  - Solo los nuevos proyectos procesados tendrán el conteo de la IA")
        print("  - Para actualizar proyectos existentes, re-procésalos desde cero")

    except sqlite3.Error as e:
        print(f"  ❌ Error obteniendo estadísticas: {e}")
    finally:
        conn.close()


def main():
    print("="*70)
    print("MIGRACIÓN DE BASE DE DATOS - CONTADOR DE PARTIDAS")
    print("="*70)
    print()

    # 1. Hacer backup
    tiene_bd = hacer_backup()

    if not tiene_bd:
        print("\n✅ No hay nada que migrar. La BD se creará automáticamente.")
        return

    # 2. Agregar columnas
    if agregar_columnas():
        # 3. Mostrar estadísticas
        mostrar_estadisticas()

        print("\n" + "="*70)
        print("✅ MIGRACIÓN COMPLETADA EXITOSAMENTE")
        print("="*70)
        print(f"\n📁 Backup guardado en: {BACKUP_PATH}")
        print("💾 Base de datos actualizada en: data/mediciones.db")
        print("\n🚀 Ya puedes iniciar el servidor y usar el sistema híbrido mejorado")
    else:
        print("\n" + "="*70)
        print("❌ MIGRACIÓN FALLIDA")
        print("="*70)
        print(f"\n📁 Tu backup está en: {BACKUP_PATH}")
        print("💡 Puedes restaurarlo manualmente si es necesario:")
        print(f"   cp {BACKUP_PATH} {DB_PATH}")


if __name__ == "__main__":
    main()
