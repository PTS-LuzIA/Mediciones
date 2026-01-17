"""
Modelos de base de datos para el sistema de mediciones.
Estructura jerárquica: Proyecto -> Capítulo -> Subcapítulo -> Apartado -> Partida
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import os

Base = declarative_base()


class Proyecto(Base):
    """Proyecto de obra completo"""
    __tablename__ = 'proyectos'

    id = Column(Integer, primary_key=True)
    nombre = Column(String(500), nullable=False)
    descripcion = Column(Text)
    fecha_creacion = Column(DateTime, default=datetime.now)
    archivo_origen = Column(String(500))
    presupuesto_total = Column(Float, default=0.0)

    # Relaciones
    capitulos = relationship("Capitulo", back_populates="proyecto", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Proyecto(id={self.id}, nombre='{self.nombre}')>"


class Capitulo(Base):
    """Capítulo principal (ej: C01 ACTUACIONES EN CALYPO FADO)"""
    __tablename__ = 'capitulos'

    id = Column(Integer, primary_key=True)
    proyecto_id = Column(Integer, ForeignKey('proyectos.id'), nullable=False)
    codigo = Column(String(50), nullable=False)
    nombre = Column(String(500), nullable=False)
    orden = Column(Integer, default=0)
    total = Column(Float, default=0.0)

    # Relaciones
    proyecto = relationship("Proyecto", back_populates="capitulos")
    subcapitulos = relationship("Subcapitulo", back_populates="capitulo", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Capitulo(codigo='{self.codigo}', nombre='{self.nombre}')>"


class Subcapitulo(Base):
    """Subcapítulo (ej: C08.01 CALLE TENERIFE)"""
    __tablename__ = 'subcapitulos'

    id = Column(Integer, primary_key=True)
    capitulo_id = Column(Integer, ForeignKey('capitulos.id'), nullable=False)
    parent_id = Column(Integer, ForeignKey('subcapitulos.id'), nullable=True)  # Para jerarquía recursiva
    codigo = Column(String(50), nullable=False)
    nombre = Column(String(500), nullable=False)
    orden = Column(Integer, default=0)
    total = Column(Float, default=0.0)

    # Relaciones
    capitulo = relationship("Capitulo", back_populates="subcapitulos")
    apartados = relationship("Apartado", back_populates="subcapitulo", cascade="all, delete-orphan")
    partidas = relationship("Partida", back_populates="subcapitulo", cascade="all, delete-orphan")

    # Relación recursiva para jerarquía de subcapítulos
    parent = relationship("Subcapitulo", remote_side=[id], back_populates="subcapitulos_hijos")
    subcapitulos_hijos = relationship("Subcapitulo", back_populates="parent", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Subcapitulo(codigo='{self.codigo}', nombre='{self.nombre}')>"


class Apartado(Base):
    """Apartado opcional (ej: C08.08.01 MURO ZONA DEPORTIVA)"""
    __tablename__ = 'apartados'

    id = Column(Integer, primary_key=True)
    subcapitulo_id = Column(Integer, ForeignKey('subcapitulos.id'), nullable=False)
    codigo = Column(String(50), nullable=False)
    nombre = Column(String(500), nullable=False)
    orden = Column(Integer, default=0)
    total = Column(Float, default=0.0)

    # Relaciones
    subcapitulo = relationship("Subcapitulo", back_populates="apartados")
    partidas = relationship("Partida", back_populates="apartado", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Apartado(codigo='{self.codigo}', nombre='{self.nombre}')>"


class Partida(Base):
    """Partida individual con mediciones"""
    __tablename__ = 'partidas'

    id = Column(Integer, primary_key=True)
    subcapitulo_id = Column(Integer, ForeignKey('subcapitulos.id'), nullable=True)
    apartado_id = Column(Integer, ForeignKey('apartados.id'), nullable=True)

    codigo = Column(String(50), nullable=False, index=True)
    unidad = Column(String(20), nullable=False)
    resumen = Column(Text, nullable=False)
    descripcion = Column(Text)
    cantidad = Column(Float, default=0.0)
    precio = Column(Float, default=0.0)
    importe = Column(Float, default=0.0)
    orden = Column(Integer, default=0)

    # Relaciones
    subcapitulo = relationship("Subcapitulo", back_populates="partidas")
    apartado = relationship("Apartado", back_populates="partidas")

    def __repr__(self):
        return f"<Partida(codigo='{self.codigo}', resumen='{self.resumen[:50]}...')>"

    def validar_importe(self, tolerancia=0.05):
        """Valida que cantidad × precio ≈ importe"""
        calculado = round(self.cantidad * self.precio, 2)
        diferencia = abs(calculado - self.importe)
        return diferencia <= tolerancia


class DatabaseManager:
    """Gestor de base de datos"""

    def __init__(self, db_path='data/mediciones.db'):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        self.engine = create_engine(f'sqlite:///{db_path}', echo=False)
        Base.metadata.create_all(self.engine)

        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def crear_proyecto(self, nombre, descripcion=None, archivo_origen=None):
        """Crea un nuevo proyecto"""
        proyecto = Proyecto(
            nombre=nombre,
            descripcion=descripcion,
            archivo_origen=archivo_origen
        )
        self.session.add(proyecto)
        self.session.commit()
        return proyecto

    def guardar_estructura(self, datos_extraidos):
        """
        Guarda la estructura completa extraída del PDF con soporte para jerarquía recursiva

        Args:
            datos_extraidos: dict con estructura jerárquica
        """
        proyecto = self.crear_proyecto(
            nombre=datos_extraidos.get('nombre', 'Proyecto sin nombre'),
            descripcion=datos_extraidos.get('descripcion'),
            archivo_origen=datos_extraidos.get('archivo_origen')
        )

        def guardar_subcapitulos_recursivo(subcapitulos_data, capitulo_id, parent_id=None):
            """
            Guarda subcapítulos recursivamente con soporte para múltiples niveles.

            Args:
                subcapitulos_data: Lista de subcapítulos a guardar
                capitulo_id: ID del capítulo padre
                parent_id: ID del subcapítulo padre (None para nivel 1)
            """
            for sub_data in subcapitulos_data:
                subcapitulo = Subcapitulo(
                    capitulo_id=capitulo_id,
                    parent_id=parent_id,
                    codigo=sub_data['codigo'],
                    nombre=sub_data['nombre'],
                    orden=sub_data.get('orden', 0)
                )
                self.session.add(subcapitulo)
                self.session.flush()

                # Apartados (opcional)
                for apt_data in sub_data.get('apartados', []):
                    apartado = Apartado(
                        subcapitulo_id=subcapitulo.id,
                        codigo=apt_data['codigo'],
                        nombre=apt_data['nombre'],
                        orden=apt_data.get('orden', 0)
                    )
                    self.session.add(apartado)
                    self.session.flush()

                    # Partidas del apartado
                    for part_data in apt_data.get('partidas', []):
                        partida = Partida(
                            apartado_id=apartado.id,
                            **part_data
                        )
                        self.session.add(partida)

                # Partidas directas del subcapítulo
                for part_data in sub_data.get('partidas', []):
                    partida = Partida(
                        subcapitulo_id=subcapitulo.id,
                        **part_data
                    )
                    self.session.add(partida)

                # Recursión: procesar subcapítulos hijos si existen
                if sub_data.get('subcapitulos_hijos'):
                    guardar_subcapitulos_recursivo(
                        sub_data['subcapitulos_hijos'],
                        capitulo_id,
                        subcapitulo.id  # El ID actual se convierte en parent_id de sus hijos
                    )

        for cap_data in datos_extraidos.get('capitulos', []):
            capitulo = Capitulo(
                proyecto_id=proyecto.id,
                codigo=cap_data['codigo'],
                nombre=cap_data['nombre'],
                orden=cap_data.get('orden', 0)
            )
            self.session.add(capitulo)
            self.session.flush()

            # Guardar subcapítulos recursivamente
            guardar_subcapitulos_recursivo(
                cap_data.get('subcapitulos', []),
                capitulo.id
            )

        self.session.commit()
        return proyecto

    def obtener_proyecto(self, proyecto_id):
        """Obtiene un proyecto completo con todas sus relaciones"""
        return self.session.query(Proyecto).filter_by(id=proyecto_id).first()

    def listar_proyectos(self):
        """Lista todos los proyectos"""
        return self.session.query(Proyecto).all()

    def calcular_totales(self, proyecto_id):
        """Calcula y actualiza los totales de todo el proyecto"""
        proyecto = self.obtener_proyecto(proyecto_id)
        if not proyecto:
            return None

        def calcular_total_subcapitulo_recursivo(subcapitulo) -> float:
            """Calcula el total de un subcapítulo incluyendo todos sus hijos recursivamente"""
            total = 0.0

            # Sumar partidas directas
            for partida in subcapitulo.partidas:
                total += partida.importe

            # Sumar partidas de apartados
            for apartado in subcapitulo.apartados:
                total_apartado = sum(p.importe for p in apartado.partidas)
                apartado.total = total_apartado
                total += total_apartado

            # Sumar subcapítulos hijos recursivamente
            for hijo in subcapitulo.subcapitulos_hijos:
                total += calcular_total_subcapitulo_recursivo(hijo)

            subcapitulo.total = total
            return total

        total_proyecto = 0.0

        for capitulo in proyecto.capitulos:
            total_capitulo = 0.0

            # Calcular totales de subcapítulos de nivel 1 (que incluirán recursivamente sus hijos)
            for subcapitulo in capitulo.subcapitulos:
                if not subcapitulo.parent_id:  # Solo procesar subcapítulos de nivel 1
                    total_capitulo += calcular_total_subcapitulo_recursivo(subcapitulo)

            capitulo.total = total_capitulo
            total_proyecto += total_capitulo

        proyecto.presupuesto_total = total_proyecto
        self.session.commit()

        return total_proyecto

    def cerrar(self):
        """Cierra la sesión de base de datos"""
        self.session.close()


if __name__ == "__main__":
    # Test básico
    db = DatabaseManager('data/test_mediciones.db')

    proyecto = db.crear_proyecto(
        nombre="Test Proyecto DANA",
        descripcion="Proyecto de prueba"
    )

    print(f"✓ Proyecto creado: {proyecto}")

    db.cerrar()
    print("✓ Base de datos creada correctamente")
