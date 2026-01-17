"""
Extractor local de descripciones de partidas.
Busca descripciones en el texto ya clasificado por el parser local,
sin necesidad de usar LLMs (coste $0).
"""

import os
import logging
from typing import Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class LocalDescriptionExtractor:
    """
    Extrae descripciones de partidas buscando en el texto ya clasificado
    por el parser local (LineClassifier).

    Reutiliza las clasificaciones cacheadas de Fase 2 para evitar re-procesar el PDF.
    """

    # Caché global de clasificaciones (compartido con PartidaExtractionAgent)
    _clasificaciones_cache = {}

    def __init__(self, pdf_path: str):
        """
        Args:
            pdf_path: Ruta al archivo PDF
        """
        self.pdf_path = pdf_path
        self.clasificaciones = None

    def _cargar_clasificaciones(self) -> List[Dict]:
        """
        Carga las clasificaciones del PDF.
        Intenta usar caché si está disponible, sino extrae y clasifica.

        Returns:
            Lista de clasificaciones de líneas
        """
        # Usar caché si está disponible
        cache_key = f"{self.pdf_path}_{os.path.getmtime(self.pdf_path)}"

        if cache_key in self._clasificaciones_cache:
            logger.info(f"✓ Usando clasificaciones cacheadas para {os.path.basename(self.pdf_path)}")
            return self._clasificaciones_cache[cache_key]

        # Si no está en caché, extraer y clasificar
        logger.info(f"📄 Extrayendo y clasificando líneas del PDF...")

        # Importar parsers locales
        import sys
        parent_dir = str(Path(__file__).parent.parent)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)

        from parser.pdf_extractor import PDFExtractor
        from parser.line_classifier import LineClassifier

        extractor = PDFExtractor(self.pdf_path)
        datos = extractor.extraer_todo()
        lineas = datos['all_lines']
        clasificaciones = LineClassifier.clasificar_bloque(lineas)

        # Guardar en caché
        self._clasificaciones_cache[cache_key] = clasificaciones
        logger.info(f"💾 Clasificaciones guardadas en caché ({len(clasificaciones)} líneas)")

        return clasificaciones

    def extraer_descripcion(self, codigo_partida: str, subcapitulo_codigo: str = None) -> str:
        """
        Busca la descripción de una partida en el texto clasificado.

        Estrategia:
        1. Localizar línea PARTIDA_HEADER con el código de partida
        2. Capturar TODAS las líneas PARTIDA_DESCRIPCION siguientes
        3. Hasta encontrar PARTIDA_DATOS (números) o nueva PARTIDA_HEADER

        Args:
            codigo_partida: Código de la partida (ej: "m23U01BP010")
            subcapitulo_codigo: Código del subcapítulo (opcional, para contexto)

        Returns:
            String con la descripción encontrada (vacío si no se encuentra)
        """
        if self.clasificaciones is None:
            self.clasificaciones = self._cargar_clasificaciones()

        descripcion_lineas = []
        encontrado_header = False
        dentro_subcapitulo = subcapitulo_codigo is None  # Si no hay filtro, buscar en todo el PDF

        # Debug: contar tipos para diagnóstico
        tipos_encontrados = {}
        for item in self.clasificaciones:
            t = item['tipo'].value if hasattr(item['tipo'], 'value') else item['tipo']
            tipos_encontrados[t] = tipos_encontrados.get(t, 0) + 1

        logger.debug(f"Tipos en clasificaciones: {tipos_encontrados}")

        for i, item in enumerate(self.clasificaciones):
            tipo = item['tipo'].value if hasattr(item['tipo'], 'value') else item['tipo']
            datos = item.get('datos', {}) or {}  # Asegurar que datos nunca sea None
            codigo_item = datos.get('codigo', '')

            # Si hay filtro de subcapítulo, verificar que estamos dentro
            if subcapitulo_codigo and not dentro_subcapitulo:
                if tipo in ['subcapitulo', 'apartado'] and codigo_item == subcapitulo_codigo:
                    dentro_subcapitulo = True
                continue

            # Si estamos fuera del subcapítulo correcto, saltar
            if subcapitulo_codigo and dentro_subcapitulo:
                # Salir si encontramos otro subcapítulo del mismo nivel
                if tipo in ['subcapitulo', 'apartado'] and codigo_item != subcapitulo_codigo:
                    # Verificar si es del mismo nivel (no hijo)
                    if subcapitulo_codigo and not codigo_item.startswith(subcapitulo_codigo + '.'):
                        break

            # 1. Buscar header de la partida
            if tipo == 'partida_header':
                codigo_header = datos.get('codigo', '')
                # Comparación exacta del código
                if codigo_header == codigo_partida:
                    encontrado_header = True
                    logger.debug(f"✓ Encontrado header de partida {codigo_partida}")
                    continue
                elif encontrado_header:
                    # Ignorar headers de solapamiento (duplicados visuales del PDF)
                    if datos.get('solapamiento_detectado'):
                        logger.debug(f"  ~ Ignorando header de solapamiento: {codigo_header}")
                        continue
                    # Encontramos otro header real, terminar búsqueda
                    logger.debug(f"Fin de descripción: encontrado nuevo header {codigo_header}")
                    break

            # 2. Si encontramos el header, capturar descripciones siguientes
            if encontrado_header:
                if tipo == 'partida_descripcion':
                    texto = datos.get('texto', '').strip()
                    if texto:
                        descripcion_lineas.append(texto)
                        logger.debug(f"  + Línea descripción: {texto[:50]}...")
                elif tipo == 'partida_datos':
                    # Fin de la descripción - encontramos los datos numéricos
                    logger.debug(f"Fin de descripción: encontrados datos numéricos")
                    break
                elif tipo == 'partida_header':
                    # Ya manejado arriba
                    break

        descripcion_completa = '\n'.join(descripcion_lineas).strip()

        if descripcion_completa:
            logger.info(f"✓ Descripción encontrada para {codigo_partida}: {len(descripcion_completa)} caracteres")
        else:
            logger.debug(f"⚠️ No se encontró descripción para {codigo_partida}")

        return descripcion_completa

    def completar_descripciones_proyecto(self, proyecto_id: int) -> Dict:
        """
        Completa todas las descripciones faltantes del proyecto usando el parser local.

        Args:
            proyecto_id: ID del proyecto

        Returns:
            Dict con estadísticas:
            {
                "success": True/False,
                "partidas_procesadas": 1000,
                "descripciones_encontradas": 700,
                "sin_descripcion": 300,
                "porcentaje_completado": 70.0
            }
        """
        try:
            # Importar DB manager
            import sys
            parent_dir = str(Path(__file__).parent.parent)
            if parent_dir not in sys.path:
                sys.path.insert(0, parent_dir)

            from models.hybrid_db_manager import HybridDatabaseManager
            from models.hybrid_models import HybridPartida, HybridSubcapitulo, HybridCapitulo

            db = HybridDatabaseManager()

            # Obtener partidas sin descripción del proyecto
            partidas_sin_desc = db.session.query(HybridPartida).join(
                HybridSubcapitulo
            ).join(
                HybridCapitulo
            ).filter(
                HybridCapitulo.proyecto_id == proyecto_id,
                (HybridPartida.descripcion == None) | (HybridPartida.descripcion == '')
            ).all()

            if not partidas_sin_desc:
                logger.info(f"✓ Todas las partidas del proyecto {proyecto_id} ya tienen descripción")
                return {
                    "success": True,
                    "partidas_procesadas": 0,
                    "descripciones_encontradas": 0,
                    "sin_descripcion": 0,
                    "porcentaje_completado": 100.0
                }

            logger.info(f"📝 [FASE 4 LOCAL] Completando descripciones para {len(partidas_sin_desc)} partidas del proyecto {proyecto_id}")

            # Cargar clasificaciones una sola vez
            if self.clasificaciones is None:
                self.clasificaciones = self._cargar_clasificaciones()

            completadas = 0
            sin_descripcion = 0

            for partida in partidas_sin_desc:
                # Obtener subcapítulo para contexto
                subcap = partida.subcapitulo
                subcap_codigo = subcap.codigo if subcap else None

                # Buscar descripción
                desc = self.extraer_descripcion(partida.codigo, subcap_codigo)

                if desc:
                    partida.descripcion = desc
                    completadas += 1
                    if completadas % 100 == 0:
                        logger.info(f"  Progreso: {completadas}/{len(partidas_sin_desc)} descripciones completadas")
                else:
                    sin_descripcion += 1

            # Commit de cambios
            db.session.commit()

            porcentaje = (completadas / len(partidas_sin_desc) * 100) if partidas_sin_desc else 0

            logger.info(f"✓ [FASE 4 LOCAL] Completado:")
            logger.info(f"  - Partidas procesadas: {len(partidas_sin_desc)}")
            logger.info(f"  - Descripciones encontradas: {completadas} ({porcentaje:.1f}%)")
            logger.info(f"  - Sin descripción: {sin_descripcion}")

            return {
                "success": True,
                "partidas_procesadas": len(partidas_sin_desc),
                "descripciones_encontradas": completadas,
                "sin_descripcion": sin_descripcion,
                "porcentaje_completado": porcentaje
            }

        except Exception as e:
            logger.error(f"❌ [FASE 4 LOCAL] Error completando descripciones: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "partidas_procesadas": 0,
                "descripciones_encontradas": 0,
                "sin_descripcion": 0,
                "porcentaje_completado": 0.0
            }


# Función helper para uso simple
def completar_descripciones(proyecto_id: int, pdf_path: str) -> Dict:
    """
    Completa descripciones faltantes de un proyecto usando el parser local.

    Args:
        proyecto_id: ID del proyecto
        pdf_path: Ruta al archivo PDF original

    Returns:
        Dict con estadísticas del proceso
    """
    extractor = LocalDescriptionExtractor(pdf_path)
    return extractor.completar_descripciones_proyecto(proyecto_id)


if __name__ == "__main__":
    # Test
    import sys

    if len(sys.argv) < 3:
        print("Uso: python local_description_extractor.py <proyecto_id> <pdf_path>")
        sys.exit(1)

    proyecto_id = int(sys.argv[1])
    pdf_path = sys.argv[2]

    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    resultado = completar_descripciones(proyecto_id, pdf_path)

    print("\n=== RESULTADO ===")
    print(f"Éxito: {resultado['success']}")
    print(f"Partidas procesadas: {resultado['partidas_procesadas']}")
    print(f"Descripciones encontradas: {resultado['descripciones_encontradas']}")
    print(f"Sin descripción: {resultado['sin_descripcion']}")
    print(f"Porcentaje completado: {resultado['porcentaje_completado']:.1f}%")
