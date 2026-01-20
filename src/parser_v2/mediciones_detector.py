"""
Mediciones Detector - Detecta si las partidas tienen tabla de mediciones auxiliares
==================================================================================

Analiza el contenido del PDF para determinar si las partidas incluyen
descomposición dimensional (UDS, LONGITUD, ANCHURA, ALTURA) o solo
cantidades directas.

"""

import logging
from typing import List

logger = logging.getLogger(__name__)


class MedicionesDetector:
    """Detecta si el PDF tiene mediciones auxiliares (tabla dimensional)"""

    # Keywords que indican presencia de tabla de mediciones
    KEYWORDS_TABLA_MEDICIONES = [
        'UDS', 'UNIDADES',
        'LONGITUD', 'LARGO', 'LONG',
        'ANCHURA', 'ANCHO', 'ANCH',
        'ALTURA', 'ALTO', 'ALT',
        'PARCIALES', 'PARCIAL',
        'SUBTOTAL'
    ]

    # Patterns que indican formato de tabla
    PATTERNS_TABLA = [
        r'UDS\s+LONGITUD\s+ANCHURA\s+ALTURA',
        r'LONG\.\s+ANCH\.\s+ALT\.',
        r'Nº\s+LARGO\s+ANCHO\s+ALTO',
    ]

    def __init__(self, lineas: List[str]):
        """
        Args:
            lineas: Lista de líneas de texto extraídas del PDF
        """
        self.lineas = lineas

    def detectar_mediciones_auxiliares(self, num_lineas_analizar: int = 300) -> bool:
        """
        Detecta si el PDF tiene tabla de mediciones auxiliares

        Estrategia:
        1. Analizar las primeras N líneas (headers de tabla)
        2. Buscar keywords específicos de mediciones
        3. Buscar patterns de tabla dimensional
        4. Decisión basada en coincidencias

        Args:
            num_lineas_analizar: Número de líneas a analizar (default: 300)

        Returns:
            True si tiene mediciones auxiliares, False si son directas
        """
        # Tomar muestra de líneas (inicio del documento)
        muestra = self.lineas[:num_lineas_analizar]
        texto_muestra = ' '.join(muestra).upper()

        # Contar keywords
        matches_keywords = sum(
            1 for keyword in self.KEYWORDS_TABLA_MEDICIONES
            if keyword in texto_muestra
        )

        # Buscar patterns de tabla
        import re
        matches_patterns = sum(
            1 for pattern in self.PATTERNS_TABLA
            if re.search(pattern, texto_muestra)
        )

        # Decisión: si encuentra 3+ keywords o 1+ pattern → tiene mediciones
        tiene_mediciones = (matches_keywords >= 3) or (matches_patterns >= 1)

        if tiene_mediciones:
            logger.info("🔍 Tipo detectado: CON mediciones auxiliares (tabla UDS/LONG/ANCH/ALT)")
            logger.info(f"   Keywords encontrados: {matches_keywords}")
            logger.info(f"   Patterns encontrados: {matches_patterns}")
        else:
            logger.info("🔍 Tipo detectado: SIN mediciones auxiliares (cantidad directa)")

        return tiene_mediciones

    def detectar_columnas_mediciones(self) -> List[str]:
        """
        Detecta qué columnas de mediciones están presentes

        Returns:
            Lista de columnas detectadas ['UDS', 'LONGITUD', 'ANCHURA', etc.]
        """
        columnas = []
        texto_muestra = ' '.join(self.lineas[:200]).upper()

        if 'UDS' in texto_muestra or 'UNIDADES' in texto_muestra:
            columnas.append('UDS')
        if 'LONGITUD' in texto_muestra or 'LARGO' in texto_muestra:
            columnas.append('LONGITUD')
        if 'ANCHURA' in texto_muestra or 'ANCHO' in texto_muestra:
            columnas.append('ANCHURA')
        if 'ALTURA' in texto_muestra or 'ALTO' in texto_muestra:
            columnas.append('ALTURA')
        if 'PARCIALES' in texto_muestra or 'PARCIAL' in texto_muestra:
            columnas.append('PARCIALES')

        return columnas


# Función de utilidad
def detectar_mediciones(lineas: List[str]) -> bool:
    """
    Detecta si las líneas contienen mediciones auxiliares

    Args:
        lineas: Lista de líneas de texto

    Returns:
        True si tiene mediciones auxiliares

    Example:
        >>> tiene_med = detectar_mediciones(lineas_pdf)
        >>> print(f"Tiene mediciones: {tiene_med}")
    """
    detector = MedicionesDetector(lineas)
    return detector.detectar_mediciones_auxiliares()


if __name__ == "__main__":
    # Test
    import sys
    from layout_detector import detectar_layout_pdf
    from layout_normalizer import normalizar_pdf

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("Uso: python mediciones_detector.py <pdf_path>")
        sys.exit(1)

    pdf_path = sys.argv[1]

    print(f"\n{'='*60}")
    print(f"ANÁLISIS: {pdf_path}")
    print(f"{'='*60}\n")

    # 1. Detectar layout
    layout = detectar_layout_pdf(pdf_path)

    # 2. Normalizar texto
    lineas = normalizar_pdf(pdf_path, layout)

    # 3. Detectar mediciones
    detector = MedicionesDetector(lineas)
    tiene_mediciones = detector.detectar_mediciones_auxiliares()

    # 4. Detectar columnas
    if tiene_mediciones:
        columnas = detector.detectar_columnas_mediciones()
        print(f"\nColumnas detectadas: {', '.join(columnas)}")

    print(f"\n{'='*60}")
    print(f"RESUMEN:")
    print(f"  Layout: {layout}")
    print(f"  Mediciones auxiliares: {'SÍ' if tiene_mediciones else 'NO'}")
    print(f"{'='*60}\n")
