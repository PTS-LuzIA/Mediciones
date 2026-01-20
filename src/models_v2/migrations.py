"""
Script de migración para Sistema V2 - PostgreSQL
================================================

Funciones:
- Crear schema v2
- Crear todas las tablas
- Resetear tablas (desarrollo)
- Verificar estructura

USO:
    python -m src.models_v2.migrations crear
    python -m src.models_v2.migrations verificar
    python -m src.models_v2.migrations reset  # PELIGRO: Borra todo

"""

import sys
from pathlib import Path
import logging

# Agregar src al path si es necesario
sys.path.append(str(Path(__file__).parent.parent.parent))

from sqlalchemy import text, inspect
from src.models_v2.db_config import engine, DB_CONFIG
from src.models_v2.db_models_v2 import Base, SCHEMA_V2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def crear_schema():
    """Crea el schema v2 si no existe"""
    try:
        with engine.connect() as conn:
            # Crear schema
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA_V2}"))
            conn.commit()

        logger.info(f"✓ Schema '{SCHEMA_V2}' creado/verificado")
        return True

    except Exception as e:
        logger.error(f"✗ Error creando schema: {e}")
        return False


def crear_tablas():
    """Crea todas las tablas del schema v2"""
    try:
        # Primero crear el schema
        if not crear_schema():
            return False

        # Crear todas las tablas definidas en Base
        Base.metadata.create_all(bind=engine)

        logger.info(f"✓ Tablas creadas en schema '{SCHEMA_V2}':")
        for table in Base.metadata.sorted_tables:
            logger.info(f"  - {table.name}")

        return True

    except Exception as e:
        logger.error(f"✗ Error creando tablas: {e}")
        return False


def verificar_estructura():
    """Verifica que las tablas existen y muestra su estructura"""
    try:
        inspector = inspect(engine)

        # Verificar que el schema existe
        schemas = inspector.get_schema_names()
        if SCHEMA_V2 not in schemas:
            logger.error(f"✗ Schema '{SCHEMA_V2}' no existe")
            return False

        logger.info(f"\n{'='*60}")
        logger.info(f"ESTRUCTURA DEL SCHEMA '{SCHEMA_V2}'")
        logger.info(f"{'='*60}\n")

        # Listar tablas del schema v2
        tablas = inspector.get_table_names(schema=SCHEMA_V2)

        if not tablas:
            logger.warning(f"⚠️  No hay tablas en el schema '{SCHEMA_V2}'")
            return False

        for tabla in tablas:
            logger.info(f"📊 Tabla: {tabla}")

            # Listar columnas
            columnas = inspector.get_columns(tabla, schema=SCHEMA_V2)
            for col in columnas:
                tipo = str(col['type'])
                nullable = "NULL" if col['nullable'] else "NOT NULL"
                logger.info(f"   - {col['name']:30} {tipo:20} {nullable}")

            # Listar índices
            indices = inspector.get_indexes(tabla, schema=SCHEMA_V2)
            if indices:
                logger.info(f"   Índices:")
                for idx in indices:
                    logger.info(f"     - {idx['name']}: {idx['column_names']}")

            # Listar foreign keys
            fks = inspector.get_foreign_keys(tabla, schema=SCHEMA_V2)
            if fks:
                logger.info(f"   Foreign Keys:")
                for fk in fks:
                    logger.info(f"     - {fk['constrained_columns']} → {fk['referred_table']}.{fk['referred_columns']}")

            logger.info("")

        logger.info(f"✓ Total de tablas: {len(tablas)}\n")
        return True

    except Exception as e:
        logger.error(f"✗ Error verificando estructura: {e}")
        return False


def reset_tablas():
    """
    PELIGRO: Elimina y recrea todas las tablas V2
    Solo para desarrollo
    """
    print("\n" + "="*60)
    print("⚠️  ADVERTENCIA: RESETEAR TABLAS V2")
    print("="*60)
    print(f"\nEsto eliminará TODAS las tablas del schema '{SCHEMA_V2}'")
    print("y todos los datos almacenados.\n")

    respuesta = input("¿Estás seguro? Escribe 'SI BORRAR TODO' para confirmar: ")

    if respuesta == 'SI BORRAR TODO':
        try:
            logger.info("Eliminando tablas...")
            Base.metadata.drop_all(bind=engine)

            logger.info("Recreando tablas...")
            crear_tablas()

            logger.info("✓ Tablas reseteadas correctamente")
            return True

        except Exception as e:
            logger.error(f"✗ Error reseteando tablas: {e}")
            return False
    else:
        logger.info("Operación cancelada")
        return False


def main():
    """Punto de entrada del script de migración"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Script de migración para Sistema V2 - PostgreSQL'
    )
    parser.add_argument(
        'accion',
        choices=['crear', 'verificar', 'reset'],
        help='Acción a realizar'
    )

    args = parser.parse_args()

    print("\n" + "="*60)
    print("MIGRACIÓN SISTEMA V2 - PostgreSQL")
    print("="*60)
    print(f"\nDatabase: {DB_CONFIG['database']}")
    print(f"Schema: {SCHEMA_V2}")
    print(f"Host: {DB_CONFIG['host']}:{DB_CONFIG['port']}\n")

    if args.accion == 'crear':
        if crear_tablas():
            print("\n✓ Migración completada exitosamente\n")
            verificar_estructura()
        else:
            print("\n✗ Error en la migración\n")
            sys.exit(1)

    elif args.accion == 'verificar':
        if verificar_estructura():
            print("✓ Verificación completada\n")
        else:
            print("✗ Error en la verificación\n")
            sys.exit(1)

    elif args.accion == 'reset':
        if reset_tablas():
            print("\n✓ Reset completado\n")
        else:
            print("\n✗ Error en el reset\n")
            sys.exit(1)


if __name__ == "__main__":
    main()
