"""
Modelos de base de datos para proyectos HÍBRIDOS.
Combina IA (estructura) + Parser Local (partidas) + Validación cruzada.

Arquitectura:
- Fase 1: Extracción de estructura con IA (capítulos/subcapítulos + totales)
- Fase 2: Extracción de partidas con parser local
- Fase 3: Validación cruzada y re-validación selectiva con IA
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from .db_models import Base
import enum


class EstadoValidacion(enum.Enum):
    """Estados de validación de un elemento"""
    PENDIENTE = "pendiente"           # Sin validar aún
    VALIDADO = "validado"             # Totales coinciden (±5%)
    DISCREPANCIA = "discrepancia"     # Totales NO coinciden
    REVISADO_IA = "revisado_ia"       # Re-validado por IA
    ERROR = "error"                   # Error en el procesamiento


class FaseProyecto(enum.Enum):
    """Fases del procesamiento híbrido"""
    CREADO = "creado"                      # Proyecto creado, sin procesar
    FASE1_ESTRUCTURA = "fase1_estructura"  # Extrayendo estructura con IA
    FASE2_PARTIDAS = "fase2_partidas"      # Extrayendo partidas con local
    FASE3_VALIDACION = "fase3_validacion"  # Validando discrepancias
    COMPLETADO = "completado"              # Proceso completado
    ERROR = "error"                        # Error en alguna fase


class HybridProyecto(Base):
    """Proyecto híbrido: IA + Local + Validación"""
    __tablename__ = 'hybrid_proyectos'

    id = Column(Integer, primary_key=True)
    nombre = Column(String(500), nullable=False)
    descripcion = Column(Text)
    fecha_creacion = Column(DateTime, default=datetime.now)
    archivo_origen = Column(String(500))
    presupuesto_total = Column(Float, default=0.0)

    # Estado del procesamiento
    fase_actual = Column(SQLEnum(FaseProyecto), default=FaseProyecto.CREADO)

    # Métricas de validación
    total_estructura_ia = Column(Float, default=0.0)      # Total según IA (Fase 1)
    total_partidas_local = Column(Float, default=0.0)     # Total según parser local (Fase 2)
    porcentaje_coincidencia = Column(Float)               # % de coincidencia global

    # Campos IA
    modelo_usado = Column(String(100), default='google/gemini-2.5-flash-lite')
    tiempo_fase1 = Column(Float)  # Segundos Fase 1
    tiempo_fase2 = Column(Float)  # Segundos Fase 2
    tiempo_fase3 = Column(Float)  # Segundos Fase 3

    # Estadísticas de validación
    subcapitulos_validados = Column(Integer, default=0)
    subcapitulos_con_discrepancia = Column(Integer, default=0)
    subcapitulos_revisados_ia = Column(Integer, default=0)

    # Metadatos
    metadatos = Column(JSON)
    notas = Column(Text)

    # Relaciones
    capitulos = relationship("HybridCapitulo", back_populates="proyecto", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<HybridProyecto(id={self.id}, nombre='{self.nombre}', fase='{self.fase_actual.value}')>"


class HybridCapitulo(Base):
    """Capítulo híbrido con validación"""
    __tablename__ = 'hybrid_capitulos'

    id = Column(Integer, primary_key=True)
    proyecto_id = Column(Integer, ForeignKey('hybrid_proyectos.id'), nullable=False)
    codigo = Column(String(50), nullable=False)
    nombre = Column(String(500), nullable=False)
    orden = Column(Integer, default=0)

    # Totales
    total_ia = Column(Float, default=0.0)        # Total según IA (Fase 1)
    total_local = Column(Float, default=0.0)     # Total según partidas locales (Fase 2)
    total_final = Column(Float, default=0.0)     # Total validado final

    # Conteo de partidas
    num_partidas_ia = Column(Integer, default=0)  # Número de partidas según IA (Fase 1)
    num_partidas_local = Column(Integer, default=0)  # Número de partidas extraídas (Fase 2)

    # Validación
    estado_validacion = Column(SQLEnum(EstadoValidacion), default=EstadoValidacion.PENDIENTE)
    diferencia_euros = Column(Float)             # Diferencia en €
    diferencia_porcentaje = Column(Float)        # Diferencia en %
    necesita_revision_ia = Column(Integer, default=0)  # Boolean: 1=Sí, 0=No

    # Campos IA
    confianza_ia = Column(Float)
    notas = Column(Text)

    # Relaciones
    proyecto = relationship("HybridProyecto", back_populates="capitulos")
    subcapitulos = relationship("HybridSubcapitulo", back_populates="capitulo", cascade="all, delete-orphan")
    partidas = relationship("HybridPartida", back_populates="capitulo", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<HybridCapitulo(codigo='{self.codigo}', estado='{self.estado_validacion.value}')>"


class HybridSubcapitulo(Base):
    """Subcapítulo híbrido con validación (soporta jerarquía multinivel)"""
    __tablename__ = 'hybrid_subcapitulos'

    id = Column(Integer, primary_key=True)
    capitulo_id = Column(Integer, ForeignKey('hybrid_capitulos.id'), nullable=False)
    parent_id = Column(Integer, ForeignKey('hybrid_subcapitulos.id'), nullable=True)
    codigo = Column(String(50), nullable=False)
    nombre = Column(String(500), nullable=False)
    orden = Column(Integer, default=0)

    # Totales
    total_ia = Column(Float, default=0.0)        # Total según IA (Fase 1)
    total_local = Column(Float, default=0.0)     # Total calculado de partidas (Fase 2)
    total_final = Column(Float, default=0.0)     # Total validado final

    # Conteo de partidas
    num_partidas_ia = Column(Integer, default=0)  # Número de partidas según IA (Fase 1)
    num_partidas_local = Column(Integer, default=0)  # Número de partidas extraídas (Fase 2)

    # Validación
    estado_validacion = Column(SQLEnum(EstadoValidacion), default=EstadoValidacion.PENDIENTE)
    diferencia_euros = Column(Float)             # Diferencia en €
    diferencia_porcentaje = Column(Float)        # Diferencia en %
    necesita_revision_ia = Column(Integer, default=0)  # Boolean: 1=Sí, 0=No

    # Campos IA
    confianza_ia = Column(Float)
    notas_ia = Column(Text)                      # Notas originales de IA
    notas_validacion = Column(Text)              # Notas de la validación en Fase 3

    # Relaciones
    capitulo = relationship("HybridCapitulo", back_populates="subcapitulos")
    apartados = relationship("HybridApartado", back_populates="subcapitulo", cascade="all, delete-orphan")
    partidas = relationship("HybridPartida", back_populates="subcapitulo", cascade="all, delete-orphan")

    # Relación recursiva
    parent = relationship("HybridSubcapitulo", remote_side=[id], back_populates="subcapitulos_hijos")
    subcapitulos_hijos = relationship("HybridSubcapitulo", back_populates="parent", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<HybridSubcapitulo(codigo='{self.codigo}', estado='{self.estado_validacion.value}')>"


class HybridApartado(Base):
    """Apartado híbrido opcional"""
    __tablename__ = 'hybrid_apartados'

    id = Column(Integer, primary_key=True)
    subcapitulo_id = Column(Integer, ForeignKey('hybrid_subcapitulos.id'), nullable=False)
    codigo = Column(String(50), nullable=False)
    nombre = Column(String(500), nullable=False)
    orden = Column(Integer, default=0)
    total = Column(Float, default=0.0)

    # Validación
    estado_validacion = Column(SQLEnum(EstadoValidacion), default=EstadoValidacion.PENDIENTE)

    # Relaciones
    subcapitulo = relationship("HybridSubcapitulo", back_populates="apartados")
    partidas = relationship("HybridPartida", back_populates="apartado", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<HybridApartado(codigo='{self.codigo}')>"


class HybridPartida(Base):
    """Partida extraída por parser local (Fase 2)"""
    __tablename__ = 'hybrid_partidas'

    id = Column(Integer, primary_key=True)
    capitulo_id = Column(Integer, ForeignKey('hybrid_capitulos.id'), nullable=True)
    subcapitulo_id = Column(Integer, ForeignKey('hybrid_subcapitulos.id'), nullable=True)
    apartado_id = Column(Integer, ForeignKey('hybrid_apartados.id'), nullable=True)

    codigo = Column(String(50), nullable=False, index=True)
    unidad = Column(String(20), nullable=False)
    resumen = Column(Text, nullable=False)
    descripcion = Column(Text)
    cantidad = Column(Float, default=0.0)
    precio = Column(Float, default=0.0)
    importe = Column(Float, default=0.0)
    orden = Column(Integer, default=0)

    # Origen
    extraido_por = Column(String(20), default='local')  # 'local' o 'ia_revision'

    # Relaciones
    capitulo = relationship("HybridCapitulo", back_populates="partidas")
    subcapitulo = relationship("HybridSubcapitulo", back_populates="partidas")
    apartado = relationship("HybridApartado", back_populates="partidas")

    def __repr__(self):
        return f"<HybridPartida(codigo='{self.codigo}', resumen='{self.resumen[:50]}...')>"
