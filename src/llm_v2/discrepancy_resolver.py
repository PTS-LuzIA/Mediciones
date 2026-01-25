"""
Agente LLM para resolver discrepancias detectadas en Fase 3.

Este agente recibe un capítulo o subcapítulo con discrepancia y utiliza IA
para extraer las partidas faltantes que explican la diferencia entre el
total del PDF (siempre válido) y el total calculado.

Principio fundamental: El total del PDF es SIEMPRE correcto (Fase 1).
Si hay discrepancia, faltan partidas o hay errores en las partidas extraídas.
"""

import httpx
import base64
import json
import os
from typing import Dict, List, Optional
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)


class DiscrepancyResolver:
    """Agente que usa LLM para resolver discrepancias encontrando partidas faltantes"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: OpenRouter API key
        """
        self.api_key = api_key or os.getenv('OPENROUTER_API_KEY')
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY no encontrada en variables de entorno")

        self.base_url = "https://openrouter.ai/api/v1"
        # Usar mismo modelo que V1 para consistencia
        self.model = "google/gemini-2.5-flash-lite"

    def encode_pdf_page(self, pdf_path: str, page_num: int) -> str:
        """Encode una página específica del PDF como base64"""
        import PyPDF2
        from pdf2image import convert_from_path

        try:
            # Convertir página a imagen
            images = convert_from_path(
                pdf_path,
                first_page=page_num,
                last_page=page_num,
                dpi=150  # Suficiente calidad para lectura
            )

            if not images:
                raise ValueError(f"No se pudo convertir la página {page_num}")

            # Guardar temporalmente y codificar
            import io
            img_byte_arr = io.BytesIO()
            images[0].save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)

            return base64.b64encode(img_byte_arr.read()).decode('utf-8')

        except Exception as e:
            logger.error(f"Error codificando página {page_num}: {e}")
            raise

    def _detectar_codigos_hijos_en_texto(self, texto: str, codigo: str) -> bool:
        """
        Detecta si el texto contiene códigos hijos del código especificado.

        Ejemplo: Si codigo = "03", busca patrones como "03.01", "03.02", etc.
                 Si codigo = "02.12", busca patrones como "02.12.01", "02.12.02", etc.

        Args:
            texto: Texto extraído del PDF
            codigo: Código del capítulo/subcapítulo

        Returns:
            True si encuentra códigos hijos, False si no
        """
        import re

        # Construir patrón para detectar hijos directos
        # Ejemplo: "03" -> buscar "03.XX"
        #          "02.12" -> buscar "02.12.XX"
        patron_hijo = rf'^{re.escape(codigo)}\.\d{{1,2}}\s+[A-ZÁÉÍÓÚÑ]'

        # Buscar en cada línea del texto
        for linea in texto.split('\n'):
            linea_limpia = linea.strip()
            if re.match(patron_hijo, linea_limpia):
                logger.debug(f"✓ Código hijo detectado en texto: '{linea_limpia[:60]}...'")
                return True

        return False

    def _extract_text_from_pdf(self, pdf_path: str, codigo: str, proyecto_id: int = None) -> str:
        """
        Extrae SOLO el texto del subcapítulo específico del PDF.
        Busca desde el código del subcapítulo hasta su línea TOTAL.

        IMPORTANTE: NO usa cache. Siempre extrae de nuevo con el extractor actual
        para garantizar que usa las últimas mejoras (column fix, etc.)
        """
        import re

        try:
            # Extraer TODO el texto del PDF con el extractor actual (sin cache)
            logger.info(f"🔄 Extrayendo texto de '{os.path.basename(pdf_path)}' sin cache (garantiza últimas mejoras)")

            from src.parser_v2.pdf_extractor import PDFExtractor

            extractor = PDFExtractor(pdf_path)
            datos = extractor.extraer_todo()
            all_lines = datos.get('all_lines', [])

            if not all_lines:
                logger.error(f"❌ No se pudo extraer texto del PDF: {pdf_path}")
                return ""

            logger.info(f"✓ Extraídas {len(all_lines)} líneas del PDF (extractor v2 actualizado)")

            # Buscar inicio del subcapítulo (código + nombre en la misma línea)
            dentro_seccion = False
            lineas_seccion = []

            codigo_pattern = re.escape(codigo)  # Escapar puntos en el código
            logger.debug(f"Buscando código: '{codigo}' con pattern: '^{codigo_pattern}\\s*[A-Z]'")

            for idx, linea in enumerate(all_lines):
                linea_limpia = linea.strip()

                # Debug: Log líneas que contienen el código
                if codigo in linea_limpia:
                    logger.debug(f"Línea {idx} contiene código '{codigo}': '{linea_limpia}'")
                    logger.debug(f"  Repr: {repr(linea_limpia)}")
                    pattern_test = rf'^{codigo_pattern}\s*[A-Z]'
                    logger.debug(f"  Match result: {re.match(pattern_test, linea_limpia)}")

                # Detectar inicio del subcapítulo (con o sin espacio después del código)
                if re.match(rf'^{codigo_pattern}\s*[A-ZÁÉÍÓÚÑ]', linea_limpia):
                    dentro_seccion = True
                    lineas_seccion.append(linea_limpia)
                    logger.info(f"✓ Inicio de sección {codigo} encontrado en línea {idx}")
                    continue

                if dentro_seccion:
                    lineas_seccion.append(linea_limpia)

                    # Detectar fin por línea TOTAL
                    if linea_limpia.startswith('TOTAL') or linea_limpia.startswith('Total'):
                        # Verificar si el TOTAL es del subcapítulo correcto
                        if codigo in linea_limpia or not re.search(r'\d{2}\.\d{2}', linea_limpia):
                            logger.debug(f"Fin de sección {codigo} detectado por TOTAL")
                            break

                    # Detectar fin por otro subcapítulo (MEJORADO: distinguir hermanos vs hijos)
                    # Ejemplo: Si buscamos 02.08.02:
                    # - 02.08.02.01 es HIJO (continuar capturando)
                    # - 02.08.03 es HERMANO (detener)
                    # - 02.09 es TÍO/SUPERIOR (detener)
                    # IMPORTANTE: Debe seguir el patrón código + espacio + mayúscula (no números + coma = importe)
                    match_codigo = re.match(r'^(\d{2}(?:\.\d{2})+)\s+[A-ZÁÉÍÓÚÑ]', linea_limpia)
                    if match_codigo:
                        codigo_detectado = match_codigo.group(1)

                        if codigo_detectado != codigo:
                            # Determinar nivel del código buscado y del detectado
                            partes_buscado = codigo.split('.')
                            partes_detectado = codigo_detectado.split('.')
                            nivel_buscado = len(partes_buscado)
                            nivel_detectado = len(partes_detectado)

                            # Verificar si es hijo directo (un nivel más profundo Y comienza con mismo prefijo)
                            es_hijo = (nivel_detectado == nivel_buscado + 1 and
                                      codigo_detectado.startswith(codigo + '.'))

                            if es_hijo:
                                # Es un hijo (sub-subcapítulo), CONTINUAR capturando
                                logger.debug(f"Código detectado {codigo_detectado} es hijo de {codigo}, continuando...")
                            else:
                                # Es hermano o superior, DETENER
                                logger.debug(f"Fin de sección {codigo} detectado por código hermano/superior {codigo_detectado}")
                                break

            if not lineas_seccion:
                logger.warning(f"No se encontró el código {codigo} en el PDF")
                return ""

            # Unir líneas
            full_text = '\n'.join(lineas_seccion)

            # TRUNCADO INTELIGENTE: Si el texto es muy largo, buscar el TOTAL para cortar
            MAX_CHARS = 100000  # Límite máximo de seguridad (Gemini soporta mucho más)

            if len(full_text) > MAX_CHARS:
                logger.warning(f"⚠️ Texto muy largo ({len(full_text)} caracteres), buscando punto de corte inteligente...")

                # Buscar la última línea con "TOTAL" antes del límite
                lineas_hasta_limite = full_text[:MAX_CHARS].split('\n')

                # Buscar la última aparición de TOTAL
                ultima_linea_total = -1
                for i, linea in enumerate(lineas_hasta_limite):
                    if linea.strip().startswith('TOTAL') or linea.strip().startswith('Total'):
                        ultima_linea_total = i

                if ultima_linea_total > 0:
                    # Cortar en el TOTAL encontrado
                    full_text = '\n'.join(lineas_hasta_limite[:ultima_linea_total + 1])
                    logger.info(f"✓ Texto truncado inteligentemente en línea TOTAL {ultima_linea_total}")
                    logger.info(f"  Texto final: {len(full_text)} caracteres")
                else:
                    # No se encontró TOTAL, cortar por límite de caracteres
                    full_text = full_text[:MAX_CHARS]
                    logger.warning(f"⚠️ No se encontró TOTAL, truncado a {MAX_CHARS} caracteres")

            logger.info(f"  Texto extraído: {len(lineas_seccion)} líneas, {len(full_text)} caracteres")
            return full_text

        except Exception as e:
            logger.error(f"Error extrayendo texto del PDF: {e}")
            return ""

    async def resolver_discrepancia(
        self,
        pdf_path: str,
        elemento: Dict,
        tipo: str,
        partidas_existentes: List[Dict],
        proyecto_id: int = None
    ) -> Dict:
        """
        Resuelve una discrepancia enviando texto del PDF al LLM para encontrar partidas faltantes

        Args:
            pdf_path: Ruta al PDF
            elemento: Dict con {id, codigo, nombre, total, total_calculado}
            tipo: "capitulo" o "subcapitulo"
            partidas_existentes: Lista de partidas ya extraídas
            proyecto_id: ID del proyecto (para reutilizar texto de Fase 2)

        Returns:
            Dict con partidas encontradas y metadatos
        """
        logger.info(f"🤖 Resolviendo discrepancia en {tipo} {elemento['codigo']}")
        logger.info(f"   Total PDF (válido): {elemento['total']} €")
        logger.info(f"   Total calculado: {elemento['total_calculado']} €")
        logger.info(f"   Diferencia: {float(elemento['total']) - float(elemento['total_calculado'])} €")
        logger.info(f"   Partidas existentes: {len(partidas_existentes)}")

        # Extraer texto relevante del PDF (reutilizando texto de Fase 2)
        pdf_text = self._extract_text_from_pdf(pdf_path, elemento['codigo'], proyecto_id)

        if not pdf_text:
            return {
                "success": False,
                "error": f"No se encontró el código {elemento['codigo']} en el PDF",
                "partidas_nuevas": [],
                "num_nuevas": 0,
                "total_nuevas": 0
            }

        # Construir prompt
        prompt = self._construir_prompt(elemento, tipo, partidas_existentes, pdf_text)

        # Guardar prompt para debugging
        import time
        timestamp = int(time.time())
        logs_dir = "logs/llm_discrepancias"
        os.makedirs(logs_dir, exist_ok=True)

        prompt_file = f"{logs_dir}/prompt_{tipo}_{elemento['codigo'].replace('.', '_')}_{timestamp}.txt"
        try:
            with open(prompt_file, 'w', encoding='utf-8') as f:
                f.write(prompt)
            logger.info(f"💾 Prompt guardado: {prompt_file}")
        except Exception as e:
            logger.warning(f"No se pudo guardar prompt: {e}")

        try:
            # Llamar al LLM solo con texto
            temperature = 0.0
            logger.info(f"🤖 Llamando a LLM con temperatura={temperature} (determinismo máximo)")

            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": temperature,  # Máxima determinismo - mismo prompt = misma respuesta
                        "response_format": {"type": "json_object"}
                    }
                )

                if response.status_code != 200:
                    error_text = response.text[:500]
                    logger.error(f"Error en LLM: {response.status_code} - {error_text}")
                    raise Exception(f"Error del LLM: {response.status_code}")

                result = response.json()
                content = result['choices'][0]['message']['content']

                # Guardar respuesta RAW del LLM ANTES de parsear para debugging
                raw_response_file = f"{logs_dir}/raw_response_{tipo}_{elemento['codigo'].replace('.', '_')}_{timestamp}.txt"
                try:
                    with open(raw_response_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    logger.info(f"💾 Respuesta RAW LLM guardada: {raw_response_file}")
                except Exception as e:
                    logger.warning(f"No se pudo guardar respuesta RAW: {e}")

                # Parsear respuesta JSON
                partidas_llm = json.loads(content)

                # Guardar respuesta parseada del LLM para debugging
                response_file = f"{logs_dir}/response_{tipo}_{elemento['codigo'].replace('.', '_')}_{timestamp}.json"
                try:
                    with open(response_file, 'w', encoding='utf-8') as f:
                        json.dump(partidas_llm, f, indent=2, ensure_ascii=False)
                    logger.info(f"💾 Respuesta LLM guardada: {response_file}")
                except Exception as e:
                    logger.warning(f"No se pudo guardar respuesta: {e}")

                # FILTRAR DUPLICADOS POST-LLM
                # El LLM puede devolver partidas que ya existen, filtrarlas ANTES de procesar
                codigos_existentes = set(p['codigo'] for p in partidas_existentes)
                partidas_faltantes_raw = partidas_llm.get('partidas_faltantes', [])

                partidas_sin_duplicar = [
                    p for p in partidas_faltantes_raw
                    if p.get('codigo') not in codigos_existentes
                ]

                logger.info(f"📊 LLM devolvió: {len(partidas_faltantes_raw)} partidas")
                if len(partidas_faltantes_raw) != len(partidas_sin_duplicar):
                    duplicados = len(partidas_faltantes_raw) - len(partidas_sin_duplicar)
                    logger.warning(f"🧹 Filtrados {duplicados} duplicados que ya existían")
                    duplicados_codigos = [p['codigo'] for p in partidas_faltantes_raw if p.get('codigo') in codigos_existentes]
                    logger.warning(f"   Códigos duplicados filtrados: {duplicados_codigos[:10]}")
                logger.info(f"✓ Después de filtrar: {len(partidas_sin_duplicar)} partidas nuevas")

                # Validar y procesar solo las partidas ya filtradas
                partidas_nuevas = self._procesar_partidas_llm(
                    {'partidas_faltantes': partidas_sin_duplicar},
                    elemento
                )

                return {
                    "success": True,
                    "partidas_nuevas": partidas_nuevas,
                    "num_nuevas": len(partidas_nuevas),
                    "total_nuevas": sum(p['importe'] for p in partidas_nuevas)
                }

        except Exception as e:
            logger.error(f"Error resolviendo discrepancia: {e}")
            return {
                "success": False,
                "error": str(e),
                "partidas_nuevas": [],
                "num_nuevas": 0,
                "total_nuevas": 0
            }

    def _encode_pdf(self, pdf_path: str) -> str:
        """Codifica el PDF completo en base64"""
        with open(pdf_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')

    def _construir_prompt(self, elemento: Dict, tipo: str, partidas_existentes: List[Dict], pdf_text: str) -> str:
        """Construye el prompt para el LLM"""

        # Listar códigos de partidas existentes
        codigos_existentes = [p['codigo'] for p in partidas_existentes]

        prompt = f"""Eres un experto en análisis de presupuestos de construcción.

TAREA:
Analiza el {tipo} "{elemento['codigo']} - {elemento['nombre']}" y encuentra las partidas FALTANTES.

CONTEXTO IMPORTANTE:
- Total del PDF (CORRECTO): {elemento['total']} €
- Total calculado (partidas actuales): {elemento['total_calculado']} €
- Diferencia: {float(elemento['total']) - float(elemento['total_calculado'])} €
- El total del PDF es SIEMPRE el valor correcto
- Faltan partidas que explican la diferencia

PARTIDAS YA EXTRAÍDAS ({len(partidas_existentes)}):
{chr(10).join(f"- {p['codigo']} = {p['importe']} €" for p in partidas_existentes[:20])}
{"... (y más)" if len(partidas_existentes) > 20 else ""}

TEXTO DEL PDF (secciones relevantes):
{pdf_text}

INSTRUCCIONES:
1. Busca en el texto de arriba el {tipo} "{elemento['codigo']}"
2. Identifica TODAS las partidas de ese {tipo}
3. Detecta cuáles NO están en la lista de partidas ya extraídas
4. Extrae SOLO las partidas faltantes con sus datos completos

IMPORTANTE:
- NO incluyas partidas que YA están extraídas (códigos: {', '.join(codigos_existentes[:10])})
- Los códigos de partidas pueden ser de cualquier formato (ej: "01.02.03", "m23U01A010", etc.)
- Extrae: código, unidad, resumen, descripción, cantidad, precio, importe
- El importe debe ser: cantidad × precio

IMPORTANTE - SOBRE DUPLICADOS:
- Si encuentras partidas con el mismo importe/cantidad/precio pero códigos diferentes, probablemente son duplicados
- NO agregues partidas que tengan valores idénticos a las ya extraídas, aunque el código sea ligeramente diferente
- UNIDAD: Extrae SOLO el código de unidad (máximo 10 caracteres):
  * Ejemplos válidos: "ud", "m2", "m3", "kg", "m", "h", "t", "l", "pa"
  * NO extraigas descripciones largas
  * Si la unidad aparece en el texto como "m3 EXCAVACIÓN...", extrae solo "m3"
  * Si no encuentras una unidad válida, usa "ud" por defecto
- RESUMEN: Título corto de la partida (máximo 80 caracteres, en mayúsculas)
  * Ejemplo: "EXCAVACIÓN EN ZANJA TERRENOS COMPACTOS"
- DESCRIPCIÓN: Texto técnico completo de la partida (puede tener varias líneas)
  * Ejemplo: "Excavación en zanjas, en terrenos compactos, por medios mecánicos..."
  * Une todas las líneas de descripción en un solo texto
  * Limpia guiones de separación de palabras (ej: "me- dios" → "medios")
- Si no encuentras partidas faltantes, devuelve un array vacío

Responde SOLO en JSON válido:
{{
  "partidas_faltantes": [
    {{
      "codigo": "01.02.03",
      "unidad": "m2",
      "resumen": "EXCAVACIÓN EN ZANJA TERRENOS COMPACTOS",
      "descripcion": "Excavación en zanjas, en terrenos compactos, por medios mecánicos, incluso perfilado de fondos y laterales, extracción de tierras fuera de la excavación, y carga sobre camión o contenedor.",
      "cantidad": 150.5,
      "precio": 12.50,
      "importe": 1881.25
    }}
  ]
}}
"""
        return prompt

    def _normalizar_unidad(self, unidad: str) -> str:
        """
        Normaliza la unidad para asegurar que sea válida y no exceda 20 caracteres.

        Args:
            unidad: Unidad raw del LLM

        Returns:
            Unidad normalizada (máximo 20 caracteres)
        """
        if not unidad or not isinstance(unidad, str):
            return "X"

        # Limpiar espacios
        unidad = unidad.strip()

        # Si es demasiado larga (probablemente una descripción), intentar extraer la unidad
        if len(unidad) > 20:
            # Intentar extraer unidades comunes al inicio
            unidades_comunes = ['m3', 'm2', 'ml', 'ud', 'kg', 'pa', 'h', 'm', 't', 'l', 'uR', 'u20R']
            for u in unidades_comunes:
                if unidad.lower().startswith(u.lower()):
                    logger.warning(f"Unidad truncada: '{unidad}' -> '{u}'")
                    return u

            # Si no encontramos una unidad común, usar "X"
            logger.warning(f"Unidad inválida (demasiado larga): '{unidad}' -> 'X'")
            return "X"

        # Si está vacía
        if not unidad:
            return "X"

        return unidad

    def _procesar_partidas_llm(self, respuesta_llm: Dict, elemento: Dict) -> List[Dict]:
        """Procesa y valida las partidas devueltas por el LLM"""
        partidas_nuevas = []

        for partida in respuesta_llm.get('partidas_faltantes', []):
            # Validar campos obligatorios
            if not all(k in partida for k in ['codigo', 'importe']):
                logger.warning(f"Partida inválida (falta código o importe): {partida}")
                continue

            # NOTA: NO validamos que el código empiece con elemento['codigo']
            # porque muchos presupuestos usan códigos internos (ej: m23U01A010)
            # que no siguen la jerarquía numérica. Confiamos en que el LLM
            # identifica correctamente las partidas del capítulo/subcapítulo solicitado.

            # Normalizar unidad
            unidad_raw = partida.get('unidad', 'ud')
            unidad = self._normalizar_unidad(unidad_raw)

            # NUEVO: Extraer resumen y descripción (SOLUCIÓN 5)
            resumen = partida.get('resumen', '').strip()
            descripcion = partida.get('descripcion', '').strip()

            # Normalizar partida
            partida_normalizada = {
                'codigo': partida['codigo'],
                'unidad': unidad,
                'resumen': resumen,  # NUEVO
                'descripcion': descripcion,  # NUEVO
                'cantidad': float(partida.get('cantidad', 0)),
                'precio': float(partida.get('precio', 0)),
                'importe': float(partida['importe'])
            }

            partidas_nuevas.append(partida_normalizada)

        return partidas_nuevas


if __name__ == "__main__":
    import asyncio

    async def test():
        resolver = DiscrepancyResolver()

        # Test con ejemplo
        resultado = await resolver.resolver_discrepancia(
            pdf_path="/path/to/test.pdf",
            elemento={
                'id': 1,
                'codigo': '01.04',
                'nombre': 'MOVIMIENTO DE TIERRAS',
                'total': 15430.50,
                'total_calculado': 15200.00
            },
            tipo='subcapitulo',
            partidas_existentes=[
                {'codigo': '01.04.01', 'resumen': 'Excavación', 'importe': 5000},
                {'codigo': '01.04.02', 'resumen': 'Relleno', 'importe': 10200}
            ]
        )

        print(json.dumps(resultado, indent=2, ensure_ascii=False))

    asyncio.run(test())
