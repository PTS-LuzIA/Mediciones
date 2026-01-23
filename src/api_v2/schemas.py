"""
Pydantic Schemas - Validación de datos API
==========================================

Define todos los esquemas de validación para:
- Request bodies
- Response models
- Query parameters

"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, validator
from decimal import Decimal


# ============================================
# Autenticación
# ============================================

class LoginRequest(BaseModel):
    """Request de login"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)


class TokenResponse(BaseModel):
    """Response de autenticación"""
    access_token: str
    token_type: str = "bearer"
    user: dict


# ============================================
# Proyectos
# ============================================

class ProyectoBase(BaseModel):
    """Base de proyecto"""
    nombre: str


class ProyectoCreate(ProyectoBase):
    """Crear proyecto (desde upload PDF)"""
    pass


class MedicionParcialResponse(BaseModel):
    """Respuesta de medición parcial"""
    id: int
    orden: int
    descripcion: Optional[str]
    uds: Decimal
    longitud: Decimal
    anchura: Decimal
    altura: Decimal
    parciales: Decimal
    subtotal: Decimal

    class Config:
        from_attributes = True


class PartidaResponse(BaseModel):
    """Respuesta de partida"""
    id: int
    codigo: str
    unidad: Optional[str]
    resumen: Optional[str]
    descripcion: Optional[str]
    cantidad_total: Decimal
    precio: Decimal
    importe: Decimal
    tiene_mediciones: bool
    mediciones_validadas: bool
    mediciones: List[MedicionParcialResponse] = []

    class Config:
        from_attributes = True


class SubcapituloResponse(BaseModel):
    """Respuesta de subcapítulo"""
    id: int
    codigo: str
    nombre: Optional[str]
    total: Decimal
    nivel: Optional[int]
    partidas: List[PartidaResponse] = []

    class Config:
        from_attributes = True


class CapituloResponse(BaseModel):
    """Respuesta de capítulo"""
    id: int
    codigo: str
    nombre: Optional[str]
    total: Decimal
    subcapitulos: List[SubcapituloResponse] = []

    class Config:
        from_attributes = True


class ProyectoResponse(BaseModel):
    """Respuesta de proyecto completo"""
    id: int
    nombre: str
    fecha_creacion: datetime
    presupuesto_total: Decimal
    pdf_nombre: Optional[str]
    layout_detectado: Optional[str]
    tiene_mediciones_auxiliares: bool
    capitulos: List[CapituloResponse] = []

    class Config:
        from_attributes = True


class ProyectoListItem(BaseModel):
    """Item de lista de proyectos (sin detalles)"""
    id: int
    nombre: str
    fecha_creacion: datetime
    presupuesto_total: Decimal
    layout_detectado: Optional[str]
    tiene_mediciones_auxiliares: bool
    num_capitulos: int = 0

    class Config:
        from_attributes = True


class ProyectoStats(BaseModel):
    """Estadísticas de un proyecto"""
    total_capitulos: int
    total_subcapitulos: int
    total_partidas: int
    partidas_con_mediciones: int
    presupuesto_total: Decimal


# ============================================
# Upload de archivos
# ============================================

class UploadResponse(BaseModel):
    """Respuesta de upload de PDF"""
    success: bool
    message: str
    proyecto_id: Optional[int] = None
    filename: str
    size_bytes: int
    procesamiento: dict = {}


# ============================================
# Validación
# ============================================

class ValidacionPartida(BaseModel):
    """Resultado de validación de partida"""
    codigo: str
    cantidad_total: Decimal
    suma_parciales: Decimal
    diferencia: Decimal
    valido: bool


class ValidacionProyectoResponse(BaseModel):
    """Resultado de validación de proyecto"""
    proyecto_id: int
    total_partidas: int
    partidas_con_mediciones: int
    partidas_validas: int
    partidas_invalidas: int
    detalles_invalidas: List[ValidacionPartida] = []


# ============================================
# Exportación
# ============================================

class ExportRequest(BaseModel):
    """Request de exportación"""
    proyecto_id: int
    formato: str = Field(..., pattern="^(csv|excel|xml|bc3)$")

    @validator('formato')
    def validate_formato(cls, v):
        formatos_validos = ['csv', 'excel', 'xml', 'bc3']
        if v not in formatos_validos:
            raise ValueError(f"Formato debe ser uno de: {', '.join(formatos_validos)}")
        return v


# ============================================
# Respuestas genéricas
# ============================================

class MessageResponse(BaseModel):
    """Respuesta genérica con mensaje"""
    success: bool
    message: str
    data: Optional[dict] = None


class ErrorResponse(BaseModel):
    """Respuesta de error"""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
