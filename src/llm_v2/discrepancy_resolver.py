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

    def _extract_text_from_pdf(self, pdf_path: str, codigo: str, proyecto_id: int = None) -> str:
        """
        Extrae SOLO el texto del subcapítulo específico del PDF.
        Busca desde el código del subcapítulo hasta su línea TOTAL.

        IMPORTANTE: Reutiliza el texto extraído en Fase 2 (logs/extracted_full_text_*.txt)
        en lugar de volver a procesar el PDF.
        """
        import re
        import glob

        try:
            # PRIORIDAD 1: Buscar texto extraído en Fase 2
            nombre_pdf_completo = os.path.basename(pdf_path).replace('.pdf', '')

            # IMPORTANTE: El PDF guardado tiene formato "{user_id}_{nombre_original}.pdf"
            # pero el archivo de texto no tiene ese prefijo. Necesitamos quitarlo.
            # Ejemplo: "7_PRESUPUESTOS.pdf" -> nombre_pdf = "PRESUPUESTOS"
            if '_' in nombre_pdf_completo:
                # Quitar el prefijo "{user_id}_" si existe
                partes = nombre_pdf_completo.split('_', 1)
                if partes[0].isdigit():  # Verificar que sea un ID numérico
                    nombre_pdf = partes[1]
                else:
                    nombre_pdf = nombre_pdf_completo
            else:
                nombre_pdf = nombre_pdf_completo

            # Buscar patrón: logs/extracted_full_text_{proyecto_id}_{nombre_pdf}.txt
            if proyecto_id:
                texto_fase2 = f"logs/extracted_full_text_{proyecto_id}_{nombre_pdf}.txt"
                if os.path.exists(texto_fase2):
                    logger.info(f"✓ Reutilizando texto de Fase 2: {texto_fase2}")
                    with open(texto_fase2, 'r', encoding='utf-8') as f:
                        all_lines = [line.rstrip('\n') for line in f.readlines()]
                else:
                    # Buscar sin proyecto_id
                    patron = f"logs/extracted_full_text_*_{nombre_pdf}.txt"
                    archivos = glob.glob(patron)
                    if archivos:
                        texto_fase2 = archivos[0]
                        logger.info(f"✓ Reutilizando texto de Fase 2: {texto_fase2}")
                        with open(texto_fase2, 'r', encoding='utf-8') as f:
                            all_lines = [line.rstrip('\n') for line in f.readlines()]
                    else:
                        logger.warning(f"⚠️ No se encontró texto de Fase 2. Esto no debería pasar.")
                        return ""
            else:
                # Sin proyecto_id, buscar cualquier archivo
                patron = f"logs/extracted_full_text_*_{nombre_pdf}.txt"
                archivos = glob.glob(patron)
                if archivos:
                    texto_fase2 = archivos[0]
                    logger.info(f"✓ Reutilizando texto de Fase 2: {texto_fase2}")
                    with open(texto_fase2, 'r', encoding='utf-8') as f:
                        all_lines = [line.rstrip('\n') for line in f.readlines()]
                else:
                    logger.warning(f"⚠️ No se encontró texto de Fase 2. Esto no debería pasar.")
                    return ""

            # Buscar inicio del subcapítulo (código + nombre en la misma línea)
            dentro_seccion = False
            lineas_seccion = []

            codigo_pattern = re.escape(codigo)  # Escapar puntos en el código
            logger.debug(f"Buscando código: '{codigo}' con pattern: '^{codigo_pattern}\\s+[A-Z]'")

            for idx, linea in enumerate(all_lines):
                linea_limpia = linea.strip()

                # Debug: Log líneas que contienen el código
                if codigo in linea_limpia:
                    logger.debug(f"Línea {idx} contiene código '{codigo}': '{linea_limpia}'")
                    logger.debug(f"  Repr: {repr(linea_limpia)}")
                    pattern_test = rf'^{codigo_pattern}\s+[A-Z]'
                    logger.debug(f"  Match result: {re.match(pattern_test, linea_limpia)}")

                # Detectar inicio del subcapítulo
                if re.match(rf'^{codigo_pattern}\s+[A-Z]', linea_limpia):
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

                    # Detectar fin por otro subcapítulo del mismo nivel o superior
                    if re.match(r'^\d{2}\.\d{2}', linea_limpia):
                        # Es otro subcapítulo
                        codigo_detectado = re.match(r'^(\d{2}\.\d{2})', linea_limpia).group(1)
                        if codigo_detectado != codigo:
                            logger.debug(f"Fin de sección {codigo} detectado por nuevo subcapítulo {codigo_detectado}")
                            break

            if not lineas_seccion:
                logger.warning(f"No se encontró el código {codigo} en el PDF")
                return ""

            # Unir líneas
            full_text = '\n'.join(lineas_seccion)

            # Limitar tamaño
            if len(full_text) > 20000:  # ~5k tokens - suficiente para un subcapítulo
                full_text = full_text[:20000]
                logger.warning(f"Texto truncado a 20k caracteres")

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
                        "temperature": 0.1,
                        "response_format": {"type": "json_object"}
                    }
                )

                if response.status_code != 200:
                    error_text = response.text[:500]
                    logger.error(f"Error en LLM: {response.status_code} - {error_text}")
                    raise Exception(f"Error del LLM: {response.status_code}")

                result = response.json()
                content = result['choices'][0]['message']['content']

                # Parsear respuesta JSON
                partidas_llm = json.loads(content)

                # Guardar respuesta del LLM para debugging
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
- Extrae: código, unidad, cantidad, precio, importe
- El importe debe ser: cantidad × precio
- Si no encuentras partidas faltantes, devuelve un array vacío

Responde SOLO en JSON válido:
{{
  "partidas_faltantes": [
    {{
      "codigo": "01.02.03",
      "unidad": "m2",
      "cantidad": 150.5,
      "precio": 12.50,
      "importe": 1881.25
    }}
  ]
}}
"""
        return prompt

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

            # Normalizar partida
            partida_normalizada = {
                'codigo': partida['codigo'],
                'unidad': partida.get('unidad', 'ud'),
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
