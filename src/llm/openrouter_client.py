"""
Cliente para interactuar con OpenRouter API usando Gemini 2.5 Flash Lite.
Procesa PDFs de presupuestos y extrae estructura jerárquica.
"""

import httpx
import base64
import json
import os
import time
from pathlib import Path
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class OpenRouterClient:
    """Cliente para OpenRouter API con Gemini 2.5 Flash Lite"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: API key de OpenRouter (si no se provee, se lee de OPENROUTER_API_KEY env var)
        """
        self.api_key = api_key or os.getenv('OPENROUTER_API_KEY')
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY no encontrada en variables de entorno")

        self.base_url = "https://openrouter.ai/api/v1"
        self.model = "google/gemini-2.5-flash-lite"  # Modelo a usar - 1M tokens context

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

    def crear_prompt_extraccion(self, desde_partida: Optional[str] = None) -> str:
        """
        Crea el prompt para extraer estructura del presupuesto con formato FLAT

        Args:
            desde_partida: Código de partida desde la cual continuar (para procesamiento por partes)

        Returns:
            String con el prompt completo
        """
        continuacion = f"""

IMPORTANTE: Extrae SOLO las partidas que vienen DESPUÉS del código "{desde_partida}" (NO incluir esta partida).
Continúa desde donde te quedaste.""" if desde_partida else ""

        return f"""Extrae TODAS las partidas del presupuesto del PDF en formato JSON de LISTA PLANA.
{continuacion}

📋 ESTRUCTURA DEL PRESUPUESTO (por numeración):

La jerarquía se identifica por el NÚMERO DE DÍGITOS/PUNTOS en el código:
- CAPÍTULO: 2 dígitos (ej: "01", "02", "03")
- SUBCAPÍTULO NIVEL 1: formato XX.XX (ej: "01.01", "01.02")
- SUBCAPÍTULO NIVEL 2: formato XX.XX.XX (ej: "01.01.01")
- SUBCAPÍTULO NIVEL 3: formato XX.XX.XX.XX (ej: "01.01.01.01")
- Y así sucesivamente hasta 6 niveles
- PARTIDA: código alfanumérico (ej: "m23U01C190", "E28RA140")

⚠️ REGLAS CRÍTICAS:

1. UNIDADES: Copia EXACTAMENTE la unidad del PDF (m3, m2, Ud, kg, t, ml, etc.)
2. NÚMEROS: Usa punto decimal (1.50 no 1,50). Respeta los decimales del PDF.
3. RESUMEN: Máximo 80 caracteres, en MAYÚSCULAS como aparece en el PDF.
4. DESCRIPCIÓN: Solo incluir si aporta información crítica (omitir en mayoría de casos).
5. JERARQUÍA: Identifica correctamente capítulos y subcapítulos por el formato de numeración.
6. CONFIANZA: 0.95-1.0 si datos claros, 0.7-0.9 si hay dudas, <0.7 si muy incierto.

📊 FORMATO JSON REQUERIDO (LISTA PLANA):

{{
  "nombre": "Nombre completo del proyecto",
  "descripcion": "Descripción breve",
  "confianza_general": 0.95,
  "notas_ia": "Última partida: CODIGO_ULTIMA, Total partidas: NUMERO",
  "partidas": [
    {{
      "codigo": "m23U01C190",
      "unidad": "Ud",
      "resumen": "DESMONTAJE DE PAPELERA",
      "descripcion": "",
      "cantidad": 9.00,
      "precio": 26.89,
      "importe": 242.01,
      "confianza": 0.99,
      "notas": "",
      "capitulo": "01",
      "capitulo_nombre": "FASE 2",
      "subcapitulo_1": "01.01",
      "subcapitulo_1_nombre": "LEVANTANDO DE ELEMENTOS",
      "subcapitulo_2": null,
      "subcapitulo_2_nombre": null,
      "subcapitulo_3": null,
      "subcapitulo_3_nombre": null,
      "subcapitulo_4": null,
      "subcapitulo_4_nombre": null,
      "subcapitulo_5": null,
      "subcapitulo_5_nombre": null
    }}
  ]
}}

✅ VALIDACIÓN:
- Si cantidad × precio ≠ importe (±5% tolerancia), anotar en "notas"
- Si falta dato, usar null y bajar confianza
- Si unidad es dudosa, anotar en "notas"

🎯 OBJETIVO: Extrae el MÁXIMO de partidas posible. El modelo cerrará automáticamente cuando alcance su límite. Asegúrate de cerrar correctamente el JSON.

Devuelve SOLO el JSON, sin texto adicional."""

    async def procesar_pdf(self, pdf_path: str, desde_partida: Optional[str] = None) -> Dict:
        """
        Procesa un PDF completo con Gemini vía OpenRouter

        Args:
            pdf_path: Ruta al archivo PDF
            desde_partida: Código de partida desde donde continuar (para procesamiento incremental)

        Returns:
            Dict con la estructura extraída
        """
        start_time = time.time()
        if desde_partida:
            logger.info(f"Continuando procesamiento desde partida {desde_partida}: {pdf_path}")
        else:
            logger.info(f"Iniciando procesamiento con IA: {pdf_path}")

        # Leer el PDF y convertir a base64
        pdf_base64 = self.encode_pdf_base64(pdf_path)

        # Preparar el mensaje con el PDF
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": self.crear_prompt_extraccion(desde_partida)
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:application/pdf;base64,{pdf_base64}"
                        }
                    }
                ]
            }
        ]

        # Preparar la petición
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,  # Baja temperatura para mayor precisión
            # SIN max_tokens - dejamos que use todo lo disponible (~65K tokens)
            "response_format": {"type": "json_object"}  # Forzar respuesta JSON
        }

        # Hacer la petición
        async with httpx.AsyncClient(timeout=600.0) as client:  # 10 minutos timeout
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()

                result = response.json()
                content = result['choices'][0]['message']['content']

                # Verificar si el modelo indicó que se detuvo intencionalmente
                finish_reason = result['choices'][0].get('finish_reason', '')
                logger.info(f"Finish reason: {finish_reason}")

                # Parsear el JSON devuelto
                try:
                    estructura = json.loads(content)

                    # Si el modelo se detuvo por límite de tokens pero el JSON es válido,
                    # es porque cerró correctamente
                    if finish_reason == 'length':
                        logger.info("✓ Modelo se detuvo por límite de tokens pero cerró JSON correctamente")

                except json.JSONDecodeError as e:
                    logger.warning(f"JSON incompleto detectado (línea {e.lineno}, columna {e.colno})")
                    logger.info("Aplicando parser progresivo para encontrar último JSON válido...")

                    # GUARDAR respuesta completa para debug (temporal)
                    debug_path = "/tmp/openrouter_response_debug.json"
                    with open(debug_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    logger.info(f"💾 Respuesta completa guardada en: {debug_path}")

                    # SOLUCIÓN 2 MEJORADA: Parser JSON Progresivo con búsqueda de patrones
                    estructura = None
                    content_limpio = content.rstrip()

                    # DIAGNÓSTICO: Tamaño total del contenido
                    logger.info(f"📊 Tamaño total del contenido recibido: {len(content_limpio):,} caracteres")
                    logger.info(f"📊 Posición del error JSON: línea {e.lineno}, columna {e.colno}, char aprox {e.pos if hasattr(e, 'pos') else 'N/A'}")

                    # Buscar el último cierre de partida completo con patrón específico
                    import re
                    # Patrón para estructura FLAT: buscar cierres de partidas completos
                    # En estructura flat, cada partida cierra con: "subcapitulo_5_nombre": null}
                    pattern_partida_cierre = r'"subcapitulo_5_nombre":\s*(?:null|"[^"]*")\s*\}'

                    # Encontrar todas las coincidencias
                    matches = list(re.finditer(pattern_partida_cierre, content_limpio))

                    if matches:
                        logger.info(f"Encontrados {len(matches)} cierres de partidas completos")

                        # Intentar desde el último match hacia atrás
                        for i, match in enumerate(reversed(matches[-100:])):  # Últimas 100 partidas
                            truncate_pos = match.end()
                            truncated = content_limpio[:truncate_pos]

                            # CRÍTICO: Buscar y eliminar coma trailing después del cierre
                            # El patrón es: }\n            },  (cierre + espacios + coma)
                            # Necesitamos eliminar esa coma final antes de cerrar arrays/objetos
                            truncated_stripped = truncated.rstrip()
                            if truncated_stripped.endswith(','):
                                truncated_stripped = truncated_stripped[:-1]

                            # Calcular cierres necesarios
                            depth_array = truncated_stripped.count('[') - truncated_stripped.count(']')
                            depth_object = truncated_stripped.count('{') - truncated_stripped.count('}')

                            # Agregar cierres - alternamos array ] y object } según la estructura jerárquica
                            # La estructura típica es: partidas ] → subcapitulo } → subcapitulos ] → capitulo } → capitulos ] → root }
                            # Por cada array cerrado, normalmente sigue un object
                            closings = '\n'
                            for idx in range(max(depth_array, depth_object)):
                                if idx < depth_array:
                                    closings += '          ]\n'
                                if idx < depth_object:
                                    closings += '        }\n'

                            test_content = truncated_stripped + closings

                            try:
                                test_estructura = json.loads(test_content)
                                estructura = test_estructura
                                logger.info(f"✓ JSON válido encontrado en posición {truncate_pos} (partida {i+1}/{len(matches[-100:])})")
                                break
                            except json.JSONDecodeError as je:
                                # Log cada 10 intentos
                                if i % 10 == 0:
                                    logger.debug(f"Intento {i+1}: pos {truncate_pos}, arrays={depth_array}, objects={depth_object}, error={je.msg[:50]}")
                                continue

                    # Si no funcionó con patrones, intentar búsquedas más agresivas
                    if estructura is None:
                        logger.info("Búsqueda por patrones falló, probando múltiples estrategias...")

                        # Estrategia 1: Buscar hacia atrás con múltiples tamaños de chunk
                        # Buscar en TODO el contenido, no solo 150K
                        for chunk_size in [1000, 500, 200, 100]:
                            logger.info(f"🔍 Probando chunk_size={chunk_size}, rango: {len(content_limpio):,} → 0")
                            intentos_realizados = 0
                            for pos in range(len(content_limpio), 0, -chunk_size):
                                intentos_realizados += 1
                                truncated = content_limpio[:pos]

                                # Eliminar coma trailing
                                truncated_stripped = truncated.rstrip()
                                if truncated_stripped.endswith(','):
                                    truncated_stripped = truncated_stripped[:-1]

                                depth_array = truncated_stripped.count('[') - truncated_stripped.count(']')
                                depth_object = truncated_stripped.count('{') - truncated_stripped.count('}')

                                if depth_array < 0 or depth_object < 0:
                                    continue

                                # Log cada 50 intentos
                                if intentos_realizados % 50 == 0:
                                    logger.debug(f"  Intento {intentos_realizados}: pos={pos:,}, depth_arr={depth_array}, depth_obj={depth_object}")

                                # Agregar cierres correctamente
                                closings = '\n'
                                for idx in range(max(depth_array, depth_object)):
                                    if idx < depth_array:
                                        closings += '          ]\n'
                                    if idx < depth_object:
                                        closings += '        }\n'

                                test_content = truncated_stripped + closings

                                try:
                                    test_estructura = json.loads(test_content)
                                    estructura = test_estructura
                                    logger.info(f"✓ JSON válido encontrado en pos {pos:,}/{len(content_limpio):,} (chunk={chunk_size}, intentos={intentos_realizados})")
                                    break
                                except:
                                    continue

                            logger.info(f"  Total intentos con chunk_size={chunk_size}: {intentos_realizados}")

                            if estructura is not None:
                                break

                    # Estrategia 2: Si aún no funciona, buscar desde el principio hacia adelante
                    if estructura is None:
                        logger.info("Búsqueda hacia atrás falló, intentando desde el inicio...")

                        # Buscar el primer punto donde tenemos al menos 1 capítulo completo
                        min_size = 5000  # Al menos 5K de contenido
                        for pos in range(min_size, len(content_limpio), 1000):
                            truncated = content_limpio[:pos]

                            # Eliminar coma trailing
                            truncated_stripped = truncated.rstrip()
                            if truncated_stripped.endswith(','):
                                truncated_stripped = truncated_stripped[:-1]

                            depth_array = truncated_stripped.count('[') - truncated_stripped.count(']')
                            depth_object = truncated_stripped.count('{') - truncated_stripped.count('}')

                            if depth_array < 0 or depth_object < 0:
                                continue

                            # Agregar cierres correctamente
                            closings = '\n'
                            for idx in range(max(depth_array, depth_object)):
                                if idx < depth_array:
                                    closings += '          ]\n'
                                if idx < depth_object:
                                    closings += '        }\n'

                            test_content = truncated_stripped + closings

                            try:
                                test_estructura = json.loads(test_content)
                                # Verificar que al menos tenga algo útil (estructura FLAT)
                                if test_estructura.get('partidas') and len(test_estructura['partidas']) > 0:
                                    estructura = test_estructura
                                    logger.info(f"✓ JSON válido encontrado desde inicio en pos {pos}")
                                    break
                            except:
                                continue

                    if estructura is None:
                        logger.error(f"No se pudo encontrar ningún JSON válido después de múltiples estrategias")
                        logger.error(f"📊 Tamaño total: {len(content):,} caracteres")
                        logger.error(f"Primeros 500 chars: {content[:500]}")
                        logger.error(f"Últimos 2000 chars: {content[-2000:]}")
                        logger.error(f"Caracteres alrededor del error (±500): {content[max(0, e.pos-500):min(len(content), e.pos+500)] if hasattr(e, 'pos') else 'N/A'}")
                        raise Exception(f"JSON incompleto y no reparable. El presupuesto es demasiado grande. Use el procesamiento local para este archivo.")

                    # Contar partidas recuperadas (estructura FLAT)
                    partidas_recuperadas = len(estructura.get('partidas', []))
                    logger.info(f"✓ Parser progresivo exitoso - {partidas_recuperadas} partidas recuperadas")

                    # Agregar nota sobre truncamiento
                    if 'notas_ia' not in estructura:
                        estructura['notas_ia'] = ''
                    estructura['notas_ia'] += f' [ADVERTENCIA: Respuesta truncada por límite del modelo. Se recuperaron {partidas_recuperadas} partidas mediante parser progresivo. Algunas partidas finales pueden faltar.]'

                # Agregar metadatos
                elapsed_time = time.time() - start_time
                estructura['tiempo_procesamiento'] = elapsed_time
                estructura['archivo_origen'] = pdf_path
                estructura['modelo_usado'] = self.model

                logger.info(f"✓ Procesamiento completado en {elapsed_time:.2f}s")

                # Contar partidas (estructura FLAT)
                total_partidas = len(estructura.get('partidas', []))
                logger.info(f"  Partidas: {total_partidas}")

                return estructura

            except httpx.HTTPStatusError as e:
                logger.error(f"Error HTTP: {e.response.status_code} - {e.response.text}")
                raise
            except json.JSONDecodeError as e:
                logger.error(f"Error parseando JSON: {e}")
                logger.error(f"Respuesta raw: {content[:500]}...")
                raise
            except Exception as e:
                logger.error(f"Error procesando PDF: {e}")
                raise

    def obtener_ultima_partida(self, estructura: Dict) -> Optional[str]:
        """
        Obtiene el código de la última partida procesada en la estructura FLAT

        Args:
            estructura: Estructura JSON del presupuesto

        Returns:
            Código de la última partida o None
        """
        partidas = estructura.get('partidas', [])
        if partidas:
            return partidas[-1].get('codigo')
        return None

    def fusionar_estructuras(self, base: Dict, adicional: Dict) -> Dict:
        """
        Fusiona dos estructuras de presupuesto FLAT, agregando las partidas adicionales

        Args:
            base: Estructura base (primera extracción)
            adicional: Estructura adicional (extracción continuación)

        Returns:
            Estructura fusionada
        """
        # La base mantiene nombre, descripción, etc.
        resultado = base.copy()

        # Estructura FLAT: simplemente extender el array de partidas
        if 'partidas' not in resultado:
            resultado['partidas'] = []

        # Agregar nuevas partidas evitando duplicados por código
        codigos_existentes = {p.get('codigo') for p in resultado['partidas']}

        for partida_nueva in adicional.get('partidas', []):
            codigo = partida_nueva.get('codigo')
            if codigo and codigo not in codigos_existentes:
                resultado['partidas'].append(partida_nueva)
                codigos_existentes.add(codigo)

        # Actualizar notas_ia
        notas_adicional = adicional.get('notas_ia', '')
        if 'Última partida:' in notas_adicional:
            resultado['notas_ia'] = notas_adicional

        # Actualizar nota sobre truncamiento
        if '[ADVERTENCIA: Respuesta truncada' in resultado.get('notas_ia', ''):
            resultado['notas_ia'] = resultado['notas_ia'].replace(
                '[ADVERTENCIA: Respuesta truncada',
                '[Procesamiento completado en múltiples partes. Respuesta inicial fue truncada'
            )

        return resultado

    async def procesar_pdf_completo(self, pdf_path: str, max_intentos: int = 20) -> Dict:
        """
        Procesa un PDF completo, haciendo múltiples peticiones si es necesario

        Args:
            pdf_path: Ruta al archivo PDF
            max_intentos: Número máximo de intentos para completar la extracción

        Returns:
            Estructura completa del presupuesto
        """
        logger.info(f"Iniciando procesamiento completo con max {max_intentos} intentos")

        # Primera extracción
        estructura_base = await self.procesar_pdf(pdf_path)

        # Verificar si fue truncada
        fue_truncada = '[ADVERTENCIA: Respuesta truncada' in estructura_base.get('notas_ia', '')

        if not fue_truncada:
            logger.info("✓ Procesamiento completado en un solo intento")
            return estructura_base

        # Necesitamos continuar
        intento = 1
        while intento < max_intentos:
            # Obtener última partida
            ultima_partida = self.obtener_ultima_partida(estructura_base)
            if not ultima_partida:
                logger.warning("No se pudo determinar la última partida, deteniendo")
                break

            logger.info(f"Intento {intento + 1}/{max_intentos}: Continuando desde partida {ultima_partida}")

            try:
                # Extraer más partidas
                estructura_adicional = await self.procesar_pdf(pdf_path, desde_partida=ultima_partida)

                # Fusionar estructuras
                estructura_base = self.fusionar_estructuras(estructura_base, estructura_adicional)

                # Verificar si esta parte también fue truncada
                fue_truncada = '[ADVERTENCIA: Respuesta truncada' in estructura_adicional.get('notas_ia', '')

                if not fue_truncada:
                    logger.info(f"✓ Procesamiento completado en {intento + 1} intentos")
                    break

                intento += 1

            except Exception as e:
                logger.error(f"Error en intento {intento + 1}: {e}")
                break

        # Contar partidas finales (estructura FLAT)
        total_partidas = len(estructura_base.get('partidas', []))
        logger.info(f"✓ Extracción finalizada: {total_partidas} partidas totales")

        return estructura_base


# Función helper para uso simple
async def procesar_pdf_con_ia(pdf_path: str) -> Dict:
    """
    Procesa un PDF usando IA y retorna la estructura extraída

    Args:
        pdf_path: Ruta al archivo PDF

    Returns:
        Dict con estructura del presupuesto
    """
    client = OpenRouterClient()
    return await client.procesar_pdf(pdf_path)


if __name__ == "__main__":
    import asyncio

    # Test
    async def test():
        pdf_path = "/Volumes/DATOS_IA/G_Drive_LuzIA/PRUEBAS/PLIEGOS/PRESUPUESTOS PARCIALES NAVAS DE TOLOSA.pdf"
        resultado = await procesar_pdf_con_ia(pdf_path)
        print(json.dumps(resultado, indent=2, ensure_ascii=False))

    asyncio.run(test())
