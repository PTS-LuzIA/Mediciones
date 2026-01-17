"""
Agente especializado en CONTAR el número de partidas de cada capítulo/subcapítulo.
Este agente recibe la estructura previamente extraída y cuenta las partidas en cada sección.
Se ejecuta DESPUÉS del StructureExtractionAgent (Fase 1).
"""

import httpx
import base64
import json
import os
import time
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class PartidaCountAgent:
    """Agente especializado en contar partidas por capítulo/subcapítulo"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: API key de OpenRouter (si no se provee, se lee de OPENROUTER_API_KEY env var)
        """
        self.api_key = api_key or os.getenv('OPENROUTER_API_KEY')
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY no encontrada en variables de entorno")

        self.base_url = "https://openrouter.ai/api/v1"
        self.model = "google/gemini-2.5-flash-lite"

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

    def crear_prompt_conteo(self, estructura: Dict) -> str:
        """
        Crea el prompt especializado para contar partidas de cada capítulo/subcapítulo

        Args:
            estructura: Estructura previamente extraída con capítulos y subcapítulos

        Returns:
            String con el prompt completo
        """
        # Crear un resumen simplificado de la estructura para incluir en el prompt
        estructura_resumen = self._generar_resumen_estructura(estructura)

        return f"""Tu tarea es contar ÚNICAMENTE el número de PARTIDAS INDIVIDUALES que pertenecen a cada capítulo o subcapítulo del presupuesto.

🎯 OBJETIVO: Contar cuántas partidas tiene cada sección (capítulo/subcapítulo).

📋 ESTRUCTURA EXISTENTE:

Ya se extrajo previamente la siguiente estructura jerárquica del presupuesto:

{estructura_resumen}

⚠️ DEFINICIÓN DE "PARTIDA":

Una PARTIDA es una línea de presupuesto con:
- Código alfanumérico o numérico largo (ej: "m23U01C190", "U01AB100", "01.05.001.0001", "DEM06")
- Unidad de medida (m³, m², ud, kg, etc.)
- Descripción del trabajo
- Precio unitario
- Cantidad
- Importe total de la línea

🔴 NO CONTAR COMO PARTIDAS:
- Títulos de capítulos (ej: "01 MOVIMIENTO DE TIERRAS")
- Títulos de subcapítulos (ej: "01.05 MUROS")
- Líneas de totales parciales
- Líneas de "TOTAL" o "Suma y sigue"

🔍 ESTRATEGIA DE CONTEO:

1. Para cada capítulo y subcapítulo de la estructura anterior:
   - Identifica su sección en el PDF (por el código y título)
   - Cuenta TODAS las partidas individuales que aparecen en esa sección
   - NO cuentes partidas de subsecciones hijas (se contarán aparte)

2. IMPORTANTE sobre jerarquía:
   - Si un capítulo "01" tiene subcapítulos "01.05" y "01.10", cuenta SOLO las partidas que están directamente bajo "01" (si las hay)
   - NO sumes las partidas de los subcapítulos al capítulo padre
   - Cada sección cuenta SUS propias partidas directas

📊 FORMATO JSON REQUERIDO (COMPACTO):

Devuelve un JSON con la MISMA estructura jerárquica, pero agregando el campo "num_partidas" a cada nivel:

{{
  "capitulos": [
    {{
      "codigo": "01",
      "num_partidas": 5,
      "subcapitulos": [
        {{
          "codigo": "01.05",
          "num_partidas": 12,
          "subcapitulos": [
            {{
              "codigo": "01.05.01",
              "num_partidas": 8,
              "subcapitulos": []
            }},
            {{
              "codigo": "01.05.02",
              "num_partidas": 4,
              "subcapitulos": []
            }}
          ]
        }},
        {{
          "codigo": "01.10",
          "num_partidas": 15,
          "subcapitulos": []
        }}
      ]
    }},
    {{
      "codigo": "02",
      "num_partidas": 20,
      "subcapitulos": []
    }}
  ]
}}

⚠️ REGLAS CRÍTICAS:

1. El campo "num_partidas" es un número entero (0, 1, 2, 3, ...)
2. Si una sección NO tiene partidas directas (solo tiene subsecciones), usar num_partidas: 0
3. La estructura JSON debe ser IDÉNTICA a la proporcionada (mismos códigos, mismo orden, misma jerarquía)
4. SOLO agrega el campo "num_partidas", NO modifies nada más
5. Si no estás seguro del conteo, usa tu mejor estimación y continúa
6. NO incluyas campos adicionales como "nombre", "total", "orden", etc. - SOLO "codigo", "num_partidas" y "subcapitulos"

✅ VALIDACIÓN:

- Verifica que el total de partidas del documento sea razonable (típicamente entre 50 y 500 partidas)
- Si un subcapítulo aparece vacío pero tiene un total en €, probablemente tiene partidas (cuenta al menos 1)
- Los subcapítulos "hoja" (sin hijos) siempre deberían tener al menos 1 partida

Devuelve SOLO el JSON compacto, sin texto adicional."""

    def _generar_resumen_estructura(self, estructura: Dict) -> str:
        """
        Genera un resumen legible de la estructura para incluir en el prompt

        Args:
            estructura: Estructura extraída

        Returns:
            String con el resumen
        """
        lineas = []

        def procesar_nivel(items, nivel=0):
            indent = "  " * nivel
            for item in items:
                codigo = item.get('codigo', '?')
                nombre = item.get('nombre', '')
                total = item.get('total', 0)
                lineas.append(f"{indent}{codigo} - {nombre} (Total: {total:.2f} €)")

                # Procesar subcapítulos recursivamente
                if item.get('subcapitulos'):
                    procesar_nivel(item['subcapitulos'], nivel + 1)

        capitulos = estructura.get('capitulos', [])
        procesar_nivel(capitulos, 0)

        return "\n".join(lineas)

    async def contar_partidas(self, pdf_path: str, estructura: Dict) -> Dict:
        """
        Cuenta las partidas de cada capítulo/subcapítulo del PDF

        Args:
            pdf_path: Ruta al archivo PDF
            estructura: Estructura extraída previamente (con capítulos y subcapítulos)

        Returns:
            Dict con la estructura y el número de partidas por sección
        """
        start_time = time.time()
        logger.info(f"Iniciando conteo de partidas: {pdf_path}")

        # Leer el PDF y convertir a base64
        pdf_base64 = self.encode_pdf_base64(pdf_path)

        # Preparar el mensaje con el PDF
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": self.crear_prompt_conteo(estructura)
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
            "temperature": 0.0,  # Temperatura a 0 para máxima determinismo
            "max_tokens": 50000,  # Suficiente para el conteo (respuesta más corta que estructura)
            "response_format": {"type": "json_object"}  # Forzar respuesta JSON
        }

        # Hacer la petición
        async with httpx.AsyncClient(timeout=300.0) as client:  # 5 minutos timeout
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()

                result = response.json()
                content = result['choices'][0]['message']['content']

                # Parsear el JSON devuelto
                try:
                    conteo_estructura = json.loads(content)
                except json.JSONDecodeError as e:
                    logger.error(f"Error parseando JSON: {e}")
                    logger.error(f"Respuesta raw: {content[:1000]}...")
                    raise ValueError(f"Error parseando JSON de la IA: {e}")

                # Verificar que tiene la estructura correcta
                # El LLM puede devolver directamente la lista de capítulos o un objeto con la clave 'capitulos'
                if isinstance(conteo_estructura, list):
                    # Si devuelve directamente la lista, envolverla en un objeto
                    logger.info("LLM devolvió lista directa de capítulos, envolviéndola en objeto")
                    conteo_estructura = {"capitulos": conteo_estructura}
                elif isinstance(conteo_estructura, dict):
                    # Si es un objeto, verificar que tenga 'capitulos'
                    if 'capitulos' not in conteo_estructura:
                        logger.error(f"Respuesta no contiene 'capitulos'. Keys: {conteo_estructura.keys()}")
                        logger.error(f"Contenido completo: {json.dumps(conteo_estructura, indent=2, ensure_ascii=False)[:1000]}")
                        raise ValueError("La respuesta del LLM no contiene el campo 'capitulos'")
                else:
                    logger.error(f"Respuesta no es ni lista ni diccionario: {type(conteo_estructura)}")
                    logger.error(f"Contenido: {str(conteo_estructura)[:500]}")
                    raise ValueError("La respuesta del LLM tiene un formato inválido")

                # Agregar metadatos
                elapsed_time = time.time() - start_time
                conteo_estructura['tiempo_conteo'] = elapsed_time
                conteo_estructura['archivo_origen'] = pdf_path
                conteo_estructura['modelo_usado'] = self.model

                logger.info(f"✓ Conteo de partidas completado en {elapsed_time:.2f}s")

                # Contar total de partidas
                total_partidas = self._contar_partidas_total(conteo_estructura.get('capitulos', []))
                logger.info(f"  Total de partidas contadas: {total_partidas}")

                return conteo_estructura

            except httpx.HTTPStatusError as e:
                logger.error(f"Error HTTP: {e.response.status_code} - {e.response.text}")
                raise
            except ValueError as e:
                # Ya se logueó el error arriba
                raise
            except Exception as e:
                logger.error(f"Error contando partidas: {e}")
                import traceback
                logger.error(traceback.format_exc())
                raise

    def _contar_partidas_total(self, capitulos: list) -> int:
        """
        Cuenta el total de partidas en todos los capítulos recursivamente

        Args:
            capitulos: Lista de capítulos con subcapítulos

        Returns:
            Número total de partidas
        """
        total = 0
        for cap in capitulos:
            total += cap.get('num_partidas', 0)
            if cap.get('subcapitulos'):
                total += self._contar_partidas_total(cap['subcapitulos'])
        return total

    def fusionar_conteo_con_estructura(self, estructura_original: Dict, conteo: Dict) -> Dict:
        """
        Fusiona el conteo de partidas con la estructura original

        Args:
            estructura_original: Estructura completa extraída (con nombres, totales, etc.)
            conteo: Estructura simplificada solo con conteo de partidas

        Returns:
            Estructura original con el campo num_partidas agregado
        """
        logger.info("Fusionando conteo de partidas con estructura original")

        # Crear mapa de conteos por código
        conteo_map = {}
        self._construir_mapa_conteo(conteo.get('capitulos', []), conteo_map)

        # Aplicar conteos a la estructura original
        estructura_fusionada = estructura_original.copy()
        self._aplicar_conteos_recursivo(estructura_fusionada.get('capitulos', []), conteo_map)

        return estructura_fusionada

    def _construir_mapa_conteo(self, capitulos: list, mapa: dict) -> None:
        """
        Construye un mapa de códigos -> num_partidas recursivamente

        Args:
            capitulos: Lista de capítulos
            mapa: Diccionario donde se guardan los conteos
        """
        for cap in capitulos:
            codigo = cap.get('codigo')
            if codigo:
                mapa[codigo] = cap.get('num_partidas', 0)

            # Recursión
            if cap.get('subcapitulos'):
                self._construir_mapa_conteo(cap['subcapitulos'], mapa)

    def _aplicar_conteos_recursivo(self, capitulos: list, conteo_map: dict) -> None:
        """
        Aplica los conteos de partidas a la estructura original recursivamente

        Args:
            capitulos: Lista de capítulos de la estructura original
            conteo_map: Mapa con los conteos
        """
        for cap in capitulos:
            codigo = cap.get('codigo')
            if codigo in conteo_map:
                cap['num_partidas'] = conteo_map[codigo]
                logger.debug(f"  {codigo}: {conteo_map[codigo]} partidas")
            else:
                cap['num_partidas'] = 0
                logger.warning(f"  {codigo}: no encontrado en conteo, asignando 0")

            # Recursión
            if cap.get('subcapitulos'):
                self._aplicar_conteos_recursivo(cap['subcapitulos'], conteo_map)


# Función helper para uso simple
async def contar_partidas_pdf(pdf_path: str, estructura: Dict) -> Dict:
    """
    Cuenta las partidas de cada capítulo/subcapítulo de un PDF

    Args:
        pdf_path: Ruta al archivo PDF
        estructura: Estructura extraída previamente

    Returns:
        Dict con estructura y conteo de partidas
    """
    agent = PartidaCountAgent()
    conteo = await agent.contar_partidas(pdf_path, estructura)
    estructura_con_conteo = agent.fusionar_conteo_con_estructura(estructura, conteo)
    return estructura_con_conteo


if __name__ == "__main__":
    import asyncio
    from structure_extraction_agent import extraer_estructura_pdf

    # Test
    async def test():
        pdf_path = "/Volumes/DATOS_IA/G_Drive_LuzIA/PRUEBAS/PLIEGOS/PRESUPUESTOS PARCIALES NAVAS DE TOLOSA.pdf"

        # Primero extraer estructura
        print("1. Extrayendo estructura...")
        estructura = await extraer_estructura_pdf(pdf_path)
        print(f"   Estructura extraída: {len(estructura.get('capitulos', []))} capítulos")

        # Luego contar partidas
        print("\n2. Contando partidas...")
        estructura_con_conteo = await contar_partidas_pdf(pdf_path, estructura)
        print(json.dumps(estructura_con_conteo, indent=2, ensure_ascii=False))

    asyncio.run(test())
