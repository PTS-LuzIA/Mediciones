"""
Extractor dirigido de partidas basado en estructura de Fase 1.
Usa la estructura de capítulos/subcapítulos para buscar partidas de forma precisa.
"""

import logging
from typing import Dict, List, Optional
from pathlib import Path

try:
    from .pdf_extractor import PDFExtractor
    from .line_classifier import LineClassifier, TipoLinea
    from ..utils.normalizer import Normalizer
except ImportError:
    import sys
    from pathlib import Path
    parent_dir = str(Path(__file__).parent.parent)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    from parser.pdf_extractor import PDFExtractor
    from parser.line_classifier import LineClassifier, TipoLinea
    from utils.normalizer import Normalizer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GuidedPartidaExtractor:
    """
    Extractor dirigido que usa la estructura de Fase 1 como guía.
    Para cada subcapítulo, busca su inicio y fin en el PDF y extrae solo sus partidas.
    """

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.extractor = PDFExtractor(pdf_path)
        self.lineas = []
        self.clasificaciones = []

    def extraer_texto(self) -> None:
        """Extrae y clasifica todo el texto del PDF"""
        logger.info(f"Extrayendo texto de {self.pdf_path}")
        datos_pdf = self.extractor.extraer_todo()
        self.lineas = datos_pdf['all_lines']
        self.clasificaciones = LineClassifier.clasificar_bloque(self.lineas)
        logger.info(f"✓ Extraídas {len(self.lineas)} líneas")

    def extraer_partidas_subcapitulo(self, codigo_subcapitulo: str) -> List[Dict]:
        """
        Extrae partidas de un subcapítulo específico.

        Estrategia:
        1. Buscar línea que empieza con el código del subcapítulo
        2. Extraer partidas hasta encontrar:
           - TOTAL del subcapítulo
           - Inicio de otro subcapítulo/capítulo del mismo nivel o superior
           - Fin del documento

        Args:
            codigo_subcapitulo: Código del subcapítulo (ej: "01.04.01")

        Returns:
            Lista de partidas extraídas
        """
        if not self.clasificaciones:
            self.extraer_texto()

        partidas = []
        dentro_subcapitulo = False
        partida_actual = None
        nivel_subcapitulo = len(codigo_subcapitulo.split('.'))

        logger.debug(f"Buscando partidas para subcapítulo {codigo_subcapitulo} (nivel {nivel_subcapitulo})")

        for i, item in enumerate(self.clasificaciones):
            tipo = item['tipo']
            datos = item['datos']

            # 1. Detectar inicio del subcapítulo
            if tipo == TipoLinea.SUBCAPITULO and datos:
                codigo = datos.get('codigo', '')

                if codigo == codigo_subcapitulo:
                    dentro_subcapitulo = True
                    logger.debug(f"  └─ Inicio encontrado en línea {i}")
                    continue

                # Si estamos dentro y encontramos otro subcapítulo, verificar si debemos salir
                elif dentro_subcapitulo:
                    nivel_nuevo = len(codigo.split('.'))

                    # CASO 1: Encontramos un hijo (ej: buscando 01.04, encontramos 01.04.01)
                    # El hijo empieza con nuestro código + punto
                    if codigo.startswith(codigo_subcapitulo + '.'):
                        logger.debug(f"  └─ Fin por subcapítulo hijo {codigo} en línea {i}")
                        break

                    # CASO 2: Encontramos un subcapítulo del mismo nivel o superior
                    if nivel_nuevo <= nivel_subcapitulo:
                        logger.debug(f"  └─ Fin por nuevo subcapítulo {codigo} en línea {i}")
                        break

            # 2. Detectar fin con TOTAL
            if tipo == TipoLinea.TOTAL and dentro_subcapitulo:
                codigo_total = datos.get('codigo') if datos else None

                # Si el TOTAL tiene código y coincide con nuestro subcapítulo, cerrar
                if codigo_total == codigo_subcapitulo:
                    if partida_actual:
                        self._cerrar_partida(partida_actual, partidas)
                        partida_actual = None
                    logger.debug(f"  └─ Fin por TOTAL {codigo_total} en línea {i}")
                    break

                # Si el TOTAL no tiene código o es de nivel superior, también cerrar
                elif not codigo_total or (codigo_total and len(codigo_total.split('.')) < nivel_subcapitulo):
                    if partida_actual:
                        self._cerrar_partida(partida_actual, partidas)
                        partida_actual = None
                    logger.debug(f"  └─ Fin por TOTAL nivel superior en línea {i}")
                    break

            # 3. Detectar capítulo (nivel superior) - fin inmediato
            if tipo == TipoLinea.CAPITULO and dentro_subcapitulo:
                if partida_actual:
                    self._cerrar_partida(partida_actual, partidas)
                    partida_actual = None
                logger.debug(f"  └─ Fin por nuevo capítulo en línea {i}")
                break

            # 4. Extraer partidas solo si estamos dentro del subcapítulo
            if not dentro_subcapitulo:
                continue

            # PARTIDA HEADER - crear nueva partida
            if tipo == TipoLinea.PARTIDA_HEADER:
                # Cerrar partida anterior
                if partida_actual:
                    self._cerrar_partida(partida_actual, partidas)

                # Validar código
                codigo = datos['codigo']
                if not self._es_codigo_valido(codigo):
                    partida_actual = None
                    continue

                # Crear nueva partida
                partida_actual = {
                    'codigo': codigo,
                    'unidad': Normalizer.normalizar_unidad(datos['unidad']),
                    'resumen': datos['resumen'],
                    'descripcion': '',
                    'descripcion_lineas': [],
                    'cantidad': 0.0,
                    'precio': 0.0,
                    'importe': 0.0
                }

                # Extraer valores numéricos si vienen en el header
                if 'cantidad_str' in datos:
                    partida_actual['cantidad'] = Normalizer.limpiar_numero_espanol(datos['cantidad_str']) or 0.0
                if 'precio_str' in datos:
                    partida_actual['precio'] = Normalizer.limpiar_numero_espanol(datos['precio_str']) or 0.0
                if 'importe_str' in datos:
                    partida_actual['importe'] = Normalizer.limpiar_numero_espanol(datos['importe_str']) or 0.0

            # PARTIDA DESCRIPCIÓN
            elif tipo == TipoLinea.PARTIDA_DESCRIPCION:
                if partida_actual:
                    partida_actual['descripcion_lineas'].append(datos['texto'])

            # PARTIDA DATOS (números)
            elif tipo == TipoLinea.PARTIDA_DATOS:
                if partida_actual:
                    cantidad = Normalizer.limpiar_numero_espanol(datos['cantidad_str'])
                    precio = Normalizer.limpiar_numero_espanol(datos['precio_str'])
                    importe = Normalizer.limpiar_numero_espanol(datos['importe_str'])

                    partida_actual['cantidad'] = cantidad if cantidad else 0.0
                    partida_actual['precio'] = precio if precio else 0.0
                    partida_actual['importe'] = importe if importe else 0.0

        # Cerrar última partida si existe
        if partida_actual and dentro_subcapitulo:
            self._cerrar_partida(partida_actual, partidas)

        logger.info(f"✓ Extraídas {len(partidas)} partidas de {codigo_subcapitulo}")
        return partidas

    def _es_codigo_valido(self, codigo: str) -> bool:
        """Valida que el código de partida sea válido"""
        if not codigo or len(codigo) <= 2:
            return False
        if not any(c.isdigit() for c in codigo):
            return False

        palabras_prohibidas = [
            'ORDEN', 'CODIGO', 'CÓDIGO', 'RESUMEN', 'CANTIDAD', 'PRECIO', 'IMPORTE',
            'UNIDAD', 'UD', 'TOTAL', 'SUBTOTAL', 'CAPITULO', 'CAPÍTULO',
            'SUBCAPITULO', 'SUBCAPÍTULO', 'APARTADO', 'FOM', 'NTE', 'RD'
        ]

        if codigo.upper() in palabras_prohibidas:
            return False

        return True

    def _cerrar_partida(self, partida: Dict, lista_partidas: List[Dict]) -> None:
        """Cierra y valida una partida antes de agregarla"""
        # Validar importe
        if partida['importe'] == 0:
            logger.debug(f"⚠️ Partida descartada (importe 0): {partida['codigo']}")
            return

        # Reconstruir descripción
        if partida['descripcion_lineas']:
            partida['descripcion'] = Normalizer.reconstruir_descripcion(
                partida['descripcion_lineas']
            )

        del partida['descripcion_lineas']

        # Agregar a la lista
        lista_partidas.append(partida)
        logger.debug(f"  ✓ Partida {partida['codigo']}: {partida['importe']:.2f}€")
