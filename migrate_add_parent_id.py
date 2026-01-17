"""
Script de migración para agregar el campo parent_id a ai_subcapitulos.

Este script agrega la columna parent_id a la tabla ai_subcapitulos
para soportar jerarquías recursivas de subcapítulos.

Uso:
    python migrate_add_parent_id.py
"""

import sqlite3
import os
from pathlib import Path

DB_PATH = "data/mediciones.db"


def migrate_database():
    """Agrega la columna parent_id a ai_subcapitulos si no existe"""

    if not os.path.exists(DB_PATH):
        print(f"⚠️  Base de datos no encontrada en {DB_PATH}")
        print("   No se requiere migración (se creará con la nueva estructura)")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Verificar si la columna ya existe
        cursor.execute("PRAGMA table_info(ai_subcapitulos)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'parent_id' in columns:
            print("✓ La columna parent_id ya existe en ai_subcapitulos")
            print("  No se requiere migración")
            return

        print("📋 Iniciando migración de base de datos...")
        print("   Agregando columna parent_id a ai_subcapitulos...")

        # Agregar la columna parent_id
        cursor.execute("""
            ALTER TABLE ai_subcapitulos
            ADD COLUMN parent_id INTEGER
            REFERENCES ai_subcapitulos(id)
        """)

        conn.commit()
        print("✓ Migración completada exitosamente")
        print("  Columna parent_id agregada a ai_subcapitulos")

        # Mostrar estadísticas
        cursor.execute("SELECT COUNT(*) FROM ai_subcapitulos")
        count = cursor.fetchone()[0]
        print(f"  Total de subcapítulos en la BD: {count}")

    except sqlite3.Error as e:
        print(f"❌ Error durante la migración: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    print("=" * 60)
    print("  MIGRACIÓN: Agregar soporte para jerarquía recursiva")
    print("=" * 60)
    print()

    migrate_database()

    print()
    print("=" * 60)
    print("  Migración finalizada")
    print("=" * 60)
    print()
    print("ℹ️  Notas importantes:")
    print("   - Los subcapítulos existentes tendrán parent_id = NULL")
    print("   - Esto es correcto: significa que son de nivel 1")
    print("   - Los nuevos proyectos procesados usarán la jerarquía completa")
    print()
