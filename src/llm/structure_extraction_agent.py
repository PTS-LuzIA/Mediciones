"""
Agente especializado en extraer SOLO la estructura jerárquica del presupuesto.
Este agente identifica capítulos, subcapítulos y sus totales.
NO extrae partidas individuales (eso se hace en fase 2).
"""

import httpx
import base64
import json
import os
import time
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class StructureExtractionAgent:
    """Agente especializado en extraer estructura de capítulos/subcapítulos"""

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

    def crear_prompt_estructura(self) -> str:
        """
        Crea el prompt especializado para extraer SOLO la estructura jerárquica

        Returns:
            String con el prompt completo
        """
        return """Extrae ÚNICAMENTE la ESTRUCTURA JERÁRQUICA COMPLETA del presupuesto (TODOS los capítulos, subcapítulos y sus totales).

🎯 OBJETIVO: Identificar la organización COMPLETA del presupuesto SIN extraer partidas individuales.

🔴 MUY IMPORTANTE: Debes extraer TODOS los capítulos que encuentres en el documento (01, 02, 03, 04, etc.), NO solo el primero.

📋 IDENTIFICACIÓN DE NIVELES (por formato de código):

⚠️ CRÍTICO: La jerarquía se determina por el NÚMERO DE PUNTOS en el código:

- CAPÍTULO: 2 dígitos SIN puntos (ej: "01", "02", "03", "10", "11")
  └─ SUBCAPÍTULO NIVEL 1: 1 punto (ej: "01.03", "01.04", "01.05")
      └─ SUBCAPÍTULO NIVEL 2: 2 puntos (ej: "01.04.01", "01.04.02", "01.05.01")
          └─ SUBCAPÍTULO NIVEL 3: 3 puntos (ej: "01.05.01.01", "01.05.01.02")
              └─ SUBCAPÍTULO NIVEL 4: 4 puntos (ej: "01.05.01.02.01")
                  └─ SUBCAPÍTULO NIVEL 5: 5 puntos (ej: "01.05.01.02.01.01")

🔴 EJEMPLO DE JERARQUÍA CORRECTA:

Si el documento tiene:
- 01 FASE 2
- 01.03 MOVIMIENTO DE TIERRAS
- 01.04 PAVIMENTACIÓN
- 01.04.01 PAVIMENTO PERMEABLE
- 01.04.02 PAVIMENTO IMPERMEABLE
- 01.05 MUROS
- 01.05.01 MUROS DE SUELO
- 01.05.01.01 MURO 1
- 01.05.01.02 MURO 2
- 01.10 SERVICIOS AFECTADOS
- 01.10.01 GAS
- 01.10.02 ELECTRICIDAD
- 01.10.05 TELEFONIA

La estructura JSON correcta es:
{
  "capitulos": [
    {
      "codigo": "01",
      "nombre": "FASE 2",
      "subcapitulos": [
        {
          "codigo": "01.03",
          "nombre": "MOVIMIENTO DE TIERRAS",
          "subcapitulos": []
        },
        {
          "codigo": "01.04",
          "nombre": "PAVIMENTACIÓN",
          "subcapitulos": [
            {
              "codigo": "01.04.01",
              "nombre": "PAVIMENTO PERMEABLE",
              "subcapitulos": []
            },
            {
              "codigo": "01.04.02",
              "nombre": "PAVIMENTO IMPERMEABLE",
              "subcapitulos": []
            }
          ]
        },
        {
          "codigo": "01.05",
          "nombre": "MUROS",
          "subcapitulos": [
            {
              "codigo": "01.05.01",
              "nombre": "MUROS DE SUELO",
              "subcapitulos": [
                {
                  "codigo": "01.05.01.01",
                  "nombre": "MURO 1",
                  "subcapitulos": []
                },
                {
                  "codigo": "01.05.01.02",
                  "nombre": "MURO 2",
                  "subcapitulos": []
                }
              ]
            }
          ]
        },
        {
          "codigo": "01.10",
          "nombre": "SERVICIOS AFECTADOS",
          "subcapitulos": [
            {
              "codigo": "01.10.01",
              "nombre": "GAS",
              "subcapitulos": []
            },
            {
              "codigo": "01.10.02",
              "nombre": "ELECTRICIDAD",
              "subcapitulos": []
            },
            {
              "codigo": "01.10.05",
              "nombre": "TELEFONIA",
              "subcapitulos": []
            }
          ]
        }
      ]
    }
  ]
}

⚠️ NOTA IMPORTANTE: En el ejemplo anterior, observa que:
- "01.10" tiene el nombre "SERVICIOS AFECTADOS" (su propio título)
- "01.10.05" tiene el nombre "TELEFONIA" (que es diferente)
- NO uses "TELEFONIA" como título de "01.10" solo porque sea el último hijo

⚠️ REGLAS CRÍTICAS:

1. **EXTRAE TODOS LOS CAPÍTULOS**: El documento puede tener múltiples capítulos principales (01, 02, 03, 04, etc.). Asegúrate de extraer TODOS, no solo el primero.
2. NO extraigas partidas individuales (códigos alfanuméricos como "m23U01C190")
3. SOLO extrae códigos numéricos con puntos que representen capítulos/subcapítulos
4. Captura el TOTAL que aparece al final de cada sección
5. El total suele aparecer después de listar todas las partidas de ese capítulo/subcapítulo
6. **MUY IMPORTANTE - TÍTULOS**: El título de cada capítulo/subcapítulo es el texto que aparece INMEDIATAMENTE DESPUÉS de su código en la MISMA LÍNEA. Por ejemplo:
   - Si ves "01.10    SERVICIOS AFECTADOS", el título de 01.10 es "SERVICIOS AFECTADOS"
   - Si luego ves "01.10.01    GAS", el título de 01.10.01 es "GAS"
   - NO uses el título de un subcapítulo hijo como título del padre
7. Respeta el nombre EXACTO como aparece en el PDF (en MAYÚSCULAS si así está)
8. Mantén el orden secuencial del documento
9. **RECORRE TODO EL DOCUMENTO**: No te detengas después del primer capítulo, continúa hasta el final del PDF

📊 FORMATO JSON REQUERIDO (COMPACTO):

IMPORTANTE: Genera un JSON COMPACTO sin espacios innecesarios para optimizar el uso de tokens.

{
  "nombre": "Nombre completo del proyecto",
  "descripcion": "Descripción breve (opcional)",
  "confianza_general": 0.95,
  "notas_ia": "Observaciones breves",
  "capitulos": [
    {
      "codigo": "01",
      "nombre": "MOVIMIENTO DE TIERRAS",
      "total": 25000.75,
      "confianza": 0.99,
      "notas": "",
      "orden": 1,
      "subcapitulos": [
        {
          "codigo": "01.01",
          "nombre": "EXCAVACIONES",
          "total": 15000.50,
          "confianza": 0.99,
          "notas": "",
          "orden": 1,
          "subcapitulos": [
            {
              "codigo": "01.01.01",
              "nombre": "EXCAVACIÓN EN ZANJAS",
              "total": 8000.25,
              "confianza": 0.99,
              "notas": "",
              "orden": 1,
              "subcapitulos": []
            }
          ]
        },
        {
          "codigo": "01.02",
          "nombre": "RELLENOS",
          "total": 10000.25,
          "confianza": 0.99,
          "notas": "",
          "orden": 2,
          "subcapitulos": []
        }
      ]
    },
    {
      "codigo": "02",
      "nombre": "CIMENTACIÓN",
      "total": 50000.00,
      "confianza": 0.95,
      "notas": "",
      "orden": 2,
      "subcapitulos": [
        {
          "codigo": "02.01",
          "nombre": "ZAPATAS",
          "total": 50000.00,
          "confianza": 0.95,
          "notas": "",
          "orden": 1,
          "subcapitulos": []
        }
      ]
    }
  ]
}

✅ VALIDACIÓN:

- Si un total parece incorrecto o falta, usar null y bajar confianza
- Si hay inconsistencias entre la suma de subcapítulos y el total del capítulo, anotar en "notas"
- Confianza: 0.95-1.0 si datos claros, 0.7-0.9 si hay dudas, <0.7 si muy incierto
- El campo "orden" indica la posición secuencial (1, 2, 3...)

🔍 ESTRATEGIA DE BÚSQUEDA:

1. **ESCANEA TODO EL DOCUMENTO**: Lee el PDF completo de principio a fin
2. Busca TODOS los títulos en MAYÚSCULAS con códigos numéricos (01, 02, 03, 04, ...)
3. Identifica dónde aparece "TOTAL" o el importe final de cada sección
4. Los totales suelen estar en negrita o al final de una tabla
5. Si hay múltiples niveles anidados, respeta la jerarquía exacta
6. **NO OMITAS CAPÍTULOS**: Asegúrate de incluir todos los capítulos que encuentres en todo el documento

⚠️ VERIFICACIÓN FINAL:
- Cuenta cuántos capítulos principales encontraste (con código de 2 dígitos sin puntos)
- Si solo encontraste 1 capítulo, REVISA DE NUEVO porque probablemente hay más
- La mayoría de presupuestos tienen entre 2 y 15 capítulos principales

Devuelve SOLO el JSON, sin texto adicional."""

    async def extraer_estructura(self, pdf_path: str) -> Dict:
        """
        Extrae la estructura jerárquica de capítulos/subcapítulos del PDF

        Args:
            pdf_path: Ruta al archivo PDF

        Returns:
            Dict con la estructura jerárquica del presupuesto
        """
        start_time = time.time()
        logger.info(f"Iniciando extracción de estructura: {pdf_path}")

        # Leer el PDF y convertir a base64
        pdf_base64 = self.encode_pdf_base64(pdf_path)

        # Preparar el mensaje con el PDF
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": self.crear_prompt_estructura()
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
            "temperature": 0.0,  # Temperatura a 0 para máxima determinismo y evitar variaciones
            "max_tokens": 100000,  # Aumentado a 100k para garantizar respuestas completas incluso sin caché
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
                estructura = json.loads(content)

                # Agregar metadatos
                elapsed_time = time.time() - start_time
                estructura['tiempo_procesamiento'] = elapsed_time
                estructura['archivo_origen'] = pdf_path
                estructura['modelo_usado'] = self.model

                logger.info(f"✓ Extracción de estructura completada en {elapsed_time:.2f}s")

                # Contar capítulos y subcapítulos
                total_capitulos = len(estructura.get('capitulos', []))
                total_subcapitulos = sum(
                    self._contar_subcapitulos_recursivo(cap)
                    for cap in estructura.get('capitulos', [])
                )
                logger.info(f"  Capítulos: {total_capitulos}")
                logger.info(f"  Subcapítulos (todos los niveles): {total_subcapitulos}")

                return estructura

            except httpx.HTTPStatusError as e:
                logger.error(f"Error HTTP: {e.response.status_code} - {e.response.text}")
                raise
            except json.JSONDecodeError as e:
                logger.error(f"Error parseando JSON: {e}")
                logger.error(f"Respuesta raw (primeros 500 caracteres): {content[:500]}...")
                logger.error(f"Respuesta raw (últimos 500 caracteres): ...{content[-500:]}")
                logger.error(f"Longitud total de la respuesta: {len(content)} caracteres")

                # Intentar dar más información sobre el error
                if len(content) > 30000:
                    logger.warning(f"⚠️ La respuesta es muy larga ({len(content)} caracteres). Puede que se haya truncado.")
                    logger.warning("Considera aumentar max_tokens o simplificar el documento.")

                raise ValueError(f"Error parseando JSON de la IA: {e}. La respuesta puede estar incompleta o mal formada.")
            except Exception as e:
                logger.error(f"Error extrayendo estructura: {e}")
                raise

    def _contar_subcapitulos_recursivo(self, nodo: Dict) -> int:
        """
        Cuenta recursivamente todos los subcapítulos en un nodo

        Args:
            nodo: Diccionario representando un capítulo o subcapítulo

        Returns:
            Número total de subcapítulos
        """
        subcapitulos = nodo.get('subcapitulos', [])
        count = len(subcapitulos)

        for sub in subcapitulos:
            count += self._contar_subcapitulos_recursivo(sub)

        return count

    def validar_totales(self, estructura: Dict) -> Dict:
        """
        Valida que los totales de subcapítulos sumen el total del capítulo

        Args:
            estructura: Estructura extraída

        Returns:
            Dict con resultados de validación
        """
        resultados = {
            "valido": True,
            "inconsistencias": []
        }

        def validar_nodo(nodo: Dict, path: str = ""):
            """Valida un nodo recursivamente"""
            codigo = nodo.get('codigo', 'unknown')
            nombre = nodo.get('nombre', '')
            total = nodo.get('total', 0)
            subcapitulos = nodo.get('subcapitulos', [])

            if subcapitulos:
                # Sumar totales de subcapítulos
                suma_subcapitulos = sum(sub.get('total', 0) for sub in subcapitulos)

                # Tolerancia del 1%
                diferencia = abs(suma_subcapitulos - total)
                tolerancia = total * 0.01

                if diferencia > tolerancia:
                    resultados["valido"] = False
                    resultados["inconsistencias"].append({
                        "codigo": codigo,
                        "nombre": nombre,
                        "total_declarado": total,
                        "suma_subcapitulos": suma_subcapitulos,
                        "diferencia": diferencia
                    })

                # Validar subcapítulos recursivamente
                for sub in subcapitulos:
                    validar_nodo(sub, f"{path}/{codigo}")

        # Validar cada capítulo
        for capitulo in estructura.get('capitulos', []):
            validar_nodo(capitulo)

        return resultados


# Función helper para uso simple
async def extraer_estructura_pdf(pdf_path: str) -> Dict:
    """
    Extrae la estructura de capítulos/subcapítulos de un PDF

    Args:
        pdf_path: Ruta al archivo PDF

    Returns:
        Dict con estructura jerárquica del presupuesto
    """
    agent = StructureExtractionAgent()
    return await agent.extraer_estructura(pdf_path)


if __name__ == "__main__":
    import asyncio

    # Test
    async def test():
        pdf_path = "/Volumes/DATOS_IA/G_Drive_LuzIA/PRUEBAS/PLIEGOS/PRESUPUESTOS PARCIALES NAVAS DE TOLOSA.pdf"
        resultado = await extraer_estructura_pdf(pdf_path)
        print(json.dumps(resultado, indent=2, ensure_ascii=False))

        # Validar totales
        agent = StructureExtractionAgent()
        validacion = agent.validar_totales(resultado)
        print("\n=== VALIDACIÓN ===")
        print(json.dumps(validacion, indent=2, ensure_ascii=False))

    asyncio.run(test())
