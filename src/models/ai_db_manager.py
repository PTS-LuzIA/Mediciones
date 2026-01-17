"""
Gestor de base de datos para proyectos procesados con IA.
Similar a DatabaseManager pero para las tablas ai_*.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typing import Dict
import os
import logging

from .db_models import Base
from .ai_models import AIProyecto, AICapitulo, AISubcapitulo, AIApartado, AIPartida

logger = logging.getLogger(__name__)


class AIDatabaseManager:
    """Gestor de base de datos para proyectos con IA"""

    def __init__(self, db_path='data/mediciones.db'):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        self.engine = create_engine(f'sqlite:///{db_path}', echo=False)
        Base.metadata.create_all(self.engine)

        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def guardar_estructura_ia(self, datos_ia: Dict) -> AIProyecto:
        """
        Guarda la estructura extraída por IA (formato FLAT)

        Args:
            datos_ia: dict con estructura extraída por el LLM en formato flat

        Returns:
            AIProyecto creado
        """
        logger.info(f"Guardando proyecto IA: {datos_ia.get('nombre', 'Sin nombre')}")

        # Crear proyecto
        proyecto = AIProyecto(
            nombre=datos_ia.get('nombre', 'Proyecto sin nombre'),
            descripcion=datos_ia.get('descripcion'),
            archivo_origen=datos_ia.get('archivo_origen'),
            modelo_usado=datos_ia.get('modelo_usado', 'google/gemini-2.5-flash-lite'),
            confianza_general=datos_ia.get('confianza_general'),
            notas_ia=datos_ia.get('notas_ia'),
            metadatos=datos_ia.get('metadatos'),
            tiempo_procesamiento=datos_ia.get('tiempo_procesamiento')
        )
        self.session.add(proyecto)
        self.session.flush()

        # Estructura FLAT: reconstruir jerarquía desde las partidas
        # Mapas para evitar duplicados
        capitulos_map = {}  # codigo -> AICapitulo
        subcapitulos_map = {}  # codigo -> AISubcapitulo
        apartados_map = {}  # codigo -> AIApartado

        logger.info(f"Procesando {len(datos_ia.get('partidas', []))} partidas...")

        for i, part_data in enumerate(datos_ia.get('partidas', [])):
            # 1. Crear/obtener capítulo
            cap_codigo = part_data.get('capitulo')
            cap_nombre = part_data.get('capitulo_nombre')

            if cap_codigo and cap_codigo not in capitulos_map:
                capitulo = AICapitulo(
                    proyecto_id=proyecto.id,
                    codigo=cap_codigo,
                    nombre=cap_nombre or f"Capítulo {cap_codigo}",
                    orden=len(capitulos_map),
                    confianza=part_data.get('confianza', 0.95),
                    notas=""
                )
                self.session.add(capitulo)
                self.session.flush()
                capitulos_map[cap_codigo] = capitulo

            capitulo = capitulos_map.get(cap_codigo)
            if not capitulo:
                logger.warning(f"Partida {part_data.get('codigo')} sin capítulo válido, saltando...")
                continue

            # 2. Crear/obtener subcapítulos (hasta 5 niveles)
            subcapitulo_actual = None
            for nivel in range(1, 6):
                sub_codigo = part_data.get(f'subcapitulo_{nivel}')
                sub_nombre = part_data.get(f'subcapitulo_{nivel}_nombre')

                if not sub_codigo:
                    break  # No hay más niveles

                if sub_codigo not in subcapitulos_map:
                    subcapitulo = AISubcapitulo(
                        capitulo_id=capitulo.id,
                        codigo=sub_codigo,
                        nombre=sub_nombre or f"Subcapítulo {sub_codigo}",
                        orden=len([s for s in subcapitulos_map.values() if s.capitulo_id == capitulo.id]),
                        confianza=part_data.get('confianza', 0.95),
                        notas=""
                    )
                    self.session.add(subcapitulo)
                    self.session.flush()
                    subcapitulos_map[sub_codigo] = subcapitulo

                subcapitulo_actual = subcapitulos_map[sub_codigo]

            if not subcapitulo_actual:
                logger.warning(f"Partida {part_data.get('codigo')} sin subcapítulo válido, saltando...")
                continue

            # 3. Crear partida asociada al último subcapítulo
            partida = AIPartida(
                subcapitulo_id=subcapitulo_actual.id,
                codigo=part_data.get('codigo'),
                unidad=part_data.get('unidad'),
                resumen=part_data.get('resumen', ''),
                descripcion=part_data.get('descripcion', ''),
                cantidad=part_data.get('cantidad', 0.0),
                precio=part_data.get('precio', 0.0),
                importe=part_data.get('importe', 0.0),
                orden=i,
                confianza=part_data.get('confianza'),
                notas=part_data.get('notas', '')
            )
            self.session.add(partida)

            # Log cada 100 partidas
            if (i + 1) % 100 == 0:
                logger.info(f"  Procesadas {i + 1} partidas...")

        self.session.commit()

        logger.info(f"✓ Guardadas {len(datos_ia.get('partidas', []))} partidas")
        logger.info(f"✓ Creados {len(capitulos_map)} capítulos, {len(subcapitulos_map)} subcapítulos")

        # Calcular totales
        self.calcular_totales(proyecto.id)

        logger.info(f"✓ Proyecto IA guardado con ID: {proyecto.id}")
        return proyecto

    def obtener_proyecto(self, proyecto_id: int) -> AIProyecto:
        """Obtiene un proyecto completo con todas sus relaciones"""
        return self.session.query(AIProyecto).filter_by(id=proyecto_id).first()

    def listar_proyectos(self):
        """Lista todos los proyectos IA"""
        return self.session.query(AIProyecto).order_by(AIProyecto.fecha_creacion.desc()).all()

    def calcular_totales(self, proyecto_id: int) -> float:
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
            for hijo in subcapitulo.subcapitulos:
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

    def guardar_solo_estructura(self, proyecto_id: int, estructura_ia: Dict) -> bool:
        """
        Guarda SOLO la estructura jerárquica (capítulos/subcapítulos) sin partidas.
        Este método se usa en la FASE 1 de extracción.

        Args:
            proyecto_id: ID del proyecto existente
            estructura_ia: Dict con estructura jerárquica extraída

        Returns:
            True si se guardó correctamente
        """
        logger.info(f"Guardando estructura para proyecto {proyecto_id}")

        proyecto = self.obtener_proyecto(proyecto_id)
        if not proyecto:
            logger.error(f"Proyecto {proyecto_id} no encontrado")
            return False

        # Limpiar capítulos/subcapítulos existentes (si los hay)
        for capitulo in proyecto.capitulos:
            self.session.delete(capitulo)
        self.session.commit()

        # Guardar nuevos capítulos y subcapítulos recursivamente
        def guardar_subcapitulos_recursivo(subcapitulos_data, capitulo_id, parent_id=None):
            """
            Guarda subcapítulos recursivamente con soporte para jerarquía multinivel.

            Args:
                subcapitulos_data: Lista de subcapítulos a guardar
                capitulo_id: ID del capítulo padre
                parent_id: ID del subcapítulo padre (None para nivel 1)
            """
            subcapitulos_creados = []
            for orden, sub_data in enumerate(subcapitulos_data):
                subcapitulo = AISubcapitulo(
                    capitulo_id=capitulo_id,
                    parent_id=parent_id,  # ✓ Ahora usamos parent_id correctamente
                    codigo=sub_data.get('codigo'),
                    nombre=sub_data.get('nombre', ''),
                    total=sub_data.get('total', 0.0),
                    orden=sub_data.get('orden', orden + 1),
                    confianza=sub_data.get('confianza', 0.95),
                    notas=sub_data.get('notas', '')
                )
                self.session.add(subcapitulo)
                self.session.flush()
                subcapitulos_creados.append(subcapitulo)

                # Procesar subcapítulos anidados si existen (recursivo)
                if sub_data.get('subcapitulos'):
                    guardar_subcapitulos_recursivo(
                        sub_data['subcapitulos'],
                        capitulo_id,
                        subcapitulo.id  # ✓ El ID actual se convierte en parent_id de sus hijos
                    )

            return subcapitulos_creados

        # Crear capítulos principales
        for orden, cap_data in enumerate(estructura_ia.get('capitulos', [])):
            capitulo = AICapitulo(
                proyecto_id=proyecto.id,
                codigo=cap_data.get('codigo'),
                nombre=cap_data.get('nombre', ''),
                total=cap_data.get('total', 0.0),
                orden=cap_data.get('orden', orden + 1),
                confianza=cap_data.get('confianza', 0.95),
                notas=cap_data.get('notas', '')
            )
            self.session.add(capitulo)
            self.session.flush()

            # Guardar subcapítulos recursivamente
            if cap_data.get('subcapitulos'):
                guardar_subcapitulos_recursivo(
                    cap_data['subcapitulos'],
                    capitulo.id
                )

        # Actualizar metadatos del proyecto
        if estructura_ia.get('confianza_general'):
            proyecto.confianza_general = estructura_ia['confianza_general']
        if estructura_ia.get('notas_ia'):
            proyecto.notas_ia = estructura_ia['notas_ia']

        self.session.commit()

        num_capitulos = len(estructura_ia.get('capitulos', []))
        logger.info(f"✓ Guardados {num_capitulos} capítulos con su estructura jerárquica")

        return True

    def guardar_partidas_capitulo(self, proyecto_id: int, capitulo_codigo: str, partidas_data: list) -> Dict:
        """
        Guarda las partidas de un capítulo específico asociándolas a sus subcapítulos

        Args:
            proyecto_id: ID del proyecto
            capitulo_codigo: Código del capítulo (ej: "01")
            partidas_data: Lista de partidas extraídas

        Returns:
            Dict con estadísticas de guardado
        """
        logger.info(f"Guardando {len(partidas_data)} partidas del capítulo {capitulo_codigo}")

        proyecto = self.obtener_proyecto(proyecto_id)
        if not proyecto:
            logger.error(f"Proyecto {proyecto_id} no encontrado")
            return {"success": False, "error": "Proyecto no encontrado"}

        # Obtener el capítulo
        capitulo = next((c for c in proyecto.capitulos if c.codigo == capitulo_codigo), None)
        if not capitulo:
            logger.error(f"Capítulo {capitulo_codigo} no encontrado")
            return {"success": False, "error": f"Capítulo {capitulo_codigo} no encontrado"}

        # Crear un mapa de subcapítulos por código para búsqueda rápida
        subcapitulos_map = {}

        def mapear_subcapitulos(subcaps):
            for sub in subcaps:
                subcapitulos_map[sub.codigo] = sub
                if sub.subcapitulos:
                    mapear_subcapitulos(sub.subcapitulos)

        mapear_subcapitulos(capitulo.subcapitulos)

        # Guardar partidas
        partidas_guardadas = 0
        partidas_sin_subcapitulo = 0

        for i, part_data in enumerate(partidas_data):
            subcapitulo_codigo = part_data.get('subcapitulo_codigo')
            subcapitulo = subcapitulos_map.get(subcapitulo_codigo)

            if not subcapitulo:
                logger.warning(f"Subcapítulo {subcapitulo_codigo} no encontrado para partida {part_data.get('codigo')}")
                partidas_sin_subcapitulo += 1
                continue

            # Mapear 'titulo' a 'resumen' para compatibilidad con el agente de extracción
            resumen_value = part_data.get('resumen') or part_data.get('titulo', '')

            partida = AIPartida(
                subcapitulo_id=subcapitulo.id,
                codigo=part_data.get('codigo', ''),
                unidad=part_data.get('unidad', ''),
                resumen=resumen_value,
                descripcion=part_data.get('descripcion', ''),
                cantidad=part_data.get('cantidad', 0.0),
                precio=part_data.get('precio', 0.0),
                importe=part_data.get('importe', 0.0),
                orden=i,
                confianza=part_data.get('confianza', 0.95),
                notas=part_data.get('notas', '')
            )
            self.session.add(partida)
            partidas_guardadas += 1

        self.session.commit()

        logger.info(f"✓ Guardadas {partidas_guardadas} partidas ({partidas_sin_subcapitulo} sin subcapítulo)")

        return {
            "success": True,
            "partidas_guardadas": partidas_guardadas,
            "partidas_sin_subcapitulo": partidas_sin_subcapitulo,
            "total": len(partidas_data)
        }

    def eliminar_proyecto(self, proyecto_id: int) -> bool:
        """Elimina un proyecto y todas sus relaciones"""
        proyecto = self.obtener_proyecto(proyecto_id)
        if proyecto:
            self.session.delete(proyecto)
            self.session.commit()
            return True
        return False

    def cerrar(self):
        """Cierra la sesión de base de datos"""
        self.session.close()
