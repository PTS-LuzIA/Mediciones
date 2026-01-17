"""
Modelos de base de datos para proyectos procesados con IA.
Estructura similar a db_models.py pero con campos adicionales para IA.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from .db_models import Base


class AIProyecto(Base):
    """Proyecto de obra procesado con IA"""
    __tablename__ = 'ai_proyectos'

    id = Column(Integer, primary_key=True)
    nombre = Column(String(500), nullable=False)
    descripcion = Column(Text)
    fecha_creacion = Column(DateTime, default=datetime.now)
    archivo_origen = Column(String(500))
    presupuesto_total = Column(Float, default=0.0)

    # Campos específicos de IA
    modelo_usado = Column(String(100), default='google/gemini-2.5-flash-lite')
    confianza_general = Column(Float)  # Confianza promedio de todas las partidas
    notas_ia = Column(Text)  # Observaciones generales generadas por la IA
    metadatos = Column(JSON)  # Información adicional del procesamiento
    tiempo_procesamiento = Column(Float)  # Segundos que tardó el procesamiento

    # Relaciones
    capitulos = relationship("AICapitulo", back_populates="proyecto", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<AIProyecto(id={self.id}, nombre='{self.nombre}', modelo='{self.modelo_usado}')>"


class AICapitulo(Base):
    """Capítulo principal procesado con IA"""
    __tablename__ = 'ai_capitulos'

    id = Column(Integer, primary_key=True)
    proyecto_id = Column(Integer, ForeignKey('ai_proyectos.id'), nullable=False)
    codigo = Column(String(50), nullable=False)
    nombre = Column(String(500), nullable=False)
    orden = Column(Integer, default=0)
    total = Column(Float, default=0.0)

    # Campos específicos de IA
    confianza = Column(Float)
    notas = Column(Text)

    # Relaciones
    proyecto = relationship("AIProyecto", back_populates="capitulos")
    subcapitulos = relationship("AISubcapitulo", back_populates="capitulo", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<AICapitulo(codigo='{self.codigo}', nombre='{self.nombre}')>"


class AISubcapitulo(Base):
    """Subcapítulo procesado con IA (soporta jerarquía multinivel)"""
    __tablename__ = 'ai_subcapitulos'

    id = Column(Integer, primary_key=True)
    capitulo_id = Column(Integer, ForeignKey('ai_capitulos.id'), nullable=False)
    parent_id = Column(Integer, ForeignKey('ai_subcapitulos.id'), nullable=True)  # Para jerarquía recursiva
    codigo = Column(String(50), nullable=False)
    nombre = Column(String(500), nullable=False)
    orden = Column(Integer, default=0)
    total = Column(Float, default=0.0)

    # Campos específicos de IA
    confianza = Column(Float)
    notas = Column(Text)

    # Relaciones
    capitulo = relationship("AICapitulo", back_populates="subcapitulos")
    apartados = relationship("AIApartado", back_populates="subcapitulo", cascade="all, delete-orphan")
    partidas = relationship("AIPartida", back_populates="subcapitulo", cascade="all, delete-orphan")

    # Relación recursiva para jerarquía de subcapítulos
    parent = relationship("AISubcapitulo", remote_side=[id], back_populates="subcapitulos")
    subcapitulos = relationship("AISubcapitulo", back_populates="parent", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<AISubcapitulo(codigo='{self.codigo}', nombre='{self.nombre}')>"


class AIApartado(Base):
    """Apartado opcional procesado con IA"""
    __tablename__ = 'ai_apartados'

    id = Column(Integer, primary_key=True)
    subcapitulo_id = Column(Integer, ForeignKey('ai_subcapitulos.id'), nullable=False)
    codigo = Column(String(50), nullable=False)
    nombre = Column(String(500), nullable=False)
    orden = Column(Integer, default=0)
    total = Column(Float, default=0.0)

    # Campos específicos de IA
    confianza = Column(Float)
    notas = Column(Text)

    # Relaciones
    subcapitulo = relationship("AISubcapitulo", back_populates="apartados")
    partidas = relationship("AIPartida", back_populates="apartado", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<AIApartado(codigo='{self.codigo}', nombre='{self.nombre}')>"


class AIPartida(Base):
    """Partida individual procesada con IA"""
    __tablename__ = 'ai_partidas'

    id = Column(Integer, primary_key=True)
    subcapitulo_id = Column(Integer, ForeignKey('ai_subcapitulos.id'), nullable=True)
    apartado_id = Column(Integer, ForeignKey('ai_apartados.id'), nullable=True)

    codigo = Column(String(50), nullable=False, index=True)
    unidad = Column(String(20), nullable=False)
    resumen = Column(Text, nullable=False)
    descripcion = Column(Text)
    cantidad = Column(Float, default=0.0)
    precio = Column(Float, default=0.0)
    importe = Column(Float, default=0.0)
    orden = Column(Integer, default=0)

    # Campos específicos de IA
    confianza = Column(Float)  # 0.0 - 1.0, nivel de confianza de la extracción
    notas = Column(Text)  # Observaciones o anomalías detectadas por IA

    # Relaciones
    subcapitulo = relationship("AISubcapitulo", back_populates="partidas")
    apartado = relationship("AIApartado", back_populates="partidas")

    def __repr__(self):
        return f"<AIPartida(codigo='{self.codigo}', resumen='{self.resumen[:50]}...', confianza={self.confianza})>"

    def validar_importe(self, tolerancia=0.05):
        """Valida que cantidad × precio ≈ importe"""
        calculado = round(self.cantidad * self.precio, 2)
        diferencia = abs(calculado - self.importe)
        return diferencia <= tolerancia
