"""
Extractor de estructura LOCAL (sin IA) para FASE 1.
Extrae SOLO la jerarquía completa de capítulos/subcapítulos y calcula totales.
NO extrae partidas (eso es Fase 2).
Guarda el resultado en JSON para reutilizarlo.

Autor: Claude Code
Fecha: 2026-01-14
"""

import json
import os
import logging
import time
from typing import Dict, List, Optional
from pathlib import Path

try:
    from .pdf_extractor import PDFExtractor
    from .structure_parser import StructureParser
except ImportError:
    import sys
    parent_dir = str(Path(__file__).parent.parent)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    from parser.pdf_extractor import PDFExtractor
    from parser.structure_parser import StructureParser

logger = logging.getLogger(__name__)


class LocalStructureExtractor:
    """
    Extractor de estructura LOCAL usando el parser determinista.
    Genera el mismo formato JSON que StructureExtractionAgent para compatibilidad.

    IMPORTANTE: Ya NO cachea la estructura procesada, solo el texto extraído del PDF.
    Esto permite que las mejoras del parser se apliquen siempre.
    """

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path

    def extraer_estructura(self) -> Dict:
        """
        Extrae la estructura completa del PDF usando el parser local.

        NOTA: Ya NO usa caché de estructura procesada. Solo el texto del PDF
        puede estar cacheado (en PDFExtractor).

        Returns:
            Dict con estructura compatible con StructureExtractionAgent
        """
        start_time = time.time()
        logger.info(f"🔧 Extrayendo estructura LOCAL de: {self.pdf_path}")

        # 1. Extraer texto del PDF
        extractor = PDFExtractor(self.pdf_path)
        datos_pdf = extractor.extraer_todo()
        lineas = datos_pdf['all_lines']

        # 2. Detectar nombre del proyecto
        nombre_proyecto = self._detectar_nombre_proyecto(lineas)

        # 3. Parsear estructura con el parser especializado de Fase 1
        parser = StructureParser()
        estructura_interna = parser.parsear(lineas)

        # 4. Convertir a formato compatible con StructureExtractionAgent
        estructura_final = self._convertir_a_formato_ia(
            estructura_interna,
            nombre_proyecto
        )

        # 5. Validar totales (aritmética)
        validacion = self._validar_totales(estructura_final)
        estructura_final['validacion_local'] = validacion

        # 6. Agregar metadatos
        elapsed_time = time.time() - start_time
        estructura_final['tiempo_procesamiento'] = elapsed_time
        estructura_final['archivo_origen'] = self.pdf_path
        estructura_final['metodo_extraccion'] = 'local_structure_parser_v2'
        estructura_final['modelo_usado'] = 'structure_parser_v2'

        logger.info(f"✓ Extracción LOCAL completada en {elapsed_time:.2f}s")
        logger.info(f"  Capítulos: {len(estructura_final.get('capitulos', []))}")

        # Contar subcapítulos totales
        total_subcaps = sum(
            self._contar_subcapitulos_recursivo(cap)
            for cap in estructura_final.get('capitulos', [])
        )
        logger.info(f"  Subcapítulos: {total_subcaps}")

        if not validacion['valido']:
            logger.warning(f"  ⚠️ Validación: {len(validacion['inconsistencias'])} inconsistencias detectadas")
        else:
            logger.info(f"  ✓ Validación: Todos los totales cuadran")

        return estructura_final

    def _detectar_nombre_proyecto(self, lineas: List[str]) -> str:
        """Detecta el nombre del proyecto desde las primeras líneas del PDF"""
        import re

        nombre_candidato = []

        for i in range(min(20, len(lineas))):
            linea = lineas[i].strip()

            # Si llegamos a un CAPÍTULO o código numérico, dejamos de buscar
            if (linea.upper().startswith('CAPÍTULO') or
                re.match(r'^\d{1,2}(\.\d{1,2})?\s+', linea)):
                break

            # Saltar líneas vacías, headers de tabla y palabras clave comunes
            if (not linea or
                len(linea) < 15 or
                'CÓDIGO' in linea.upper() or
                'RESUMEN' in linea.upper() or
                'CANTIDAD' in linea.upper() or
                'PRECIO' in linea.upper() or
                'IMPORTE' in linea.upper()):
                continue

            # Si la línea parece ser un título (mayúsculas, larga, descriptiva)
            if len(linea) > 30 and not nombre_candidato:
                nombre_candidato.append(linea)
                break

        if nombre_candidato:
            texto_completo = ' '.join(nombre_candidato)
            if not re.match(r'^[\d\.\s]+$', texto_completo):
                return texto_completo

        return Path(self.pdf_path).stem


    def _convertir_a_formato_ia(self, estructura: Dict, nombre_proyecto: str) -> Dict:
        """
        Convierte estructura interna a formato compatible con StructureExtractionAgent
        """
        return {
            'nombre': nombre_proyecto,
            'descripcion': 'Extracción LOCAL determinista (parser)',
            'confianza_general': 1.0,  # Parser local es determinista
            'notas_ia': 'Estructura extraída con parser local (sin IA)',
            'capitulos': [
                self._convertir_capitulo(cap) for cap in estructura['capitulos']
            ]
        }

    def _convertir_capitulo(self, capitulo: Dict) -> Dict:
        """Convierte un capítulo al formato de IA"""
        # Limpiar campos internos
        capitulo_limpio = {k: v for k, v in capitulo.items() if not k.startswith('_')}

        return {
            'codigo': capitulo['codigo'],
            'nombre': capitulo['nombre'],
            'total': capitulo.get('total', 0.0),
            'confianza': 1.0,
            'notas': '[GENERADO AUTOMÁTICAMENTE]' if capitulo.get('_generado') else '',
            'orden': capitulo['orden'],
            'subcapitulos': [
                self._convertir_subcapitulo(sub) for sub in capitulo.get('subcapitulos', [])
            ]
        }

    def _convertir_subcapitulo(self, subcapitulo: Dict) -> Dict:
        """Convierte un subcapítulo al formato de IA (recursivo)"""
        return {
            'codigo': subcapitulo['codigo'],
            'nombre': subcapitulo['nombre'],
            'total': subcapitulo.get('total', 0.0),
            'confianza': 1.0,
            'notas': '[GENERADO AUTOMÁTICAMENTE]' if subcapitulo.get('_generado') else '',
            'orden': subcapitulo['orden'],
            'subcapitulos': [
                self._convertir_subcapitulo(sub) for sub in subcapitulo.get('subcapitulos', [])
            ]
        }

    def _validar_totales(self, estructura: Dict) -> Dict:
        """
        Valida que los totales de subcapítulos sumen el total del capítulo

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

                # Tolerancia del 0.1% (más estricto que IA)
                diferencia = abs(suma_subcapitulos - total)
                tolerancia = max(total * 0.001, 0.01)  # 0.1% o 0.01€ mínimo

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

    def _contar_subcapitulos_recursivo(self, nodo: Dict) -> int:
        """Cuenta recursivamente todos los subcapítulos en un nodo"""
        subcapitulos = nodo.get('subcapitulos', [])
        count = len(subcapitulos)

        for sub in subcapitulos:
            count += self._contar_subcapitulos_recursivo(sub)

        return count


# Función helper para uso simple
def extraer_estructura_local(pdf_path: str) -> Dict:
    """
    Extrae la estructura de capítulos/subcapítulos de un PDF usando parser local

    Args:
        pdf_path: Ruta al archivo PDF

    Returns:
        Dict con estructura jerárquica del presupuesto
    """
    extractor = LocalStructureExtractor(pdf_path)
    return extractor.extraer_estructura()


if __name__ == "__main__":
    # Test
    pdf_path = "ejemplo/PROYECTO CALYPOFADO_extract.pdf"

    if os.path.exists(pdf_path):
        resultado = extraer_estructura_local(pdf_path)

        print("\n" + "="*80)
        print("ESTRUCTURA LOCAL EXTRAÍDA")
        print("="*80)
        print(f"Proyecto: {resultado['nombre']}")
        print(f"Capítulos: {len(resultado['capitulos'])}")
        print(f"Método: {resultado['metodo_extraccion']}")
        print(f"Tiempo: {resultado['tiempo_procesamiento']:.2f}s")

        # Mostrar primeros 2 capítulos
        for i, cap in enumerate(resultado['capitulos'][:2]):
            print(f"\n{cap['codigo']} - {cap['nombre']}")
            print(f"  Total: {cap['total']:.2f} €")
            print(f"  Partidas: {cap['num_partidas']}")
            print(f"  Subcapítulos: {len(cap['subcapitulos'])}")

        # Validación
        if resultado.get('validacion_local'):
            val = resultado['validacion_local']
            if val['valido']:
                print(f"\n✓ Validación: Todos los totales cuadran")
            else:
                print(f"\n⚠️ Validación: {len(val['inconsistencias'])} inconsistencias")

        print("="*80 + "\n")
    else:
        print(f"PDF no encontrado: {pdf_path}")
