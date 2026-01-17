"""
Gestor de base de datos para proyectos HÍBRIDOS.
Maneja las 3 fases del procesamiento híbrido.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typing import Dict, List
import os
import logging

from .db_models import Base
from .hybrid_models import (
    HybridProyecto, HybridCapitulo, HybridSubcapitulo, HybridApartado, HybridPartida,
    EstadoValidacion, FaseProyecto
)

logger = logging.getLogger(__name__)


class HybridDatabaseManager:
    """Gestor de base de datos para proyectos híbridos"""

    def __init__(self, db_path='data/mediciones.db'):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        self.engine = create_engine(f'sqlite:///{db_path}', echo=False)
        Base.metadata.create_all(self.engine)

        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def crear_proyecto(self, nombre: str, descripcion: str = None, archivo_origen: str = None) -> HybridProyecto:
        """
        Crea un nuevo proyecto híbrido vacío (Fase: CREADO)

        Args:
            nombre: Nombre del proyecto
            descripcion: Descripción opcional
            archivo_origen: Ruta al PDF original

        Returns:
            HybridProyecto creado
        """
        proyecto = HybridProyecto(
            nombre=nombre,
            descripcion=descripcion,
            archivo_origen=archivo_origen,
            fase_actual=FaseProyecto.CREADO
        )
        self.session.add(proyecto)
        self.session.commit()

        logger.info(f"✓ Proyecto híbrido creado: ID={proyecto.id}, nombre='{nombre}'")
        return proyecto

    def guardar_estructura_fase1(self, proyecto_id: int, estructura_ia: Dict, tiempo_segundos: float) -> bool:
        """
        FASE 1: Guarda la estructura extraída por IA (capítulos/subcapítulos + totales)

        Args:
            proyecto_id: ID del proyecto híbrido
            estructura_ia: Estructura extraída por StructureExtractionAgent
            tiempo_segundos: Tiempo que tardó la extracción

        Returns:
            True si se guardó correctamente
        """
        try:
            proyecto = self.session.query(HybridProyecto).filter_by(id=proyecto_id).first()
            if not proyecto:
                logger.error(f"Proyecto {proyecto_id} no encontrado")
                return False

            logger.info(f"[FASE 1] Guardando estructura IA para proyecto {proyecto_id}")

            # Actualizar proyecto
            proyecto.fase_actual = FaseProyecto.FASE1_ESTRUCTURA
            proyecto.nombre = estructura_ia.get('nombre', proyecto.nombre)
            proyecto.tiempo_fase1 = tiempo_segundos

            # Guardar capítulos y subcapítulos recursivamente
            total_estructura = 0.0

            for cap_data in estructura_ia.get('capitulos', []):
                capitulo = HybridCapitulo(
                    proyecto_id=proyecto.id,
                    codigo=cap_data['codigo'],
                    nombre=cap_data['nombre'],
                    orden=cap_data.get('orden', 0),
                    total_ia=cap_data.get('total', 0.0),
                    num_partidas_ia=cap_data.get('num_partidas', 0),
                    confianza_ia=cap_data.get('confianza', 0.95),
                    notas=cap_data.get('notas', ''),
                    estado_validacion=EstadoValidacion.PENDIENTE
                )
                self.session.add(capitulo)
                self.session.flush()

                total_estructura += cap_data.get('total', 0.0)

                # Guardar subcapítulos recursivamente
                self._guardar_subcapitulos_recursivo(
                    cap_data.get('subcapitulos', []),
                    capitulo.id,
                    parent_id=None
                )

            proyecto.total_estructura_ia = total_estructura
            self.session.commit()

            logger.info(f"✓ [FASE 1] Estructura guardada: {len(estructura_ia.get('capitulos', []))} capítulos, total={total_estructura:.2f} €")
            return True

        except Exception as e:
            logger.error(f"❌ [FASE 1] Error guardando estructura: {e}")
            self.session.rollback()
            return False

    def _guardar_subcapitulos_recursivo(self, subcapitulos_data: List[Dict], capitulo_id: int, parent_id: int = None):
        """Helper recursivo para guardar subcapítulos con jerarquía"""
        for sub_data in subcapitulos_data:
            subcapitulo = HybridSubcapitulo(
                capitulo_id=capitulo_id,
                parent_id=parent_id,
                codigo=sub_data['codigo'],
                nombre=sub_data['nombre'],
                orden=sub_data.get('orden', 0),
                total_ia=sub_data.get('total', 0.0),
                num_partidas_ia=sub_data.get('num_partidas', 0),
                confianza_ia=sub_data.get('confianza', 0.95),
                notas_ia=sub_data.get('notas', ''),
                estado_validacion=EstadoValidacion.PENDIENTE
            )
            self.session.add(subcapitulo)
            self.session.flush()

            # Recursión: procesar subcapítulos hijos
            if sub_data.get('subcapitulos'):
                self._guardar_subcapitulos_recursivo(
                    sub_data['subcapitulos'],
                    capitulo_id,
                    subcapitulo.id
                )

    def guardar_partidas_fase2(self, proyecto_id: int, partidas_locales: List[Dict], tiempo_segundos: float) -> Dict:
        """
        FASE 2: Guarda las partidas extraídas por el parser local

        Args:
            proyecto_id: ID del proyecto híbrido
            partidas_locales: Lista de partidas extraídas por PartidaParser
            tiempo_segundos: Tiempo que tardó la extracción

        Returns:
            Dict con estadísticas del guardado
        """
        try:
            proyecto = self.session.query(HybridProyecto).filter_by(id=proyecto_id).first()
            if not proyecto:
                return {"success": False, "error": f"Proyecto {proyecto_id} no encontrado"}

            logger.info(f"[FASE 2] Guardando {len(partidas_locales)} partidas para proyecto {proyecto_id}")
            logger.warning("🔧 [FASE 2] CÓDIGO MODIFICADO: NO se crearán subcapítulos automáticamente - Versión 2026-01-14")

            # LIMPIEZA: Borrar partidas y apartados previos antes de re-procesar
            # Esto evita duplicados si se vuelve a ejecutar la Fase 2
            # IMPORTANTE: NO se borran los subcapítulos creados en Fase 1 (IA)
            partidas_previas = self.session.query(HybridPartida).join(
                HybridCapitulo
            ).filter(
                HybridCapitulo.proyecto_id == proyecto_id
            ).count()

            if partidas_previas > 0:
                logger.info(f"[FASE 2] Limpiando {partidas_previas} partidas previas del proyecto")

                # Obtener IDs de partidas a borrar (no se puede delete con join)
                partidas_ids = [p.id for p in self.session.query(HybridPartida.id).join(
                    HybridCapitulo
                ).filter(
                    HybridCapitulo.proyecto_id == proyecto_id
                ).all()]

                if partidas_ids:
                    self.session.query(HybridPartida).filter(
                        HybridPartida.id.in_(partidas_ids)
                    ).delete(synchronize_session=False)

                # Obtener IDs de apartados a borrar
                apartados_ids = [a.id for a in self.session.query(HybridApartado.id).join(
                    HybridSubcapitulo
                ).join(
                    HybridCapitulo
                ).filter(
                    HybridCapitulo.proyecto_id == proyecto_id
                ).all()]

                if apartados_ids:
                    self.session.query(HybridApartado).filter(
                        HybridApartado.id.in_(apartados_ids)
                    ).delete(synchronize_session=False)

                # Resetear totales locales a 0 (se recalcularán al final de la fase 2)
                for capitulo in proyecto.capitulos:
                    capitulo.total_local = 0.0
                    for subcapitulo in capitulo.subcapitulos:
                        self._resetear_totales_subcapitulo_recursivo(subcapitulo)

                self.session.commit()
                logger.info(f"✓ [FASE 2] Limpieza completada")

            # Actualizar proyecto
            proyecto.fase_actual = FaseProyecto.FASE2_PARTIDAS
            proyecto.tiempo_fase2 = tiempo_segundos

            partidas_guardadas = 0
            partidas_sin_subcapitulo = 0

            # 🔧 OPTIMIZACIÓN: Pre-cargar TODOS los subcapítulos existentes en BD en un mapa
            # Esto permite buscar rápidamente sin recorrer recursivamente cada vez
            subcapitulos_map = {}
            logger.info(f"[FASE 2] 🔍 Pre-cargando estructura de subcapítulos desde BD...")
            for cap in proyecto.capitulos:
                self._precargar_subcapitulos_recursivo(cap.subcapitulos, subcapitulos_map)

            logger.info(f"[FASE 2] ✓ Pre-cargados {len(subcapitulos_map)} subcapítulos desde BD")

            # Mapa de capítulos para acceso rápido
            capitulos_map = {cap.codigo: cap for cap in proyecto.capitulos}

            for part_data in partidas_locales:
                # Buscar subcapítulo correspondiente por código
                subcap_codigo = part_data.get('subcapitulo') or part_data.get('codigo_subcapitulo')
                apt_codigo = part_data.get('apartado') or part_data.get('codigo_apartado')
                codigo_partida = part_data.get('codigo', '')
                codigo_capitulo = part_data.get('capitulo')

                subcapitulo = None
                apartado = None

                # Si no hay subcap_codigo, intentar inferirlo del código de partida
                # SOLO si el código de partida tiene formato numérico estándar (ej: "01.05.001")
                # NO para códigos alfanuméricos como "DEM06", "U01AB100", etc.
                if not subcap_codigo and codigo_partida:
                    partes_partida = codigo_partida.split('.')
                    # Solo inferir si tiene 3+ partes Y todas son numéricas
                    if len(partes_partida) >= 3 and all(p.isdigit() for p in partes_partida[:-1]):
                        subcap_codigo = '.'.join(partes_partida[:-1])
                        logger.debug(f"Inferido subcapítulo {subcap_codigo} desde código partida {codigo_partida}")

                if subcap_codigo:
                    # 🔍 BÚSQUEDA OPTIMIZADA: Primero buscar en el mapa pre-cargado de BD
                    if subcap_codigo in subcapitulos_map:
                        subcapitulo = subcapitulos_map[subcap_codigo]
                        logger.debug(f"✓ Subcapítulo {subcap_codigo} encontrado en BD (pre-cargado)")
                    else:
                        # Subcapítulo NO existe en Fase 1
                        # Buscar padre más cercano que SÍ exista
                        partes = subcap_codigo.split('.')
                        subcap_padre = None

                        for i in range(len(partes)-1, 0, -1):
                            codigo_padre_posible = '.'.join(partes[:i])
                            if codigo_padre_posible in subcapitulos_map:
                                subcap_padre = codigo_padre_posible
                                break

                        if subcap_padre:
                            # Asignar al padre que SÍ existe
                            subcapitulo = subcapitulos_map[subcap_padre]
                            logger.warning(f"[FASE 2] ⚠️ Partida {codigo_partida}: subcapítulo '{subcap_codigo}' NO existe. Asignada a padre '{subcap_padre}'")
                        else:
                            # No hay padre, rechazar partida
                            partidas_sin_subcapitulo += 1
                            logger.warning(f"[FASE 2] ⚠️ Partida {codigo_partida}: subcapítulo {subcap_codigo} NO existe y no se encontró padre. Partida rechazada.")
                            continue

                # Si no hay subcapítulo, buscar el capítulo padre para asignar la partida directamente
                capitulo_partida = None
                if not subcapitulo and codigo_capitulo:
                    capitulo_partida = capitulos_map.get(codigo_capitulo)
                    if capitulo_partida:
                        logger.debug(f"Partida {codigo_partida} sin subcapítulo → asignada directamente al capítulo {codigo_capitulo}")
                    else:
                        partidas_sin_subcapitulo += 1
                        logger.warning(f"Partida {codigo_partida}: capítulo {codigo_capitulo} no encontrado")
                        continue
                elif not subcapitulo:
                    partidas_sin_subcapitulo += 1
                    logger.warning(f"Partida {codigo_partida} sin subcapítulo ni capítulo válido - se omite")
                    continue

                # Buscar apartado si existe (solo si hay subcapítulo)
                if apt_codigo and subcapitulo:
                    apartado = next((apt for apt in subcapitulo.apartados if apt.codigo == apt_codigo), None)
                    if not apartado:
                        # Crear apartado si no existe
                        apartado = HybridApartado(
                            subcapitulo_id=subcapitulo.id,
                            codigo=apt_codigo,
                            nombre=part_data.get('apartado_nombre', f"Apartado {apt_codigo}"),
                            orden=len(subcapitulo.apartados)
                        )
                        self.session.add(apartado)
                        self.session.flush()

                # Crear partida
                # Determinar padre: apartado > subcapítulo > capítulo
                partida = HybridPartida(
                    capitulo_id=capitulo_partida.id if capitulo_partida else None,
                    subcapitulo_id=subcapitulo.id if subcapitulo and not apartado else None,
                    apartado_id=apartado.id if apartado else None,
                    codigo=part_data['codigo'],
                    unidad=part_data['unidad'],
                    resumen=part_data['resumen'],
                    descripcion=part_data.get('descripcion', ''),
                    cantidad=part_data.get('cantidad', 0.0),
                    precio=part_data.get('precio', 0.0),
                    importe=part_data.get('importe', 0.0),
                    orden=part_data.get('orden', 0),
                    extraido_por='local'
                )
                self.session.add(partida)
                partidas_guardadas += 1

            self.session.commit()

            # Calcular totales locales
            self._calcular_totales_locales(proyecto_id)

            # Estadísticas finales
            # Contar cuántos subcapítulos hay ahora en BD (después de crear los faltantes)
            subcapitulos_totales_bd = 0
            for cap in proyecto.capitulos:
                subcapitulos_totales_bd += len(self._contar_subcapitulos_plano(cap.subcapitulos))

            subcapitulos_iniciales = len(subcapitulos_map)
            subcapitulos_creados = subcapitulos_totales_bd - subcapitulos_iniciales

            logger.info(f"✓ [FASE 2] {partidas_guardadas} partidas guardadas, {partidas_sin_subcapitulo} sin subcapítulo")
            logger.info(f"[FASE 2] 📊 Subcapítulos en BD (Fase 1): {subcapitulos_iniciales}")
            logger.info(f"[FASE 2] 📊 Subcapítulos en BD (después): {subcapitulos_totales_bd}")
            if subcapitulos_creados > 0:
                logger.warning(f"[FASE 2] ⚠️ Subcapítulos creados automáticamente (no estaban en Fase 1): {subcapitulos_creados}")

            return {
                "success": True,
                "partidas_guardadas": partidas_guardadas,
                "partidas_sin_subcapitulo": partidas_sin_subcapitulo,
                "subcapitulos_bd_inicial": subcapitulos_iniciales,
                "subcapitulos_bd_final": subcapitulos_totales_bd,
                "subcapitulos_creados": subcapitulos_creados
            }

        except Exception as e:
            logger.error(f"❌ [FASE 2] Error guardando partidas: {e}")
            self.session.rollback()
            return {"success": False, "error": str(e)}

    def guardar_partidas_fase2_dirigido(self, proyecto_id: int, partidas_por_subcapitulo: Dict[str, List[Dict]], tiempo_segundos: float) -> Dict:
        """
        Guarda partidas extraídas con el método dirigido (por subcapítulo).

        Args:
            proyecto_id: ID del proyecto híbrido
            partidas_por_subcapitulo: Dict con código_subcapitulo -> lista de partidas
            tiempo_segundos: Tiempo que tardó la extracción

        Returns:
            Dict con estadísticas del guardado
        """
        try:
            proyecto = self.session.query(HybridProyecto).filter_by(id=proyecto_id).first()
            if not proyecto:
                return {"success": False, "error": f"Proyecto {proyecto_id} no encontrado"}

            total_partidas = sum(len(partidas) for partidas in partidas_por_subcapitulo.values())
            logger.info(f"[FASE 2 DIRIGIDO] Guardando {total_partidas} partidas para proyecto {proyecto_id}")

            # LIMPIEZA: Borrar partidas previas
            partidas_previas = self.session.query(HybridPartida).join(
                HybridCapitulo
            ).filter(
                HybridCapitulo.proyecto_id == proyecto_id
            ).count()

            if partidas_previas > 0:
                logger.info(f"[FASE 2] Limpiando {partidas_previas} partidas previas del proyecto")
                partidas_ids = [p.id for p in self.session.query(HybridPartida.id).join(
                    HybridCapitulo
                ).filter(
                    HybridCapitulo.proyecto_id == proyecto_id
                ).all()]

                if partidas_ids:
                    self.session.query(HybridPartida).filter(
                        HybridPartida.id.in_(partidas_ids)
                    ).delete(synchronize_session=False)

                # Resetear totales locales
                for capitulo in proyecto.capitulos:
                    capitulo.total_local = 0.0
                    for subcapitulo in capitulo.subcapitulos:
                        self._resetear_totales_subcapitulo_recursivo(subcapitulo)

                self.session.commit()

            # Actualizar proyecto
            proyecto.fase_actual = FaseProyecto.FASE2_PARTIDAS
            proyecto.tiempo_fase2 = tiempo_segundos

            # Crear mapa de subcapítulos en BD
            subcapitulos_map = {}

            def mapear_subcapitulos(subcaps, cap_id):
                for subcap in subcaps:
                    subcapitulos_map[subcap.codigo] = subcap
                    mapear_subcapitulos(subcap.subcapitulos_hijos, cap_id)

            for cap in proyecto.capitulos:
                for subcap in cap.subcapitulos:
                    mapear_subcapitulos([subcap], cap.id)

            logger.info(f"[FASE 2] Mapa de subcapítulos: {len(subcapitulos_map)} subcapítulos en BD")

            # Guardar partidas por subcapítulo
            partidas_guardadas = 0
            partidas_sin_subcapitulo = 0

            for codigo_subcap, partidas in partidas_por_subcapitulo.items():
                if codigo_subcap not in subcapitulos_map:
                    logger.warning(f"[FASE 2] ⚠️ Subcapítulo '{codigo_subcap}' NO existe en BD (Fase 1). Partidas: {len(partidas)}")
                    partidas_sin_subcapitulo += len(partidas)
                    continue

                subcapitulo = subcapitulos_map[codigo_subcap]

                for i, part_data in enumerate(partidas):
                    partida = HybridPartida(
                        codigo=part_data.get('codigo'),
                        unidad=part_data.get('unidad'),
                        resumen=part_data.get('resumen'),
                        descripcion=part_data.get('descripcion', ''),
                        cantidad=part_data.get('cantidad', 0.0),
                        precio=part_data.get('precio', 0.0),
                        importe=part_data.get('importe', 0.0),
                        orden=i,
                        extraido_por='local',
                        subcapitulo_id=subcapitulo.id
                    )
                    self.session.add(partida)
                    partidas_guardadas += 1

            self.session.commit()

            # Calcular totales locales
            self._calcular_totales_locales(proyecto_id)
            # Commit después del cálculo para persistir los totales
            self.session.commit()

            logger.info(f"✓ [FASE 2 DIRIGIDO] {partidas_guardadas} partidas guardadas")
            if partidas_sin_subcapitulo > 0:
                logger.warning(f"⚠️ [FASE 2 DIRIGIDO] {partidas_sin_subcapitulo} partidas sin subcapítulo (ignoradas)")

            return {
                "success": True,
                "partidas_guardadas": partidas_guardadas,
                "partidas_sin_subcapitulo": partidas_sin_subcapitulo
            }

        except Exception as e:
            logger.error(f"❌ [FASE 2 DIRIGIDO] Error guardando partidas: {e}")
            self.session.rollback()
            return {"success": False, "error": str(e)}

    def _resetear_totales_subcapitulo_recursivo(self, subcapitulo) -> None:
        """
        Resetea los totales locales de un subcapítulo y sus hijos recursivamente a 0

        Args:
            subcapitulo: Objeto HybridSubcapitulo
        """
        subcapitulo.total_local = 0.0

        # Resetear subcapítulos hijos recursivamente
        for hijo in subcapitulo.subcapitulos_hijos:
            self._resetear_totales_subcapitulo_recursivo(hijo)

    def _precargar_subcapitulos_recursivo(self, subcapitulos, mapa: dict) -> None:
        """
        Pre-carga todos los subcapítulos de la BD en un diccionario para búsqueda rápida

        Args:
            subcapitulos: Lista de objetos HybridSubcapitulo
            mapa: Diccionario {codigo: subcapitulo_obj} donde se guardan
        """
        for sub in subcapitulos:
            mapa[sub.codigo] = sub
            logger.debug(f"[FASE 2] Pre-cargado subcapítulo {sub.codigo} - {sub.nombre}")
            # Recursión: pre-cargar hijos
            if sub.subcapitulos_hijos:
                self._precargar_subcapitulos_recursivo(sub.subcapitulos_hijos, mapa)

    def _contar_subcapitulos_plano(self, subcapitulos) -> List:
        """
        Obtiene lista plana de todos los subcapítulos recursivamente

        Args:
            subcapitulos: Lista de objetos HybridSubcapitulo

        Returns:
            Lista plana con todos los subcapítulos (incluyendo hijos)
        """
        resultado = []
        for sub in subcapitulos:
            resultado.append(sub)
            if sub.subcapitulos_hijos:
                resultado.extend(self._contar_subcapitulos_plano(sub.subcapitulos_hijos))
        return resultado

    def _buscar_subcapitulo_por_codigo(self, subcapitulos, codigo: str):
        """Helper recursivo para buscar un subcapítulo por código"""
        for sub in subcapitulos:
            if sub.codigo == codigo:
                return sub
            # Buscar en hijos
            if sub.subcapitulos_hijos:
                encontrado = self._buscar_subcapitulo_por_codigo(sub.subcapitulos_hijos, codigo)
                if encontrado:
                    return encontrado
        return None

    def _crear_jerarquia_subcapitulos(self, capitulo, codigo_completo: str, subcapitulos_map: dict):
        """
        Crea la jerarquía completa de subcapítulos necesaria para un código.
        Maneja códigos como "01.05", "01.05.02", "01.05.02.03", etc.
        Similar a la lógica del local_partida_parser.py

        Args:
            capitulo: Objeto capítulo padre
            codigo_completo: Código completo del subcapítulo (ej: "01.05.02")
            subcapitulos_map: Diccionario de subcapítulos ya creados

        Returns:
            Subcapítulo final creado
        """
        partes = codigo_completo.split('.')

        # Necesitamos al menos 2 partes (capitulo.subcapitulo)
        if len(partes) < 2:
            return None

        subcapitulo_actual = None

        # Crear cada nivel de la jerarquía
        for i in range(2, len(partes) + 1):
            codigo_nivel = '.'.join(partes[:i])

            # Si ya existe en el mapa, reutilizarlo
            if codigo_nivel in subcapitulos_map:
                subcapitulo_actual = subcapitulos_map[codigo_nivel]
                continue

            # Determinar el padre
            if i == 2:  # Nivel 1: padre es el capítulo
                parent_id = None
                parent_obj = capitulo
                orden = len(capitulo.subcapitulos)
            else:  # Nivel 2+: padre es el subcapítulo anterior
                codigo_padre = '.'.join(partes[:i-1])
                if codigo_padre in subcapitulos_map:
                    parent_obj = subcapitulos_map[codigo_padre]
                    parent_id = parent_obj.id
                    orden = len(parent_obj.subcapitulos_hijos)
                else:
                    logger.error(f"Padre {codigo_padre} no encontrado al crear {codigo_nivel}")
                    return None

            # Determinar nombre del subcapítulo
            # Si es un subcapítulo virtual .00, darle nombre descriptivo
            if codigo_nivel.endswith('.00'):
                nombre_subcap = f"Partidas directas del capítulo {capitulo.codigo}"
            else:
                nombre_subcap = f"Subcapítulo {codigo_nivel}"

            # Crear nuevo subcapítulo
            nuevo_subcapitulo = HybridSubcapitulo(
                capitulo_id=capitulo.id,
                parent_id=parent_id,
                codigo=codigo_nivel,
                nombre=nombre_subcap,
                total_ia=0.0,
                total_local=0.0,
                total_final=0.0,
                estado_validacion=EstadoValidacion.PENDIENTE,
                orden=orden
            )

            self.session.add(nuevo_subcapitulo)
            self.session.flush()  # Para obtener el ID

            # Guardar en mapa
            subcapitulos_map[codigo_nivel] = nuevo_subcapitulo
            subcapitulo_actual = nuevo_subcapitulo

            logger.info(f"[FASE 2] Creado subcapítulo {codigo_nivel} (nivel {i-1})")

        return subcapitulo_actual

    def _calcular_totales_locales(self, proyecto_id: int):
        """Calcula totales locales y conteo de partidas a partir de las partidas extraídas"""
        proyecto = self.session.query(HybridProyecto).filter_by(id=proyecto_id).first()
        if not proyecto:
            return

        total_proyecto = 0.0

        for capitulo in proyecto.capitulos:
            total_capitulo = 0.0
            num_partidas_capitulo = 0

            # Contar y sumar partidas directas del capítulo (sin subcapítulo)
            for partida in capitulo.partidas:
                total_capitulo += partida.importe
                num_partidas_capitulo += 1

            # Sumar subcapítulos recursivamente
            for subcapitulo in capitulo.subcapitulos:
                if not subcapitulo.parent_id:  # Solo nivel 1
                    total_subcap, num_partidas_subcap = self._calcular_total_subcapitulo_recursivo(subcapitulo)
                    total_capitulo += total_subcap
                    num_partidas_capitulo += num_partidas_subcap

            capitulo.total_local = total_capitulo
            capitulo.num_partidas_local = num_partidas_capitulo
            total_proyecto += total_capitulo

        proyecto.total_partidas_local = total_proyecto
        self.session.commit()

    def _calcular_total_subcapitulo_recursivo(self, subcapitulo) -> tuple:
        """
        Calcula total y conteo de partidas de un subcapítulo recursivamente

        Returns:
            tuple: (total_euros, num_partidas)
        """
        total = 0.0
        num_partidas = 0

        # Contar y sumar partidas directas
        for partida in subcapitulo.partidas:
            total += partida.importe
            num_partidas += 1

        # Contar y sumar partidas de apartados
        for apartado in subcapitulo.apartados:
            for partida in apartado.partidas:
                total += partida.importe
                num_partidas += 1
            apartado.total = sum(p.importe for p in apartado.partidas)

        # Sumar subcapítulos hijos recursivamente
        for hijo in subcapitulo.subcapitulos_hijos:
            total_hijo, num_partidas_hijo = self._calcular_total_subcapitulo_recursivo(hijo)
            total += total_hijo
            num_partidas += num_partidas_hijo

        subcapitulo.total_local = total
        subcapitulo.num_partidas_local = num_partidas
        return total, num_partidas

    def validar_fase3(self, proyecto_id: int, tolerancia_porcentaje: float = 5.0) -> Dict:
        """
        FASE 3: Valida coincidencia entre totales IA vs totales locales

        Args:
            proyecto_id: ID del proyecto
            tolerancia_porcentaje: % de tolerancia para considerar coincidencia (default: 5%)

        Returns:
            Dict con resultados de validación
        """
        try:
            proyecto = self.session.query(HybridProyecto).filter_by(id=proyecto_id).first()
            if not proyecto:
                return {"success": False, "error": f"Proyecto {proyecto_id} no encontrado"}

            logger.info(f"[FASE 3] Validando proyecto {proyecto_id} (tolerancia: ±{tolerancia_porcentaje}%)")

            proyecto.fase_actual = FaseProyecto.FASE3_VALIDACION

            validados = 0
            discrepancias = 0
            elementos_a_revisar = []  # Capítulos y subcapítulos con discrepancias

            for capitulo in proyecto.capitulos:
                # Validar cada subcapítulo recursivamente
                for subcapitulo in capitulo.subcapitulos:
                    resultado = self._validar_subcapitulo_recursivo(subcapitulo, tolerancia_porcentaje)
                    validados += resultado['validados']
                    discrepancias += resultado['discrepancias']
                    elementos_a_revisar.extend(resultado['a_revisar'])

                # Validar capítulo completo
                if self._validar_elemento(capitulo, tolerancia_porcentaje):
                    # Capítulo validado - solo si no tiene subcapítulos (si tiene, ya se validaron arriba)
                    if not capitulo.subcapitulos:
                        validados += 1
                else:
                    # Capítulo con discrepancia
                    if not capitulo.subcapitulos:
                        discrepancias += 1

                    # Si necesita revisión IA, agregarlo a la lista
                    if capitulo.necesita_revision_ia and capitulo.total_ia > 0 and capitulo.total_local > 0:
                        elementos_a_revisar.append({
                            "tipo": "capitulo",
                            "codigo": capitulo.codigo,
                            "nombre": capitulo.nombre,
                            "total_ia": capitulo.total_ia,
                            "total_local": capitulo.total_local,
                            "num_partidas_ia": capitulo.num_partidas_ia,
                            "num_partidas_local": capitulo.num_partidas_local,
                            "diferencia_euros": capitulo.diferencia_euros,
                            "diferencia_porcentaje": capitulo.diferencia_porcentaje,
                            "capitulo_id": capitulo.id
                        })

            # Calcular coincidencia global
            if proyecto.total_estructura_ia > 0:
                diferencia = abs(proyecto.total_estructura_ia - proyecto.total_partidas_local)
                proyecto.porcentaje_coincidencia = 100 - (diferencia / proyecto.total_estructura_ia * 100)
            else:
                proyecto.porcentaje_coincidencia = 0.0

            proyecto.subcapitulos_validados = validados
            proyecto.subcapitulos_con_discrepancia = discrepancias

            # Marcar como completado solo si no hay elementos pendientes de revisar
            if elementos_a_revisar:
                proyecto.fase_actual = FaseProyecto.FASE3_VALIDACION
            else:
                proyecto.fase_actual = FaseProyecto.COMPLETADO

            self.session.commit()

            logger.info(f"✓ [FASE 3] Validación completada: {validados} OK, {discrepancias} discrepancias")
            if elementos_a_revisar:
                logger.warning(f"⚠️ [FASE 3] {len(elementos_a_revisar)} elementos necesitan revisión IA")

            return {
                "success": True,
                "validados": validados,
                "discrepancias": discrepancias,
                "elementos_a_revisar": elementos_a_revisar,
                "subcapitulos_a_revisar": elementos_a_revisar,  # Alias por compatibilidad
                "porcentaje_coincidencia": proyecto.porcentaje_coincidencia
            }

        except Exception as e:
            logger.error(f"❌ [FASE 3] Error validando: {e}")
            self.session.rollback()
            return {"success": False, "error": str(e)}

    def _validar_subcapitulo_recursivo(self, subcapitulo, tolerancia: float) -> Dict:
        """
        Valida un subcapítulo y sus hijos recursivamente

        Solo valida elementos que tienen partidas directas (hojas del árbol).
        Los padres se validan pero NO se cuentan en las estadísticas ni se agregan a revisar.
        """
        validados = 0
        discrepancias = 0
        a_revisar = []

        # Primero validar hijos recursivamente
        tiene_hijos = len(subcapitulo.subcapitulos_hijos) > 0

        if tiene_hijos:
            # Si tiene hijos, validar recursivamente
            for hijo in subcapitulo.subcapitulos_hijos:
                resultado = self._validar_subcapitulo_recursivo(hijo, tolerancia)
                validados += resultado['validados']
                discrepancias += resultado['discrepancias']
                a_revisar.extend(resultado['a_revisar'])

            # Validar este nivel pero NO contarlo (es solo agregación)
            self._validar_elemento(subcapitulo, tolerancia)
        else:
            # Es una HOJA (tiene partidas directas), validar y contar
            tiene_partidas = len(subcapitulo.partidas) > 0 or len(subcapitulo.apartados) > 0

            if tiene_partidas:
                if self._validar_elemento(subcapitulo, tolerancia):
                    validados += 1
                else:
                    discrepancias += 1
                    # Solo agregar a revisar si tiene partidas y necesita revisión
                    if subcapitulo.necesita_revision_ia and subcapitulo.total_ia > 0 and subcapitulo.total_local > 0:
                        a_revisar.append({
                            "tipo": "subcapitulo",
                            "codigo": subcapitulo.codigo,
                            "nombre": subcapitulo.nombre,
                            "total_ia": subcapitulo.total_ia,
                            "total_local": subcapitulo.total_local,
                            "num_partidas_ia": subcapitulo.num_partidas_ia,
                            "num_partidas_local": subcapitulo.num_partidas_local,
                            "diferencia_euros": subcapitulo.diferencia_euros,
                            "diferencia_porcentaje": subcapitulo.diferencia_porcentaje,
                            "subcapitulo_id": subcapitulo.id,
                            "capitulo_id": subcapitulo.capitulo_id
                        })

        return {
            "validados": validados,
            "discrepancias": discrepancias,
            "a_revisar": a_revisar
        }

    def _validar_elemento(self, elemento, tolerancia: float) -> bool:
        """
        Valida un elemento (Capítulo o Subcapítulo) comparando SOLO el total en euros.

        Validación: total_ia vs total_local (IGUALDAD EXACTA - 0% tolerancia)
        NO se valida el conteo de partidas.

        Returns:
            True si el total es EXACTAMENTE IGUAL (diff < 0.01€)
        """
        total_ia = getattr(elemento, 'total_ia', 0.0)
        total_local = getattr(elemento, 'total_local', 0.0)

        # Si total_ia es 0, es un error (no se extrajo nada)
        if total_ia == 0:
            elemento.estado_validacion = EstadoValidacion.ERROR
            elemento.necesita_revision_ia = 1
            return False

        # Si total_local es 0 pero total_ia > 0, significa que Fase 2 no se ejecutó
        # o no se encontraron partidas locales
        if total_local == 0 and total_ia > 0:
            elemento.estado_validacion = EstadoValidacion.DISCREPANCIA
            elemento.necesita_revision_ia = 1
            elemento.diferencia_euros = total_ia
            elemento.diferencia_porcentaje = 100.0
            elemento.total_final = total_ia
            logger.warning(f"[VALIDACIÓN] {elemento.codigo} - ✗ DISCREPANCIA: total_local=0 pero total_ia={total_ia:.2f}€")
            return False

        # Validación de totales en euros (IGUALDAD EXACTA)
        diferencia_euros = abs(total_ia - total_local)
        diferencia_porcentaje = (diferencia_euros / total_ia) * 100 if total_ia > 0 else 0

        elemento.diferencia_euros = diferencia_euros
        elemento.diferencia_porcentaje = diferencia_porcentaje

        # Criterio de igualdad exacta: tolerancia de 0.01€ para errores de redondeo
        total_exacto = diferencia_euros < 0.01

        # El elemento es válido SOLO si el total es exactamente igual
        if total_exacto:
            elemento.estado_validacion = EstadoValidacion.VALIDADO
            elemento.necesita_revision_ia = 0
            elemento.total_final = total_local
            logger.info(f"[VALIDACIÓN] {elemento.codigo} - ✓ VALIDADO (diff: €{diferencia_euros:.2f})")
            return True
        else:
            elemento.estado_validacion = EstadoValidacion.DISCREPANCIA
            elemento.necesita_revision_ia = 1
            elemento.total_final = total_ia  # Usar total IA por defecto
            logger.warning(f"[VALIDACIÓN] {elemento.codigo} - ✗ DISCREPANCIA en TOTAL: {diferencia_porcentaje:.2f}% (€{diferencia_euros:.2f})")
            return False

    def obtener_proyecto(self, proyecto_id: int) -> HybridProyecto:
        """Obtiene un proyecto híbrido completo"""
        return self.session.query(HybridProyecto).filter_by(id=proyecto_id).first()

    def listar_proyectos(self) -> List[HybridProyecto]:
        """Lista todos los proyectos híbridos"""
        return self.session.query(HybridProyecto).all()

    async def actualizar_partidas_elemento(
        self,
        elemento_tipo: str,
        elemento_id: int,
        partidas_ia: List[Dict]
    ) -> Dict:
        """
        Compara partidas IA con partidas locales y actualiza la base de datos

        Args:
            elemento_tipo: "capitulo" o "subcapitulo"
            elemento_id: ID del elemento
            partidas_ia: Lista de partidas extraídas por IA

        Returns:
            Dict con estadísticas de la actualización
        """
        try:
            logger.info(f"[ACTUALIZACION] Comparando {len(partidas_ia)} partidas IA con partidas locales")

            # Obtener elemento
            if elemento_tipo == "capitulo":
                elemento = self.session.query(HybridCapitulo).filter_by(id=elemento_id).first()
                partidas_existentes = elemento.partidas if elemento else []
            elif elemento_tipo == "subcapitulo":
                elemento = self.session.query(HybridSubcapitulo).filter_by(id=elemento_id).first()
                partidas_existentes = elemento.partidas if elemento else []
            else:
                return {"success": False, "error": "Tipo de elemento inválido"}

            if not elemento:
                return {"success": False, "error": f"{elemento_tipo} no encontrado"}

            # ⚠️ VALIDACIÓN DE SEGURIDAD: Si IA no extrajo NINGUNA partida y hay partidas locales,
            # probablemente es un ERROR de extracción (sección vacía, clasificación fallida, etc.)
            # NO eliminar las partidas locales en este caso
            if len(partidas_ia) == 0 and len(partidas_existentes) > 0:
                logger.error(f"[ACTUALIZACION] ❌ ERROR: IA extrajo 0 partidas pero hay {len(partidas_existentes)} partidas locales")
                logger.error(f"[ACTUALIZACION] Esto indica un fallo en la extracción (sección vacía, clasificador fallido, etc.)")
                logger.error(f"[ACTUALIZACION] ABORTANDO actualización para prevenir pérdida de datos")
                return {
                    "success": False,
                    "error": f"IA no extrajo partidas del {elemento_tipo} {elemento.codigo}. "
                            f"Esto indica un error en la extracción de sección del PDF. "
                            f"Revisa que el clasificador detecte correctamente los códigos de capítulos/subcapítulos.",
                    "actualizadas": 0,
                    "agregadas": 0,
                    "eliminadas": 0,
                    "total_local_nuevo": elemento.total_local,
                    "total_ia": elemento.total_ia,
                    "diferencia_euros": elemento.diferencia_euros,
                    "diferencia_porcentaje": elemento.diferencia_porcentaje,
                    "estado_validacion": elemento.estado_validacion.value
                }

            # CASO ESPECIAL: IA extrajo 0 partidas Y hay 0 partidas locales
            # Verificar si es válido (subcapítulo padre con solo hijos) o error
            if len(partidas_ia) == 0 and len(partidas_existentes) == 0:
                if elemento_tipo == "subcapitulo" and len(elemento.subcapitulos_hijos) > 0:
                    # Subcapítulo padre sin partidas directas pero con hijos - VÁLIDO
                    logger.info(f"[ACTUALIZACION] ✓ Subcapítulo {elemento.codigo} sin partidas directas pero con {len(elemento.subcapitulos_hijos)} hijos")
                    # Continuar para recalcular totales recursivamente
                elif elemento_tipo == "subcapitulo":
                    # Subcapítulo sin partidas ni hijos - posible error
                    logger.error(f"[ACTUALIZACION] ❌ ERROR: Subcapítulo {elemento.codigo} no tiene partidas ni hijos")
                    return {
                        "success": False,
                        "error": f"Subcapítulo {elemento.codigo} no tiene partidas ni subcapítulos hijos",
                        "actualizadas": 0,
                        "agregadas": 0,
                        "eliminadas": 0,
                        "total_local_nuevo": elemento.total_local,
                        "total_ia": elemento.total_ia,
                        "diferencia_euros": elemento.diferencia_euros,
                        "diferencia_porcentaje": elemento.diferencia_porcentaje,
                        "estado_validacion": elemento.estado_validacion.value
                    }

            # Crear diccionario de partidas existentes por código
            partidas_local_dict = {p.codigo: p for p in partidas_existentes}
            partidas_ia_dict = {p['codigo']: p for p in partidas_ia}

            actualizadas = 0
            agregadas = 0
            eliminadas = 0

            # 1. Actualizar o agregar partidas de IA
            for codigo, partida_ia in partidas_ia_dict.items():
                if codigo in partidas_local_dict:
                    # Actualizar partida existente
                    # IMPORTANTE: Actualizar campos numéricos (cantidad, precio, importe) Y resumen si está vacío
                    # El LLM ahora devuelve "resumen" (título corto) para completar partidas sin título
                    # NO actualizar descripcion (no se solicita al LLM para ahorrar tokens)
                    partida_local = partidas_local_dict[codigo]

                    # Actualizar solo si hay cambios en los valores numéricos
                    cambios = False
                    if partida_local.cantidad != partida_ia.get('cantidad', partida_local.cantidad):
                        partida_local.cantidad = partida_ia.get('cantidad', partida_local.cantidad)
                        cambios = True
                    if partida_local.precio != partida_ia.get('precio', partida_local.precio):
                        partida_local.precio = partida_ia.get('precio', partida_local.precio)
                        cambios = True
                    if partida_local.importe != partida_ia.get('importe', partida_local.importe):
                        partida_local.importe = partida_ia.get('importe', partida_local.importe)
                        cambios = True

                    # Solo actualizar unidad si viene en la respuesta del LLM (raro, pero por si acaso)
                    if 'unidad' in partida_ia and partida_ia['unidad']:
                        if partida_local.unidad != partida_ia['unidad']:
                            partida_local.unidad = partida_ia['unidad']
                            cambios = True

                    # NUEVO: Actualizar resumen si viene de IA y está vacío en local
                    if 'resumen' in partida_ia and partida_ia['resumen']:
                        if not partida_local.resumen or partida_local.resumen == '':
                            partida_local.resumen = partida_ia['resumen']
                            cambios = True
                            logger.info(f"  ✓ Resumen actualizado: {codigo}")

                    # PRESERVAR descripción existente - NO sobrescribir
                    # partida_local.descripcion NO se modifica (se completará en Fase 4 local)

                    if cambios:
                        partida_local.extraido_por = 'ia_revision'
                        actualizadas += 1
                        logger.info(f"  ✓ Actualizada: {codigo} (cambios detectados en valores numéricos)")
                    else:
                        logger.debug(f"  = Sin cambios: {codigo} (valores numéricos idénticos)")
                else:
                    # Verificar si esta "nueva" partida es en realidad un duplicado con código erróneo
                    # Comparamos cantidad, precio e importe con todas las partidas locales existentes
                    cantidad_ia = partida_ia.get('cantidad', 0.0)
                    precio_ia = partida_ia.get('precio', 0.0)
                    importe_ia = partida_ia.get('importe', 0.0)

                    es_duplicado = False
                    codigo_duplicado = None

                    for codigo_local, partida_local in partidas_local_dict.items():
                        # Comparar con tolerancia mínima para valores flotantes (0.01 euros/unidades)
                        if (abs(partida_local.cantidad - cantidad_ia) < 0.01 and
                            abs(partida_local.precio - precio_ia) < 0.01 and
                            abs(partida_local.importe - importe_ia) < 0.01):
                            es_duplicado = True
                            codigo_duplicado = codigo_local
                            break

                    if es_duplicado:
                        # Es un duplicado: el LLM devolvió un código erróneo pero los valores coinciden
                        logger.warning(f"  ⚠️  Duplicado detectado: {codigo} tiene los mismos valores que {codigo_duplicado} (cantidad={cantidad_ia}, precio={precio_ia}, importe={importe_ia})")
                        logger.warning(f"  ⚠️  Se omite la creación de la partida duplicada - el LLM probablemente procesó mal el código")
                    else:
                        # Agregar nueva partida (realmente nueva)
                        nueva_partida = HybridPartida(
                            capitulo_id=elemento.id if elemento_tipo == "capitulo" else None,
                            subcapitulo_id=elemento.id if elemento_tipo == "subcapitulo" else None,
                            codigo=partida_ia['codigo'],
                            unidad=partida_ia.get('unidad', 'ud'),
                            resumen=partida_ia.get('resumen', ''),
                            descripcion=partida_ia.get('descripcion', ''),
                            cantidad=cantidad_ia,
                            precio=precio_ia,
                            importe=importe_ia,
                            extraido_por='ia_revision'
                        )
                        self.session.add(nueva_partida)
                        agregadas += 1
                        logger.info(f"  + Agregada: {codigo}")

            # 2. NO eliminar partidas locales que no están en respuesta IA
            # Las partidas que faltan en la respuesta del LLM generalmente indican un error
            # de extracción, NO que deban ser eliminadas. Preservar siempre los datos existentes.
            # for codigo, partida_local in partidas_local_dict.items():
            #     if codigo not in partidas_ia_dict:
            #         self.session.delete(partida_local)
            #         eliminadas += 1
            #         logger.info(f"  - Eliminada: {codigo}")

            # En su lugar, solo registrar las partidas que están en local pero no en IA
            partidas_solo_en_local = [codigo for codigo in partidas_local_dict if codigo not in partidas_ia_dict]
            if partidas_solo_en_local:
                logger.warning(f"  ⚠️  {len(partidas_solo_en_local)} partidas en local NO encontradas en respuesta IA (se preservan): {partidas_solo_en_local[:5]}")
            eliminadas = 0  # No se elimina nada

            # 3. Recalcular totales del elemento
            # IMPORTANTE: Hacer flush() para persistir las partidas nuevas
            self.session.flush()

            # CRÍTICO: Refrescar el objeto elemento para que SQLAlchemy recargue la relación partidas
            # Si no hacemos esto, elemento.partidas contiene el valor cacheado ANTES de añadir las 3 nuevas
            self.session.expire(elemento, ['partidas'])

            # Ahora sí, recalcular usando TODAS las partidas (actualizadas + preservadas + agregadas)
            if elemento_tipo == "capitulo":
                total_local_nuevo = sum(p.importe for p in elemento.partidas)
            elif elemento_tipo == "subcapitulo":
                # IMPORTANTE: Recalcular recursivamente para incluir subcapítulos hijos
                # No solo sumar partidas directas (puede ser 0 si solo tiene hijos)
                total_local_nuevo, _ = self._calcular_total_subcapitulo_recursivo(elemento)
            elemento.total_local = total_local_nuevo

            logger.info(f"[ACTUALIZACION] Total recalculado: {len(elemento.partidas)} partidas = {total_local_nuevo:.2f}€")

            # 4. Re-validar el elemento (igualdad exacta)
            self._validar_elemento(elemento, tolerancia=0.0)

            self.session.commit()

            logger.info(f"[ACTUALIZACION] ✓ Completada: {actualizadas} actualizadas, {agregadas} agregadas, {eliminadas} eliminadas")

            return {
                "success": True,
                "actualizadas": actualizadas,
                "agregadas": agregadas,
                "eliminadas": eliminadas,
                "total_local_nuevo": total_local_nuevo,
                "total_ia": elemento.total_ia,
                "diferencia_euros": elemento.diferencia_euros,
                "diferencia_porcentaje": elemento.diferencia_porcentaje,
                "estado_validacion": elemento.estado_validacion.value
            }

        except Exception as e:
            logger.error(f"❌ Error actualizando partidas: {e}")
            self.session.rollback()
            return {"success": False, "error": str(e)}

    def eliminar_proyecto(self, proyecto_id: int) -> bool:
        """Elimina un proyecto híbrido"""
        try:
            proyecto = self.obtener_proyecto(proyecto_id)
            if not proyecto:
                return False

            self.session.delete(proyecto)
            self.session.commit()
            return True
        except Exception as e:
            logger.error(f"Error eliminando proyecto híbrido {proyecto_id}: {e}")
            self.session.rollback()
            return False

    def cerrar(self):
        """Cierra la sesión de base de datos"""
        self.session.close()
