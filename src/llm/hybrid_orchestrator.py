"""
Orquestador del sistema HÍBRIDO de extracción.

Coordina las 4 fases:
1. Extracción de estructura con IA (StructureExtractionAgent)
2. Extracción de partidas con parser local (PartidaParser)
3. Validación cruzada y re-validación selectiva con IA
4. Completado de descripciones con parser local (LocalDescriptionExtractor)

Autor: Claude Code
Fecha: 2026-01-16
"""

import logging
import time
import os
from typing import Dict, List
from pathlib import Path

# Importar agentes existentes
try:
    from .structure_extraction_agent import StructureExtractionAgent
    from .partida_count_agent import PartidaCountAgent
    from ..parser.partida_parser import PartidaParser
    from ..parser.local_structure_extractor import LocalStructureExtractor
    from ..models.hybrid_db_manager import HybridDatabaseManager
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from llm.structure_extraction_agent import StructureExtractionAgent
    from llm.partida_count_agent import PartidaCountAgent
    from parser.partida_parser import PartidaParser
    from parser.local_structure_extractor import LocalStructureExtractor
    from models.hybrid_db_manager import HybridDatabaseManager

logger = logging.getLogger(__name__)


class HybridOrchestrator:
    """
    Orquestador del procesamiento híbrido IA + Local + Validación
    """

    def __init__(self, db_manager: HybridDatabaseManager = None, use_local_extraction: bool = True):
        """
        Args:
            db_manager: Gestor de BD (opcional)
            use_local_extraction: Si True, usa extracción local en lugar de IA (default: True)
        """
        self.db = db_manager or HybridDatabaseManager()
        self.use_local_extraction = use_local_extraction
        self.structure_agent = StructureExtractionAgent()
        self.count_agent = PartidaCountAgent()

    async def procesar_proyecto_completo(
        self,
        pdf_path: str,
        nombre_proyecto: str = None,
        tolerancia_validacion: float = 5.0,
        completar_descripciones: bool = True
    ) -> Dict:
        """
        Procesa un proyecto completo con las 4 fases

        Args:
            pdf_path: Ruta al archivo PDF
            nombre_proyecto: Nombre del proyecto (opcional)
            tolerancia_validacion: % de tolerancia para validación (default: 5%)
            completar_descripciones: Si True, ejecuta Fase 4 (completar descripciones localmente)

        Returns:
            Dict con resultado completo del procesamiento
        """
        tiempo_inicio = time.time()

        try:
            # Crear proyecto vacío
            if not nombre_proyecto:
                nombre_proyecto = Path(pdf_path).stem

            proyecto = self.db.crear_proyecto(
                nombre=nombre_proyecto,
                descripcion=f"Proyecto híbrido - {Path(pdf_path).name}",
                archivo_origen=pdf_path
            )

            logger.info(f"🚀 Iniciando procesamiento híbrido para proyecto {proyecto.id}")

            # ============================================================
            # FASE 1: Extraer estructura (LOCAL o IA)
            # ============================================================
            if self.use_local_extraction:
                logger.info("🔧 [FASE 1/3] Extrayendo estructura con PARSER LOCAL...")
                fase1_inicio = time.time()

                # Usar extractor local (cacheado, determinista, confiable)
                local_extractor = LocalStructureExtractor(pdf_path)
                estructura_ia = local_extractor.extraer_estructura(force_refresh=False)

                if not estructura_ia.get('capitulos'):
                    raise Exception("No se pudo extraer estructura con parser local")

                fase1_tiempo = time.time() - fase1_inicio
                logger.info(f"  ✓ Extracción LOCAL completada en {fase1_tiempo:.2f}s")

                # Validación automática
                validacion = estructura_ia.get('validacion_local', {})
                if not validacion.get('valido', True):
                    logger.warning(f"  ⚠️ Detectadas {len(validacion.get('inconsistencias', []))} inconsistencias en totales")
                    logger.warning(f"  ⚠️ Puede que falten partidas o haya errores en el PDF")
                else:
                    logger.info(f"  ✓ Validación: Todos los totales cuadran correctamente")

            else:
                logger.info("📊 [FASE 1/3] Extrayendo estructura con IA...")
                fase1_inicio = time.time()

                # Paso 1.1: Extraer estructura (capítulos, subcapítulos, totales)
                logger.info("  [FASE 1.1] Extrayendo jerarquía de capítulos y subcapítulos...")
                estructura_ia = await self.structure_agent.extraer_estructura(pdf_path)

                if not estructura_ia.get('capitulos'):
                    raise Exception("No se pudo extraer estructura con IA")

                # Paso 1.2: Contar partidas de cada capítulo/subcapítulo
                logger.info("  [FASE 1.2] Contando número de partidas por sección...")
                conteo_inicio = time.time()

                conteo = await self.count_agent.contar_partidas(pdf_path, estructura_ia)
                estructura_ia = self.count_agent.fusionar_conteo_con_estructura(estructura_ia, conteo)

                conteo_tiempo = time.time() - conteo_inicio
                logger.info(f"  ✓ Conteo completado en {conteo_tiempo:.2f}s")

                fase1_tiempo = time.time() - fase1_inicio

            # Guardar estructura en BD
            success_fase1 = self.db.guardar_estructura_fase1(
                proyecto.id,
                estructura_ia,
                fase1_tiempo
            )

            if not success_fase1:
                raise Exception("Error guardando estructura IA en BD")

            logger.info(f"✓ [FASE 1] Completada en {fase1_tiempo:.2f}s - {len(estructura_ia['capitulos'])} capítulos extraídos")

            # ============================================================
            # FASE 2: Extraer partidas con parser local
            # ============================================================
            logger.info("🔧 [FASE 2/3] Extrayendo partidas con parser local...")
            fase2_inicio = time.time()

            parser = PartidaParser(pdf_path)
            resultado_parser = parser.parsear()

            # Guardar texto completo del PDF para debugging manual
            try:
                nombre_pdf = os.path.basename(pdf_path).replace('.pdf', '')
                texto_completo_path = f"logs/extracted_full_text_{proyecto.id}_{nombre_pdf}.txt"
                os.makedirs('logs', exist_ok=True)
                parser.extractor.guardar_texto(texto_completo_path)
                logger.info(f"💾 Texto completo guardado en: {texto_completo_path}")
            except Exception as e:
                logger.warning(f"⚠️ No se pudo guardar texto completo: {e}")

            fase2_tiempo = time.time() - fase2_inicio

            # Obtener partidas planas
            partidas_locales = parser.obtener_todas_partidas()

            if not partidas_locales:
                logger.warning("⚠️ Parser local no extrajo partidas")

            # Guardar partidas en BD
            resultado_fase2 = self.db.guardar_partidas_fase2(
                proyecto.id,
                partidas_locales,
                fase2_tiempo
            )

            if not resultado_fase2['success']:
                raise Exception(f"Error guardando partidas: {resultado_fase2.get('error')}")

            logger.info(f"✓ [FASE 2] Completada en {fase2_tiempo:.2f}s - {resultado_fase2['partidas_guardadas']} partidas extraídas")

            # ============================================================
            # FASE 3: Validación cruzada
            # ============================================================
            logger.info("🔍 [FASE 3/4] Validando coincidencias IA vs Local...")
            fase3_inicio = time.time()

            resultado_validacion = self.db.validar_fase3(proyecto.id, tolerancia_validacion)

            fase3_tiempo = time.time() - fase3_inicio

            if not resultado_validacion['success']:
                raise Exception(f"Error en validación: {resultado_validacion.get('error')}")

            logger.info(f"✓ [FASE 3] Completada en {fase3_tiempo:.2f}s")
            logger.info(f"  • Validados: {resultado_validacion['validados']}")
            logger.info(f"  • Discrepancias: {resultado_validacion['discrepancias']}")
            logger.info(f"  • Coincidencia global: {resultado_validacion['porcentaje_coincidencia']:.2f}%")

            # ============================================================
            # FASE 4: Completar descripciones (OPCIONAL - LOCAL)
            # ============================================================
            fase4_tiempo = 0
            resultado_fase4 = None

            if completar_descripciones:
                logger.info("📝 [FASE 4/4] Completando descripciones con parser local...")
                fase4_inicio = time.time()

                try:
                    from ..parser.local_description_extractor import LocalDescriptionExtractor

                    extractor = LocalDescriptionExtractor(pdf_path)
                    resultado_fase4 = extractor.completar_descripciones_proyecto(proyecto.id)

                    fase4_tiempo = time.time() - fase4_inicio

                    if resultado_fase4['success']:
                        logger.info(f"✓ [FASE 4] Completada en {fase4_tiempo:.2f}s")
                        logger.info(f"  • Partidas procesadas: {resultado_fase4['partidas_procesadas']}")
                        logger.info(f"  • Descripciones encontradas: {resultado_fase4['descripciones_encontradas']} ({resultado_fase4['porcentaje_completado']:.1f}%)")
                        logger.info(f"  • Sin descripción: {resultado_fase4['sin_descripcion']}")
                    else:
                        logger.warning(f"⚠️ [FASE 4] Error: {resultado_fase4.get('error')}")

                except Exception as e:
                    logger.warning(f"⚠️ [FASE 4] Error completando descripciones: {e}")
                    resultado_fase4 = {
                        "success": False,
                        "error": str(e),
                        "partidas_procesadas": 0,
                        "descripciones_encontradas": 0
                    }
            else:
                logger.info("⏭️ [FASE 4] Omitida (completar_descripciones=False)")

            # ============================================================
            # Resultado final
            # ============================================================
            tiempo_total = time.time() - tiempo_inicio

            # Actualizar tiempo total en proyecto
            proyecto_actualizado = self.db.obtener_proyecto(proyecto.id)
            proyecto_actualizado.tiempo_fase3 = fase3_tiempo
            self.db.session.commit()

            resultado_final = {
                "success": True,
                "proyecto_id": proyecto.id,
                "nombre": proyecto_actualizado.nombre,
                "fase_actual": proyecto_actualizado.fase_actual.value,
                "tiempos": {
                    "fase1_estructura_ia": fase1_tiempo,
                    "fase2_partidas_local": fase2_tiempo,
                    "fase3_validacion": fase3_tiempo,
                    "fase4_descripciones": fase4_tiempo,
                    "total": tiempo_total
                },
                "totales": {
                    "estructura_ia": proyecto_actualizado.total_estructura_ia,
                    "partidas_local": proyecto_actualizado.total_partidas_local,
                    "porcentaje_coincidencia": resultado_validacion['porcentaje_coincidencia']
                },
                "estadisticas": {
                    "capitulos": len(estructura_ia['capitulos']),
                    "partidas": resultado_fase2['partidas_guardadas'],
                    "validados": resultado_validacion['validados'],
                    "discrepancias": resultado_validacion['discrepancias']
                },
                "subcapitulos_a_revisar": resultado_validacion['subcapitulos_a_revisar']
            }

            # Añadir estadísticas de Fase 4 si se ejecutó
            if resultado_fase4:
                resultado_final["fase4_descripciones"] = {
                    "partidas_procesadas": resultado_fase4.get('partidas_procesadas', 0),
                    "descripciones_encontradas": resultado_fase4.get('descripciones_encontradas', 0),
                    "sin_descripcion": resultado_fase4.get('sin_descripcion', 0),
                    "porcentaje_completado": resultado_fase4.get('porcentaje_completado', 0.0)
                }

            return resultado_final

        except Exception as e:
            logger.error(f"❌ Error en procesamiento híbrido: {e}")
            return {
                "success": False,
                "error": str(e),
                "proyecto_id": proyecto.id if 'proyecto' in locals() else None
            }

    async def revisar_discrepancias_con_ia(self, proyecto_id: int, codigos_subcapitulos: List[str] = None) -> Dict:
        """
        Re-valida subcapítulos con discrepancias usando IA

        Args:
            proyecto_id: ID del proyecto híbrido
            codigos_subcapitulos: Lista de códigos de subcapítulos a revisar (None = todos los con discrepancia)

        Returns:
            Dict con resultado de la revisión
        """
        try:
            proyecto = self.db.obtener_proyecto(proyecto_id)
            if not proyecto:
                return {"success": False, "error": f"Proyecto {proyecto_id} no encontrado"}

            logger.info(f"🔍 Revisando discrepancias con IA para proyecto {proyecto_id}")

            # TODO: Implementar lógica de re-validación selectiva con IA
            # Por ahora retorna placeholder

            return {
                "success": True,
                "mensaje": "Revisión con IA pendiente de implementar",
                "subcapitulos_revisados": 0
            }

        except Exception as e:
            logger.error(f"❌ Error revisando con IA: {e}")
            return {"success": False, "error": str(e)}


async def procesar_pdf_hibrido(
    pdf_path: str,
    nombre_proyecto: str = None,
    tolerancia: float = 5.0,
    use_local_extraction: bool = True
) -> Dict:
    """
    Función helper para procesar un PDF con el sistema híbrido

    Args:
        pdf_path: Ruta al PDF
        nombre_proyecto: Nombre del proyecto (opcional)
        tolerancia: % de tolerancia para validación (default: 5%)
        use_local_extraction: Si True, usa extracción local en lugar de IA (default: True)

    Returns:
        Dict con resultado del procesamiento
    """
    orchestrator = HybridOrchestrator(use_local_extraction=use_local_extraction)
    return await orchestrator.procesar_proyecto_completo(
        pdf_path,
        nombre_proyecto,
        tolerancia
    )


if __name__ == "__main__":
    import asyncio

    # Test
    pdf_test = "ejemplo/PROYECTO CALYPOFADO_extract.pdf"

    async def test():
        resultado = await procesar_pdf_hibrido(pdf_test, "Proyecto Test Híbrido")
        print("\n" + "="*80)
        print("RESULTADO PROCESAMIENTO HÍBRIDO")
        print("="*80)
        print(f"Success: {resultado['success']}")
        if resultado['success']:
            print(f"Proyecto ID: {resultado['proyecto_id']}")
            print(f"Fase: {resultado['fase_actual']}")
            print(f"\nTiempos:")
            for fase, tiempo in resultado['tiempos'].items():
                print(f"  {fase}: {tiempo:.2f}s")
            print(f"\nTotales:")
            print(f"  IA: {resultado['totales']['estructura_ia']:.2f} €")
            print(f"  Local: {resultado['totales']['partidas_local']:.2f} €")
            print(f"  Coincidencia: {resultado['totales']['porcentaje_coincidencia']:.2f}%")
            print(f"\nEstadísticas:")
            print(f"  Capítulos: {resultado['estadisticas']['capitulos']}")
            print(f"  Partidas: {resultado['estadisticas']['partidas']}")
            print(f"  Validados: {resultado['estadisticas']['validados']}")
            print(f"  Discrepancias: {resultado['estadisticas']['discrepancias']}")
        else:
            print(f"Error: {resultado['error']}")
        print("="*80)

    asyncio.run(test())
