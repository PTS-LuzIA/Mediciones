"""
Partida Parser V2 - Parser Unificado Multi-formato
==================================================

Parser que maneja automáticamente las 4 variantes:
1. 1 columna SIN mediciones auxiliares
2. 2 columnas SIN mediciones auxiliares
3. 1 columna CON mediciones auxiliares
4. 2 columnas CON mediciones auxiliares

FLUJO:
1. Detectar layout (1 vs 2 columnas)
2. Normalizar texto a flujo lineal
3. Detectar tipo de mediciones (con/sin tabla)
4. Procesar con estrategia adaptada

"""

import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from .layout_detector import LayoutDetector
from .layout_normalizer import LayoutNormalizer
from .mediciones_detector import MedicionesDetector
from .line_classifier_v2 import LineClassifier, TipoLinea

logger = logging.getLogger(__name__)


class PartidaParserV2:
    """Parser unificado que maneja múltiples formatos automáticamente"""

    def __init__(self, pdf_path: str):
        """
        Args:
            pdf_path: Ruta al archivo PDF
        """
        self.pdf_path = pdf_path
        self.pdf_nombre = Path(pdf_path).name

        # Metadata de detección (se llenará en parsear())
        self.layout_detectado = None
        self.tiene_mediciones_auxiliares = None
        self.lineas = []
        self.clasificaciones = []

        logger.info(f"\n{'='*80}")
        logger.info(f"PARSER V2 INICIALIZADO: {self.pdf_nombre}")
        logger.info(f"{'='*80}\n")

    def parsear(self) -> Dict:
        """
        Parsea el PDF detectando automáticamente su formato

        Returns:
            Dict con:
                - estructura: jerarquía de capítulos/subcapítulos/partidas
                - estadisticas: resumen del procesamiento
                - metadata: información de detección
        """
        # PASO 1: Detectar layout (1 vs 2 columnas)
        logger.info("PASO 1/4: Detectando layout...")
        with LayoutDetector(self.pdf_path) as detector:
            self.layout_detectado = detector.detectar_layout()

        # PASO 2: Normalizar texto
        logger.info("\nPASO 2/4: Normalizando texto...")
        with LayoutNormalizer(self.pdf_path) as normalizer:
            self.lineas = normalizer.normalizar(self.layout_detectado)

        # PASO 3: Detectar tipo de mediciones
        logger.info("\nPASO 3/4: Detectando tipo de mediciones...")
        detector_med = MedicionesDetector(self.lineas)
        self.tiene_mediciones_auxiliares = detector_med.detectar_mediciones_auxiliares()

        # PASO 4: Procesar estructura
        logger.info("\nPASO 4/4: Procesando estructura...")
        logger.info(f"\n📋 Configuración detectada:")
        logger.info(f"   Layout: {self.layout_detectado}")
        logger.info(f"   Mediciones auxiliares: {'SÍ' if self.tiene_mediciones_auxiliares else 'NO'}\n")

        # Clasificar líneas
        self.clasificaciones = self._clasificar_lineas()

        # Construir estructura jerárquica
        estructura = self._construir_estructura()

        # Calcular estadísticas
        estadisticas = self._calcular_estadisticas(estructura)

        return {
            'estructura': estructura,
            'estadisticas': estadisticas,
            'metadata': {
                'pdf_path': self.pdf_path,
                'pdf_nombre': self.pdf_nombre,
                'layout_detectado': self.layout_detectado,
                'tiene_mediciones_auxiliares': self.tiene_mediciones_auxiliares,
                'total_lineas': len(self.lineas),
                'fecha_procesamiento': datetime.now().isoformat()
            }
        }

    def _clasificar_lineas(self) -> List[Dict]:
        """
        Clasifica cada línea según su tipo

        Returns:
            Lista de clasificaciones
        """
        clasificaciones = []
        contexto = {}

        for i, linea in enumerate(self.lineas):
            clasificacion = LineClassifier.clasificar(linea, contexto)
            clasificacion['numero_linea'] = i + 1
            clasificacion['texto_original'] = linea
            clasificaciones.append(clasificacion)

            # Actualizar contexto
            if clasificacion['tipo'] != TipoLinea.IGNORAR:
                contexto['ultima_clasificacion'] = clasificacion

        # Log resumen
        tipos_count = {}
        for c in clasificaciones:
            tipo = c['tipo'].value if hasattr(c['tipo'], 'value') else str(c['tipo'])
            tipos_count[tipo] = tipos_count.get(tipo, 0) + 1

        logger.info("Clasificación completada:")
        for tipo, count in sorted(tipos_count.items()):
            logger.info(f"  {tipo:20} {count:5} líneas")

        return clasificaciones

    def _construir_estructura(self) -> Dict:
        """
        Construye la estructura jerárquica del presupuesto

        Returns:
            Dict con proyecto, capítulos, subcapítulos y partidas
        """
        proyecto = {
            'nombre': self.pdf_nombre.replace('.pdf', '').replace('_', ' ').title(),
            'capitulos': []
        }

        capitulo_actual = None
        subcapitulo_actual = None

        for clasificacion in self.clasificaciones:
            tipo = clasificacion['tipo']

            if tipo == TipoLinea.CAPITULO:
                # Nuevo capítulo
                capitulo_actual = {
                    'codigo': clasificacion['datos'].get('codigo', ''),
                    'nombre': clasificacion['datos'].get('nombre', ''),
                    'subcapitulos': [],
                    'partidas': []
                }
                proyecto['capitulos'].append(capitulo_actual)
                subcapitulo_actual = None

            elif tipo == TipoLinea.SUBCAPITULO:
                # Nuevo subcapítulo
                if capitulo_actual is None:
                    # Crear capítulo implícito si no existe
                    codigo_cap = clasificacion['datos'].get('codigo', '').split('.')[0]
                    capitulo_actual = {
                        'codigo': codigo_cap,
                        'nombre': f'Capítulo {codigo_cap}',
                        'subcapitulos': [],
                        'partidas': []
                    }
                    proyecto['capitulos'].append(capitulo_actual)

                subcapitulo_actual = {
                    'codigo': clasificacion['datos'].get('codigo', ''),
                    'nombre': clasificacion['datos'].get('nombre', ''),
                    'partidas': []
                }
                capitulo_actual['subcapitulos'].append(subcapitulo_actual)

            elif tipo == TipoLinea.PARTIDA_HEADER or tipo == TipoLinea.PARTIDA_DATOS:
                # Nueva partida
                partida = self._extraer_partida(clasificacion)

                if partida:
                    # Agregar a subcapítulo o capítulo
                    if subcapitulo_actual:
                        subcapitulo_actual['partidas'].append(partida)
                    elif capitulo_actual:
                        capitulo_actual['partidas'].append(partida)

        return proyecto

    def _extraer_partida(self, clasificacion: Dict) -> Optional[Dict]:
        """
        Extrae datos de una partida

        Args:
            clasificacion: Clasificación de la línea

        Returns:
            Dict con datos de la partida o None
        """
        datos = clasificacion.get('datos', {})

        if not datos.get('codigo'):
            return None

        partida = {
            'codigo': datos.get('codigo', ''),
            'unidad': datos.get('unidad', ''),
            'descripcion': datos.get('descripcion', ''),
            'cantidad': self._parsear_numero(datos.get('cantidad', 0)),
            'precio': self._parsear_numero(datos.get('precio', 0)),
            'importe': self._parsear_numero(datos.get('importe', 0)),
            'mediciones_parciales': []  # Se llenará si tiene mediciones
        }

        # TODO: Si tiene_mediciones_auxiliares, buscar líneas siguientes
        # para extraer tabla de mediciones

        return partida

    def _parsear_numero(self, valor) -> float:
        """
        Convierte string a número (formato español)

        Args:
            valor: String o número

        Returns:
            Float
        """
        if isinstance(valor, (int, float)):
            return float(valor)

        if isinstance(valor, str):
            # Formato español: 1.234,56 → 1234.56
            valor = valor.replace('.', '').replace(',', '.')
            try:
                return float(valor)
            except ValueError:
                return 0.0

        return 0.0

    def _calcular_estadisticas(self, estructura: Dict) -> Dict:
        """
        Calcula estadísticas del procesamiento

        Args:
            estructura: Estructura del proyecto

        Returns:
            Dict con estadísticas
        """
        stats = {
            'total_capitulos': len(estructura.get('capitulos', [])),
            'total_subcapitulos': 0,
            'total_partidas': 0,
            'presupuesto_total': 0.0
        }

        for capitulo in estructura.get('capitulos', []):
            stats['total_subcapitulos'] += len(capitulo.get('subcapitulos', []))
            stats['total_partidas'] += len(capitulo.get('partidas', []))

            for subcap in capitulo.get('subcapitulos', []):
                stats['total_partidas'] += len(subcap.get('partidas', []))

                for partida in subcap.get('partidas', []):
                    stats['presupuesto_total'] += partida.get('importe', 0)

            for partida in capitulo.get('partidas', []):
                stats['presupuesto_total'] += partida.get('importe', 0)

        return stats

    def imprimir_resumen(self, estructura: Dict, estadisticas: Dict):
        """
        Imprime resumen del procesamiento

        Args:
            estructura: Estructura del proyecto
            estadisticas: Estadísticas
        """
        print(f"\n{'='*80}")
        print("RESUMEN DEL PROCESAMIENTO")
        print(f"{'='*80}\n")

        print(f"📄 Proyecto: {estructura.get('nombre', 'Sin nombre')}")
        print(f"📊 Layout: {self.layout_detectado.replace('_', ' ').title()}")
        print(f"📐 Mediciones auxiliares: {'Sí' if self.tiene_mediciones_auxiliares else 'No'}\n")

        print(f"📈 Estadísticas:")
        print(f"   Capítulos: {estadisticas['total_capitulos']}")
        print(f"   Subcapítulos: {estadisticas['total_subcapitulos']}")
        print(f"   Partidas: {estadisticas['total_partidas']}")
        print(f"   Presupuesto total: {estadisticas['presupuesto_total']:,.2f} €\n")

        print(f"{'='*80}\n")


if __name__ == "__main__":
    # Test del parser
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s'
    )

    if len(sys.argv) < 2:
        print("Uso: python partida_parser_v2.py <pdf_path>")
        sys.exit(1)

    pdf_path = sys.argv[1]

    # Parsear
    parser = PartidaParserV2(pdf_path)
    resultado = parser.parsear()

    # Imprimir resumen
    parser.imprimir_resumen(
        resultado['estructura'],
        resultado['estadisticas']
    )

    # Mostrar primeros capítulos
    print("PRIMEROS CAPÍTULOS:")
    print("="*80)
    for i, cap in enumerate(resultado['estructura']['capitulos'][:3], 1):
        print(f"\n{i}. {cap['codigo']} - {cap['nombre']}")
        print(f"   Subcapítulos: {len(cap['subcapitulos'])}")
        print(f"   Partidas directas: {len(cap['partidas'])}")
