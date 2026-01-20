"""
Layout Detector - Detecta si el PDF tiene 1 o 2 columnas
========================================================

Analiza la distribución espacial del texto en el PDF para determinar
si está organizado en una o dos columnas.

Estrategia:
1. Extraer bloques de texto con posiciones (x, y)
2. Analizar distribución horizontal
3. Detectar si hay dos flujos paralelos de texto

"""

import fitz  # PyMuPDF
import logging
from typing import Literal

logger = logging.getLogger(__name__)

LayoutType = Literal['single_column', 'double_column']


class LayoutDetector:
    """Detecta el layout de un PDF (1 o 2 columnas)"""

    def __init__(self, pdf_path: str):
        """
        Args:
            pdf_path: Ruta al archivo PDF
        """
        self.pdf_path = pdf_path
        self.doc = None

    def __enter__(self):
        """Context manager para abrir el PDF"""
        self.doc = fitz.open(self.pdf_path)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager para cerrar el PDF"""
        if self.doc:
            self.doc.close()

    def detectar_layout(self, num_paginas_analizar: int = 3) -> LayoutType:
        """
        Detecta el layout del PDF

        Args:
            num_paginas_analizar: Número de páginas a analizar (default: 3)

        Returns:
            'single_column' | 'double_column'
        """
        if not self.doc:
            self.doc = fitz.open(self.pdf_path)

        # Analizar las primeras N páginas
        total_paginas = min(num_paginas_analizar, len(self.doc))
        resultados = []

        for i in range(total_paginas):
            pagina = self.doc[i]
            layout = self._analizar_pagina(pagina)
            resultados.append(layout)
            logger.debug(f"Página {i+1}: {layout}")

        # Decisión: mayoría de páginas
        conteo = {
            'single_column': resultados.count('single_column'),
            'double_column': resultados.count('double_column')
        }

        layout_final = 'double_column' if conteo['double_column'] > conteo['single_column'] else 'single_column'

        logger.info(f"🔍 Layout detectado: {layout_final.upper().replace('_', ' ')}")
        logger.info(f"   Análisis: {conteo}")

        return layout_final

    def _analizar_pagina(self, pagina) -> LayoutType:
        """
        Analiza una página individual

        Estrategia:
        1. Dividir página en mitad izquierda y mitad derecha
        2. Contar bloques de texto en cada mitad
        3. Si ambas mitades tienen texto significativo → 2 columnas
        4. Si solo una mitad tiene texto → 1 columna

        Args:
            pagina: Objeto fitz.Page

        Returns:
            'single_column' | 'double_column'
        """
        # Obtener dimensiones de la página
        rect = pagina.rect
        ancho_pagina = rect.width
        alto_pagina = rect.height
        mitad_x = ancho_pagina / 2

        # Márgenes (ignorar headers/footers y bordes)
        margen_superior = alto_pagina * 0.1
        margen_inferior = alto_pagina * 0.9
        margen_izq = ancho_pagina * 0.05
        margen_der = ancho_pagina * 0.95

        # Extraer bloques de texto con posiciones
        bloques = pagina.get_text("dict")["blocks"]

        bloques_izq = 0
        bloques_der = 0
        texto_izq_chars = 0
        texto_der_chars = 0

        for bloque in bloques:
            if "lines" not in bloque:  # No es texto
                continue

            # Posición del bloque
            x0, y0, x1, y1 = bloque["bbox"]

            # Ignorar bloques en márgenes (headers/footers)
            if y0 < margen_superior or y0 > margen_inferior:
                continue
            if x0 < margen_izq or x1 > margen_der:
                continue

            # Contar caracteres del bloque
            num_chars = sum(
                len(span["text"])
                for line in bloque["lines"]
                for span in line["spans"]
            )

            # Clasificar según posición horizontal
            centro_x = (x0 + x1) / 2

            if centro_x < mitad_x:
                bloques_izq += 1
                texto_izq_chars += num_chars
            else:
                bloques_der += 1
                texto_der_chars += num_chars

        # Decisión basada en distribución
        # Si ambas columnas tienen > 20% del texto total → 2 columnas
        total_chars = texto_izq_chars + texto_der_chars

        if total_chars == 0:
            return 'single_column'

        ratio_izq = texto_izq_chars / total_chars
        ratio_der = texto_der_chars / total_chars

        # Criterios para 2 columnas:
        # 1. Ambas mitades tienen al menos 25% del texto
        # 2. Ambas mitades tienen al menos 5 bloques
        tiene_texto_balanceado = (ratio_izq > 0.25 and ratio_der > 0.25)
        tiene_bloques_suficientes = (bloques_izq >= 5 and bloques_der >= 5)

        if tiene_texto_balanceado and tiene_bloques_suficientes:
            logger.debug(f"  2 columnas: izq={ratio_izq:.1%} ({bloques_izq} bloques), der={ratio_der:.1%} ({bloques_der} bloques)")
            return 'double_column'
        else:
            logger.debug(f"  1 columna: izq={ratio_izq:.1%} ({bloques_izq} bloques), der={ratio_der:.1%} ({bloques_der} bloques)")
            return 'single_column'


# Función de utilidad para uso directo
def detectar_layout_pdf(pdf_path: str) -> LayoutType:
    """
    Detecta el layout de un PDF

    Args:
        pdf_path: Ruta al archivo PDF

    Returns:
        'single_column' | 'double_column'

    Example:
        >>> layout = detectar_layout_pdf("proyecto.pdf")
        >>> print(layout)
        'double_column'
    """
    with LayoutDetector(pdf_path) as detector:
        return detector.detectar_layout()


if __name__ == "__main__":
    # Test del detector
    import sys

    logging.basicConfig(level=logging.DEBUG)

    if len(sys.argv) < 2:
        print("Uso: python layout_detector.py <pdf_path>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    layout = detectar_layout_pdf(pdf_path)

    print(f"\n{'='*60}")
    print(f"Resultado: {layout.upper().replace('_', ' ')}")
    print(f"{'='*60}\n")
