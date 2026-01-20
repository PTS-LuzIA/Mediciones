"""
Modelos SQLAlchemy para PostgreSQL - Sistema V2
==============================================

Schema: v2
Nuevas características:
- Tabla mediciones_parciales (almacena descomposición dimensional)
- Validación de sumas (parciales vs total)
- Metadata de detección automática (layout, tipo de mediciones)

"""

from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, Boolean, DateTime, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

# Schema v2 para todas las tablas del sistema nuevo
SCHEMA_V2 = 'v2'


class Proyecto(Base):
    """Proyecto de mediciones (presupuesto completo)"""
    __tablename__ = 'proyectos'
    __table_args__ = {'schema': SCHEMA_V2}

    id = Column(Integer, primary_key=True)
    nombre = Column(String(200), nullable=False)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    presupuesto_total = Column(Numeric(14, 2), default=0)

    # Metadata del PDF procesado
    pdf_path = Column(String(500))
    pdf_nombre = Column(String(200))
    pdf_hash = Column(String(64))  # SHA256 para detectar duplicados

    # Metadata de detección automática (NUEVO EN V2)
    layout_detectado = Column(String(20))  # 'single_column' | 'double_column'
    tiene_mediciones_auxiliares = Column(Boolean, default=False)
    numero_paginas = Column(Integer)

    # Relaciones
    capitulos = relationship("Capitulo", back_populates="proyecto", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Proyecto(id={self.id}, nombre='{self.nombre}', total={self.presupuesto_total})>"


class Capitulo(Base):
    """Capítulo de presupuesto (nivel 1)"""
    __tablename__ = 'capitulos'
    __table_args__ = (
        Index('idx_capitulo_proyecto', 'proyecto_id'),
        {'schema': SCHEMA_V2}
    )

    id = Column(Integer, primary_key=True)
    proyecto_id = Column(Integer, ForeignKey(f'{SCHEMA_V2}.proyectos.id'), nullable=False)
    codigo = Column(String(20), nullable=False)
    nombre = Column(String(300))
    total = Column(Numeric(14, 2), default=0)  # Total original del PDF
    total_calculado = Column(Numeric(14, 2))  # Total calculado sumando partidas (Fase 3)
    orden = Column(Integer)  # Para mantener orden original del PDF

    # Relaciones
    proyecto = relationship("Proyecto", back_populates="capitulos")
    subcapitulos = relationship("Subcapitulo", back_populates="capitulo", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Capitulo(codigo='{self.codigo}', nombre='{self.nombre[:30]}...')>"


class Subcapitulo(Base):
    """Subcapítulo de presupuesto (nivel 2, 3, 4...)"""
    __tablename__ = 'subcapitulos'
    __table_args__ = (
        Index('idx_subcapitulo_capitulo', 'capitulo_id'),
        {'schema': SCHEMA_V2}
    )

    id = Column(Integer, primary_key=True)
    capitulo_id = Column(Integer, ForeignKey(f'{SCHEMA_V2}.capitulos.id'), nullable=False)
    codigo = Column(String(30), nullable=False)
    nombre = Column(String(300))
    total = Column(Numeric(14, 2), default=0)  # Total original del PDF
    total_calculado = Column(Numeric(14, 2))  # Total calculado sumando partidas (Fase 3)
    nivel = Column(Integer)  # Profundidad jerárquica (1, 2, 3...)
    orden = Column(Integer)

    # Relaciones
    capitulo = relationship("Capitulo", back_populates="subcapitulos")
    partidas = relationship("Partida", back_populates="subcapitulo", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Subcapitulo(codigo='{self.codigo}', nivel={self.nivel})>"


class Partida(Base):
    """Partida de mediciones (línea de presupuesto)"""
    __tablename__ = 'partidas'
    __table_args__ = (
        Index('idx_partida_subcapitulo', 'subcapitulo_id'),
        Index('idx_partida_codigo', 'codigo'),
        {'schema': SCHEMA_V2}
    )

    id = Column(Integer, primary_key=True)
    subcapitulo_id = Column(Integer, ForeignKey(f'{SCHEMA_V2}.subcapitulos.id'), nullable=False)
    codigo = Column(String(50), nullable=False)
    unidad = Column(String(20))
    resumen = Column(String(500))  # Título corto de la partida
    descripcion = Column(Text)  # Descripción completa (opcional)

    # Valores principales
    cantidad_total = Column(Numeric(12, 4))  # Más precisión para mediciones
    precio = Column(Numeric(12, 4))
    importe = Column(Numeric(14, 2))

    # Flags de control (NUEVO EN V2)
    tiene_mediciones = Column(Boolean, default=False)
    mediciones_validadas = Column(Boolean, default=False)
    suma_parciales = Column(Numeric(12, 4))  # Suma calculada de mediciones parciales
    orden = Column(Integer)  # Para mantener orden original del PDF

    # Relaciones
    subcapitulo = relationship("Subcapitulo", back_populates="partidas")
    mediciones = relationship(
        "MedicionParcial",
        back_populates="partida",
        cascade="all, delete-orphan",
        order_by="MedicionParcial.orden"
    )

    def calcular_total_parciales(self):
        """Suma todos los subtotales de mediciones parciales"""
        if not self.mediciones:
            return 0.0
        return sum(float(m.subtotal or 0) for m in self.mediciones)

    def validar_mediciones(self, tolerancia=0.01):
        """
        Verifica que suma de parciales = cantidad_total

        Args:
            tolerancia: Diferencia máxima permitida (por redondeos)

        Returns:
            bool: True si es válido
        """
        if not self.mediciones:
            return True

        suma = self.calcular_total_parciales()
        diferencia = abs(suma - float(self.cantidad_total or 0))
        return diferencia < tolerancia

    def __repr__(self):
        return f"<Partida(codigo='{self.codigo}', cantidad={self.cantidad_total}, importe={self.importe})>"


class MedicionParcial(Base):
    """
    NUEVA TABLA V2: Medición parcial (descomposición dimensional)

    Almacena cada línea de medición de una partida con su descomposición:
    - Descripción: "En red acometida C.T."
    - Dimensiones: UDS x LONGITUD x ANCHURA x ALTURA
    - Subtotal: Resultado del cálculo dimensional
    """
    __tablename__ = 'mediciones_parciales'
    __table_args__ = (
        Index('idx_medicion_partida', 'partida_id'),
        {'schema': SCHEMA_V2}
    )

    id = Column(Integer, primary_key=True)
    partida_id = Column(Integer, ForeignKey(f'{SCHEMA_V2}.partidas.id'), nullable=False)
    orden = Column(Integer)  # Para mantener orden original del PDF

    # Descripción de la medición
    descripcion = Column(String(300))

    # Valores dimensionales
    uds = Column(Numeric(12, 4), default=1)
    longitud = Column(Numeric(12, 4), default=0)
    anchura = Column(Numeric(12, 4), default=0)
    altura = Column(Numeric(12, 4), default=0)
    parciales = Column(Numeric(12, 4), default=0)  # Campo intermedio (si existe en PDF)

    # Subtotal calculado (uds * longitud * anchura * altura o parciales)
    subtotal = Column(Numeric(12, 4))

    # Relación inversa
    partida = relationship("Partida", back_populates="mediciones")

    def calcular_subtotal(self):
        """
        Calcula el subtotal según los valores dimensionales

        Lógica:
        - Si parciales > 0: subtotal = uds * parciales
        - Si no: subtotal = uds * longitud * anchura * altura
        """
        uds = float(self.uds or 1)
        parciales = float(self.parciales or 0)

        if parciales > 0:
            return uds * parciales
        else:
            longitud = float(self.longitud or 0)
            anchura = float(self.anchura or 0)
            altura = float(self.altura or 0)
            return uds * longitud * anchura * altura

    def __repr__(self):
        return f"<MedicionParcial(desc='{self.descripcion[:30]}...', subtotal={self.subtotal})>"
