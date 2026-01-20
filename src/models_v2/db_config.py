"""
Configuración de PostgreSQL para Sistema V2
===========================================

Base de datos: PostgreSQL local
Schema: v2 (separado del schema public/v1)

"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import logging

# Cargar variables de entorno
load_dotenv()

logger = logging.getLogger(__name__)

# Configuración PostgreSQL Local
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': os.getenv('POSTGRES_PORT', '5432'),
    'database': os.getenv('POSTGRES_DB', 'mediciones_db'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', 'postgres'),
    'schema': os.getenv('POSTGRES_SCHEMA_V2', 'v2')
}

# URL de conexión PostgreSQL
DATABASE_URL = (
    f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
    f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
)

# Engine con schema v2 por defecto
# El schema v2 se usa para todas las tablas del sistema V2
engine = create_engine(
    DATABASE_URL,
    connect_args={'options': f"-c search_path={DB_CONFIG['schema']},public"},
    echo=False,  # True para debug SQL
    pool_pre_ping=True,  # Verifica conexión antes de usar
    pool_size=5,
    max_overflow=10
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    Dependency para obtener sesión de BD

    Uso:
        db = next(get_db())
        try:
            # ... operaciones
            db.commit()
        finally:
            db.close()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_connection():
    """
    Prueba la conexión a PostgreSQL

    Returns:
        bool: True si la conexión es exitosa
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            logger.info(f"✓ Conexión PostgreSQL exitosa")
            logger.info(f"  Versión: {version}")
            logger.info(f"  Database: {DB_CONFIG['database']}")
            logger.info(f"  Schema: {DB_CONFIG['schema']}")
            return True
    except Exception as e:
        logger.error(f"✗ Error de conexión PostgreSQL: {e}")
        return False


if __name__ == "__main__":
    # Test de conexión
    from sqlalchemy import text
    logging.basicConfig(level=logging.INFO)

    print("\n" + "="*60)
    print("TEST DE CONEXIÓN POSTGRESQL - SISTEMA V2")
    print("="*60 + "\n")

    print(f"Host: {DB_CONFIG['host']}")
    print(f"Port: {DB_CONFIG['port']}")
    print(f"Database: {DB_CONFIG['database']}")
    print(f"User: {DB_CONFIG['user']}")
    print(f"Schema: {DB_CONFIG['schema']}\n")

    if test_connection():
        print("\n✓ Conexión exitosa\n")
    else:
        print("\n✗ Error de conexión")
        print("\nPara instalar PostgreSQL en macOS:")
        print("  brew install postgresql@16")
        print("  brew services start postgresql@16")
        print("\nPara crear la base de datos:")
        print(f"  createdb {DB_CONFIG['database']}")
        print()
