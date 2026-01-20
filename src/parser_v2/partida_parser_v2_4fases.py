"""
Parser V2 con Sistema de 4 Fases (idéntico a V1)
================================================

Sistema de debugging paso a paso:
- FASE 1: Extracción de estructura jerárquica (capítulos/subcapítulos)
- FASE 2: Clasificación de líneas y extracción de partidas
- FASE 3: Validación de totales (si hay datos de referencia)
- FASE 4: Completado de descripciones (opcional)

Cada fase guarda resultados intermedios para debugging.

Autor: Claude Code
Fecha: 2026-01-19
"""

import os
import json
import logging
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime

# Importar componentes
from .pdf_extractor import PDFExtractor
from .column_detector import ColumnDetector
from .line_classifier import LineClassifier, TipoLinea
from .structure_parser import StructureParser

logger = logging.getLogger(__name__)


class PartidaParserV2_4Fases:
    """
    Parser con 4 fases idéntico al V1 para debugging paso a paso
    """

    def __init__(self, pdf_path: str):
        self.pdf_path = Path(pdf_path)
        self.pdf_name = self.pdf_path.stem

        # Directorio para resultados intermedios
        self.output_dir = Path("logs/parser_v2_fases")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Timestamp para esta ejecución
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Resultados de cada fase
        self.fase1_resultado = None
        self.fase2_resultado = None
        self.fase3_resultado = None
        self.fase4_resultado = None

        # Componentes
        self.pdf_extractor = None
        self.line_classifier = None
        self.structure_parser = None

    def parsear(self) -> Dict:
        """
        Ejecuta las 4 fases completas y retorna resultado final

        Returns:
            Dict con estructura completa y metadatos
        """
        logger.info("=" * 80)
        logger.info(f"🚀 Iniciando Parser V2 (4 Fases) - PDF: {self.pdf_name}")
        logger.info("=" * 80)

        # FASE 1: Estructura jerárquica
        self.ejecutar_fase1()

        # FASE 2: Extracción de partidas
        self.ejecutar_fase2()

        # FASE 3: Validación (opcional si hay totales de referencia)
        self.ejecutar_fase3()

        # FASE 4: Completar descripciones (opcional)
        self.ejecutar_fase4()

        # Compilar resultado final
        resultado_final = self._compilar_resultado_final()

        logger.info("=" * 80)
        logger.info("✅ Parser V2 (4 Fases) COMPLETADO")
        logger.info("=" * 80)

        return resultado_final

    # ================================================================
    # FASE 1: EXTRACCIÓN DE ESTRUCTURA JERÁRQUICA
    # ================================================================

    def ejecutar_fase1(self):
        """
        FASE 1: Extrae estructura jerárquica (capítulos/subcapítulos con totales)

        Salida:
        - logs/parser_v2_fases/fase1_estructura_{timestamp}.json
        - logs/parser_v2_fases/fase1_texto_extraido_{timestamp}.txt
        """
        logger.info("")
        logger.info("🔧 " + "=" * 70)
        logger.info("🔧 [FASE 1/4] Extrayendo ESTRUCTURA con Parser Local")
        logger.info("🔧 " + "=" * 70)

        inicio = datetime.now()

        # Paso 1.1: Extraer texto del PDF
        logger.info("  📄 Paso 1.1: Extrayendo texto del PDF con pdfplumber...")
        self.pdf_extractor = PDFExtractor(str(self.pdf_path))
        datos_pdf = self.pdf_extractor.extraer_todo()

        lineas = datos_pdf['all_lines']
        layout_info = datos_pdf.get('layout_summary', {})

        logger.info(f"    ✓ Extraídas {len(lineas)} líneas")
        logger.info(f"    ✓ Layout detectado: {layout_info}")

        # Guardar texto extraído para debugging
        texto_file = self.output_dir / f"fase1_texto_extraido_{self.timestamp}.txt"
        with open(texto_file, 'w', encoding='utf-8') as f:
            f.write(f"PDF: {self.pdf_name}\n")
            f.write(f"Líneas extraídas: {len(lineas)}\n")
            f.write(f"Layout: {layout_info}\n")
            f.write("=" * 80 + "\n\n")
            for i, linea in enumerate(lineas, 1):
                f.write(f"{i:5d}: {linea}\n")
        logger.info(f"    💾 Texto guardado: {texto_file}")

        # Paso 1.2: Parsear estructura jerárquica
        logger.info("  🏗️  Paso 1.2: Parseando estructura jerárquica...")
        self.structure_parser = StructureParser()
        estructura = self.structure_parser.parsear(lineas)

        num_caps = len(estructura.get('capitulos', []))
        num_subs = self._contar_subcapitulos_recursivo(estructura)

        logger.info(f"    ✓ Capítulos encontrados: {num_caps}")
        logger.info(f"    ✓ Subcapítulos encontrados: {num_subs}")

        # Mostrar desglose de estructura
        for cap in estructura.get('capitulos', []):
            logger.info(f"      • CAP {cap['codigo']}: {cap['nombre'][:50]}... (Total: {cap.get('total', 0):.2f} €)")
            self._log_subcapitulos_recursivo(cap.get('subcapitulos', []), nivel=1)

        # Guardar estructura en JSON para debugging
        estructura_file = self.output_dir / f"fase1_estructura_{self.timestamp}.json"
        with open(estructura_file, 'w', encoding='utf-8') as f:
            json.dump(estructura, f, indent=2, ensure_ascii=False)
        logger.info(f"    💾 Estructura guardada: {estructura_file}")

        duracion = (datetime.now() - inicio).total_seconds()

        self.fase1_resultado = {
            'estructura': estructura,
            'num_capitulos': num_caps,
            'num_subcapitulos': num_subs,
            'layout_info': layout_info,
            'num_lineas': len(lineas),
            'duracion_segundos': duracion,
            'archivo_estructura': str(estructura_file),
            'archivo_texto': str(texto_file)
        }

        logger.info(f"  ✅ [FASE 1] Completada en {duracion:.2f}s")
        logger.info("")

    def _contar_subcapitulos_recursivo(self, estructura: Dict) -> int:
        """Cuenta subcapítulos recursivamente"""
        total = 0
        for cap in estructura.get('capitulos', []):
            total += self._contar_subs_en_elemento(cap)
        return total

    def _contar_subs_en_elemento(self, elemento: Dict) -> int:
        """Cuenta subcapítulos en un elemento"""
        subs = elemento.get('subcapitulos', [])
        total = len(subs)
        for sub in subs:
            total += self._contar_subs_en_elemento(sub)
        return total

    def _log_subcapitulos_recursivo(self, subcapitulos: List[Dict], nivel: int = 1):
        """Log subcapítulos con indentación"""
        indent = "    " * (nivel + 1)
        for sub in subcapitulos:
            logger.info(f"{indent}└─ SUB {sub['codigo']}: {sub['nombre'][:40]}... (Total: {sub.get('total', 0):.2f} €)")
            if sub.get('subcapitulos'):
                self._log_subcapitulos_recursivo(sub['subcapitulos'], nivel + 1)

    # ================================================================
    # FASE 2: CLASIFICACIÓN DE LÍNEAS Y EXTRACCIÓN DE PARTIDAS
    # ================================================================

    def ejecutar_fase2(self):
        """
        FASE 2: Clasifica líneas y extrae partidas individuales

        Salida:
        - logs/parser_v2_fases/fase2_clasificaciones_{timestamp}.json
        - logs/parser_v2_fases/fase2_partidas_{timestamp}.json
        """
        logger.info("")
        logger.info("🔧 " + "=" * 70)
        logger.info("🔧 [FASE 2/4] Clasificando LÍNEAS y Extrayendo PARTIDAS")
        logger.info("🔧 " + "=" * 70)

        inicio = datetime.now()

        # Paso 2.1: Obtener líneas del PDF (ya las tenemos de Fase 1)
        logger.info("  📋 Paso 2.1: Obteniendo líneas del PDF...")
        datos_pdf = self.pdf_extractor.extraer_todo()
        lineas = datos_pdf['all_lines']
        logger.info(f"    ✓ {len(lineas)} líneas a clasificar")

        # Paso 2.2: Clasificar cada línea
        logger.info("  🏷️  Paso 2.2: Clasificando líneas con LineClassifier...")
        clasificaciones = LineClassifier.clasificar_bloque(lineas)

        # Contar tipos
        conteo_tipos = {}
        for item in clasificaciones:
            tipo = item['tipo']
            conteo_tipos[tipo] = conteo_tipos.get(tipo, 0) + 1

        logger.info(f"    ✓ {len(clasificaciones)} líneas clasificadas:")
        for tipo, count in sorted(conteo_tipos.items(), key=lambda x: -x[1]):
            logger.info(f"      • {tipo}: {count}")

        # Guardar clasificaciones para debugging
        clasificaciones_file = self.output_dir / f"fase2_clasificaciones_{self.timestamp}.json"
        with open(clasificaciones_file, 'w', encoding='utf-8') as f:
            # Convertir TipoLinea enum a string para JSON
            clasificaciones_serializable = []
            for item in clasificaciones:
                item_copy = item.copy()
                item_copy['tipo'] = str(item_copy['tipo'])
                clasificaciones_serializable.append(item_copy)
            json.dump(clasificaciones_serializable, f, indent=2, ensure_ascii=False)
        logger.info(f"    💾 Clasificaciones guardadas: {clasificaciones_file}")

        # Paso 2.3: Construir estructura completa con partidas
        logger.info("  🏗️  Paso 2.3: Construyendo estructura con partidas...")
        estructura_completa = self._construir_estructura_completa(clasificaciones)

        # Contar partidas
        num_partidas = self._contar_partidas_recursivo(estructura_completa)
        logger.info(f"    ✓ {num_partidas} partidas extraídas")

        # Guardar estructura con partidas
        partidas_file = self.output_dir / f"fase2_estructura_con_partidas_{self.timestamp}.json"
        with open(partidas_file, 'w', encoding='utf-8') as f:
            json.dump(estructura_completa, f, indent=2, ensure_ascii=False)
        logger.info(f"    💾 Estructura con partidas guardada: {partidas_file}")

        duracion = (datetime.now() - inicio).total_seconds()

        self.fase2_resultado = {
            'estructura_completa': estructura_completa,
            'clasificaciones': clasificaciones,
            'conteo_tipos': conteo_tipos,
            'num_partidas': num_partidas,
            'duracion_segundos': duracion,
            'archivo_clasificaciones': str(clasificaciones_file),
            'archivo_partidas': str(partidas_file)
        }

        logger.info(f"  ✅ [FASE 2] Completada en {duracion:.2f}s - {num_partidas} partidas extraídas")
        logger.info("")

    def _construir_estructura_completa(self, clasificaciones: List[Dict]) -> Dict:
        """
        Construye estructura jerárquica completa con partidas
        (igual que en partida_parser_v2_unified.py)
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
                subcapitulos_map = {}  # Reset map
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
                        'subcapitulos': [],
                        'partidas': []
                    }
                    if capitulo_actual:
                        capitulo_actual['subcapitulos'].append(subcapitulo_actual)
                    subcapitulos_map[codigo] = subcapitulo_actual
                    logger.debug(f"Subcapítulo L1 creado: {codigo} - {nombre}")

                elif nivel >= 2:  # Nivel 2+: XX.YY.ZZ o más
                    # Encontrar padre
                    partes = codigo.split('.')
                    codigo_padre = '.'.join(partes[:-1])

                    padre = subcapitulos_map.get(codigo_padre)

                    nuevo_subcapitulo = {
                        'codigo': codigo,
                        'nombre': nombre,
                        'total': 0.0,
                        'subcapitulos': [],
                        'partidas': []
                    }

                    if padre:
                        padre['subcapitulos'].append(nuevo_subcapitulo)
                        logger.debug(f"Subcapítulo L{nivel} creado bajo {codigo_padre}: {codigo} - {nombre}")
                    elif capitulo_actual:
                        # Fallback: crear nivel intermedio automáticamente
                        logger.warning(f"Subcapítulo {codigo} sin padre {codigo_padre}, creando nivel intermedio")

                        # Crear todos los niveles intermedios que falten
                        niveles_crear = []
                        for i in range(1, nivel):
                            codigo_intermedio = '.'.join(partes[:i+1])
                            if codigo_intermedio not in subcapitulos_map:
                                niveles_crear.append(codigo_intermedio)

                        # Crear niveles intermedios
                        for codigo_intermedio in niveles_crear:
                            partes_intermedio = codigo_intermedio.split('.')
                            nivel_intermedio = len(partes_intermedio) - 1

                            if nivel_intermedio == 1:
                                # Nivel 1: añadir a capítulo
                                sub_intermedio = {
                                    'codigo': codigo_intermedio,
                                    'nombre': f'(Nivel intermedio {codigo_intermedio})',
                                    'total': 0.0,
                                    'subcapitulos': [],
                                    'partidas': []
                                }
                                capitulo_actual['subcapitulos'].append(sub_intermedio)
                                subcapitulos_map[codigo_intermedio] = sub_intermedio
                                logger.debug(f"Nivel intermedio L1 creado: {codigo_intermedio}")
                            else:
                                # Nivel 2+: añadir a padre
                                codigo_padre_intermedio = '.'.join(partes_intermedio[:-1])
                                padre_intermedio = subcapitulos_map.get(codigo_padre_intermedio)
                                if padre_intermedio:
                                    sub_intermedio = {
                                        'codigo': codigo_intermedio,
                                        'nombre': f'(Nivel intermedio {codigo_intermedio})',
                                        'total': 0.0,
                                        'subcapitulos': [],
                                        'partidas': []
                                    }
                                    padre_intermedio['subcapitulos'].append(sub_intermedio)
                                    subcapitulos_map[codigo_intermedio] = sub_intermedio
                                    logger.debug(f"Nivel intermedio L{nivel_intermedio} creado: {codigo_intermedio}")

                        # Ahora intentar de nuevo
                        padre = subcapitulos_map.get(codigo_padre)
                        if padre:
                            padre['subcapitulos'].append(nuevo_subcapitulo)
                        else:
                            # Último recurso: añadir al capítulo
                            capitulo_actual['subcapitulos'].append(nuevo_subcapitulo)

                    subcapitulos_map[codigo] = nuevo_subcapitulo
                    subcapitulo_actual = nuevo_subcapitulo

            elif tipo == TipoLinea.PARTIDA_HEADER:
                # CERRAR PARTIDA ANTERIOR
                if partida_actual:
                    # Finalizar partida anterior si existe
                    if partida_actual['descripcion_lineas']:
                        partida_actual['descripcion'] = ' '.join(partida_actual['descripcion_lineas'])

                    # Solo agregar si tiene importe > 0
                    if partida_actual['importe'] > 0:
                        if subcapitulo_actual:
                            subcapitulo_actual['partidas'].append(partida_actual)
                        elif capitulo_actual:
                            capitulo_actual['partidas'].append(partida_actual)
                        logger.debug(f"Partida completada: {partida_actual['codigo']} = {partida_actual['importe']}")
                    else:
                        logger.debug(f"Partida rechazada (importe 0): {partida_actual['codigo']}")

                    partida_actual = None

                # VALIDAR CÓDIGO ANTES DE CREAR PARTIDA
                codigo = datos.get('codigo', '')

                # Lista de palabras prohibidas
                palabras_prohibidas = ['ORDEN', 'CODIGO', 'CÓDIGO', 'RESUMEN', 'CANTIDAD', 'PRECIO', 'IMPORTE',
                                      'UNIDAD', 'UD', 'TOTAL', 'SUBTOTAL', 'CAPITULO', 'CAPÍTULO',
                                      'SUBCAPITULO', 'SUBCAPÍTULO', 'APARTADO', 'PROYECTO', 'DE']

                # Validaciones
                es_valido = True
                if not codigo:
                    es_valido = False
                elif codigo.upper() in palabras_prohibidas:
                    es_valido = False
                elif not any(c.isdigit() for c in codigo):
                    es_valido = False
                elif len(codigo) <= 2:
                    es_valido = False
                elif not codigo[-1].isdigit():
                    es_valido = False

                # Si no es válido, ignorar esta línea
                if not es_valido:
                    logger.debug(f"Código rechazado: '{codigo}'")
                    continue

                # Extraer valores numéricos si vienen en el header
                cantidad = self._limpiar_numero(datos.get('cantidad_str', '0'))
                precio = self._limpiar_numero(datos.get('precio_str', '0'))
                importe = self._limpiar_numero(datos.get('importe_str', '0'))

                # VALIDAR IMPORTE: Si tiene importe 0 y datos completos, rechazar
                if importe == 0 and datos.get('importe_str'):
                    logger.debug(f"Partida rechazada (importe 0): {codigo}")
                    continue

                # CREAR NUEVA PARTIDA
                partida_actual = {
                    'codigo': codigo,
                    'unidad': datos.get('unidad', ''),
                    'resumen': datos.get('resumen', ''),
                    'descripcion': '',
                    'descripcion_lineas': [],
                    'cantidad': cantidad,
                    'precio': precio,
                    'importe': importe
                }
                logger.debug(f"Partida iniciada: {partida_actual['codigo']}")

                # Si el header ya tiene datos numéricos completos, finalizar inmediatamente
                if importe > 0 and cantidad > 0 and precio > 0:
                    partida_actual['descripcion'] = partida_actual['resumen']

                    # Agregar partida al contexto actual
                    if subcapitulo_actual:
                        subcapitulo_actual['partidas'].append(partida_actual)
                    elif capitulo_actual:
                        capitulo_actual['partidas'].append(partida_actual)

                    logger.debug(f"Partida completada (inline): {partida_actual['codigo']} = {partida_actual['importe']}")
                    partida_actual = None

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

                    # Solo agregar si importe > 0
                    if partida_actual['importe'] > 0:
                        # Determinar dónde agregar la partida (al último subcapítulo o capítulo)
                        if subcapitulo_actual:
                            subcapitulo_actual['partidas'].append(partida_actual)
                        elif capitulo_actual:
                            capitulo_actual['partidas'].append(partida_actual)
                        logger.debug(f"Partida completada: {partida_actual['codigo']} = {partida_actual['importe']}")
                    else:
                        logger.debug(f"Partida rechazada (importe 0): {partida_actual['codigo']}")

                    partida_actual = None

            elif tipo == TipoLinea.TOTAL:
                # Los totales ya fueron procesados en Fase 1
                pass

        return estructura

    def _contar_partidas_recursivo(self, estructura: Dict) -> int:
        """Cuenta partidas recursivamente"""
        total = 0
        for cap in estructura.get('capitulos', []):
            total += len(cap.get('partidas', []))
            total += self._contar_partidas_en_elemento(cap)
        return total

    def _contar_partidas_en_elemento(self, elemento: Dict) -> int:
        """Cuenta partidas en un elemento y sus hijos"""
        total = len(elemento.get('partidas', []))
        for sub in elemento.get('subcapitulos', []):
            total += len(sub.get('partidas', []))
            total += self._contar_partidas_en_elemento(sub)
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

    # ================================================================
    # FASE 3: VALIDACIÓN (merge totales de Fase 1 con Fase 2)
    # ================================================================

    def ejecutar_fase3(self):
        """
        FASE 3: Merge totales de Fase 1 en estructura de Fase 2 y valida

        Salida:
        - logs/parser_v2_fases/fase3_validacion_{timestamp}.json
        """
        logger.info("")
        logger.info("🔧 " + "=" * 70)
        logger.info("🔧 [FASE 3/4] Merging Totales y Validación")
        logger.info("🔧 " + "=" * 70)

        inicio = datetime.now()

        if not self.fase1_resultado or not self.fase2_resultado:
            logger.warning("  ⚠️  Fases 1 o 2 no completadas, saltando Fase 3")
            self.fase3_resultado = {'saltada': True}
            return

        estructura_fase1 = self.fase1_resultado['estructura']
        estructura_fase2 = self.fase2_resultado['estructura_completa']

        logger.info("  🔄 Paso 3.1: Mergeando totales de Fase 1 en Fase 2...")
        self._merge_totales_fase1(estructura_fase2, estructura_fase1)

        logger.info("  ✅ Paso 3.2: Calculando totales faltantes...")
        self._calcular_totales(estructura_fase2)

        logger.info("  🔍 Paso 3.3: Validando coherencia...")
        discrepancias = self._validar_coherencia(estructura_fase2)

        if discrepancias:
            logger.warning(f"    ⚠️  Se encontraron {len(discrepancias)} discrepancias:")
            for disc in discrepancias[:5]:  # Mostrar solo las primeras 5
                logger.warning(f"      • {disc['codigo']}: {disc['descripcion']}")
            if len(discrepancias) > 5:
                logger.warning(f"      ... y {len(discrepancias) - 5} más")
        else:
            logger.info("    ✓ Sin discrepancias detectadas")

        # Guardar validación
        validacion_file = self.output_dir / f"fase3_validacion_{self.timestamp}.json"
        with open(validacion_file, 'w', encoding='utf-8') as f:
            json.dump({
                'discrepancias': discrepancias,
                'estructura_final': estructura_fase2
            }, f, indent=2, ensure_ascii=False)
        logger.info(f"    💾 Validación guardada: {validacion_file}")

        duracion = (datetime.now() - inicio).total_seconds()

        self.fase3_resultado = {
            'discrepancias': discrepancias,
            'num_discrepancias': len(discrepancias),
            'duracion_segundos': duracion,
            'archivo_validacion': str(validacion_file)
        }

        logger.info(f"  ✅ [FASE 3] Completada en {duracion:.2f}s")
        logger.info("")

    def _merge_totales_fase1(self, estructura_fase2: Dict, estructura_fase1: Dict):
        """Incorpora totales de Fase 1 en estructura de Fase 2"""
        totales_fase1 = {}

        # Extraer totales de Fase 1
        for cap in estructura_fase1.get('capitulos', []):
            if 'total' in cap:
                totales_fase1[cap['codigo']] = cap['total']
            self._extraer_totales_recursivo(cap, totales_fase1)

        # Aplicar totales a la estructura de Fase 2
        for cap in estructura_fase2.get('capitulos', []):
            if cap['codigo'] in totales_fase1:
                cap['total'] = totales_fase1[cap['codigo']]
            self._aplicar_totales_recursivo(cap, totales_fase1)

    def _extraer_totales_recursivo(self, elemento: Dict, totales: Dict):
        """Extrae totales recursivamente"""
        for sub in elemento.get('subcapitulos', []):
            if 'total' in sub:
                totales[sub['codigo']] = sub['total']
            self._extraer_totales_recursivo(sub, totales)

    def _aplicar_totales_recursivo(self, elemento: Dict, totales: Dict):
        """Aplica totales recursivamente"""
        for sub in elemento.get('subcapitulos', []):
            if sub['codigo'] in totales:
                sub['total'] = totales[sub['codigo']]
            self._aplicar_totales_recursivo(sub, totales)

    def _calcular_totales(self, estructura: Dict):
        """Calcula totales sumando partidas (solo donde no hay total de Fase 1)"""
        for cap in estructura.get('capitulos', []):
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

    def _validar_coherencia(self, estructura: Dict) -> List[Dict]:
        """Valida que suma de partidas ≈ total del subcapítulo"""
        discrepancias = []

        for cap in estructura.get('capitulos', []):
            self._validar_elemento_recursivo(cap, discrepancias)

        return discrepancias

    def _validar_elemento_recursivo(self, elemento: Dict, discrepancias: List[Dict]):
        """Valida un elemento recursivamente"""
        codigo = elemento.get('codigo', '')
        total_declarado = elemento.get('total', 0.0)

        # Calcular total real (suma de partidas + subcapítulos)
        total_real = 0.0
        for partida in elemento.get('partidas', []):
            total_real += partida.get('importe', 0.0)

        for sub in elemento.get('subcapitulos', []):
            total_real += sub.get('total', 0.0)
            # Validar recursivamente
            self._validar_elemento_recursivo(sub, discrepancias)

        # Validar (tolerancia 0.1%)
        if total_declarado > 0:
            diferencia = abs(total_real - total_declarado)
            porcentaje = (diferencia / total_declarado) * 100 if total_declarado > 0 else 0

            if porcentaje > 0.1:
                discrepancias.append({
                    'codigo': codigo,
                    'total_declarado': total_declarado,
                    'total_real': total_real,
                    'diferencia': diferencia,
                    'porcentaje': porcentaje,
                    'descripcion': f"Diferencia de {diferencia:.2f}€ ({porcentaje:.2f}%)"
                })

    # ================================================================
    # FASE 4: COMPLETAR DESCRIPCIONES (opcional)
    # ================================================================

    def ejecutar_fase4(self):
        """
        FASE 4: Completar descripciones faltantes (opcional)

        En V2 las descripciones ya se extraen en Fase 2,
        así que esta fase es principalmente para estadísticas
        """
        logger.info("")
        logger.info("🔧 " + "=" * 70)
        logger.info("🔧 [FASE 4/4] Completando Descripciones (Opcional)")
        logger.info("🔧 " + "=" * 70)

        inicio = datetime.now()

        if not self.fase2_resultado:
            logger.warning("  ⚠️  Fase 2 no completada, saltando Fase 4")
            self.fase4_resultado = {'saltada': True}
            return

        estructura = self.fase2_resultado['estructura_completa']

        logger.info("  📝 Verificando descripciones de partidas...")

        total_partidas = 0
        con_descripcion = 0
        sin_descripcion = 0

        for cap in estructura.get('capitulos', []):
            stats = self._contar_descripciones_recursivo(cap)
            total_partidas += stats['total']
            con_descripcion += stats['con_desc']
            sin_descripcion += stats['sin_desc']

        porcentaje = (con_descripcion / total_partidas * 100) if total_partidas > 0 else 0

        logger.info(f"    • Total partidas: {total_partidas}")
        logger.info(f"    • Con descripción: {con_descripcion} ({porcentaje:.1f}%)")
        logger.info(f"    • Sin descripción: {sin_descripcion}")

        duracion = (datetime.now() - inicio).total_seconds()

        self.fase4_resultado = {
            'total_partidas': total_partidas,
            'con_descripcion': con_descripcion,
            'sin_descripcion': sin_descripcion,
            'porcentaje_completado': porcentaje,
            'duracion_segundos': duracion
        }

        logger.info(f"  ✅ [FASE 4] Completada en {duracion:.2f}s")
        logger.info("")

    def _contar_descripciones_recursivo(self, elemento: Dict) -> Dict:
        """Cuenta partidas con/sin descripción"""
        total = 0
        con_desc = 0
        sin_desc = 0

        for partida in elemento.get('partidas', []):
            total += 1
            if partida.get('descripcion', '').strip():
                con_desc += 1
            else:
                sin_desc += 1

        for sub in elemento.get('subcapitulos', []):
            stats = self._contar_descripciones_recursivo(sub)
            total += stats['total']
            con_desc += stats['con_desc']
            sin_desc += stats['sin_desc']

        return {'total': total, 'con_desc': con_desc, 'sin_desc': sin_desc}

    # ================================================================
    # COMPILAR RESULTADO FINAL
    # ================================================================

    def _compilar_resultado_final(self) -> Dict:
        """
        Compila resultado final en formato esperado por la API
        """
        estructura = self.fase2_resultado['estructura_completa'] if self.fase2_resultado else {'capitulos': []}

        # Calcular estadísticas finales
        estadisticas = {
            'total_capitulos': len(estructura.get('capitulos', [])),
            'total_subcapitulos': self._contar_subcapitulos_recursivo(estructura),
            'total_partidas': self._contar_partidas_recursivo(estructura),
            'presupuesto_total': sum(cap.get('total', 0.0) for cap in estructura.get('capitulos', []))
        }

        # Tiempos de cada fase
        tiempos = {
            'fase1': self.fase1_resultado.get('duracion_segundos', 0) if self.fase1_resultado else 0,
            'fase2': self.fase2_resultado.get('duracion_segundos', 0) if self.fase2_resultado else 0,
            'fase3': self.fase3_resultado.get('duracion_segundos', 0) if self.fase3_resultado else 0,
            'fase4': self.fase4_resultado.get('duracion_segundos', 0) if self.fase4_resultado else 0,
        }
        tiempos['total'] = sum(tiempos.values())

        # Metadata completa
        metadata = {
            'pdf_nombre': self.pdf_path.name,
            'pdf_path': str(self.pdf_path),
            'num_columnas': self.fase1_resultado.get('layout_info', {}).get('total_columnas', 1) if self.fase1_resultado else 1,
            'layout_info': self.fase1_resultado.get('layout_info', {}) if self.fase1_resultado else {},
            'tiempos_fases': tiempos,
            'archivos_intermedios': {
                'fase1_estructura': self.fase1_resultado.get('archivo_estructura', '') if self.fase1_resultado else '',
                'fase1_texto': self.fase1_resultado.get('archivo_texto', '') if self.fase1_resultado else '',
                'fase2_clasificaciones': self.fase2_resultado.get('archivo_clasificaciones', '') if self.fase2_resultado else '',
                'fase2_partidas': self.fase2_resultado.get('archivo_partidas', '') if self.fase2_resultado else '',
                'fase3_validacion': self.fase3_resultado.get('archivo_validacion', '') if self.fase3_resultado else ''
            },
            'timestamp': self.timestamp
        }

        logger.info("📊 RESUMEN FINAL:")
        logger.info(f"   • Capítulos: {estadisticas['total_capitulos']}")
        logger.info(f"   • Subcapítulos: {estadisticas['total_subcapitulos']}")
        logger.info(f"   • Partidas: {estadisticas['total_partidas']}")
        logger.info(f"   • Presupuesto total: {estadisticas['presupuesto_total']:.2f} €")
        logger.info(f"   • Tiempo total: {tiempos['total']:.2f}s")
        logger.info("")
        logger.info("📁 Archivos intermedios guardados en:")
        logger.info(f"   {self.output_dir}")

        return {
            'estructura': estructura,
            'metadata': metadata,
            'estadisticas': estadisticas
        }
