"""
Configuración de la API V2
==========================

Todas las configuraciones de seguridad y producción
"""

import os
from typing import List
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Configuración de la aplicación"""

    # Aplicación
    APP_NAME: str = "Mediciones API V2"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False") == "True"

    # Seguridad
    SECRET_KEY: str = os.getenv("SECRET_KEY", "CHANGE_THIS_IN_PRODUCTION_USE_STRONG_SECRET")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS - Dominios permitidos
    @property
    def CORS_ORIGINS(self) -> List[str]:
        """Parse CORS origins from environment or use defaults"""
        cors_env = os.getenv("CORS_ORIGINS", "")
        if cors_env:
            # Split by comma and strip whitespace
            return [origin.strip() for origin in cors_env.split(",")]
        # Defaults si no hay variable de entorno
        return [
            "http://localhost:3015",  # Frontend desarrollo V2
            "http://localhost:8000",  # Backend API
        ]

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # Upload de archivos
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50 MB
    ALLOWED_EXTENSIONS: List[str] = [".pdf"]
    UPLOAD_DIR: str = "uploads"

    # Database (PostgreSQL)
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "mediciones_db")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "imac")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "")
    POSTGRES_SCHEMA: str = os.getenv("POSTGRES_SCHEMA_V2", "v2")

    @property
    def DATABASE_URL(self) -> str:
        """URL de conexión a PostgreSQL"""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = "logs/api_v2.log"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignorar campos extra del .env


# Instancia global de configuración
settings = Settings()


# Validar configuración crítica en producción
if not settings.DEBUG:
    if settings.SECRET_KEY == "CHANGE_THIS_IN_PRODUCTION_USE_STRONG_SECRET":
        raise ValueError(
            "⚠️  CRITICAL: SECRET_KEY must be changed in production! "
            "Generate one with: openssl rand -hex 32"
        )
