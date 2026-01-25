"""
Database Manager V2 - Gestión de PostgreSQL con mediciones parciales
====================================================================

Maneja toda la interacción con la base de datos PostgreSQL:
- Guardar proyectos completos
- Guardar mediciones parciales
- Validar sumas
- Calcular totales
- Consultas

"""

import logging
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime
import hashlib

from sqlalchemy.orm import Session
from .db_config import SessionLocal, engine
from .db_models_v2 import Proyecto, Capitulo, Subcapitulo, Partida, MedicionParcial

logger = logging.getLogger(__name__)


class DatabaseManagerV2:
    """Manager para operaciones con PostgreSQL"""

    def __init__(self):
        """Inicializa el manager con una sesión de BD"""
        self.session: Session = SessionLocal()

    def cerrar(self):
        """Cierra la sesión de BD"""
        if self.session:
            self.session.close()

    def __enter__(self):
        """Context manager"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup"""
        self.cerrar()

    def guardar_estructura(
        self,
        estructura: Dict,
        metadata: Dict,
        pdf_path: str
    ) -> Proyecto:
        """
        Guarda la estructura completa del presupuesto en PostgreSQL

        Args:
            estructura: Dict con proyecto/capítulos/subcapítulos/partidas
            metadata: Metadata de detección (layout, mediciones, etc.)
            pdf_path: Ruta al PDF original

        Returns:
            Objeto Proyecto guardado
        """
        logger.info("Guardando en PostgreSQL...")

        # Calcular hash del PDF
        pdf_hash = self._calcular_hash_archivo(pdf_path)

        # Crear proyecto
        proyecto = Proyecto(
            nombre=estructura.get('nombre', 'Proyecto sin nombre'),
            pdf_path=pdf_path,
            pdf_nombre=metadata.get('pdf_nombre', ''),
            pdf_hash=pdf_hash,
            layout_detectado=metadata.get('layout_detectado', ''),
            tiene_mediciones_auxiliares=metadata.get('tiene_mediciones_auxiliares', False),
            presupuesto_total=Decimal('0')  # Se calculará después
        )

        self.session.add(proyecto)
        self.session.flush()  # Para obtener proyecto.id

        # Guardar capítulos
        for orden_cap, cap_data in enumerate(estructura.get('capitulos', []), 1):
            capitulo = self._guardar_capitulo(proyecto.id, cap_data, orden_cap)
            proyecto.capitulos.append(capitulo)

        # Calcular total del proyecto
        total = self.calcular_totales(proyecto.id)
        proyecto.presupuesto_total = total

        # Commit
        self.session.commit()

        logger.info(f"✓ Proyecto guardado con ID: {proyecto.id}")
        logger.info(f"✓ Presupuesto total: {total:,.2f} €")

        return proyecto

    def crear_proyecto_vacio(
        self,
        nombre: str,
        pdf_path: str,
        filename: str
    ) -> Proyecto:
        """
        Crea un proyecto vacío (sin procesar) para procesamiento por fases

        Args:
            nombre: Nombre del proyecto
            pdf_path: Ruta al PDF
            filename: Nombre del archivo

        Returns:
            Objeto Proyecto creado
        """
        logger.info(f"Creando proyecto vacío: {nombre}")

        # Calcular hash del PDF
        pdf_hash = self._calcular_hash_archivo(pdf_path)

        # Crear proyecto vacío
        proyecto = Proyecto(
            nombre=nombre,
            pdf_path=pdf_path,
            pdf_nombre=filename,
            pdf_hash=pdf_hash,
            layout_detectado='pendiente',
            tiene_mediciones_auxiliares=False,
            presupuesto_total=Decimal('0')
        )

        self.session.add(proyecto)
        self.session.commit()

        logger.info(f"✓ Proyecto vacío creado con ID: {proyecto.id}")

        return proyecto

    def actualizar_fase1(self, proyecto_id: int, estructura: Dict, metadata: Dict) -> Proyecto:
        """
        FASE 1: Guarda estructura jerárquica (capítulos y subcapítulos con totales)

        Args:
            proyecto_id: ID del proyecto
            estructura: Dict con capitulos y subcapitulos
            metadata: Metadata de layout

        Returns:
            Objeto Proyecto actualizado
        """
        logger.info(f"FASE 1: Guardando estructura para proyecto {proyecto_id}")

        proyecto = self.session.query(Proyecto).filter_by(id=proyecto_id).first()
        if not proyecto:
            raise ValueError(f"Proyecto {proyecto_id} no encontrado")

        # Actualizar metadata
        proyecto.layout_detectado = metadata.get('layout_detectado', 'pendiente')

        # Limpiar datos existentes si los hay (en orden correcto por foreign keys)
        logger.info("🧹 Limpiando datos existentes antes de reprocesar Fase 1...")

        # 1. Primero eliminar partidas
        partidas_count = 0
        for capitulo in proyecto.capitulos:
            for subcapitulo in capitulo.subcapitulos:
                count = self.session.query(Partida).filter_by(subcapitulo_id=subcapitulo.id).count()
                partidas_count += count
                self.session.query(Partida).filter_by(subcapitulo_id=subcapitulo.id).delete()

        if partidas_count > 0:
            logger.info(f"  ✓ Eliminadas {partidas_count} partidas")

        # 2. Luego eliminar subcapítulos
        subcapitulos_count = 0
        for capitulo in proyecto.capitulos:
            count = self.session.query(Subcapitulo).filter_by(capitulo_id=capitulo.id).count()
            subcapitulos_count += count
            self.session.query(Subcapitulo).filter_by(capitulo_id=capitulo.id).delete()

        if subcapitulos_count > 0:
            logger.info(f"  ✓ Eliminados {subcapitulos_count} subcapítulos")

        # 3. Finalmente eliminar capítulos
        capitulos_count = self.session.query(Capitulo).filter_by(proyecto_id=proyecto_id).count()
        self.session.query(Capitulo).filter_by(proyecto_id=proyecto_id).delete()

        if capitulos_count > 0:
            logger.info(f"  ✓ Eliminados {capitulos_count} capítulos")

        if partidas_count == 0 and subcapitulos_count == 0 and capitulos_count == 0:
            logger.info("  ℹ️  No había datos previos que limpiar")

        self.session.flush()
        logger.info("✓ Limpieza completada, guardando nueva estructura...")

        # Guardar capítulos con totales de Fase 1
        for orden_cap, cap_data in enumerate(estructura.get('capitulos', []), 1):
            capitulo = Capitulo(
                proyecto_id=proyecto_id,
                codigo=cap_data.get('codigo', ''),
                nombre=cap_data.get('nombre', ''),
                total=Decimal(str(cap_data.get('total', 0))),
                orden=orden_cap
            )
            self.session.add(capitulo)
            self.session.flush()

            # Guardar subcapítulos (sin partidas aún)
            self._guardar_subcapitulos_fase1(capitulo.id, cap_data.get('subcapitulos', []))

        # Calcular total del proyecto desde capitulos
        total = sum(Decimal(str(cap.get('total', 0))) for cap in estructura.get('capitulos', []))
        proyecto.presupuesto_total = total

        self.session.commit()

        logger.info(f"✓ Fase 1 guardada: {len(estructura.get('capitulos', []))} capítulos, total: {total:,.2f} €")

        return proyecto

    def _guardar_subcapitulos_fase1(self, capitulo_id: int, subcapitulos: List[Dict], orden_base: int = 0):
        """
        Guarda subcapítulos en estructura plana recursivamente (Fase 1 - sin partidas)

        Usa una estructura plana donde todos los subcapítulos pertenecen al mismo capitulo_id,
        pero mantienen su jerarquía mediante los campos 'nivel' y 'orden'.
        """
        orden_actual = orden_base

        for sub_data in subcapitulos:
            orden_actual += 1
            codigo = sub_data.get('codigo', '')
            nivel = codigo.count('.') if codigo else 1

            subcapitulo = Subcapitulo(
                capitulo_id=capitulo_id,
                codigo=codigo,
                nombre=sub_data.get('nombre', ''),
                total=Decimal(str(sub_data.get('total', 0))),
                nivel=nivel,
                orden=orden_actual
            )
            self.session.add(subcapitulo)
            self.session.flush()

            # Recursivo para subniveles (se agregan después en el orden)
            if sub_data.get('subcapitulos'):
                orden_actual = self._guardar_subcapitulos_fase1(
                    capitulo_id,
                    sub_data['subcapitulos'],
                    orden_actual
                )

        return orden_actual

    def actualizar_fase2(self, proyecto_id: int, estructura_completa: Dict) -> Proyecto:
        """
        FASE 2: Agrega partidas a la estructura existente

        Args:
            proyecto_id: ID del proyecto
            estructura_completa: Dict con capitulos, subcapitulos Y partidas

        Returns:
            Objeto Proyecto actualizado
        """
        logger.info(f"FASE 2: Guardando partidas para proyecto {proyecto_id}")

        proyecto = self.session.query(Proyecto).filter_by(id=proyecto_id).first()
        if not proyecto:
            raise ValueError(f"Proyecto {proyecto_id} no encontrado")

        # LIMPIAR PARTIDAS EXISTENTES antes de reprocesar Fase 2
        logger.info("🧹 Limpiando partidas existentes antes de reprocesar Fase 2...")
        partidas_count = 0
        for capitulo in proyecto.capitulos:
            for subcapitulo in capitulo.subcapitulos:
                count = self.session.query(Partida).filter_by(subcapitulo_id=subcapitulo.id).count()
                partidas_count += count
                self.session.query(Partida).filter_by(subcapitulo_id=subcapitulo.id).delete()

        if partidas_count > 0:
            logger.info(f"  ✓ Eliminadas {partidas_count} partidas previas")
        else:
            logger.info("  ℹ️  No había partidas previas que limpiar")

        self.session.flush()
        logger.info("✓ Limpieza completada, guardando nuevas partidas...")

        # Crear mapa de capítulos existentes por código
        capitulos_map = {}
        for capitulo in proyecto.capitulos:
            capitulos_map[capitulo.codigo] = capitulo

        # Crear mapa de subcapítulos existentes por código
        subcapitulos_map = {}
        for capitulo in proyecto.capitulos:
            for subcap in capitulo.subcapitulos:
                subcapitulos_map[subcap.codigo] = subcap

        total_partidas = 0

        # Agregar partidas a capítulos y subcapítulos correspondientes
        for cap_data in estructura_completa.get('capitulos', []):
            self._agregar_partidas_fase2(cap_data, capitulos_map, subcapitulos_map)
            total_partidas += self._contar_partidas(cap_data)

        self.session.commit()

        logger.info(f"✓ Fase 2 guardada: {total_partidas} partidas agregadas")

        return proyecto

    def _agregar_partidas_fase2(self, elemento: Dict, capitulos_map: Dict, subcapitulos_map: Dict, es_capitulo: bool = True):
        """Agrega partidas recursivamente tanto a capítulos como a subcapítulos"""
        codigo_elemento = elemento.get('codigo', '')

        # Agregar partidas del elemento actual
        if elemento.get('partidas'):
            # Determinar si es capítulo o subcapítulo por el código
            target_obj = None
            target_id = None

            if es_capitulo:
                # Es un capítulo principal
                cap = capitulos_map.get(codigo_elemento)
                if cap:
                    # Las partidas de capítulo las guardamos en un subcapítulo especial o en el primer subcapítulo
                    # Por ahora, buscar el primer subcapítulo del capítulo
                    if cap.subcapitulos:
                        target_obj = cap.subcapitulos[0]
                        target_id = target_obj.id
                    else:
                        logger.warning(f"Capítulo {codigo_elemento} no tiene subcapítulos para agregar {len(elemento['partidas'])} partidas")
            else:
                # Es un subcapítulo
                subcap = subcapitulos_map.get(codigo_elemento)
                if subcap:
                    target_obj = subcap
                    target_id = subcap.id

            if target_id:
                # Limpiar partidas existentes
                self.session.query(Partida).filter_by(subcapitulo_id=target_id).delete()

                for orden, part_data in enumerate(elemento['partidas'], 1):
                    partida = Partida(
                        subcapitulo_id=target_id,
                        codigo=part_data.get('codigo', ''),
                        unidad=part_data.get('unidad', ''),
                        resumen=part_data.get('resumen', ''),
                        descripcion=part_data.get('descripcion', ''),
                        cantidad_total=Decimal(str(part_data.get('cantidad', 0))),
                        precio=Decimal(str(part_data.get('precio', 0))),
                        importe=Decimal(str(part_data.get('importe', 0))),
                        tiene_mediciones=False,
                        mediciones_validadas=False,
                        suma_parciales=Decimal('0'),
                        orden=orden
                    )
                    self.session.add(partida)
                    logger.debug(f"Partida agregada: {partida.codigo} (resumen: {part_data.get('resumen', '')[:50]}) a {'capítulo' if es_capitulo else 'subcapítulo'} {codigo_elemento}")

        # Recursivo para subcapítulos
        for sub_data in elemento.get('subcapitulos', []):
            self._agregar_partidas_fase2(sub_data, capitulos_map, subcapitulos_map, es_capitulo=False)

    def _contar_partidas(self, elemento: Dict) -> int:
        """Cuenta partidas recursivamente"""
        total = len(elemento.get('partidas', []))
        for sub in elemento.get('subcapitulos', []):
            total += self._contar_partidas(sub)
        return total

    def actualizar_fase3(self, proyecto_id: int, validacion: Dict) -> Proyecto:
        """
        FASE 3: Calcula totales recursivamente y detecta discrepancias

        NO modifica los totales originales ('total'), solo calcula 'total_calculado'
        para comparación.

        Args:
            proyecto_id: ID del proyecto
            validacion: Dict con resultados de validación

        Returns:
            Objeto Proyecto actualizado con discrepancias detectadas
        """
        logger.info(f"FASE 3: Calculando totales para proyecto {proyecto_id}")

        proyecto = self.session.query(Proyecto).filter_by(id=proyecto_id).first()
        if not proyecto:
            raise ValueError(f"Proyecto {proyecto_id} no encontrado")

        # RESETEAR TOTALES CALCULADOS antes de reprocesar Fase 3
        logger.info("🧹 Reseteando totales calculados antes de reprocesar Fase 3...")
        caps_reset = 0
        subs_reset = 0

        for capitulo in proyecto.capitulos:
            if capitulo.total_calculado is not None:
                capitulo.total_calculado = None
                caps_reset += 1

            for subcapitulo in capitulo.subcapitulos:
                if subcapitulo.total_calculado is not None:
                    subcapitulo.total_calculado = None
                    subs_reset += 1

        if caps_reset > 0 or subs_reset > 0:
            logger.info(f"  ✓ Reseteados {caps_reset} capítulos y {subs_reset} subcapítulos")
        else:
            logger.info("  ℹ️  No había totales calculados previos")

        self.session.flush()
        logger.info("✓ Reset completado, recalculando totales...")

        discrepancias = []
        discrepancias_ids = set()  # Para evitar duplicados

        # Calcular totales recursivamente para cada capítulo
        for capitulo in proyecto.capitulos:
            total_cap_calculado = self._calcular_total_capitulo_recursivo(capitulo, discrepancias, discrepancias_ids)
            capitulo.total_calculado = total_cap_calculado

            # Detectar discrepancia en capítulo
            clave = f"capitulo_{capitulo.id}"
            if (clave not in discrepancias_ids and
                capitulo.total and
                abs(float(capitulo.total) - float(total_cap_calculado)) > 0.01):
                discrepancias.append({
                    'tipo': 'capitulo',
                    'id': capitulo.id,
                    'codigo': capitulo.codigo,
                    'nombre': capitulo.nombre,
                    'total_original': float(capitulo.total),
                    'total_calculado': float(total_cap_calculado),
                    'diferencia': float(capitulo.total) - float(total_cap_calculado)
                })
                discrepancias_ids.add(clave)

        self.session.commit()

        # Calcular total del proyecto (suma de capitulos calculados)
        total_proyecto_calculado = sum(c.total_calculado or 0 for c in proyecto.capitulos)

        logger.info(f"✓ Fase 3 completada: {len(discrepancias)} discrepancias detectadas")
        logger.info(f"  Total original: {proyecto.presupuesto_total:,.2f} €")
        logger.info(f"  Total calculado: {total_proyecto_calculado:,.2f} €")

        return {
            'proyecto': proyecto,
            'discrepancias': discrepancias,
            'total_original': float(proyecto.presupuesto_total) if proyecto.presupuesto_total else 0,
            'total_calculado': float(total_proyecto_calculado)
        }

    def _calcular_total_capitulo_recursivo(self, capitulo, discrepancias: list, discrepancias_ids: set) -> Decimal:
        """
        Calcula el total de un capítulo sumando recursivamente:
        - SOLO subcapítulos de NIVEL 1 (los hijos se calculan recursivamente)
        - Partidas directas de subcapítulos hoja
        """
        total = Decimal('0')

        # IMPORTANTE: Sumar SOLO subcapítulos de nivel 1
        # Los niveles 2, 3, 4 ya están incluidos recursivamente en sus padres
        for subcapitulo in capitulo.subcapitulos:
            if subcapitulo.nivel == 1:  # SOLO nivel 1
                total_sub = self._calcular_total_subcapitulo_recursivo(subcapitulo, discrepancias, discrepancias_ids)
                subcapitulo.total_calculado = total_sub
                total += total_sub

                # Detectar discrepancia en subcapítulo (evitando duplicados)
                clave = f"subcapitulo_{subcapitulo.id}"
                if (clave not in discrepancias_ids and
                    subcapitulo.total and
                    abs(float(subcapitulo.total) - float(total_sub)) > 0.01):
                    discrepancias.append({
                        'tipo': 'subcapitulo',
                        'id': subcapitulo.id,
                        'codigo': subcapitulo.codigo,
                        'nombre': subcapitulo.nombre,
                        'total_original': float(subcapitulo.total),
                        'total_calculado': float(total_sub),
                        'diferencia': float(subcapitulo.total) - float(total_sub)
                    })
                    discrepancias_ids.add(clave)

        return total

    def _calcular_total_subcapitulo_recursivo(self, subcapitulo, discrepancias: list, discrepancias_ids: set) -> Decimal:
        """
        Calcula el total de un subcapítulo:
        - Suma partidas directas del subcapítulo
        - Suma recursivamente SOLO hijos directos (nivel N+1)
        """
        total = Decimal('0')

        # 1. Sumar partidas directas (si las tiene)
        for partida in subcapitulo.partidas:
            total += partida.importe or Decimal('0')

        # 2. Buscar y sumar subcapítulos hijos directos (nivel inmediatamente inferior)
        # En V2 los subcapítulos están planos, buscar hijos por patrón de código
        codigo_base = subcapitulo.codigo
        nivel_base = subcapitulo.nivel

        # Buscar hijos directos: nivel = nivel_base + 1 Y código empieza con codigo_base
        subcapitulos_hijos = self.session.query(Subcapitulo).filter(
            Subcapitulo.capitulo_id == subcapitulo.capitulo_id,
            Subcapitulo.nivel == nivel_base + 1,  # SOLO nivel inmediatamente inferior
            Subcapitulo.codigo.like(f"{codigo_base}.%"),
            Subcapitulo.codigo != codigo_base
        ).all()

        # Filtrar solo hijos directos por código (verificación adicional)
        hijos_directos = []
        for hijo in subcapitulos_hijos:
            partes_base = codigo_base.split('.')
            partes_hijo = hijo.codigo.split('.')
            # Es hijo directo si tiene exactamente un nivel más Y el prefijo coincide
            if len(partes_hijo) == len(partes_base) + 1 and hijo.codigo.startswith(codigo_base + '.'):
                hijos_directos.append(hijo)

        # Sumar recursivamente cada hijo directo
        for hijo in hijos_directos:
            total_hijo = self._calcular_total_subcapitulo_recursivo(hijo, discrepancias, discrepancias_ids)
            hijo.total_calculado = total_hijo
            total += total_hijo

            # Detectar discrepancia en hijo (evitando duplicados)
            clave = f"subcapitulo_{hijo.id}"
            if (clave not in discrepancias_ids and
                hijo.total and
                abs(float(hijo.total) - float(total_hijo)) > 0.01):
                discrepancias.append({
                    'tipo': 'subcapitulo',
                    'id': hijo.id,
                    'codigo': hijo.codigo,
                    'nombre': hijo.nombre,
                    'total_original': float(hijo.total),
                    'total_calculado': float(total_hijo),
                    'diferencia': float(hijo.total) - float(total_hijo)
                })
                discrepancias_ids.add(clave)

        return total

    async def resolver_discrepancia_con_ia(self, proyecto_id: int, tipo: str, elemento_id: int, pdf_path: str) -> Dict:
        """
        Resuelve una discrepancia usando IA para encontrar partidas faltantes

        IMPORTANTE: El total del PDF (Fase 1) es SIEMPRE correcto.
        Si hay discrepancia, faltan partidas. El LLM las busca y extrae.

        Args:
            proyecto_id: ID del proyecto
            tipo: "capitulo" o "subcapitulo"
            elemento_id: ID del elemento con discrepancia
            pdf_path: Ruta al PDF original

        Returns:
            Dict con resultados {success, partidas_agregadas, total_agregado}
        """
        from llm_v2.discrepancy_resolver import DiscrepancyResolver

        try:
            # Obtener elemento
            if tipo == "capitulo":
                elemento = self.session.query(Capitulo).filter_by(id=elemento_id).first()
                partidas = self.session.query(Partida).join(Subcapitulo).filter(
                    Subcapitulo.capitulo_id == elemento_id
                ).all()
            elif tipo == "subcapitulo":
                elemento = self.session.query(Subcapitulo).filter_by(id=elemento_id).first()
                partidas = elemento.partidas
            else:
                raise ValueError(f"Tipo inválido: {tipo}")

            if not elemento:
                raise ValueError(f"{tipo} {elemento_id} no encontrado")

            # Preparar datos para el LLM
            elemento_dict = {
                'id': elemento.id,
                'codigo': elemento.codigo,
                'nombre': elemento.nombre,
                'total': float(elemento.total),
                'total_calculado': float(elemento.total_calculado) if elemento.total_calculado else 0
            }

            partidas_existentes = [
                {
                    'codigo': p.codigo,
                    'resumen': p.resumen,
                    'importe': float(p.importe) if p.importe else 0
                }
                for p in partidas
            ]

            # Llamar al LLM
            logger.info(f"🤖 Resolviendo discrepancia en {tipo} {elemento.codigo} con IA...")
            resolver = DiscrepancyResolver()
            resultado_llm = await resolver.resolver_discrepancia(
                pdf_path=pdf_path,
                elemento=elemento_dict,
                tipo=tipo,
                partidas_existentes=partidas_existentes,
                proyecto_id=proyecto_id  # Pasar proyecto_id para reutilizar texto de Fase 2
            )

            if not resultado_llm['success']:
                return resultado_llm

            # Agregar partidas nuevas a la BD
            partidas_nuevas = resultado_llm['partidas_nuevas']

            # ⚠️ VALIDACIÓN DE SEGURIDAD 1: Si IA no extrajo NINGUNA partida y hay partidas locales,
            # probablemente es un ERROR de extracción (sección vacía, clasificación fallida, etc.)
            # NO actualizar en este caso para prevenir pérdida de datos
            if len(partidas_nuevas) == 0 and len(partidas_existentes) > 0:
                logger.error(f"❌ ERROR: IA extrajo 0 partidas pero hay {len(partidas_existentes)} partidas locales")
                logger.error(f"   Esto indica un fallo en la extracción (sección vacía, texto incompleto, etc.)")
                logger.error(f"   ABORTANDO actualización para prevenir pérdida de datos")
                return {
                    'success': False,
                    'error': f"IA no extrajo partidas del {tipo} {elemento_dict['codigo']}. "
                            f"Esto indica un error en la extracción de texto del PDF. "
                            f"Revisa que el texto extraído contenga las partidas completas.",
                    'partidas_agregadas': 0,
                    'partidas_actualizadas': 0,
                    'total_agregado': 0
                }

            partidas_actualizadas = 0
            partidas_nuevas_insertadas = 0

            # Determinar subcapítulo destino
            if tipo == "capitulo":
                # Crear o usar subcapítulo para partidas directas
                subcap_destino = self.session.query(Subcapitulo).filter_by(
                    capitulo_id=elemento.id,
                    codigo=f"{elemento.codigo}.00"
                ).first()

                if not subcap_destino:
                    subcap_destino = Subcapitulo(
                        capitulo_id=elemento.id,
                        codigo=f"{elemento.codigo}.00",
                        nombre="Partidas encontradas por IA",
                        nivel=1,
                        orden=999
                    )
                    self.session.add(subcap_destino)
                    self.session.flush()
            else:
                subcap_destino = elemento

            # Crear mapa de partidas existentes para búsqueda rápida
            partidas_locales_map = {p['codigo']: p for p in partidas_existentes}

            # Insertar o actualizar partidas
            for partida_data in partidas_nuevas:
                # Verificar si la partida ya existe (por código y subcapítulo)
                partida_existente = self.session.query(Partida).filter_by(
                    subcapitulo_id=subcap_destino.id,
                    codigo=partida_data['codigo']
                ).first()

                if partida_existente:
                    # Actualizar partida existente
                    # SOLUCIÓN 5: Actualizar también resumen y descripción si vienen del LLM
                    partida_existente.unidad = partida_data.get('unidad', 'ud')
                    partida_existente.cantidad_total = Decimal(str(partida_data.get('cantidad', 0)))
                    partida_existente.precio = Decimal(str(partida_data.get('precio', 0)))
                    partida_existente.importe = Decimal(str(partida_data['importe']))

                    # Si el LLM proporcionó resumen/descripción Y la partida NO los tiene, actualizarlos
                    if partida_data.get('resumen') and not partida_existente.resumen:
                        partida_existente.resumen = partida_data['resumen']
                        logger.info(f"    ✓ Resumen agregado: {partida_data['resumen'][:40]}...")

                    if partida_data.get('descripcion') and not partida_existente.descripcion:
                        partida_existente.descripcion = partida_data['descripcion']
                        logger.info(f"    ✓ Descripción agregada: {partida_data['descripcion'][:40]}...")

                    partidas_actualizadas += 1
                    logger.info(f"  ↻ Actualizada: {partida_data['codigo']}")
                else:
                    # ⚠️ VALIDACIÓN DE SEGURIDAD 2: Verificar si esta "nueva" partida es en realidad
                    # un duplicado con código erróneo (el LLM puede devolver códigos incorrectos)
                    # Comparamos cantidad, precio e importe con todas las partidas locales existentes
                    cantidad_ia = partida_data.get('cantidad', 0.0)
                    precio_ia = partida_data.get('precio', 0.0)
                    importe_ia = partida_data.get('importe', 0.0)

                    es_duplicado = False
                    codigo_duplicado = None

                    for codigo_local, partida_local in partidas_locales_map.items():
                        # Comparar con tolerancia mínima para valores flotantes (0.01 euros/unidades)
                        if (abs(partida_local['importe'] - importe_ia) < 0.01 and
                            abs(partida_local.get('cantidad', 0) - cantidad_ia) < 0.01 and
                            abs(partida_local.get('precio', 0) - precio_ia) < 0.01):
                            es_duplicado = True
                            codigo_duplicado = codigo_local
                            break

                    if es_duplicado:
                        # Es un duplicado: el LLM devolvió un código erróneo pero los valores coinciden
                        logger.warning(f"  ⚠️  Duplicado detectado: {partida_data['codigo']} tiene los mismos valores que {codigo_duplicado}")
                        logger.warning(f"      Cantidad={cantidad_ia}, Precio={precio_ia}, Importe={importe_ia}")
                        logger.warning(f"      Se omite la creación de la partida duplicada")
                    else:
                        # Crear nueva partida (realmente nueva)
                        # SOLUCIÓN 5: Incluir resumen y descripción del LLM
                        partida = Partida(
                            subcapitulo_id=subcap_destino.id,
                            codigo=partida_data['codigo'],
                            unidad=partida_data.get('unidad', 'ud'),
                            resumen=partida_data.get('resumen', ''),  # NUEVO
                            descripcion=partida_data.get('descripcion', ''),  # NUEVO
                            cantidad_total=Decimal(str(cantidad_ia)),
                            precio=Decimal(str(precio_ia)),
                            importe=Decimal(str(importe_ia)),
                            orden=999 + partidas_nuevas_insertadas
                        )
                        self.session.add(partida)
                        partidas_nuevas_insertadas += 1
                        logger.info(f"  + Nueva: {partida_data['codigo']}")

            self.session.commit()

            logger.info(f"✓ Resultado: {partidas_nuevas_insertadas} nuevas, {partidas_actualizadas} actualizadas")
            logger.info(f"  Total agregado: {resultado_llm['total_nuevas']} €")

            return {
                'success': True,
                'partidas_agregadas': partidas_nuevas_insertadas,  # Solo las realmente nuevas
                'partidas_actualizadas': partidas_actualizadas,
                'total_agregado': resultado_llm['total_nuevas'],
                'partidas': partidas_nuevas
            }

        except Exception as e:
            logger.error(f"Error resolviendo discrepancia con IA: {e}", exc_info=True)
            self.session.rollback()
            return {
                'success': False,
                'error': str(e),
                'partidas_agregadas': 0,
                'total_agregado': 0
            }

    async def resolver_discrepancias_bulk_con_ia(self, proyecto_id: int, pdf_path: str) -> Dict:
        """
        Resuelve TODAS las discrepancias de un proyecto usando IA

        Itera sobre todas las discrepancias y llama al LLM para encontrar
        partidas faltantes en cada una.

        IMPORTANTE: Solo resuelve discrepancias en capítulos/subcapítulos que tienen
        partidas directas. Si un elemento solo tiene subcapítulos hijos pero no partidas
        propias, se omite para evitar que el LLM extraiga partidas de los hijos y las
        duplique en el padre.

        Args:
            proyecto_id: ID del proyecto
            pdf_path: Ruta al PDF original

        Returns:
            Dict con estadísticas de resolución
        """
        import time

        try:
            proyecto = self.session.query(Proyecto).filter_by(id=proyecto_id).first()
            if not proyecto:
                raise ValueError(f"Proyecto {proyecto_id} no encontrado")

            resueltas_exitosas = 0
            resueltas_fallidas = 0
            total_partidas_agregadas = 0
            omitidas_sin_partidas = 0
            errores = []

            logger.info(f"🤖 Resolviendo TODAS las discrepancias del proyecto {proyecto_id} con IA...")

            # Importar resolver una sola vez
            from src.llm_v2.discrepancy_resolver import DiscrepancyResolver
            resolver = DiscrepancyResolver()

            # Sistema de reintentos: máximo 2 intentos
            max_intentos = 2

            for intento in range(1, max_intentos + 1):
                if intento > 1:
                    # Recargar proyecto para obtener estado actualizado
                    self.session.expire_all()
                    proyecto = self.session.query(Proyecto).filter_by(id=proyecto_id).first()

                    logger.info(f"\n{'='*60}")
                    logger.info(f"🔄 REINTENTO {intento}/{max_intentos}: Verificando discrepancias restantes...")
                    logger.info(f"{'='*60}\n")
                    time.sleep(2)  # Delay entre reintentos

                discrepancias_procesadas_en_intento = 0

                # Resolver discrepancias en capítulos
                for capitulo in proyecto.capitulos:
                    if (capitulo.total and capitulo.total_calculado and
                        abs(float(capitulo.total) - float(capitulo.total_calculado)) > 0.01):

                        # VALIDACIÓN: Solo resolver si el capítulo tiene partidas directas
                        # (no solo subcapítulos hijos)
                        num_partidas_directas = self.session.query(Partida).join(Subcapitulo).filter(
                            Subcapitulo.capitulo_id == capitulo.id
                        ).count()

                        if num_partidas_directas == 0:
                            if intento == 1:  # Solo contar omisiones en primer intento
                                logger.info(f"  ⏭️  Omitiendo capítulo {capitulo.codigo} (sin partidas directas)")
                                omitidas_sin_partidas += 1
                            continue

                        # VALIDACIÓN ADICIONAL: Verificar en el texto PDF si hay códigos hijos
                        # Esto previene duplicaciones cuando el capítulo tiene subcapítulos en el PDF
                        # pero no están registrados en la BD
                        texto_pdf = resolver._extract_text_from_pdf(pdf_path, capitulo.codigo, proyecto_id)

                        if texto_pdf and resolver._detectar_codigos_hijos_en_texto(texto_pdf, capitulo.codigo):
                            if intento == 1:  # Solo contar omisiones en primer intento
                                logger.info(f"  ⏭️  Omitiendo capítulo {capitulo.codigo} (tiene subcapítulos hijos en el PDF)")
                                omitidas_sin_partidas += 1
                            continue

                        logger.info(f"  [Intento {intento}/{max_intentos}] Resolviendo capítulo {capitulo.codigo}...")
                        discrepancias_procesadas_en_intento += 1

                        resultado = await self.resolver_discrepancia_con_ia(
                            proyecto_id, "capitulo", capitulo.id, pdf_path
                        )

                        if resultado['success']:
                            resueltas_exitosas += 1
                            total_partidas_agregadas += resultado['partidas_agregadas']
                        else:
                            if intento == max_intentos:  # Solo contar como fallo en último intento
                                resueltas_fallidas += 1
                                errores.append(f"Capítulo {capitulo.codigo}: {resultado.get('error', 'Error desconocido')}")

                # Resolver discrepancias en subcapítulos (LOOP SEPARADO)
                for capitulo in proyecto.capitulos:
                    for subcapitulo in capitulo.subcapitulos:
                        if (subcapitulo.total and subcapitulo.total_calculado and
                            abs(float(subcapitulo.total) - float(subcapitulo.total_calculado)) > 0.01):

                            # VALIDACIÓN: Solo resolver si el subcapítulo tiene partidas directas
                            # (no solo subcapítulos hijos)
                            num_partidas_directas = len(subcapitulo.partidas)

                            if num_partidas_directas == 0:
                                if intento == 1:  # Solo contar omisiones en primer intento
                                    logger.info(f"  ⏭️  Omitiendo subcapítulo {subcapitulo.codigo} (sin partidas directas)")
                                    omitidas_sin_partidas += 1
                                continue

                            # VALIDACIÓN ADICIONAL: Verificar en el texto PDF si hay códigos hijos
                            # Esto previene duplicaciones cuando el subcapítulo tiene hijos en el PDF
                            # pero no están registrados en la BD
                            texto_pdf = resolver._extract_text_from_pdf(pdf_path, subcapitulo.codigo, proyecto_id)

                            if texto_pdf and resolver._detectar_codigos_hijos_en_texto(texto_pdf, subcapitulo.codigo):
                                if intento == 1:  # Solo contar omisiones en primer intento
                                    logger.info(f"  ⏭️  Omitiendo subcapítulo {subcapitulo.codigo} (tiene subcapítulos hijos en el PDF)")
                                    omitidas_sin_partidas += 1
                                continue

                            logger.info(f"  [Intento {intento}/{max_intentos}] Resolviendo subcapítulo {subcapitulo.codigo}...")
                            discrepancias_procesadas_en_intento += 1

                            resultado = await self.resolver_discrepancia_con_ia(
                                proyecto_id, "subcapitulo", subcapitulo.id, pdf_path
                            )

                            if resultado['success']:
                                resueltas_exitosas += 1
                                total_partidas_agregadas += resultado['partidas_agregadas']
                            else:
                                if intento == max_intentos:  # Solo contar como fallo en último intento
                                    resueltas_fallidas += 1
                                    errores.append(f"Subcapítulo {subcapitulo.codigo}: {resultado.get('error', 'Error desconocido')}")

                # Si no se procesó ninguna discrepancia en este intento, salir del loop
                if discrepancias_procesadas_en_intento == 0:
                    logger.info(f"✓ Todas las discrepancias resueltas en intento {intento}")
                    break

            logger.info(f"\n{'='*60}")
            logger.info(f"✓ Resolución bulk completada:")
            logger.info(f"  Exitosas: {resueltas_exitosas}")
            logger.info(f"  Fallidas: {resueltas_fallidas}")
            logger.info(f"  Omitidas (sin partidas directas): {omitidas_sin_partidas}")
            logger.info(f"  Total partidas agregadas: {total_partidas_agregadas}")
            logger.info(f"{'='*60}\n")

            return {
                'success': True,
                'resueltas_exitosas': resueltas_exitosas,
                'resueltas_fallidas': resueltas_fallidas,
                'omitidas_sin_partidas': omitidas_sin_partidas,
                'total_partidas_agregadas': total_partidas_agregadas,
                'errores': errores
            }

        except Exception as e:
            logger.error(f"Error al resolver discrepancias bulk con IA: {e}", exc_info=True)
            self.session.rollback()
            return {
                'success': False,
                'error': str(e),
                'resueltas_exitosas': 0,
                'resueltas_fallidas': 0,
                'omitidas_sin_partidas': 0,
                'total_partidas_agregadas': 0,
                'errores': []
            }

    def _guardar_capitulo(self, proyecto_id: int, cap_data: Dict, orden: int) -> Capitulo:
        """Guarda un capítulo y sus hijos"""
        capitulo = Capitulo(
            proyecto_id=proyecto_id,
            codigo=cap_data.get('codigo', ''),
            nombre=cap_data.get('nombre', ''),
            total=Decimal('0'),
            orden=orden
        )

        self.session.add(capitulo)
        self.session.flush()

        # Guardar subcapítulos
        for orden_sub, sub_data in enumerate(cap_data.get('subcapitulos', []), 1):
            subcapitulo = self._guardar_subcapitulo(capitulo.id, sub_data, orden_sub)
            capitulo.subcapitulos.append(subcapitulo)

        # Guardar partidas directas del capítulo
        for orden_part, part_data in enumerate(cap_data.get('partidas', []), 1):
            # Las partidas directas van en un subcapítulo implícito
            if cap_data.get('partidas'):
                subcap_implicito = Subcapitulo(
                    capitulo_id=capitulo.id,
                    codigo=f"{cap_data.get('codigo', '')}.00",
                    nombre="Partidas directas",
                    nivel=1,
                    orden=0
                )
                self.session.add(subcap_implicito)
                self.session.flush()

                for ord_p, p_data in enumerate(cap_data.get('partidas', []), 1):
                    partida = self._guardar_partida(subcap_implicito.id, p_data, ord_p)
                    subcap_implicito.partidas.append(partida)

                capitulo.subcapitulos.append(subcap_implicito)
                break  # Solo crear una vez

        return capitulo

    def _guardar_subcapitulo(self, capitulo_id: int, sub_data: Dict, orden: int) -> Subcapitulo:
        """Guarda un subcapítulo y sus partidas"""
        # Calcular nivel según puntos en el código
        codigo = sub_data.get('codigo', '')
        nivel = codigo.count('.') if codigo else 1

        subcapitulo = Subcapitulo(
            capitulo_id=capitulo_id,
            codigo=codigo,
            nombre=sub_data.get('nombre', ''),
            total=Decimal('0'),
            nivel=nivel,
            orden=orden
        )

        self.session.add(subcapitulo)
        self.session.flush()

        # Guardar partidas
        for orden_part, part_data in enumerate(sub_data.get('partidas', []), 1):
            partida = self._guardar_partida(subcapitulo.id, part_data, orden_part)
            subcapitulo.partidas.append(partida)

        return subcapitulo

    def _guardar_partida(self, subcapitulo_id: int, part_data: Dict, orden: int) -> Partida:
        """Guarda una partida y sus mediciones parciales"""
        # Extraer mediciones parciales
        mediciones_data = part_data.get('mediciones_parciales', [])
        tiene_mediciones = len(mediciones_data) > 0

        partida = Partida(
            subcapitulo_id=subcapitulo_id,
            codigo=part_data.get('codigo', ''),
            unidad=part_data.get('unidad', ''),
            resumen=part_data.get('resumen', ''),
            descripcion=part_data.get('descripcion', ''),
            cantidad_total=Decimal(str(part_data.get('cantidad', 0))),
            precio=Decimal(str(part_data.get('precio', 0))),
            importe=Decimal(str(part_data.get('importe', 0))),
            tiene_mediciones=tiene_mediciones,
            mediciones_validadas=False,
            suma_parciales=Decimal('0'),
            orden=orden
        )

        self.session.add(partida)
        self.session.flush()

        # Guardar mediciones parciales
        if mediciones_data:
            for orden_med, med_data in enumerate(mediciones_data, 1):
                medicion = self._guardar_medicion_parcial(partida.id, med_data, orden_med)
                partida.mediciones.append(medicion)

            # Calcular suma y validar
            partida.suma_parciales = Decimal(str(partida.calcular_total_parciales()))
            partida.mediciones_validadas = partida.validar_mediciones()

        return partida

    def _guardar_medicion_parcial(
        self,
        partida_id: int,
        med_data: Dict,
        orden: int
    ) -> MedicionParcial:
        """Guarda una medición parcial"""
        medicion = MedicionParcial(
            partida_id=partida_id,
            orden=orden,
            descripcion=med_data.get('descripcion', ''),
            uds=Decimal(str(med_data.get('uds', 1))),
            longitud=Decimal(str(med_data.get('longitud', 0))),
            anchura=Decimal(str(med_data.get('anchura', 0))),
            altura=Decimal(str(med_data.get('altura', 0))),
            parciales=Decimal(str(med_data.get('parciales', 0))),
            subtotal=Decimal(str(med_data.get('subtotal', 0)))
        )

        # Calcular subtotal si no viene calculado
        if medicion.subtotal == 0:
            medicion.subtotal = Decimal(str(medicion.calcular_subtotal()))

        self.session.add(medicion)
        return medicion

    def calcular_totales(self, proyecto_id: int) -> Decimal:
        """
        Calcula los totales de todo el proyecto

        Args:
            proyecto_id: ID del proyecto

        Returns:
            Decimal con el total del proyecto
        """
        proyecto = self.session.query(Proyecto).filter_by(id=proyecto_id).first()

        if not proyecto:
            return Decimal('0')

        total_proyecto = Decimal('0')

        for capitulo in proyecto.capitulos:
            total_capitulo = Decimal('0')

            for subcapitulo in capitulo.subcapitulos:
                total_subcapitulo = Decimal('0')

                for partida in subcapitulo.partidas:
                    total_subcapitulo += partida.importe or Decimal('0')

                subcapitulo.total = total_subcapitulo
                total_capitulo += total_subcapitulo

            capitulo.total = total_capitulo
            total_proyecto += total_capitulo

        self.session.commit()

        return total_proyecto

    def listar_proyectos(self) -> List[Proyecto]:
        """
        Lista todos los proyectos en la BD

        Returns:
            Lista de objetos Proyecto
        """
        return self.session.query(Proyecto).order_by(Proyecto.fecha_creacion.desc()).all()

    def obtener_proyecto(self, proyecto_id: int) -> Optional[Proyecto]:
        """
        Obtiene un proyecto por ID con eager loading de todas las relaciones

        Args:
            proyecto_id: ID del proyecto

        Returns:
            Objeto Proyecto o None
        """
        from sqlalchemy.orm import joinedload

        # Eager load de toda la jerarquía para evitar DetachedInstanceError
        proyecto = (
            self.session.query(Proyecto)
            .options(
                joinedload(Proyecto.capitulos)
                .joinedload(Capitulo.subcapitulos)
                .joinedload(Subcapitulo.partidas)
                .joinedload(Partida.mediciones)  # Corregido: 'mediciones' no 'mediciones_parciales'
            )
            .filter_by(id=proyecto_id)
            .first()
        )

        # Ordenar capítulos y subcapítulos por nivel y orden para mantener jerarquía visual
        if proyecto:
            # Ordenar capítulos por código numérico (01, 02, 03, etc.)
            proyecto.capitulos.sort(key=lambda c: c.orden or 0)

            for capitulo in proyecto.capitulos:
                # Ordenar subcapítulos por orden para mantener la secuencia correcta
                capitulo.subcapitulos.sort(key=lambda s: s.orden or 0)

        return proyecto

    def validar_mediciones_proyecto(self, proyecto_id: int) -> Dict:
        """
        Valida todas las mediciones parciales de un proyecto

        Args:
            proyecto_id: ID del proyecto

        Returns:
            Dict con resultado de validación
        """
        proyecto = self.obtener_proyecto(proyecto_id)

        if not proyecto:
            return {'error': 'Proyecto no encontrado'}

        total_partidas = 0
        partidas_con_mediciones = 0
        partidas_validas = 0
        partidas_invalidas = []

        for capitulo in proyecto.capitulos:
            for subcapitulo in capitulo.subcapitulos:
                for partida in subcapitulo.partidas:
                    total_partidas += 1

                    if partida.tiene_mediciones:
                        partidas_con_mediciones += 1

                        if partida.validar_mediciones():
                            partidas_validas += 1
                        else:
                            partidas_invalidas.append({
                                'codigo': partida.codigo,
                                'cantidad_total': float(partida.cantidad_total),
                                'suma_parciales': float(partida.calcular_total_parciales()),
                                'diferencia': float(abs(
                                    partida.cantidad_total - Decimal(str(partida.calcular_total_parciales()))
                                ))
                            })

        return {
            'total_partidas': total_partidas,
            'partidas_con_mediciones': partidas_con_mediciones,
            'partidas_validas': partidas_validas,
            'partidas_invalidas': len(partidas_invalidas),
            'detalles_invalidas': partidas_invalidas
        }

    def _calcular_hash_archivo(self, filepath: str) -> str:
        """
        Calcula SHA256 de un archivo

        Args:
            filepath: Ruta al archivo

        Returns:
            Hash SHA256 en hexadecimal
        """
        sha256_hash = hashlib.sha256()

        try:
            with open(filepath, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.warning(f"No se pudo calcular hash: {e}")
            return ""


if __name__ == "__main__":
    # Test de conexión
    logging.basicConfig(level=logging.INFO)

    with DatabaseManagerV2() as db:
        proyectos = db.listar_proyectos()
        print(f"\nProyectos en BD: {len(proyectos)}\n")

        for p in proyectos:
            print(f"ID: {p.id}")
            print(f"  Nombre: {p.nombre}")
            print(f"  Layout: {p.layout_detectado}")
            print(f"  Mediciones: {'Sí' if p.tiene_mediciones_auxiliares else 'No'}")
            print(f"  Total: {p.presupuesto_total:,.2f} €\n")
