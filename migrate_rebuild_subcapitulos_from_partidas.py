"""
Migración: Reconstruye la jerarquía de subcapítulos analizando los códigos de partidas existentes.

Este script:
1. Analiza todas las partidas de cada proyecto
2. Detecta subcapítulos faltantes basándose en los códigos de partidas (ej: partida 01.10.01.001 indica que existe subcapítulo 01.10.01)
3. Crea los subcapítulos faltantes con jerarquía correcta
4. Reasigna las partidas a los subcapítulos correspondientes
"""

import sqlite3
import os
import re

def rebuild_subcapitulos_hierarchy():
    """Reconstruye jerarquía de subcapítulos desde códigos de partidas"""

    db_path = 'data/mediciones.db'

    if not os.path.exists(db_path):
        print(f"❌ Base de datos no encontrada: {db_path}")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Obtener todos los proyectos
        cursor.execute("SELECT id, nombre FROM proyectos")
        proyectos = cursor.fetchall()

        print(f"📊 Encontrados {len(proyectos)} proyectos")
        print("=" * 70)

        for proyecto_id, proyecto_nombre in proyectos:
            print(f"\n🔄 Procesando: {proyecto_nombre} (ID: {proyecto_id})")

            # Obtener capítulos del proyecto
            cursor.execute("""
                SELECT id, codigo
                FROM capitulos
                WHERE proyecto_id = ?
            """, (proyecto_id,))
            capitulos = cursor.fetchall()

            for cap_id, cap_codigo in capitulos:
                print(f"   Capítulo {cap_codigo}")

                # Obtener todas las partidas del capítulo
                cursor.execute("""
                    SELECT p.id, p.codigo, p.subcapitulo_id
                    FROM partidas p
                    JOIN subcapitulos s ON p.subcapitulo_id = s.id
                    WHERE s.capitulo_id = ?
                    ORDER BY p.codigo
                """, (cap_id,))
                partidas = cursor.fetchall()

                if not partidas:
                    continue

                # Analizar códigos de partidas para detectar subcapítulos necesarios
                subcapitulos_necesarios = set()

                for part_id, part_codigo, sub_id in partidas:
                    # Extraer prefijo del código de partida (ej: m23U02BZ010 -> ?, C08.01.001 -> C08.01)
                    # Detectar diferentes patrones
                    match = re.match(r'^([A-Z]?\d{1,2}\.\d{1,2}(?:\.\d{1,2})*)', part_codigo)

                    if match:
                        prefijo = match.group(1)
                        # Agregar todos los niveles intermedios
                        partes = prefijo.split('.')
                        for i in range(2, len(partes) + 1):
                            subcap_codigo = '.'.join(partes[:i])
                            subcapitulos_necesarios.add(subcap_codigo)

                if not subcapitulos_necesarios:
                    print(f"      ⚠️  No se detectaron subcapítulos en códigos de partidas")
                    continue

                print(f"      📋 Subcapítulos detectados: {len(subcapitulos_necesarios)}")

                # Obtener subcapítulos existentes
                cursor.execute("""
                    SELECT id, codigo
                    FROM subcapitulos
                    WHERE capitulo_id = ?
                """, (cap_id,))
                subs_existentes = {codigo: sub_id for sub_id, codigo in cursor.fetchall()}

                # Crear subcapítulos faltantes
                for codigo in sorted(subcapitulos_necesarios):
                    if codigo not in subs_existentes:
                        # Determinar parent_id basándose en el código
                        partes = codigo.split('.')
                        parent_id = None

                        if len(partes) > 2:  # Tiene padre
                            codigo_padre = '.'.join(partes[:-1])
                            if codigo_padre in subs_existentes:
                                parent_id = subs_existentes[codigo_padre]

                        # Crear subcapítulo
                        nombre = f"Subcapítulo {codigo}"  # Nombre genérico
                        cursor.execute("""
                            INSERT INTO subcapitulos (capitulo_id, parent_id, codigo, nombre, orden, total)
                            VALUES (?, ?, ?, ?, 0, 0.0)
                        """, (cap_id, parent_id, codigo, nombre))

                        new_id = cursor.lastrowid
                        subs_existentes[codigo] = new_id
                        print(f"         ✓ Creado: {codigo} (parent: {codigo_padre if parent_id else 'nivel 1'})")

                # Reasignar partidas a los subcapítulos correctos
                reasignaciones = 0
                for part_id, part_codigo, sub_id_actual in partidas:
                    # Detectar a qué subcapítulo debería pertenecer
                    match = re.match(r'^([A-Z]?\d{1,2}\.\d{1,2}(?:\.\d{1,2})*)', part_codigo)

                    if match:
                        prefijo = match.group(1)

                        if prefijo in subs_existentes:
                            nuevo_sub_id = subs_existentes[prefijo]

                            if nuevo_sub_id != sub_id_actual:
                                cursor.execute("""
                                    UPDATE partidas
                                    SET subcapitulo_id = ?
                                    WHERE id = ?
                                """, (nuevo_sub_id, part_id))
                                reasignaciones += 1

                if reasignaciones > 0:
                    print(f"         🔄 Reasignadas {reasignaciones} partidas")

        conn.commit()
        print("\n✅ Migración completada")

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
    print("MIGRACIÓN: Reconstruir jerarquía de subcapítulos desde partidas")
    print("=" * 70)

    if rebuild_subcapitulos_hierarchy():
        print("\n✅ Migración exitosa")
        print("\n⚠️  NOTA: Los nombres de los nuevos subcapítulos son genéricos.")
        print("   Considera reprocesar los PDFs para obtener nombres correctos.")
    else:
        print("\n❌ Migración fallida")
