"""
Parser Unificado V2 - Sistema de Dos Fases (adaptado de V1)
===========================================================

Aplica el mismo enfoque probado del V1:
- FASE 1: Extracción de estructura (capítulos/subcapítulos)
- FASE 2: Extracción de partidas individuales

"""

import logging
from typing import Dict, List, Optional
from pathlib import Path

# Importar componentes del V1 (ahora en parser_v2/)
from .pdf_extractor import PDFExtractor
from .column_detector import ColumnDetector
from .line_classifier import LineClassifier, TipoLinea
from .structure_parser import StructureParser

logger = logging.getLogger(__name__)


class PartidaParserV2Unified:
    """
    Parser unificado V2 que usa el enfoque de dos fases del V1
    """

    def __init__(self, pdf_path: str):
        self.pdf_path = Path(pdf_path)
        self.pdf_extractor = None
        self.column_detector = None
        self.line_classifier = None
        self.estructura = None
        self.partidas = []

    def parsear(self) -> Dict:
        """
        Parsea el PDF completo usando sistema de dos fases

        Returns:
            Dict con estructura completa
        """
        logger.info(f"Iniciando parseo unificado V2 de: {self.pdf_path}")

        # PASO 1: Extraer texto del PDF
        logger.info("PASO 1: Extrayendo texto del PDF...")
        self.pdf_extractor = PDFExtractor(str(self.pdf_path))
        datos_pdf = self.pdf_extractor.extraer_todo()

        lineas = datos_pdf['all_lines']
        layout_info = datos_pdf.get('layout_summary', {})

        logger.info(f"  - {len(lineas)} líneas extraídas")
        logger.info(f"  - Layout: {layout_info}")

        # PASO 2: Detectar columnas si es necesario
        num_columnas = layout_info.get('total_columnas', 1)
        logger.info(f"PASO 2: Documento con {num_columnas} columna(s)")

        # PASO 3: Clasificar líneas
        logger.info("PASO 3: Clasificando líneas...")
        clasificaciones = LineClassifier.clasificar_bloque(lineas)
        logger.info(f"  - {len(clasificaciones)} líneas clasificadas")

        # Contar tipos
        conteo_tipos = {}
        for item in clasificaciones:
            tipo = item['tipo']
            conteo_tipos[tipo] = conteo_tipos.get(tipo, 0) + 1
        logger.info(f"  - Tipos detectados: {conteo_tipos}")

        # FASE 1: Extraer estructura (capítulos/subcapítulos)
        logger.info("=" * 60)
        logger.info("FASE 1: Extrayendo estructura jerárquica...")
        logger.info("=" * 60)

        structure_parser = StructureParser()
        estructura_fase1 = structure_parser.parsear(lineas)

        logger.info(f"Fase 1 completada:")
        logger.info(f"  - Capítulos: {len(estructura_fase1.get('capitulos', []))}")

        # FASE 2: Construir estructura completa con partidas
        logger.info("=" * 60)
        logger.info("FASE 2: Construyendo estructura completa con partidas...")
        logger.info("=" * 60)

        self.estructura = self._construir_estructura_completa(clasificaciones)

        # Merge información de Fase 1 (totales de capítulos)
        self._merge_totales_fase1(estructura_fase1)

        # Calcular totales
        self._calcular_totales()

        # Calcular estadísticas
        estadisticas = self._calcular_estadisticas()

        logger.info("Parseo completado exitosamente")
        logger.info(f"Estadísticas: {estadisticas}")

        # Retornar formato esperado por la API
        return {
            'estructura': self.estructura,
            'metadata': {
                'pdf_nombre': self.pdf_path.name,
                'pdf_path': str(self.pdf_path),
                'num_columnas': num_columnas,
                'layout_info': layout_info
            },
            'estadisticas': estadisticas
        }

    def _construir_estructura_completa(self, clasificaciones: List[Dict]) -> Dict:
        """
        Construye estructura jerárquica completa con partidas
        Basado en el enfoque del V1
        """
        estructura = {
            'capitulos': [],
            'metadata': {
                'pdf_nombre': self.pdf_path.name,
                'total_lineas': len(clasificaciones)
            }
        }

        # Estado actual
        capitulo_actual = None
        subcapitulo_actual = None
        subcapitulo_nivel2_actual = None
        partida_actual = None

        # Mapa para niveles multinivel
        subcapitulos_map = {}

        for idx, item in enumerate(clasificaciones):
            tipo = item['tipo']
            datos = item.get('datos', {})
            linea = item.get('linea', '')

            if tipo == TipoLinea.CAPITULO:
                # Crear nuevo capítulo
                capitulo_actual = {
                    'codigo': datos.get('codigo', ''),
                    'nombre': datos.get('nombre', ''),
                    'total': 0.0,
                    'subcapitulos': [],
                    'partidas': []
                }
                estructura['capitulos'].append(capitulo_actual)
                subcapitulo_actual = None
                subcapitulo_nivel2_actual = None
                logger.debug(f"Capítulo creado: {capitulo_actual['codigo']} - {capitulo_actual['nombre']}")

            elif tipo == TipoLinea.SUBCAPITULO:
                codigo = datos.get('codigo', '')
                nombre = datos.get('nombre', '')

                # Determinar nivel del subcapítulo
                nivel = codigo.count('.')

                if nivel == 1:  # Nivel 1: XX.YY
                    subcapitulo_actual = {
                        'codigo': codigo,
                        'nombre': nombre,
                        'total': 0.0,
                        'subcapitulos': [],  # Para subniveles
                        'partidas': []
                    }
                    if capitulo_actual:
                        capitulo_actual['subcapitulos'].append(subcapitulo_actual)
                    subcapitulos_map[codigo] = subcapitulo_actual
                    subcapitulo_nivel2_actual = None
                    logger.debug(f"Subcapítulo L1 creado: {codigo} - {nombre}")

                elif nivel >= 2:  # Nivel 2+: XX.YY.ZZ o más
                    # Encontrar padre
                    partes = codigo.split('.')
                    codigo_padre = '.'.join(partes[:-1])

                    padre = subcapitulos_map.get(codigo_padre)

                    if padre is None and subcapitulo_actual:
                        # Si no hay padre explícito, usar subcapítulo_actual
                        padre = subcapitulo_actual

                    nuevo_subcapitulo = {
                        'codigo': codigo,
                        'nombre': nombre,
                        'total': 0.0,
                        'subcapitulos': [],
                        'partidas': []
                    }

                    if padre:
                        padre['subcapitulos'].append(nuevo_subcapitulo)
                    elif capitulo_actual:
                        # Fallback: agregar al capítulo
                        capitulo_actual['subcapitulos'].append(nuevo_subcapitulo)

                    subcapitulos_map[codigo] = nuevo_subcapitulo
                    subcapitulo_nivel2_actual = nuevo_subcapitulo
                    logger.debug(f"Subcapítulo L{nivel} creado: {codigo} - {nombre}")

            elif tipo == TipoLinea.PARTIDA_HEADER:
                # Iniciar nueva partida
                partida_actual = {
                    'codigo': datos.get('codigo', ''),
                    'unidad': datos.get('unidad', ''),
                    'resumen': datos.get('resumen', ''),
                    'descripcion': '',
                    'descripcion_lineas': [],
                    'cantidad': 0.0,
                    'precio': 0.0,
                    'importe': 0.0
                }
                logger.debug(f"Partida iniciada: {partida_actual['codigo']}")

            elif tipo == TipoLinea.PARTIDA_DESCRIPCION:
                # Agregar línea de descripción
                if partida_actual:
                    desc_texto = datos.get('texto', linea)
                    partida_actual['descripcion_lineas'].append(desc_texto)

            elif tipo == TipoLinea.PARTIDA_DATOS:
                # Finalizar partida con datos numéricos
                if partida_actual:
                    # Extraer números
                    partida_actual['cantidad'] = self._limpiar_numero(datos.get('cantidad_str', '0'))
                    partida_actual['precio'] = self._limpiar_numero(datos.get('precio_str', '0'))
                    partida_actual['importe'] = self._limpiar_numero(datos.get('importe_str', '0'))

                    # Construir descripción completa
                    if partida_actual['descripcion_lineas']:
                        partida_actual['descripcion'] = ' '.join(partida_actual['descripcion_lineas'])

                    # Determinar dónde agregar la partida
                    if subcapitulo_nivel2_actual:
                        subcapitulo_nivel2_actual['partidas'].append(partida_actual)
                    elif subcapitulo_actual:
                        subcapitulo_actual['partidas'].append(partida_actual)
                    elif capitulo_actual:
                        capitulo_actual['partidas'].append(partida_actual)

                    logger.debug(f"Partida completada: {partida_actual['codigo']} = {partida_actual['importe']}")
                    partida_actual = None

            elif tipo == TipoLinea.TOTAL:
                # Los totales se procesarán después con _merge_totales_fase1
                pass

        return estructura

    def _merge_totales_fase1(self, estructura_fase1: Dict):
        """
        Incorpora totales de la Fase 1 a la estructura completa
        """
        totales_fase1 = {}

        # Extraer totales de Fase 1
        for cap in estructura_fase1.get('capitulos', []):
            if 'total' in cap:
                totales_fase1[cap['codigo']] = cap['total']
            for sub in cap.get('subcapitulos', []):
                if 'total' in sub:
                    totales_fase1[sub['codigo']] = sub['total']
                # Recursivo para subniveles
                self._extraer_totales_recursivo(sub, totales_fase1)

        # Aplicar totales a la estructura actual
        for cap in self.estructura.get('capitulos', []):
            if cap['codigo'] in totales_fase1:
                cap['total'] = totales_fase1[cap['codigo']]
            for sub in cap.get('subcapitulos', []):
                if sub['codigo'] in totales_fase1:
                    sub['total'] = totales_fase1[sub['codigo']]
                self._aplicar_totales_recursivo(sub, totales_fase1)

    def _extraer_totales_recursivo(self, subcap: Dict, totales: Dict):
        """Extrae totales recursivamente"""
        for sub in subcap.get('subcapitulos', []):
            if 'total' in sub:
                totales[sub['codigo']] = sub['total']
            self._extraer_totales_recursivo(sub, totales)

    def _aplicar_totales_recursivo(self, subcap: Dict, totales: Dict):
        """Aplica totales recursivamente"""
        for sub in subcap.get('subcapitulos', []):
            if sub['codigo'] in totales:
                sub['total'] = totales[sub['codigo']]
            self._aplicar_totales_recursivo(sub, totales)

    def _calcular_totales(self):
        """
        Calcula totales sumando partidas
        (solo para elementos sin total de Fase 1)
        """
        for cap in self.estructura.get('capitulos', []):
            if cap['total'] == 0.0:
                cap['total'] = self._calcular_total_recursivo(cap)

    def _calcular_total_recursivo(self, elemento: Dict) -> float:
        """Calcula total sumando partidas recursivamente"""
        total = 0.0

        # Sumar partidas directas
        for partida in elemento.get('partidas', []):
            total += partida.get('importe', 0.0)

        # Sumar subcapítulos
        for sub in elemento.get('subcapitulos', []):
            if sub.get('total', 0.0) > 0:
                total += sub['total']
            else:
                sub['total'] = self._calcular_total_recursivo(sub)
                total += sub['total']

        return total

    def _limpiar_numero(self, texto: str) -> float:
        """
        Limpia string de número español a float
        Ejemplos: "1.234,56" -> 1234.56
        """
        if not texto:
            return 0.0

        # Remover espacios
        texto = texto.strip()

        # Remover separadores de miles (puntos)
        texto = texto.replace('.', '')

        # Reemplazar coma decimal por punto
        texto = texto.replace(',', '.')

        try:
            return float(texto)
        except ValueError:
            logger.warning(f"No se pudo convertir '{texto}' a número")
            return 0.0

    def _calcular_estadisticas(self) -> Dict:
        """
        Calcula estadísticas del procesamiento
        """
        total_capitulos = len(self.estructura.get('capitulos', []))
        total_subcapitulos = 0
        total_partidas = 0
        presupuesto_total = 0.0

        for cap in self.estructura.get('capitulos', []):
            presupuesto_total += cap.get('total', 0.0)

            # Contar subcapítulos y partidas recursivamente
            stats = self._contar_recursivo(cap)
            total_subcapitulos += stats['subcapitulos']
            total_partidas += stats['partidas']

        return {
            'total_capitulos': total_capitulos,
            'total_subcapitulos': total_subcapitulos,
            'total_partidas': total_partidas,
            'presupuesto_total': presupuesto_total
        }

    def _contar_recursivo(self, elemento: Dict) -> Dict:
        """Cuenta subcapítulos y partidas recursivamente"""
        subcaps = len(elemento.get('subcapitulos', []))
        partidas = len(elemento.get('partidas', []))

        for sub in elemento.get('subcapitulos', []):
            stats = self._contar_recursivo(sub)
            subcaps += stats['subcapitulos']
            partidas += stats['partidas']

        return {
            'subcapitulos': subcaps,
            'partidas': partidas
        }
