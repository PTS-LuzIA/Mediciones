"""
Migración: Agregar columna parent_id a la tabla subcapitulos
para soportar jerarquía recursiva de subcapítulos.
"""

import sqlite3
import os

def migrar_subcapitulos():
    """Agrega parent_id a la tabla subcapitulos"""

    db_path = 'data/mediciones.db'

    if not os.path.exists(db_path):
        print(f"❌ Base de datos no encontrada: {db_path}")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Verificar si la columna ya existe
        cursor.execute("PRAGMA table_info(subcapitulos)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'parent_id' in columns:
            print("✓ La columna parent_id ya existe en subcapitulos")
            conn.close()
            return True

        print("📝 Agregando columna parent_id a subcapitulos...")

        # Agregar columna parent_id
        cursor.execute("""
            ALTER TABLE subcapitulos
            ADD COLUMN parent_id INTEGER REFERENCES subcapitulos(id)
        """)

        conn.commit()
        print("✓ Columna parent_id agregada correctamente")

        # Verificar
        cursor.execute("PRAGMA table_info(subcapitulos)")
        columns_after = [col[1] for col in cursor.fetchall()]
        print(f"✓ Columnas en subcapitulos: {', '.join(columns_after)}")

        conn.close()
        return True

    except Exception as e:
        print(f"❌ Error en migración: {e}")
        conn.rollback()
        conn.close()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("MIGRACIÓN: Agregar parent_id a subcapitulos")
    print("=" * 60)

    if migrar_subcapitulos():
        print("\n✅ Migración completada exitosamente")
    else:
        print("\n❌ Migración fallida")
