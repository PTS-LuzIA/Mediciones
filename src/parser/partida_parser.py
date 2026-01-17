"""
Parser completo de presupuestos de mediciones.
Integra extractor, clasificador y normalizador para generar estructura completa.
"""

import logging
from typing import Dict, List

try:
    from .pdf_extractor import PDFExtractor
    from .line_classifier import LineClassifier, TipoLinea
    from ..utils.normalizer import Normalizer
except ImportError:
    import sys
    from pathlib import Path
    # Añadir directorio padre al path si no está
    parent_dir = str(Path(__file__).parent.parent)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    # Intentar importar como módulos absolutos
    from parser.pdf_extractor import PDFExtractor
    from parser.line_classifier import LineClassifier, TipoLinea
    from utils.normalizer import Normalizer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PartidaParser:
    """Parser principal que procesa PDFs de mediciones"""

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.extractor = PDFExtractor(pdf_path)
        self.estructura = {
            'nombre': '',
            'descripcion': '',
            'archivo_origen': pdf_path,
            'capitulos': []
        }
        self.estadisticas = {
            'lineas_totales': 0,
            'capitulos': 0,
            'subcapitulos': 0,
            'apartados': 0,
            'partidas': 0,
            'partidas_validas': 0,
            'errores': []
        }

    def parsear(self) -> Dict:
        """
        Parsea el PDF completo y retorna estructura jerárquica

        Returns:
            dict con toda la estructura extraída
        """
        logger.info(f"Iniciando parseo de {self.pdf_path}")

        # 1. Extraer texto del PDF
        datos_pdf = self.extractor.extraer_todo()
        lineas = datos_pdf['all_lines']
        self.estadisticas['lineas_totales'] = len(lineas)

        # 2. Detectar nombre del proyecto desde las primeras líneas
        self._detectar_nombre_proyecto(lineas)

        # 3. Clasificar líneas
        clasificaciones = LineClassifier.clasificar_bloque(lineas)

        # 4. Construir estructura jerárquica
        self._construir_estructura(clasificaciones)

        # 5. Normalizar estructura: convertir partidas directas en subcapítulos
        self._normalizar_estructura()

        # 6. Calcular estadísticas
        self._calcular_estadisticas()

        logger.info(f"✓ Parseo completado: {self.estadisticas['partidas']} partidas extraídas")

        return {
            'estructura': self.estructura,
            'estadisticas': self.estadisticas
        }

    def _detectar_nombre_proyecto(self, lineas: List[str]) -> None:
        """
        Detecta el nombre del proyecto desde las primeras líneas del PDF.
        Estrategia:
        1. Busca líneas antes del primer CAPÍTULO que parezcan títulos de proyecto
        2. Combina líneas consecutivas si parecen ser continuación del título
        3. Evita headers de tabla, capítulos y partidas
        """
        import re

        # Buscar líneas antes del primer capítulo (generalmente las primeras 10-15 líneas)
        nombre_candidato = []

        for i in range(min(20, len(lineas))):
            linea = lineas[i].strip()

            # Si llegamos a un CAPÍTULO o código numérico (01, 01.01), dejamos de buscar
            if (linea.upper().startswith('CAPÍTULO') or
                re.match(r'^\d{1,2}(\.\d{1,2})?\s+', linea)):
                break

            # Saltar líneas vacías, headers de tabla y palabras clave comunes
            if (not linea or
                len(linea) < 15 or  # Líneas muy cortas no son títulos
                'CÓDIGO' in linea.upper() or
                'RESUMEN' in linea.upper() or
                'CANTIDAD' in linea.upper() or
                'PRECIO' in linea.upper() or
                'IMPORTE' in linea.upper() or
                linea.upper() in ['PRESUPUESTO', 'MEDICIONES Y PRESUPUESTO', 'MEDICIONES', 'RESUMEN'] or
                LineClassifier.PATRON_PARTIDA.match(linea)):  # No es una partida
                continue

            # Si la línea parece ser un título (mayúsculas, larga, descriptiva)
            # Solo tomar la primera línea de título, no continuaciones
            if len(linea) > 30 and not nombre_candidato:  # Solo la primera línea larga
                nombre_candidato.append(linea)
                break  # Solo tomar UNA línea de título

        # Si acumulamos algo, usarlo
        if nombre_candidato:
            # Unir las líneas
            texto_completo = ' '.join(nombre_candidato)
            # Verificar que no sea solo números o códigos
            if not re.match(r'^[\d\.\s]+$', texto_completo):
                self.estructura['nombre'] = texto_completo
                logger.info(f"Nombre del proyecto detectado: {texto_completo}")
                return

        logger.warning("No se pudo detectar el nombre del proyecto")

    def _cerrar_partida(self, partida_actual, apartado_actual, subcapitulo_actual, capitulo_actual):
        """Helper: cierra y guarda una partida en la estructura correcta"""
        if not partida_actual:
            return

        # VALIDACIÓN FINAL: Rechazar partidas con importe 0
        # Las partidas válidas siempre tienen importe > 0
        if partida_actual.get('importe', 0) == 0:
            logger.debug(f"⚠️ Partida descartada (importe 0): {partida_actual.get('codigo', 'SIN_CODIGO')}")
            self.estadisticas['errores'].append({
                'tipo': 'partida_rechazada',
                'partida': partida_actual.get('codigo', 'SIN_CODIGO'),
                'mensaje': 'Partida con importe 0 (rechazada)'
            })
            return

        # VALIDACIÓN FINAL: Rechazar partidas con código inválido
        codigo = partida_actual.get('codigo', '')
        if not codigo or len(codigo) <= 2 or not any(c.isdigit() for c in codigo):
            logger.debug(f"⚠️ Partida descartada (código inválido): {codigo}")
            self.estadisticas['errores'].append({
                'tipo': 'partida_rechazada',
                'partida': codigo,
                'mensaje': 'Código de partida inválido'
            })
            return

        # Reconstruir descripción
        if partida_actual.get('descripcion_lineas'):
            partida_actual['descripcion'] = Normalizer.reconstruir_descripcion(
                partida_actual['descripcion_lineas']
            )

        # SIEMPRE eliminar descripcion_lineas (aunque esté vacía)
        if 'descripcion_lineas' in partida_actual:
            del partida_actual['descripcion_lineas']

        # Validar
        if not Normalizer.validar_importe(
            partida_actual['cantidad'],
            partida_actual['precio'],
            partida_actual['importe']
        ):
            self.estadisticas['errores'].append({
                'tipo': 'validacion_importe',
                'partida': partida_actual['codigo'],
                'mensaje': f"Importe no coincide: {partida_actual['cantidad']} × {partida_actual['precio']} ≠ {partida_actual['importe']}"
            })

        # Añadir a la estructura correcta
        if apartado_actual:
            partida_actual['orden'] = len(apartado_actual['partidas'])
            apartado_actual['partidas'].append(partida_actual)
        elif subcapitulo_actual:
            partida_actual['orden'] = len(subcapitulo_actual['partidas'])
            subcapitulo_actual['partidas'].append(partida_actual)
        elif capitulo_actual:
            # Partida directa del capítulo (sin subcapítulo)
            partida_actual['orden'] = len(capitulo_actual['partidas'])
            capitulo_actual['partidas'].append(partida_actual)

    def _construir_estructura(self, clasificaciones: List[Dict]) -> None:
        """
        Construye la estructura jerárquica a partir de líneas clasificadas.
        Ahora soporta múltiples niveles de subcapítulos (ej: 01.04.01.01)

        Args:
            clasificaciones: lista de líneas clasificadas
        """
        capitulo_actual = None
        # Mapa de código -> subcapítulo para construir jerarquía
        subcapitulos_map = {}
        subcapitulo_actual = None
        apartado_actual = None
        partida_actual = None

        for item in clasificaciones:
            tipo = item['tipo']
            datos = item['datos']

            # CAPÍTULO
            if tipo == TipoLinea.CAPITULO:
                # Cerrar partida anterior antes de cambiar de capítulo
                self._cerrar_partida(partida_actual, apartado_actual, subcapitulo_actual, capitulo_actual)
                capitulo_actual = {
                    'codigo': datos['codigo'],
                    'nombre': datos['nombre'],
                    'subcapitulos': [],
                    'partidas': [],  # Partidas directas del capítulo (sin subcapítulos)
                    'orden': len(self.estructura['capitulos'])
                }
                self.estructura['capitulos'].append(capitulo_actual)
                subcapitulos_map.clear()  # Limpiar mapa al cambiar de capítulo
                subcapitulo_actual = None
                apartado_actual = None
                partida_actual = None

            # SUBCAPÍTULO (maneja múltiples niveles)
            elif tipo == TipoLinea.SUBCAPITULO:
                if capitulo_actual:
                    # Cerrar partida anterior
                    self._cerrar_partida(partida_actual, apartado_actual, subcapitulo_actual, capitulo_actual)

                    codigo = datos['codigo']
                    partes = codigo.split('.')

                    # Crear nuevo subcapítulo
                    nuevo_subcapitulo = {
                        'codigo': codigo,
                        'nombre': datos['nombre'],
                        'apartados': [],
                        'partidas': [],
                        'subcapitulos_hijos': [],  # Para jerarquía recursiva
                        'orden': 0
                    }

                    # Determinar dónde agregarlo basándose en el nivel
                    if len(partes) == 2:  # Nivel 1 (ej: 01.04)
                        # Agregar directamente al capítulo
                        nuevo_subcapitulo['orden'] = len(capitulo_actual['subcapitulos'])
                        capitulo_actual['subcapitulos'].append(nuevo_subcapitulo)
                    else:  # Nivel 2+ (ej: 01.04.01, 01.04.01.01)
                        # Buscar el padre (código sin el último número)
                        codigo_padre = '.'.join(partes[:-1])

                        if codigo_padre in subcapitulos_map:
                            padre = subcapitulos_map[codigo_padre]
                            nuevo_subcapitulo['orden'] = len(padre['subcapitulos_hijos'])
                            padre['subcapitulos_hijos'].append(nuevo_subcapitulo)
                        else:
                            # Si no encontramos el padre, agregarlo al capítulo como nivel 1
                            logger.warning(f"Padre no encontrado para {codigo}, agregando como nivel 1")
                            nuevo_subcapitulo['orden'] = len(capitulo_actual['subcapitulos'])
                            capitulo_actual['subcapitulos'].append(nuevo_subcapitulo)

                    # Guardar en el mapa para futuros hijos
                    subcapitulos_map[codigo] = nuevo_subcapitulo
                    subcapitulo_actual = nuevo_subcapitulo
                    apartado_actual = None
                    partida_actual = None

            # APARTADO
            elif tipo == TipoLinea.APARTADO:
                if subcapitulo_actual:
                    apartado_actual = {
                        'codigo': datos['codigo'],
                        'nombre': datos['nombre'],
                        'partidas': [],
                        'orden': len(subcapitulo_actual['apartados'])
                    }
                    subcapitulo_actual['apartados'].append(apartado_actual)
                    partida_actual = None

            # PARTIDA DESCRIPCIÓN
            elif tipo == TipoLinea.PARTIDA_DESCRIPCION:
                if partida_actual:
                    partida_actual['descripcion_lineas'].append(datos['texto'])

            # PARTIDA DATOS
            elif tipo == TipoLinea.PARTIDA_DATOS:
                if partida_actual:
                    # Normalizar números
                    cantidad = Normalizer.limpiar_numero_espanol(datos['cantidad_str'])
                    precio = Normalizer.limpiar_numero_espanol(datos['precio_str'])
                    importe = Normalizer.limpiar_numero_espanol(datos['importe_str'])

                    # Actualizar valores (si hay múltiples líneas con números, se queda con la última)
                    partida_actual['cantidad'] = cantidad if cantidad else 0.0
                    partida_actual['precio'] = precio if precio else 0.0
                    partida_actual['importe'] = importe if importe else 0.0

            # PARTIDA HEADER - al detectar una nueva partida, cerrar la anterior
            elif tipo == TipoLinea.PARTIDA_HEADER:
                # Cerrar partida anterior usando helper
                self._cerrar_partida(partida_actual, apartado_actual, subcapitulo_actual, capitulo_actual)

                # VALIDAR CÓDIGO ANTES DE CREAR LA PARTIDA
                codigo = datos['codigo']

                # Lista de palabras prohibidas (headers de tabla, no son códigos)
                palabras_prohibidas = ['ORDEN', 'CODIGO', 'CÓDIGO', 'RESUMEN', 'CANTIDAD', 'PRECIO', 'IMPORTE',
                                      'UNIDAD', 'UD', 'TOTAL', 'SUBTOTAL', 'CAPITULO', 'CAPÍTULO',
                                      'SUBCAPITULO', 'SUBCAPÍTULO', 'APARTADO', 'FOM', 'NTE', 'RD']

                # Validaciones críticas
                es_valido = True
                razon_invalido = None

                if not codigo:
                    es_valido = False
                    razon_invalido = 'código vacío'
                elif codigo.upper() in palabras_prohibidas:
                    es_valido = False
                    razon_invalido = 'palabra prohibida (header de tabla)'
                elif not any(c.isdigit() for c in codigo):
                    es_valido = False
                    razon_invalido = 'código sin números'
                elif len(codigo) <= 2:
                    es_valido = False
                    razon_invalido = 'código muy corto'
                elif not codigo[-1].isdigit():
                    es_valido = False
                    razon_invalido = 'no termina en número'

                # Si el código es inválido, NO crear la partida y seguir al siguiente item
                if not es_valido:
                    logger.debug(f"⚠️ Partida rechazada: código '{codigo}' ({razon_invalido})")
                    partida_actual = None
                    continue

                # Extraer valores numéricos si vienen en el header (línea completa)
                cantidad = 0.0
                precio = 0.0
                importe = 0.0

                if 'cantidad_str' in datos:
                    cantidad = Normalizer.limpiar_numero_espanol(datos['cantidad_str']) or 0.0
                if 'precio_str' in datos:
                    precio = Normalizer.limpiar_numero_espanol(datos['precio_str']) or 0.0
                if 'importe_str' in datos:
                    importe = Normalizer.limpiar_numero_espanol(datos['importe_str']) or 0.0

                # VALIDAR IMPORTE: Si tiene importe 0 y está completo, rechazar
                if importe == 0 and 'importe_str' in datos:
                    logger.debug(f"⚠️ Partida rechazada: código '{codigo}' (importe 0)")
                    partida_actual = None
                    continue

                # Crear nueva partida (solo si pasó todas las validaciones)
                partida_actual = {
                    'codigo': codigo,
                    'unidad': Normalizer.normalizar_unidad(datos['unidad']),
                    'resumen': datos['resumen'],
                    'descripcion': '',
                    'descripcion_lineas': [],
                    'cantidad': cantidad,
                    'precio': precio,
                    'importe': importe,
                    'orden': 0
                }

            # TOTAL - cerrar partida y subcapítulo/apartado actual
            elif tipo == TipoLinea.TOTAL:
                self._cerrar_partida(partida_actual, apartado_actual, subcapitulo_actual, capitulo_actual)
                partida_actual = None

                # IMPORTANTE: Cerrar también el subcapítulo/apartado actual
                # El TOTAL marca el fin de una sección jerárquica
                codigo_total = datos.get('codigo')

                # Si el TOTAL tiene código, verificar qué nivel cerrar
                if codigo_total:
                    # Si es apartado, cerrar apartado
                    if apartado_actual and apartado_actual.get('codigo') == codigo_total:
                        logger.debug(f"TOTAL cierra apartado {codigo_total}")
                        apartado_actual = None
                    # Si es subcapítulo, cerrar subcapítulo Y apartado
                    elif subcapitulo_actual and subcapitulo_actual.get('codigo') == codigo_total:
                        logger.debug(f"TOTAL cierra subcapítulo {codigo_total}")

                        # Si el subcapítulo tiene padre (nivel 3+), volver al padre
                        partes_codigo = codigo_total.split('.')
                        if len(partes_codigo) > 2:  # Nivel 3+ (ej: 01.04.01)
                            codigo_padre = '.'.join(partes_codigo[:-1])
                            if codigo_padre in subcapitulos_map:
                                subcapitulo_actual = subcapitulos_map[codigo_padre]
                                logger.debug(f"  └─ Volviendo al padre {codigo_padre}")
                            else:
                                subcapitulo_actual = None
                        else:
                            # Nivel 2 (ej: 01.04), cerrar completamente
                            subcapitulo_actual = None

                        apartado_actual = None
                else:
                    # TOTAL sin código: cerrar cualquier sección abierta (apartado o subcapítulo)
                    if apartado_actual:
                        logger.debug(f"TOTAL sin código cierra apartado actual")
                        apartado_actual = None
                    elif subcapitulo_actual:
                        logger.debug(f"TOTAL sin código cierra subcapítulo actual")
                        # Intentar volver al padre si existe
                        codigo_actual = subcapitulo_actual.get('codigo', '')
                        partes_codigo = codigo_actual.split('.')
                        if len(partes_codigo) > 2:
                            codigo_padre = '.'.join(partes_codigo[:-1])
                            if codigo_padre in subcapitulos_map:
                                subcapitulo_actual = subcapitulos_map[codigo_padre]
                                logger.debug(f"  └─ Volviendo al padre {codigo_padre}")
                            else:
                                subcapitulo_actual = None
                        else:
                            subcapitulo_actual = None

        # Cerrar última partida si existe (al final del loop)
        self._cerrar_partida(partida_actual, apartado_actual, subcapitulo_actual, capitulo_actual)

    def _normalizar_estructura(self) -> None:
        """
        Normaliza la estructura: si un capítulo tiene partidas directas pero no subcapítulos,
        crea un subcapítulo automático con el mismo nombre del capítulo
        """
        for capitulo in self.estructura['capitulos']:
            partidas_directas = capitulo.get('partidas', [])

            # Si hay partidas directas y no hay subcapítulos, crear subcapítulo automático
            if partidas_directas and not capitulo['subcapitulos']:
                subcapitulo_auto = {
                    'codigo': capitulo['codigo'],
                    'nombre': capitulo['nombre'],
                    'apartados': [],
                    'partidas': partidas_directas,
                    'orden': 0
                }
                capitulo['subcapitulos'].append(subcapitulo_auto)
                capitulo['partidas'] = []  # Limpiar partidas directas

                logger.info(f"Creado subcapítulo automático para {capitulo['codigo']} con {len(partidas_directas)} partidas")

    def _calcular_estadisticas(self) -> None:
        """Calcula estadísticas del parseo"""
        self.estadisticas['capitulos'] = len(self.estructura['capitulos'])

        for capitulo in self.estructura['capitulos']:
            # Contar partidas directas del capítulo (sin subcapítulos)
            self.estadisticas['partidas'] += len(capitulo.get('partidas', []))

            self.estadisticas['subcapitulos'] += len(capitulo['subcapitulos'])

            for subcapitulo in capitulo['subcapitulos']:
                self.estadisticas['apartados'] += len(subcapitulo['apartados'])
                self.estadisticas['partidas'] += len(subcapitulo['partidas'])

                for apartado in subcapitulo['apartados']:
                    self.estadisticas['partidas'] += len(apartado['partidas'])

        # Contar partidas válidas
        self.estadisticas['partidas_validas'] = (
            self.estadisticas['partidas'] - len(self.estadisticas['errores'])
        )

    def obtener_todas_partidas(self) -> List[Dict]:
        """
        Obtiene lista plana de todas las partidas

        Returns:
            lista de dicts con todas las partidas
        """
        partidas = []

        for capitulo in self.estructura['capitulos']:
            # Partidas directas del capítulo (sin subcapítulo)
            for partida in capitulo.get('partidas', []):
                partidas.append({
                    **partida,
                    'capitulo': capitulo['codigo'],
                    'subcapitulo': None,
                    'apartado': None
                })

            for subcapitulo in capitulo['subcapitulos']:
                # Partidas directas del subcapítulo
                for partida in subcapitulo['partidas']:
                    partidas.append({
                        **partida,
                        'capitulo': capitulo['codigo'],
                        'subcapitulo': subcapitulo['codigo'],
                        'apartado': None
                    })

                # Partidas de apartados
                for apartado in subcapitulo['apartados']:
                    for partida in apartado['partidas']:
                        partidas.append({
                            **partida,
                            'capitulo': capitulo['codigo'],
                            'subcapitulo': subcapitulo['codigo'],
                            'apartado': apartado['codigo']
                        })

        return partidas

    def imprimir_resumen(self) -> None:
        """Imprime resumen del parseo"""
        print("\n" + "=" * 80)
        print("RESUMEN DEL PARSEO")
        print("=" * 80)
        print(f"Archivo: {self.pdf_path}")
        print(f"Líneas procesadas: {self.estadisticas['lineas_totales']}")
        print(f"\nEstructura extraída:")
        print(f"  • Capítulos: {self.estadisticas['capitulos']}")
        print(f"  • Subcapítulos: {self.estadisticas['subcapitulos']}")
        print(f"  • Apartados: {self.estadisticas['apartados']}")
        print(f"  • Partidas: {self.estadisticas['partidas']}")
        print(f"  • Partidas válidas: {self.estadisticas['partidas_validas']}")

        if self.estadisticas['errores']:
            print(f"\n⚠ Errores de validación: {len(self.estadisticas['errores'])}")
            for error in self.estadisticas['errores'][:5]:
                print(f"  - {error['partida']}: {error['mensaje']}")
            if len(self.estadisticas['errores']) > 5:
                print(f"  ... y {len(self.estadisticas['errores']) - 5} más")

        print("=" * 80 + "\n")


def parsear_pdf(pdf_path: str) -> Dict:
    """
    Función helper para parsear rápidamente un PDF

    Args:
        pdf_path: ruta al PDF

    Returns:
        dict con estructura y estadísticas
    """
    parser = PartidaParser(pdf_path)
    resultado = parser.parsear()
    parser.imprimir_resumen()
    return resultado


if __name__ == "__main__":
    # Test con el PDF de ejemplo
    import os
    from pathlib import Path

    pdf_ejemplo = "ejemplo/PROYECTO CALYPOFADO_extract.pdf"

    if Path(pdf_ejemplo).exists():
        print(f"Parseando {pdf_ejemplo}...\n")

        parser = PartidaParser(pdf_ejemplo)
        resultado = parser.parsear()
        parser.imprimir_resumen()

        # Mostrar primeras partidas
        partidas = parser.obtener_todas_partidas()
        print(f"Primeras 3 partidas extraídas:")
        print("-" * 80)
        for i, p in enumerate(partidas[:3], 1):
            print(f"\n{i}. {p['codigo']} - {p['resumen'][:50]}...")
            print(f"   Unidad: {p['unidad']}")
            print(f"   Cantidad: {p['cantidad']}, Precio: {p['precio']}, Importe: {p['importe']}")
            if p['descripcion']:
                print(f"   Descripción: {p['descripcion'][:80]}...")
    else:
        print(f"❌ No se encuentra el archivo {pdf_ejemplo}")
