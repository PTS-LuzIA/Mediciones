"""
Agente especializado en extraer partidas de un capítulo específico.
Procesa por capítulos para mejor control, validación y manejo de errores.
"""

import httpx
import base64
import json
import os
import time
from typing import Dict, List, Optional
import logging
import PyPDF2

logger = logging.getLogger(__name__)


class PartidaExtractionAgent:
    """Agente especializado en extraer partidas de capítulos específicos"""

    # Caché global de clasificaciones por PDF (para evitar re-procesar el mismo PDF)
    _clasificaciones_cache = {}

    def __init__(self, api_key: Optional[str] = None, use_openrouter: bool = True):
        """
        Args:
            api_key: API key (OPENROUTER_API_KEY o ANTHROPIC_API_KEY según use_openrouter)
            use_openrouter: Si True, usa OpenRouter (mejor rate limit). Si False, usa Anthropic directo
        """
        self.use_openrouter = use_openrouter

        if use_openrouter:
            self.api_key = api_key or os.getenv('OPENROUTER_API_KEY')
            if not self.api_key:
                raise ValueError("OPENROUTER_API_KEY no encontrada en variables de entorno")
            self.base_url = "https://openrouter.ai/api/v1"
            # Usar Gemini 2.5 Flash Lite (más rápido y económico)
            self.model = "google/gemini-2.5-flash-lite"
        else:
            self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
            if not self.api_key:
                raise ValueError("ANTHROPIC_API_KEY no encontrada en variables de entorno")
            self.base_url = "https://api.anthropic.com/v1"
            self.model = "claude-3-5-haiku-20241022"

    def compress_pdf_for_llm(self, pdf_path: str) -> str:
        """
        Comprime el PDF agresivamente para reducir tokens en Claude.
        Claude procesa PDFs visualmente, por lo que reducir la resolución
        de imágenes es crítico para PDFs grandes.

        Args:
            pdf_path: Ruta al archivo PDF original

        Returns:
            Ruta al PDF comprimido (o original si falla la compresión)
        """
        import subprocess

        # SIEMPRE comprimir para PDFs que van a Claude (reduce tokens dramáticamente)
        compressed_path = pdf_path.replace('.pdf', '_compressed_for_llm.pdf')

        # Si ya existe el comprimido, reutilizarlo
        if os.path.exists(compressed_path):
            logger.info(f"✓ Using existing compressed PDF: {compressed_path}")
            return compressed_path

        try:
            file_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
            logger.info(f"🗜️ Compressing PDF for LLM ({file_size_mb:.2f} MB)...")

            subprocess.run([
                'gs',
                '-sDEVICE=pdfwrite',
                '-dCompatibilityLevel=1.4',
                '-dPDFSETTINGS=/screen',  # Máxima compresión (72 DPI) - reduce tokens significativamente
                '-dDownsampleColorImages=true',
                '-dColorImageResolution=72',  # Resolución mínima pero legible
                '-dNOPAUSE',
                '-dQUIET',
                '-dBATCH',
                f'-sOutputFile={compressed_path}',
                pdf_path
            ], check=True, capture_output=True, timeout=120)

            compressed_size_mb = os.path.getsize(compressed_path) / (1024 * 1024)
            reduction = ((file_size_mb - compressed_size_mb) / file_size_mb) * 100
            logger.info(f"✓ PDF compressed: {file_size_mb:.2f} MB → {compressed_size_mb:.2f} MB ({reduction:.1f}% reduction)")

            return compressed_path

        except FileNotFoundError:
            logger.warning("⚠️ Ghostscript (gs) not found. Install with: brew install ghostscript")
            logger.warning("Using original PDF (may exceed token limits)")
            return pdf_path
        except subprocess.TimeoutExpired:
            logger.warning(f"⚠️ Compression timeout. Using original PDF")
            return pdf_path
        except Exception as e:
            logger.warning(f"⚠️ Compression failed: {e}. Using original PDF")
            return pdf_path

    def extract_text_from_pdf(self, pdf_path: str, max_tokens: int = 170000) -> str:
        """
        Extrae texto del PDF y lo comprime agresivamente para caber en límite de tokens.

        Args:
            pdf_path: Ruta al archivo PDF
            max_tokens: Máximo de tokens permitidos (default: 170K para dejar margen)

        Returns:
            String con el texto extraído y comprimido del PDF
        """
        import re

        try:
            with open(pdf_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                text_parts = []

                for page in pdf_reader.pages:
                    text = page.extract_text()
                    if text.strip():
                        # Compactar agresivamente
                        lines = [line.strip() for line in text.split('\n') if line.strip()]
                        text_parts.append(' '.join(lines))

                # Unir todo el texto
                full_text = ' '.join(text_parts)

                # Limpiezas agresivas para reducir tokens:
                # 1. Eliminar espacios múltiples
                full_text = re.sub(r'\s+', ' ', full_text)

                # 2. Reducir repeticiones de caracteres (ej: "===" -> "=")
                full_text = re.sub(r'([=\-_])\1{2,}', r'\1', full_text)

                # 3. Eliminar puntos suspensivos excesivos
                full_text = re.sub(r'\.{3,}', '...', full_text)

                full_text = full_text.strip()

                # Estimación de tokens
                estimated_tokens = int(len(full_text) * 0.37)
                logger.info(f"✓ Texto extraído: {len(full_text)} caracteres (~{estimated_tokens} tokens)")

                # Si excede el límite, truncar (manteniendo inicio que tiene info clave)
                if estimated_tokens > max_tokens:
                    target_chars = int(max_tokens / 0.37)
                    full_text = full_text[:target_chars]
                    logger.warning(f"⚠️ PDF truncado de {estimated_tokens} a {max_tokens} tokens")
                    estimated_tokens = max_tokens

                return full_text

        except Exception as e:
            logger.error(f"Error extrayendo texto del PDF: {e}")
            raise

    def extraer_texto_seccion(self, pdf_path: str, capitulo_codigo: str, subcapitulos_filtrados: List[str] = None) -> str:
        """
        Extrae solo el texto de una sección específica usando el parser local (probado y confiable)

        Args:
            pdf_path: Ruta al PDF
            capitulo_codigo: Código del capítulo (ej: "01", "14")
            subcapitulos_filtrados: Lista de códigos de subcapítulos específicos o None para todo el capítulo

        Returns:
            Texto solo de esa sección
        """
        try:
            # Importar parser local
            import sys
            from pathlib import Path
            parent_dir = str(Path(__file__).parent.parent)
            if parent_dir not in sys.path:
                sys.path.insert(0, parent_dir)

            from parser.pdf_extractor import PDFExtractor
            from parser.line_classifier import LineClassifier

            logger.info(f"📄 Extrayendo sección: capítulo {capitulo_codigo}" +
                       (f", subcapítulos {subcapitulos_filtrados}" if subcapitulos_filtrados else ""))

            # 1. Obtener clasificaciones del PDF (usando caché si está disponible)
            cache_key = f"{pdf_path}_{os.path.getmtime(pdf_path)}"  # Clave única por PDF + timestamp

            if cache_key in self._clasificaciones_cache:
                logger.info(f"✓ Usando clasificaciones cacheadas para {os.path.basename(pdf_path)}")
                clasificaciones = self._clasificaciones_cache[cache_key]
            else:
                logger.info(f"📄 Extrayendo y clasificando líneas del PDF (primera vez)...")
                extractor = PDFExtractor(pdf_path)
                datos = extractor.extraer_todo()
                lineas = datos['all_lines']
                clasificaciones = LineClassifier.clasificar_bloque(lineas)

                # Guardar en caché
                self._clasificaciones_cache[cache_key] = clasificaciones
                logger.info(f"💾 Clasificaciones guardadas en caché ({len(clasificaciones)} líneas)")

                # ✅ GUARDAR TEXTO COMPLETO del PDF (una sola vez por PDF)
                try:
                    nombre_pdf = os.path.basename(pdf_path).replace('.pdf', '')

                    # Buscar archivo con formato de Fase 2: extracted_full_text_{proyecto_id}_{nombre_pdf}.txt
                    # Primero intentar encontrar archivos existentes con cualquier proyecto_id
                    import glob
                    patron_busqueda = f"logs/extracted_full_text_*_{nombre_pdf}.txt"
                    archivos_existentes = glob.glob(patron_busqueda)

                    if archivos_existentes:
                        # Ya existe un archivo generado previamente (probablemente en Fase 2)
                        texto_completo_path = archivos_existentes[0]
                        logger.info(f"✓ Texto completo ya existe (generado en Fase 2): {texto_completo_path}")
                    else:
                        # No existe, generar sin proyecto_id (no lo tenemos disponible aquí)
                        texto_completo_path = f"logs/extracted_full_text_{nombre_pdf}.txt"

                        # Solo guardar si no existe
                        if not os.path.exists(texto_completo_path):
                            os.makedirs('logs', exist_ok=True)
                            extractor.guardar_texto(texto_completo_path)
                            logger.info(f"💾 Texto completo guardado en: {texto_completo_path}")
                        else:
                            logger.info(f"✓ Texto completo ya existe: {texto_completo_path}")
                except Exception as e:
                    logger.warning(f"⚠️ No se pudo guardar texto completo: {e}")

            logger.info(f"Total clasificaciones: {len(clasificaciones)}")

            # DEBUG: Mostrar primeras clasificaciones de capítulos, subcapítulos y apartados
            capitulos_encontrados = []
            subcapitulos_encontrados = []
            apartados_encontrados = []
            for i, clasificacion in enumerate(clasificaciones[:200]):  # primeras 200 líneas
                tipo = clasificacion['tipo'].value if hasattr(clasificacion['tipo'], 'value') else clasificacion['tipo']
                # El código está en clasificacion['datos']['codigo']
                datos = clasificacion.get('datos', {})
                codigo = datos.get('codigo', '') if datos else ''
                if tipo == 'capitulo':
                    capitulos_encontrados.append(codigo)
                elif tipo == 'subcapitulo':
                    subcapitulos_encontrados.append(codigo)
                elif tipo == 'apartado':
                    apartados_encontrados.append(codigo)

            logger.info(f"DEBUG - Capítulos encontrados (primeros 200 líneas): {capitulos_encontrados[:10]}")
            logger.info(f"DEBUG - Subcapítulos encontrados (primeros 200 líneas): {subcapitulos_encontrados[:10]}")
            logger.info(f"DEBUG - Apartados encontrados (primeros 200 líneas): {apartados_encontrados[:10]}")

            # 2. Filtrar líneas de la sección solicitada
            lineas_seccion = []
            dentro_capitulo = False
            dentro_subcapitulo_correcto = False

            logger.info(f"DEBUG - Buscando capítulo: '{capitulo_codigo}', subcapítulos: {subcapitulos_filtrados}")

            for i, clasificacion in enumerate(clasificaciones):
                tipo = clasificacion['tipo'].value if hasattr(clasificacion['tipo'], 'value') else clasificacion['tipo']
                # El código está en clasificacion['datos']['codigo'], no en clasificacion['codigo']
                datos = clasificacion.get('datos', {})
                codigo = datos.get('codigo', '') if datos else ''
                linea = clasificacion.get('linea', '')

                # Detectar inicio del capítulo
                if tipo == 'capitulo' and codigo == capitulo_codigo:
                    dentro_capitulo = True
                    lineas_seccion.append(linea)
                    logger.info(f"✓ Encontrado inicio capítulo {codigo}")
                    continue

                # Detectar fin del capítulo (siguiente capítulo)
                if dentro_capitulo and tipo == 'capitulo' and codigo != capitulo_codigo:
                    logger.debug(f"Fin capítulo (encontrado siguiente: {codigo})")
                    break

                # MEJORAR: Detectar fin de capítulo por TOTAL del capítulo
                if dentro_capitulo and not subcapitulos_filtrados and tipo == 'total':
                    codigo_total = datos.get('codigo', '')
                    logger.debug(f"DEBUG - TOTAL detectado en capítulo: codigo_total='{codigo_total}', capitulo='{capitulo_codigo}'")

                    # Si el TOTAL tiene código explícito, verificar que coincida con el capítulo
                    if codigo_total:
                        if codigo_total == capitulo_codigo:
                            # Es el TOTAL del capítulo que estamos extrayendo
                            lineas_seccion.append(linea)
                            logger.info(f"✓ Fin de capítulo {codigo_total} detectado por TOTAL")
                            break
                        else:
                            # Es el TOTAL de otro capítulo - indica fin
                            logger.info(f"✓ Fin de capítulo detectado por TOTAL de {codigo_total}")
                            break
                    else:
                        # TOTAL sin código explícito - buscar en la línea
                        if capitulo_codigo in linea:
                            lineas_seccion.append(linea)
                            logger.info(f"✓ Fin de capítulo {capitulo_codigo} detectado por TOTAL en texto")
                            break

                # MEJORAR: Detectar fin de capítulo por código numérico del mismo nivel (XX)
                if dentro_capitulo and not subcapitulos_filtrados:
                    import re
                    # Buscar código de capítulo (2 dígitos sin puntos) al inicio de la línea
                    match_codigo_cap = re.match(r'^(\d{2})\s+[A-Z]', linea)
                    if match_codigo_cap:
                        codigo_detectado = match_codigo_cap.group(1)
                        if codigo_detectado != capitulo_codigo:
                            # Es el inicio de OTRO capítulo
                            logger.info(f"✓ Fin de capítulo detectado por código numérico: {codigo_detectado}")
                            break

                # Si estamos dentro del capítulo
                if dentro_capitulo:
                    # Si hay filtro de subcapítulos específicos
                    if subcapitulos_filtrados:
                        # Detectar inicio de subcapítulo/apartado filtrado
                        # IMPORTANTE: Los códigos con 3 niveles (01.07.01) se clasifican como 'apartado', no 'subcapitulo'
                        if (tipo in ['subcapitulo', 'apartado']) and codigo in subcapitulos_filtrados:
                            dentro_subcapitulo_correcto = True
                            lineas_seccion.append(linea)
                            logger.info(f"✓ Encontrado inicio {tipo} {codigo}")
                            continue
                        elif tipo in ['subcapitulo', 'apartado']:
                            # Si estamos dentro del subcapítulo y encontramos otro subcapítulo/apartado
                            if dentro_subcapitulo_correcto:
                                # Verificar si es un hijo (empieza con código del padre + ".")
                                for subcap_filtrado in subcapitulos_filtrados:
                                    if codigo.startswith(subcap_filtrado + '.'):
                                        logger.info(f"✓ Fin de subcapítulo {subcap_filtrado} detectado por hijo {codigo}")
                                        dentro_subcapitulo_correcto = False
                                        break

                                # Si salimos porque encontramos un hijo, salir del loop principal
                                if not dentro_subcapitulo_correcto:
                                    break

                            # DEBUG: mostrar subcapítulos/apartados que no coinciden
                            logger.debug(f"{tipo.capitalize()} encontrado pero no coincide: '{codigo}' vs {subcapitulos_filtrados}")

                        # MEJORAR: Detectar fin de subcapítulo por línea TOTAL
                        if dentro_subcapitulo_correcto and tipo == 'total':
                            codigo_total = datos.get('codigo', '')
                            logger.info(f"DEBUG - TOTAL detectado: codigo_total='{codigo_total}', subcapitulos_filtrados={subcapitulos_filtrados}")

                            if codigo_total:
                                # Si el TOTAL tiene código explícito, verificar que coincida
                                if codigo_total in subcapitulos_filtrados:
                                    # Es el TOTAL del subcapítulo que estamos extrayendo
                                    lineas_seccion.append(linea)
                                    logger.info(f"✓ Fin de subcapítulo {codigo_total} detectado por TOTAL")
                                    dentro_subcapitulo_correcto = False
                                    break  # Salir del loop - terminamos la extracción
                                else:
                                    # Es el TOTAL de otro subcapítulo - también indica fin
                                    logger.info(f"✓ Fin de sección detectado por TOTAL de {codigo_total}")
                                    dentro_subcapitulo_correcto = False
                                    break  # No incluir este TOTAL, ya es de otra sección
                            else:
                                # TOTAL sin código explícito - buscar en el texto de la línea
                                encontrado = False
                                for subcap in subcapitulos_filtrados:
                                    if subcap in linea:
                                        codigo_total = subcap
                                        encontrado = True
                                        break

                                if encontrado:
                                    # Es el TOTAL del subcapítulo que estamos extrayendo
                                    lineas_seccion.append(linea)
                                    logger.info(f"✓ Fin de subcapítulo {codigo_total} detectado por TOTAL en texto")
                                    dentro_subcapitulo_correcto = False
                                    break
                                else:
                                    # TOTAL sin código identificable - asumir que cierra el subcapítulo actual
                                    lineas_seccion.append(linea)
                                    logger.info(f"✓ Fin de subcapítulo detectado por TOTAL (sin código)")
                                    dentro_subcapitulo_correcto = False
                                    break

                        # MEJORAR: Detectar fin de subcapítulo/apartado por cambio de nivel jerárquico
                        if dentro_subcapitulo_correcto and tipo in ['subcapitulo', 'apartado'] and codigo not in subcapitulos_filtrados:
                            # Verificar si es del mismo nivel o superior (mismo número de puntos o menos)
                            # Calcular el nivel mínimo de los subcapítulos filtrados
                            nivel_minimo_actual = min(len(sc.split('.')) for sc in subcapitulos_filtrados)
                            nivel_nuevo = len(codigo.split('.'))

                            if nivel_nuevo <= nivel_minimo_actual:
                                dentro_subcapitulo_correcto = False
                                logger.info(f"✓ Fin de sección detectado por código de nivel {nivel_nuevo}: {codigo}")
                                continue

                        # NUEVO: Detectar fin de subcapítulo por código numérico en línea sin clasificar
                        if dentro_subcapitulo_correcto:
                            import re
                            # Buscar código numérico (XX.XX.XX...) al inicio de la línea
                            match_codigo = re.match(r'^(\d{2}(?:\.\d{2})+)\s+', linea)
                            if match_codigo:
                                codigo_detectado = match_codigo.group(1)
                                if codigo_detectado not in subcapitulos_filtrados:
                                    # Verificar nivel jerárquico
                                    nivel_minimo_actual = min(len(sc.split('.')) for sc in subcapitulos_filtrados)
                                    nivel_detectado = len(codigo_detectado.split('.'))

                                    if nivel_detectado <= nivel_minimo_actual:
                                        # Es un código del mismo nivel o superior - indica fin
                                        logger.info(f"✓ Fin de sección detectado por código numérico no clasificado: {codigo_detectado}")
                                        dentro_subcapitulo_correcto = False
                                        continue

                        # Capturar solo si estamos en subcapítulo correcto
                        if dentro_subcapitulo_correcto:
                            lineas_seccion.append(linea)
                    else:
                        # Sin filtro: capturar todo el capítulo
                        lineas_seccion.append(linea)

            texto_seccion = ' '.join(lineas_seccion)
            num_chars = len(texto_seccion)
            estimated_tokens = int(num_chars * 0.37)

            logger.info(f"✓ Sección extraída: {num_chars} caracteres (~{estimated_tokens} tokens), {len(lineas_seccion)} líneas")

            # Guardar texto extraído para debugging manual
            try:
                timestamp = int(time.time())
                subcaps_str = '_'.join(subcapitulos_filtrados) if subcapitulos_filtrados else 'ALL'
                debug_filename = f"extracted_text_{capitulo_codigo}_{subcaps_str}_{timestamp}.txt"
                debug_path = os.path.join("logs", "TEMP_BORRAR", debug_filename)

                os.makedirs(os.path.dirname(debug_path), exist_ok=True)
                with open(debug_path, 'w', encoding='utf-8') as f:
                    f.write(f"=== TEXTO EXTRAÍDO ===\n")
                    f.write(f"Capítulo: {capitulo_codigo}\n")
                    f.write(f"Subcapítulos: {subcapitulos_filtrados}\n")
                    f.write(f"Caracteres: {num_chars}\n")
                    f.write(f"Líneas: {len(lineas_seccion)}\n")
                    f.write(f"PDF: {os.path.basename(pdf_path)}\n")
                    f.write(f"\n{'='*80}\n\n")
                    f.write(texto_seccion)
                logger.info(f"💾 Texto extraído guardado en: {debug_path}")
            except Exception as e:
                logger.warning(f"⚠️ No se pudo guardar texto de debug: {e}")

            return texto_seccion

        except Exception as e:
            logger.warning(f"⚠️ Error extrayendo sección con parser: {e}")
            logger.warning("Fallback: usando extracción completa del PDF")
            # Fallback: usar método original
            return self.extract_text_from_pdf(pdf_path, max_tokens=999999999)

    def encode_pdf_base64(self, pdf_path: str) -> str:
        """
        Codifica un PDF en base64 para enviarlo a la API

        Args:
            pdf_path: Ruta al archivo PDF

        Returns:
            String en base64 del PDF
        """
        with open(pdf_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')

    def _formatear_estructura_capitulo(self, capitulo: Dict) -> str:
        """
        Formatea la estructura de un capítulo para incluirla en el prompt

        Args:
            capitulo: Dict con código, nombre y subcapítulos del capítulo

        Returns:
            String formateado con la estructura jerárquica
        """
        resultado = [f"Capítulo {capitulo['codigo']} - {capitulo['nombre']}"]

        def formatear_subcapitulos(subcaps: List[Dict], nivel: int = 1):
            lines = []
            for sub in subcaps:
                indent = "  " * nivel
                lines.append(f"{indent}└─ {sub['codigo']} - {sub['nombre']}")
                if sub.get('subcapitulos'):
                    lines.extend(formatear_subcapitulos(sub['subcapitulos'], nivel + 1))
            return lines

        if capitulo.get('subcapitulos'):
            resultado.extend(formatear_subcapitulos(capitulo['subcapitulos']))

        return "\n".join(resultado)

    def _obtener_subcapitulos_hoja(self, capitulo: Dict) -> List[str]:
        """
        Obtiene los códigos de todos los subcapítulos hoja (sin hijos) del capítulo

        Args:
            capitulo: Dict con la estructura del capítulo

        Returns:
            Lista de códigos de subcapítulos hoja
        """
        hojas = []

        def recorrer(subcaps: List[Dict]):
            for sub in subcaps:
                if sub.get('subcapitulos'):
                    # Tiene hijos, seguir buscando
                    recorrer(sub['subcapitulos'])
                else:
                    # Es hoja
                    hojas.append(sub['codigo'])

        if capitulo.get('subcapitulos'):
            recorrer(capitulo['subcapitulos'])

        return hojas

    def crear_prompt_partidas_capitulo(self, capitulo: Dict, subcapitulos_filtrados: List[str] = None) -> str:
        """
        Crea el prompt para extraer partidas de un capítulo específico

        Args:
            capitulo: Dict con código, nombre, total y subcapítulos del capítulo
            subcapitulos_filtrados: Lista de códigos de subcapítulos a procesar (si None, procesa todos)

        Returns:
            String con el prompt completo
        """
        subcapitulos_hoja = self._obtener_subcapitulos_hoja(capitulo)

        # Si hay filtro, usar solo esos subcapítulos
        if subcapitulos_filtrados:
            subcapitulos_hoja = [s for s in subcapitulos_hoja if s in subcapitulos_filtrados]

        # Diferenciar entre capítulo con subcapítulos y capítulo con partidas directas
        if subcapitulos_hoja:
            # Capítulo con subcapítulos
            return f"""Extrae TODAS las partidas de los subcapítulos: {', '.join(subcapitulos_hoja)}

IMPORTANTE: El campo "subcapitulo_codigo" es OBLIGATORIO. Cada partida DEBE tener el código del subcapítulo al que pertenece.
IMPORTANTE: El campo "resumen" es OBLIGATORIO. Extrae el título/descripción corta de la partida (máximo 100 caracteres).

FORMATO DE PARTIDA:
Cada línea tiene este formato: CÓDIGO UNIDAD DESCRIPCIÓN CANTIDAD PRECIO IMPORTE

IMPORTANTE: Los 3 valores numéricos (CANTIDAD, PRECIO, IMPORTE) están SIEMPRE al FINAL de la línea.
Si la descripción contiene números (ejemplo: "14,65 m2"), IGNÓRALOS y extrae los ÚLTIMOS 3 NÚMEROS.

CASOS ESPECIALES - CÓDIGOS PEGADOS SIN ESPACIOS:
A veces el código está PEGADO a la descripción sin espacios ni unidad visible.
Identifica el código por su LONGITUD TÍPICA (8-15 caracteres alfanuméricos) y corta justo antes de que empiece la descripción en MAYÚSCULAS.

Ejemplo 1 - Código normal con espacios:
m23U01BP010 m2 DEMOLICIÓN MEDIOS MECÁNICOS PAVIMENTO ASFÁLTICO 450,40 2,34 1.053,94

Extracción correcta:
- codigo: "m23U01BP010" (TODO hasta el primer espacio, incluye letras y números)
- resumen: "DEMOLICIÓN MEDIOS MECÁNICOS PAVIMENTO ASFÁLTICO" (título corto, max 100 caracteres)
- unidad: "m2" (IGNORAR, no incluir en el código)
- cantidad: 450.40 (ÚLTIMO tercio de números)
- precio: 2.34 (ÚLTIMO segundo número)
- importe: 1053.94 (ÚLTIMO número)

Ejemplo 2 - Código normal con unidad corta:
APUI_003 d ALQUILER DIARIO DE GRUA SOBRE CAMIÓN 6,00 620,65 3.723,90

Extracción correcta:
- codigo: "APUI_003" (TODO hasta el primer espacio)
- resumen: "ALQUILER DIARIO DE GRUA SOBRE CAMIÓN" (título corto)
- unidad: "d" (IGNORAR, no incluir en el código)
- cantidad: 6.00
- precio: 620.65
- importe: 3723.90

Ejemplo 3 - Con números en la descripción:
m23S03RC050 mes ALQUILER CASETA ALMACÉN 14,65 m2 16,00 205,16 3.282,56

Extracción correcta:
- codigo: "m23S03RC050"
- resumen: "ALQUILER CASETA ALMACÉN" (título corto)
- unidad: "mes"
- cantidad: 16.00 (NO 14.65 - tomar ÚLTIMOS 3 números)
- precio: 205.16
- importe: 3282.56
Descripción contiene "14,65 m2" pero NO es la cantidad, son los ÚLTIMOS 3 números

Ejemplo 4 - CÓDIGO PEGADO SIN ESPACIOS (caso problemático):
APUI_V_mU16NROU822SUMINISTRO E INSTALACIÓN DE EQUIPO REFERENCIA NRO824 DE JUEGOS KOMPAN 5,00 603,54 3.017,70

Extracción correcta:
- codigo: "APUI_V_mU16NROU822" (cortar ANTES de que empiece la descripción en mayúsculas)
- Pista: El código típicamente tiene 8-20 caracteres alfanuméricos con guiones bajos
- "SUMINISTRO" es claramente una palabra descriptiva, NO parte del código
- cantidad: 5.00
- precio: 603.54
- importe: 3017.70

Ejemplo 5 - CÓDIGO PEGADO con descripción multi-línea:
APUI_V_mU16NROU822SUMINISTRO E INSTALACIÓN DE EQUIPO REFERENCIA NRO824 DE JUEGOS KOMPAN S.A, O SIMILAR. 5,00 603,54 3.017,70

Extracción correcta:
- codigo: "APUI_V_mU16NROU822"
- La descripción "SUMINISTRO E INSTALACIÓN... S.A, O SIMILAR." puede estar en 2+ líneas unidas
- NO incluir palabras descriptivas en MAYÚSCULAS dentro del código
- cantidad: 5.00
- precio: 603.54
- importe: 3017.70

JSON:
{{
  "capitulo_codigo": "{capitulo['codigo']}",
  "partidas": [
    {{"codigo":"m23U01BP010","resumen":"DEMOLICIÓN MEDIOS MECÁNICOS PAVIMENTO ASFÁLTICO","subcapitulo_codigo":"{subcapitulos_hoja[0]}","cantidad":450.40,"precio":2.34,"importe":1053.94}},
    {{"codigo":"APUI_003","resumen":"ALQUILER DIARIO DE GRUA SOBRE CAMIÓN","subcapitulo_codigo":"{subcapitulos_hoja[0] if len(subcapitulos_hoja) == 1 else '...' }","cantidad":6.00,"precio":620.65,"importe":3723.90}}
  ]
}}

Reglas CRÍTICAS:
1. "codigo" = TODO el texto desde el inicio hasta el PRIMER ESPACIO (incluye letras, números, guiones bajos)
   - EXCEPCIÓN: Si el código está PEGADO a la descripción sin espacios, identifica el código por:
     * Longitud típica: 8-20 caracteres alfanuméricos
     * Corta ANTES de que empiece una palabra descriptiva en MAYÚSCULAS (ej: "SUMINISTRO", "DEMOLICIÓN")
     * Los códigos NO contienen palabras completas en español
2. "resumen" = Título/descripción corta de la partida (MÁXIMO 100 caracteres, UNA LÍNEA)
3. NO incluir la unidad (m2, m3, ud, d, kg, etc.) en el código
4. NO incluir palabras descriptivas en MAYÚSCULAS dentro del código
5. SOLO partidas de subcapítulos: {', '.join(subcapitulos_hoja)}
6. Cada partida DEBE incluir "subcapitulo_codigo" con uno de: {', '.join(subcapitulos_hoja)}
7. NO repetir códigos de partida
8. NO incluir líneas de totales

VALIDACIÓN (antes de enviar):
1. Verificar que "codigo" NO contiene la unidad (no debe terminar en m2, m3, ud, d, etc.)
2. Verificar que "codigo" NO contiene palabras descriptivas (SUMINISTRO, DEMOLICIÓN, etc.)
3. Verificar que "resumen" existe y no está vacío (OBLIGATORIO)
4. cantidad × precio = importe (CADA partida)
5. Códigos de partida únicos
6. TODAS las partidas tienen subcapitulo_codigo y resumen
7. Revisa primera y última partida"""
        else:
            # Capítulo SIN subcapítulos (partidas directas)
            return f"""Extrae partidas del capítulo {capitulo['codigo']}

IMPORTANTE: El campo "resumen" es OBLIGATORIO. Extrae el título/descripción corta de la partida (máximo 100 caracteres).

FORMATO DE PARTIDA:
Cada línea tiene este formato: CÓDIGO UNIDAD DESCRIPCIÓN CANTIDAD PRECIO IMPORTE

IMPORTANTE: Los 3 valores numéricos (CANTIDAD, PRECIO, IMPORTE) están SIEMPRE al FINAL de la línea.
Si la descripción contiene números (ejemplo: "14,65 m2"), IGNÓRALOS y extrae los ÚLTIMOS 3 NÚMEROS.

CASOS ESPECIALES - CÓDIGOS PEGADOS SIN ESPACIOS:
A veces el código está PEGADO a la descripción sin espacios ni unidad visible.
Identifica el código por su LONGITUD TÍPICA (8-15 caracteres alfanuméricos) y corta justo antes de que empiece la descripción en MAYÚSCULAS.

Ejemplo 1 - Código normal con espacios:
m23U01BP010 m2 DEMOLICIÓN MEDIOS MECÁNICOS PAVIMENTO ASFÁLTICO 450,40 2,34 1.053,94

Extracción correcta:
- codigo: "m23U01BP010" (TODO hasta el primer espacio, incluye letras y números)
- resumen: "DEMOLICIÓN MEDIOS MECÁNICOS PAVIMENTO ASFÁLTICO" (título corto, max 100 caracteres)
- unidad: "m2" (IGNORAR, no incluir en el código)
- cantidad: 450.40 (ÚLTIMO tercio de números)
- precio: 2.34 (ÚLTIMO segundo número)
- importe: 1053.94 (ÚLTIMO número)

Ejemplo 2 - Código normal con unidad corta:
APUI_003 d ALQUILER DIARIO DE GRUA SOBRE CAMIÓN 6,00 620,65 3.723,90

Extracción correcta:
- codigo: "APUI_003" (TODO hasta el primer espacio)
- resumen: "ALQUILER DIARIO DE GRUA SOBRE CAMIÓN" (título corto)
- unidad: "d" (IGNORAR, no incluir en el código)
- cantidad: 6.00
- precio: 620.65
- importe: 3723.90

Ejemplo 3 - Con números en la descripción:
m23S03RC050 mes ALQUILER CASETA ALMACÉN 14,65 m2 16,00 205,16 3.282,56

Extracción correcta:
- codigo: "m23S03RC050"
- resumen: "ALQUILER CASETA ALMACÉN" (título corto)
- unidad: "mes"
- cantidad: 16.00 (NO 14.65 - tomar ÚLTIMOS 3 números)
- precio: 205.16
- importe: 3282.56
Descripción contiene "14,65 m2" pero NO es la cantidad, son los ÚLTIMOS 3 números

Ejemplo 4 - CÓDIGO PEGADO SIN ESPACIOS (caso problemático):
APUI_V_mU16NROU822SUMINISTRO E INSTALACIÓN DE EQUIPO REFERENCIA NRO824 DE JUEGOS KOMPAN 5,00 603,54 3.017,70

Extracción correcta:
- codigo: "APUI_V_mU16NROU822" (cortar ANTES de que empiece la descripción en mayúsculas)
- Pista: El código típicamente tiene 8-20 caracteres alfanuméricos con guiones bajos
- "SUMINISTRO" es claramente una palabra descriptiva, NO parte del código
- cantidad: 5.00
- precio: 603.54
- importe: 3017.70

Ejemplo 5 - CÓDIGO PEGADO con descripción multi-línea:
APUI_V_mU16NROU822SUMINISTRO E INSTALACIÓN DE EQUIPO REFERENCIA NRO824 DE JUEGOS KOMPAN S.A, O SIMILAR. 5,00 603,54 3.017,70

Extracción correcta:
- codigo: "APUI_V_mU16NROU822"
- La descripción "SUMINISTRO E INSTALACIÓN... S.A, O SIMILAR." puede estar en 2+ líneas unidas
- NO incluir palabras descriptivas en MAYÚSCULAS dentro del código
- cantidad: 5.00
- precio: 603.54
- importe: 3017.70

JSON:
{{
  "capitulo_codigo": "{capitulo['codigo']}",
  "partidas": [
    {{"codigo":"m23U01BP010","resumen":"DEMOLICIÓN MEDIOS MECÁNICOS PAVIMENTO ASFÁLTICO","cantidad":450.40,"precio":2.34,"importe":1053.94}},
    {{"codigo":"APUI_003","resumen":"ALQUILER DIARIO DE GRUA SOBRE CAMIÓN","cantidad":6.00,"precio":620.65,"importe":3723.90}}
  ]
}}

Reglas CRÍTICAS:
1. "codigo" = TODO el texto desde el inicio hasta el PRIMER ESPACIO (incluye letras, números, guiones bajos)
   - EXCEPCIÓN: Si el código está PEGADO a la descripción sin espacios, identifica el código por:
     * Longitud típica: 8-20 caracteres alfanuméricos
     * Corta ANTES de que empiece una palabra descriptiva en MAYÚSCULAS (ej: "SUMINISTRO", "DEMOLICIÓN")
     * Los códigos NO contienen palabras completas en español
2. "resumen" = Título/descripción corta de la partida (MÁXIMO 100 caracteres, UNA LÍNEA)
3. NO incluir la unidad (m2, m3, ud, d, kg, etc.) en el código
4. NO incluir palabras descriptivas en MAYÚSCULAS dentro del código
5. NO repetir códigos de partida
6. NO incluir líneas de totales
7. NO incluir campo subcapitulo_codigo

VALIDACIÓN (antes de enviar):
1. Verificar que "codigo" NO contiene la unidad (no debe terminar en m2, m3, ud, d, etc.)
2. Verificar que "codigo" NO contiene palabras descriptivas (SUMINISTRO, DEMOLICIÓN, etc.)
3. Verificar que "resumen" existe y no está vacío (OBLIGATORIO)
4. cantidad × precio = importe (CADA partida)
5. Códigos únicos
6. TODAS las partidas tienen resumen
7. Revisa primera y última partida"""

    async def extraer_partidas_capitulo(
        self,
        pdf_path: str,
        capitulo: Dict,
        subcapitulos_filtrados: List[str] = None
    ) -> Dict:
        """
        Extrae todas las partidas de un capítulo específico

        Args:
            pdf_path: Ruta al archivo PDF
            capitulo: Dict con código, nombre, total y subcapítulos del capítulo
            subcapitulos_filtrados: Lista de códigos de subcapítulos a procesar (si None, procesa todos)

        Returns:
            Dict con:
            {
                "capitulo_codigo": "01",
                "partidas": [...],
                "total_extraido": 500125.75,
                "num_partidas": 245,
                "success": True/False,
                "error": None/string
            }
        """
        start_time = time.time()
        if subcapitulos_filtrados:
            logger.info(f"Extrayendo partidas del capítulo {capitulo['codigo']} - Subcapítulos: {', '.join(subcapitulos_filtrados[:3])}{'...' if len(subcapitulos_filtrados) > 3 else ''}")
        else:
            logger.info(f"Extrayendo partidas del capítulo {capitulo['codigo']} - {capitulo['nombre']}")

        try:
            # Extraer SOLO el texto de la sección solicitada usando el parser local
            pdf_text = self.extraer_texto_seccion(
                pdf_path=pdf_path,
                capitulo_codigo=capitulo['codigo'],
                subcapitulos_filtrados=subcapitulos_filtrados
            )

            # VALIDACIÓN: Verificar que hay contenido suficiente antes de enviar al LLM
            MIN_CHARS = 300  # Mínimo 300 caracteres para considerar que hay contenido real
            if len(pdf_text) < MIN_CHARS:
                subcaps_str = ', '.join(subcapitulos_filtrados) if subcapitulos_filtrados else 'TODO'
                logger.warning(f"⚠️ Sección {capitulo['codigo']} ({subcaps_str}) tiene muy poco contenido: {len(pdf_text)} caracteres")
                logger.warning(f"⚠️ El subcapítulo probablemente NO EXISTE en el PDF. Devolviendo partidas vacías.")
                return {
                    "capitulo_codigo": capitulo['codigo'],
                    "partidas": [],
                    "total_extraido": 0.0,
                    "num_partidas": 0,
                    "success": True,
                    "error": None,
                    "warning": f"Subcapítulo no encontrado o sin contenido (solo {len(pdf_text)} caracteres)"
                }

            pdf_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
            logger.info(f"📄 PDF: {pdf_size_mb:.2f} MB, enviando texto de sección específica")

            # Preparar headers para OpenRouter
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            # Crear prompt específico para el capítulo/subcapítulo
            prompt_texto = self.crear_prompt_partidas_capitulo(capitulo, subcapitulos_filtrados)

            # Estructura de 3 mensajes (como funcionaba originalmente):
            # 1. User: Texto completo del PDF
            # 2. Assistant: Confirmación
            # 3. User: Instrucción específica
            messages = [
                {
                    "role": "user",
                    "content": f"A continuación te proporciono el texto completo del presupuesto:\n\n{pdf_text}"
                },
                {
                    "role": "assistant",
                    "content": "Entendido. He recibido y analizado el presupuesto completo. ¿Qué partidas específicas necesitas que extraiga?"
                },
                {
                    "role": "user",
                    "content": prompt_texto
                }
            ]

            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.0,
                # Sin límite de max_tokens - dejamos que use todo lo necesario
                "response_format": {"type": "json_object"}  # Forzar respuesta JSON
            }

            # DEBUG: Guardar el payload enviado para análisis
            subcaps_str = '_'.join(subcapitulos_filtrados[:3]) if subcapitulos_filtrados else 'all'
            prompt_file = f"logs/TEMP_BORRAR/prompt_{capitulo['codigo']}_{subcaps_str}_{int(time.time())}_BORRAR.json"
            os.makedirs('logs/TEMP_BORRAR', exist_ok=True)
            with open(prompt_file, 'w', encoding='utf-8') as f:
                # Guardar solo estructura (no el texto completo que es muy largo)
                debug_payload = {
                    "model": payload["model"],
                    "temperature": payload["temperature"],
                    "messages": [
                        {
                            "role": msg["role"],
                            "content_length": len(msg["content"]),
                            "content_preview": msg["content"][:500] if len(msg["content"]) > 500 else msg["content"]
                        }
                        for msg in messages
                    ]
                }
                json.dump(debug_payload, f, indent=2, ensure_ascii=False)
            logger.info(f"💾 Prompt guardado en {prompt_file}")

            # Hacer la petición
            async with httpx.AsyncClient(timeout=120.0) as client:  # 2 minutos timeout
                response = await client.post(
                    f"{self.base_url}/chat/completions",  # Endpoint correcto para OpenRouter
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()

                result = response.json()
                content = result['choices'][0]['message']['content']

                # Log de usage para monitorear tokens
                usage = result.get('usage', {})
                if usage:
                    logger.info(f"📊 Tokens: input={usage.get('prompt_tokens', 0)}, output={usage.get('completion_tokens', 0)}, total={usage.get('total_tokens', 0)}")

                # SIEMPRE guardar la respuesta RAW completa para análisis
                subcaps_str = '_'.join(subcapitulos_filtrados[:3]) if subcapitulos_filtrados else 'all'
                raw_file = f"logs/TEMP_BORRAR/raw_response_{capitulo['codigo']}_{subcaps_str}_{int(time.time())}_BORRAR.json"
                try:
                    os.makedirs('logs/TEMP_BORRAR', exist_ok=True)
                    with open(raw_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    logger.info(f"📁 Respuesta RAW guardada en: {raw_file}")
                    logger.info(f"📊 Tamaño de respuesta: {len(content)} caracteres")
                except Exception as save_error:
                    logger.warning(f"No se pudo guardar respuesta RAW: {save_error}")

                # Parsear el JSON devuelto
                # Limpiar markdown si el LLM devolvió ```json...```
                content_clean = content.strip()

                # Buscar bloque de código markdown en cualquier parte del texto
                if '```json' in content_clean or '```' in content_clean:
                    # Extraer JSON del bloque de código markdown
                    lines = content_clean.split('\n')
                    start_idx = -1
                    end_idx = len(lines)

                    # Buscar inicio del bloque
                    for i, line in enumerate(lines):
                        if '```json' in line or (line.strip() == '```' and start_idx == -1):
                            start_idx = i + 1
                            break

                    # Buscar fin del bloque
                    if start_idx != -1:
                        for i in range(start_idx, len(lines)):
                            if lines[i].strip() == '```':
                                end_idx = i
                                break

                        content_clean = '\n'.join(lines[start_idx:end_idx])
                        logger.info(f"🧹 JSON extraído de bloque markdown (líneas {start_idx}-{end_idx})")

                resultado = json.loads(content_clean)

                # 🔍 VALIDACIÓN Y CORRECCIÓN: Detectar códigos mal extraídos
                # El LLM a veces incluye la unidad en el código (ej: "m23U01BP010m2" en lugar de "m23U01BP010")
                # o extrae solo la unidad (ej: "d" en lugar de "APUI_003")
                import re
                patron_unidades = re.compile(r'(m[23²³]?|M[23²³]?|Ml|ml|ud?|Ud?|d|kg|Kg|h|H|l|L|t|T|pa|Pa|P\.A\.)$', re.IGNORECASE)
                partidas_corregidas = 0

                for partida in resultado.get('partidas', []):
                    codigo_original = partida.get('codigo', '')

                    # Caso 1: Código termina con unidad (ej: "m23U01BP010m2")
                    match_unidad = patron_unidades.search(codigo_original)
                    if match_unidad:
                        # Remover la unidad del final
                        codigo_limpio = patron_unidades.sub('', codigo_original)
                        if codigo_limpio and len(codigo_limpio) >= 3:
                            partida['codigo'] = codigo_limpio
                            partidas_corregidas += 1
                            logger.debug(f"✓ Código corregido: '{codigo_original}' → '{codigo_limpio}'")

                    # Caso 2: Código es solo una unidad corta (ej: "d", "m2", "ud")
                    elif len(codigo_original) <= 3 and patron_unidades.match(codigo_original):
                        # Este es un error grave - el código completo se perdió
                        # Lo marcaremos para filtrado posterior
                        logger.warning(f"⚠️ Código inválido (solo unidad): '{codigo_original}' - será filtrado")
                        partida['codigo'] = ''  # Marcar como inválido

                if partidas_corregidas > 0:
                    logger.info(f"🔧 {partidas_corregidas} código(s) de partida corregidos (unidad removida)")

                # 🔍 VALIDACIÓN ADICIONAL: Detectar códigos con palabras descriptivas pegadas
                # Palabras descriptivas comunes que NO deben estar en códigos
                palabras_descriptivas = [
                    'SUMINISTRO', 'INSTALACION', 'INSTALACIÓN', 'DEMOLICION', 'DEMOLICIÓN',
                    'LEVANTAMIENTO', 'RETIRADA', 'MONTAJE', 'DESMONTAJE', 'COLOCACION', 'COLOCACIÓN',
                    'EXCAVACION', 'EXCAVACIÓN', 'RELLENO', 'COMPACTACION', 'COMPACTACIÓN',
                    'HORMIGON', 'HORMIGÓN', 'PAVIMENTO', 'SOLERA', 'ACERA', 'BORDILLO',
                    'ALQUILER', 'EQUIPO', 'MAQUINARIA', 'MATERIAL', 'TRANSPORTE'
                ]

                codigos_corregidos_descriptivos = 0
                for partida in resultado.get('partidas', []):
                    codigo = partida.get('codigo', '')

                    # Buscar si el código contiene alguna palabra descriptiva
                    for palabra in palabras_descriptivas:
                        if palabra in codigo.upper():
                            # Encontrar dónde empieza la palabra descriptiva
                            idx = codigo.upper().find(palabra)
                            if idx > 0:
                                # Truncar el código antes de la palabra descriptiva
                                codigo_corregido = codigo[:idx]

                                # Verificar que el código resultante es válido (mínimo 5 caracteres alfanuméricos)
                                if len(codigo_corregido) >= 5 and any(c.isdigit() for c in codigo_corregido):
                                    partida['codigo'] = codigo_corregido
                                    codigos_corregidos_descriptivos += 1
                                    logger.info(f"🔧 Código con descripción pegada corregido: '{codigo}' → '{codigo_corregido}'")
                                    break

                if codigos_corregidos_descriptivos > 0:
                    logger.info(f"🔧 {codigos_corregidos_descriptivos} código(s) con palabras descriptivas pegadas corregidos")

                # 🧹 LIMPIEZA: Deduplicar partidas
                partidas_originales = len(resultado.get('partidas', []))

                # NOTA: NO filtramos por subcapitulo_codigo porque ya enviamos al LLM
                # solo el texto de la sección específica solicitada.
                # Todo lo que devuelva el LLM pertenece a esa sección.

                # Deduplicar por código de partida (mantener primera ocurrencia)
                # Y VALIDAR que los códigos sean válidos (formato m23... o similares)
                partidas_unicas = {}
                partidas_invalidas = []

                import re
                # Patrón para códigos válidos: m23... o patrones alfanuméricos comunes de presupuestos
                # Excluir códigos que parezcan subcapítulos (XX.XX.XX) o simples letras/números
                patron_valido = re.compile(r'^[a-zA-Z0-9]{3,}[a-zA-Z0-9._-]*$')
                patron_subcapitulo = re.compile(r'^\d{2}\.\d{2}(\.\d{2})?(\.\d{2})?$')

                for partida in resultado.get('partidas', []):
                    codigo = partida.get('codigo', '')
                    importe = partida.get('importe', 0)

                    # Validar formato de código
                    if not codigo:
                        partidas_invalidas.append({'codigo': codigo, 'razon': 'código vacío'})
                        continue

                    # CRÍTICO: Rechazar palabras comunes que NO son códigos de partida
                    # Estos son headers de tabla o palabras descriptivas
                    palabras_prohibidas = ['ORDEN', 'CODIGO', 'CÓDIGO', 'RESUMEN', 'CANTIDAD', 'PRECIO', 'IMPORTE',
                                          'UNIDAD', 'UD', 'TOTAL', 'SUBTOTAL', 'CAPITULO', 'CAPÍTULO',
                                          'SUBCAPITULO', 'SUBCAPÍTULO', 'APARTADO', 'FOM', 'NTE', 'RD']
                    if codigo.upper() in palabras_prohibidas:
                        partidas_invalidas.append({'codigo': codigo, 'razon': 'palabra prohibida (no es código)'})
                        logger.warning(f"⚠️ Código rechazado (palabra prohibida): {codigo}")
                        continue

                    # CRÍTICO: Rechazar códigos que contienen solo letras sin números
                    # Los códigos válidos siempre tienen números (ej: DEM06, U01AB100)
                    if not any(c.isdigit() for c in codigo):
                        partidas_invalidas.append({'codigo': codigo, 'razon': 'no contiene números'})
                        logger.warning(f"⚠️ Código rechazado (sin números): {codigo}")
                        continue

                    # CRÍTICO: Rechazar partidas con importe 0
                    # Una partida válida siempre tiene importe > 0
                    if importe == 0 or importe is None:
                        partidas_invalidas.append({'codigo': codigo, 'razon': 'importe es 0'})
                        logger.warning(f"⚠️ Partida rechazada (importe 0): {codigo}")
                        continue

                    # Rechazar códigos que parezcan subcapítulos
                    if patron_subcapitulo.match(codigo):
                        partidas_invalidas.append({'codigo': codigo, 'razon': 'parece subcapítulo'})
                        logger.warning(f"⚠️ Código rechazado (parece subcapítulo): {codigo}")
                        continue

                    # Rechazar códigos muy cortos o solo letras/números simples
                    if len(codigo) <= 2 or codigo in ['d', 'a', 'b', 'c', '1', '2']:
                        partidas_invalidas.append({'codigo': codigo, 'razon': 'código inválido'})
                        logger.warning(f"⚠️ Código rechazado (inválido): {codigo}")
                        continue

                    # CRÍTICO: Verificar que el último carácter sea un número
                    # Los códigos de partida válidos terminan siempre en número (ej: DEM06, U01AB100, m23U01BP010)
                    # Si termina en letra, probablemente es parte de la unidad mal extraída
                    if not codigo[-1].isdigit():
                        partidas_invalidas.append({'codigo': codigo, 'razon': 'no termina en número'})
                        logger.warning(f"⚠️ Código rechazado (no termina en número): {codigo}")
                        continue

                    # CRÍTICO: Verificar que no termine con unidades pegadas (m2, m3, ml, ud, etc.)
                    # Patrón: letras + número al final (ej: "m2", "m3", "ml", "ud")
                    # Casos problemáticos: "DEM06m2", "U01AB100ud", "m23U01BP010m2"
                    patron_unidad_pegada = re.compile(r'[a-zA-Z]{1,2}\d$')
                    if patron_unidad_pegada.search(codigo):
                        # Verificar si los últimos 2-3 caracteres son una unidad conocida
                        ultimos_2 = codigo[-2:].lower()
                        ultimos_3 = codigo[-3:].lower()
                        unidades_conocidas = ['m2', 'm3', 'ml', 'ud', 'uf', 'pa', 'kg']
                        if ultimos_2 in unidades_conocidas or ultimos_3 in unidades_conocidas:
                            partidas_invalidas.append({'codigo': codigo, 'razon': 'termina con unidad pegada'})
                            logger.warning(f"⚠️ Código rechazado (unidad pegada al final): {codigo}")
                            continue

                    # Validar patrón básico
                    if not patron_valido.match(codigo):
                        partidas_invalidas.append({'codigo': codigo, 'razon': 'formato incorrecto'})
                        logger.warning(f"⚠️ Código rechazado (formato incorrecto): {codigo}")
                        continue

                    # Si pasó todas las validaciones, agregar si no está duplicado
                    if codigo not in partidas_unicas:
                        partidas_unicas[codigo] = partida

                resultado['partidas'] = list(partidas_unicas.values())

                if partidas_invalidas:
                    logger.warning(f"⚠️ Se rechazaron {len(partidas_invalidas)} partidas con códigos inválidos")
                    for inv in partidas_invalidas[:5]:  # Mostrar primeras 5
                        logger.warning(f"   - {inv['codigo']}: {inv['razon']}")
                partidas_finales = len(resultado['partidas'])

                # Actualizar totales
                resultado['num_partidas'] = partidas_finales
                resultado['total_extraido'] = sum(p.get('importe', 0) for p in resultado['partidas'])

                # Log de limpieza
                if partidas_originales != partidas_finales:
                    logger.warning(f"  🧹 Limpieza: {partidas_originales} → {partidas_finales} partidas (eliminados {partidas_originales - partidas_finales} duplicados/extras)")

                # Agregar metadatos
                elapsed_time = time.time() - start_time
                resultado['tiempo_procesamiento'] = elapsed_time
                resultado['success'] = True
                resultado['error'] = None
                resultado['raw_file'] = raw_file
                resultado['partidas_originales'] = partidas_originales

                logger.info(f"✓ Extracción completada en {elapsed_time:.2f}s")
                logger.info(f"  Partidas extraídas: {resultado.get('num_partidas', 0)}")
                logger.info(f"  Total: {resultado.get('total_extraido', 0):.2f} €")

                return resultado

        except httpx.HTTPStatusError as e:
            logger.error(f"Error HTTP: {e.response.status_code} - {e.response.text}")
            return {
                "capitulo_codigo": capitulo['codigo'],
                "partidas": [],
                "total_extraido": 0,
                "num_partidas": 0,
                "success": False,
                "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"
            }
        except json.JSONDecodeError as e:
            logger.error(f"Error parseando JSON: {e}")
            logger.error(f"Respuesta raw (primeros 500 caracteres): {content[:500]}...")

            # Guardar respuesta completa para análisis
            subcaps_str = '_'.join(subcapitulos_filtrados[:3]) if subcapitulos_filtrados else 'all'
            debug_file = f"logs/TEMP_BORRAR/error_response_{capitulo['codigo']}_{subcaps_str}_{int(time.time())}_BORRAR.json"
            try:
                os.makedirs('logs/TEMP_BORRAR', exist_ok=True)
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.info(f"📁 Respuesta de error guardada en: {debug_file}")
                logger.info(f"📊 Tamaño de respuesta: {len(content)} caracteres")
            except Exception as save_error:
                logger.error(f"Error guardando debug file: {save_error}")

            return {
                "capitulo_codigo": capitulo['codigo'],
                "partidas": [],
                "total_extraido": 0,
                "num_partidas": 0,
                "success": False,
                "error": f"JSON parsing error: {str(e)}",
                "debug_file": debug_file if os.path.exists(debug_file) else None
            }
        except Exception as e:
            logger.error(f"Error extrayendo partidas: {e}")
            return {
                "capitulo_codigo": capitulo['codigo'],
                "partidas": [],
                "total_extraido": 0,
                "num_partidas": 0,
                "success": False,
                "error": str(e)
            }

    def validar_totales(self, total_esperado: float, total_extraido: float, tolerancia: float = 0.02) -> Dict:
        """
        Valida que los totales cuadren dentro de una tolerancia

        Args:
            total_esperado: Total del capítulo según estructura
            total_extraido: Total sumado de partidas extraídas
            tolerancia: Tolerancia permitida (0.02 = 2%)

        Returns:
            Dict con validación:
            {
                "valido": True/False,
                "diferencia": 125.25,
                "diferencia_porcentual": 0.025,
                "mensaje": "..."
            }
        """
        diferencia = abs(total_esperado - total_extraido)
        diferencia_pct = (diferencia / total_esperado) if total_esperado > 0 else 0

        valido = diferencia_pct <= tolerancia

        return {
            "valido": valido,
            "diferencia": round(diferencia, 2),
            "diferencia_porcentual": round(diferencia_pct, 4),
            "mensaje": f"Diferencia: {diferencia:.2f}€ ({diferencia_pct*100:.2f}%)"
        }


# Función helper para uso simple
async def extraer_partidas_de_capitulo(pdf_path: str, capitulo: Dict) -> Dict:
    """
    Extrae partidas de un capítulo específico

    Args:
        pdf_path: Ruta al archivo PDF
        capitulo: Dict con código, nombre, total y subcapítulos

    Returns:
        Dict con partidas extraídas y metadatos
    """
    agent = PartidaExtractionAgent()
    return await agent.extraer_partidas_capitulo(pdf_path, capitulo)


if __name__ == "__main__":
    import asyncio

    # Test
    async def test():
        pdf_path = "/Volumes/DATOS_IA/G_Drive_LuzIA/PRUEBAS/PLIEGOS/PRESUPUESTOS PARCIALES NAVAS DE TOLOSA.pdf"

        # Capítulo de ejemplo
        capitulo = {
            "codigo": "01",
            "nombre": "FASE 2",
            "total": 500000.0,
            "subcapitulos": [
                {
                    "codigo": "01.01",
                    "nombre": "LEVANTANDO DE ELEMENTOS EN SUPERFICIE",
                    "subcapitulos": []
                }
            ]
        }

        resultado = await extraer_partidas_de_capitulo(pdf_path, capitulo)
        print(json.dumps(resultado, indent=2, ensure_ascii=False))

    asyncio.run(test())
