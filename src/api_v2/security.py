"""
Módulo de Seguridad - Autenticación y Autorización
==================================================

Implementa:
- Autenticación JWT
- Hashing de contraseñas
- Verificación de usuarios
- Middleware de seguridad

"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from .config import settings

# Configuración de hashing de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Esquema de seguridad Bearer Token
security = HTTPBearer()


class TokenData(BaseModel):
    """Datos contenidos en el token"""
    username: Optional[str] = None
    user_id: Optional[int] = None


class Token(BaseModel):
    """Respuesta de token"""
    access_token: str
    token_type: str = "bearer"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica que la contraseña coincida con el hash

    Args:
        plain_password: Contraseña en texto plano
        hashed_password: Hash almacenado

    Returns:
        bool: True si coincide
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Genera hash de contraseña

    Args:
        password: Contraseña en texto plano

    Returns:
        str: Hash bcrypt
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Crea un token JWT

    Args:
        data: Datos a incluir en el token
        expires_delta: Tiempo de expiración

    Returns:
        str: Token JWT firmado
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    return encoded_jwt


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenData:
    """
    Verifica y decodifica un token JWT

    Args:
        credentials: Credenciales HTTP Bearer

    Returns:
        TokenData: Datos del token

    Raises:
        HTTPException: Si el token es inválido
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token = credentials.credentials
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        user_id: int = payload.get("user_id")

        if username is None:
            raise credentials_exception

        token_data = TokenData(username=username, user_id=user_id)

    except JWTError:
        raise credentials_exception

    return token_data


# Usuario de demostración (en producción esto vendría de una BD de usuarios)
# TODO: Implementar tabla de usuarios en PostgreSQL
# NOTA: En desarrollo usamos contraseña simple, en producción usar hash real
DEMO_USERS = {
    "admin": {
        "username": "admin",
        "plain_password": "admin123",  # Solo para desarrollo
        "user_id": 1,
        "is_active": True
    }
}


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """
    Autentica un usuario

    Args:
        username: Nombre de usuario
        password: Contraseña

    Returns:
        dict: Datos del usuario o None si falla
    """
    user = DEMO_USERS.get(username)

    if not user:
        return None

    # En desarrollo: comparación simple
    # En producción: usar verify_password con hash
    if settings.DEBUG and "plain_password" in user:
        if password != user["plain_password"]:
            return None
    else:
        if not verify_password(password, user.get("hashed_password", "")):
            return None

    return user


def get_current_user(token_data: TokenData = Depends(verify_token)) -> dict:
    """
    Obtiene el usuario actual desde el token

    Args:
        token_data: Datos del token verificado

    Returns:
        dict: Datos del usuario

    Raises:
        HTTPException: Si el usuario no existe
    """
    user = DEMO_USERS.get(token_data.username)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    return user
