"""
Migración: Establece correctamente las relaciones parent_id en subcapítulos
basándose en la jerarquía de sus códigos.

Por ejemplo:
- 01.04 (nivel 1, parent_id=NULL)
- 01.04.01 (nivel 2, parent_id=id de 01.04)
- 01.04.01.01 (nivel 3, parent_id=id de 01.04.01)
"""

import sqlite3
import os

def fix_subcapitulos_hierarchy():
    """Establece parent_id correctamente basándose en los códigos"""

    db_path = 'data/mediciones.db'

    if not os.path.exists(db_path):
        print(f"❌ Base de datos no encontrada: {db_path}")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Obtener todos los subcapítulos
        cursor.execute("""
            SELECT id, capitulo_id, codigo, nombre, parent_id
            FROM subcapitulos
            ORDER BY capitulo_id, codigo
        """)
        subcapitulos = cursor.fetchall()

        print(f"📊 Encontrados {len(subcapitulos)} subcapítulos")

        # Crear un mapa de subcapítulos por capítulo
        subs_por_capitulo = {}
        for sub_id, cap_id, codigo, nombre, parent_id in subcapitulos:
            if cap_id not in subs_por_capitulo:
                subs_por_capitulo[cap_id] = []
            subs_por_capitulo[cap_id].append({
                'id': sub_id,
                'codigo': codigo,
                'nombre': nombre,
                'parent_id': parent_id
            })

        actualizaciones = 0
        errores = 0

        # Para cada capítulo, establecer parent_id basándose en jerarquía de códigos
        for cap_id, subs in subs_por_capitulo.items():
            # Crear mapa código -> id
            codigo_a_id = {sub['codigo']: sub['id'] for sub in subs}

            for sub in subs:
                codigo = sub['codigo']
                partes = codigo.split('.')

                # Determinar el parent_id basándose en el código
                new_parent_id = None

                if len(partes) > 2:  # Tiene padre (ej: 01.04.01 -> padre es 01.04)
                    # El código del padre es todo menos el último número
                    codigo_padre = '.'.join(partes[:-1])

                    if codigo_padre in codigo_a_id:
                        new_parent_id = codigo_a_id[codigo_padre]
                    else:
                        print(f"⚠️  Padre no encontrado para {codigo} (buscando {codigo_padre})")
                        errores += 1
                        continue

                # Solo actualizar si cambió
                if new_parent_id != sub['parent_id']:
                    cursor.execute("""
                        UPDATE subcapitulos
                        SET parent_id = ?
                        WHERE id = ?
                    """, (new_parent_id, sub['id']))

                    actualizaciones += 1

                    if actualizaciones <= 10:  # Mostrar solo las primeras 10
                        print(f"  ✓ {codigo}: parent_id {sub['parent_id']} -> {new_parent_id}")

        conn.commit()

        print(f"\n✅ Migraci ón completada:")
        print(f"   - {actualizaciones} subcapítulos actualizados")
        print(f"   - {errores} errores encontrados")

        # Verificar algunos ejemplos
        print("\n📋 Verificación de ejemplos:")
        cursor.execute("""
            SELECT s.codigo, s.nombre, s.parent_id,
                   (SELECT p.codigo FROM subcapitulos p WHERE p.id = s.parent_id) as parent_codigo
            FROM subcapitulos s
            WHERE s.codigo LIKE '01.04%' OR s.codigo LIKE '01.10%'
            ORDER BY s.codigo
            LIMIT 15
        """)

        for codigo, nombre, parent_id, parent_codigo in cursor.fetchall():
            parent_info = f"-> {parent_codigo}" if parent_codigo else "(nivel 1)"
            print(f"   {codigo:20} {parent_info}")

        conn.close()
        return True

    except Exception as e:
        print(f"❌ Error en migración: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        conn.close()
        return False


if __name__ == "__main__":
    print("=" * 70)
    print("MIGRACIÓN: Establecer jerarquía de subcapítulos basada en códigos")
    print("=" * 70)

    if fix_subcapitulos_hierarchy():
        print("\n✅ Migración completada exitosamente")
    else:
        print("\n❌ Migración fallida")
