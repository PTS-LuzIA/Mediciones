"""
Layout Normalizer - Normaliza texto de PDFs a flujo lineal
==========================================================

Convierte PDFs con diferentes layouts (1 o 2 columnas) a un flujo
de texto lineal normalizado, manteniendo el orden de lectura correcto.

CRÍTICO para 2 columnas:
- Procesar TODA la columna izquierda primero
- Luego procesar TODA la columna derecha
- NO intercalar líneas entre columnas

"""

import fitz  # PyMuPDF
import logging
from typing import List, Literal

logger = logging.getLogger(__name__)

LayoutType = Literal['single_column', 'double_column']


class LayoutNormalizer:
    """Normaliza el texto de un PDF según su layout"""

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

    def normalizar(self, layout: LayoutType) -> List[str]:
        """
        Extrae texto del PDF y lo normaliza según el layout

        Args:
            layout: Tipo de layout ('single_column' | 'double_column')

        Returns:
            Lista de líneas de texto en orden correcto
        """
        if not self.doc:
            self.doc = fitz.open(self.pdf_path)

        if layout == 'single_column':
            lineas = self._extraer_una_columna()
        else:
            lineas = self._extraer_dos_columnas()

        logger.info(f"✓ Texto normalizado: {len(lineas)} líneas extraídas")
        return lineas

    def _extraer_una_columna(self) -> List[str]:
        """
        Extracción normal secuencial (1 columna)

        Returns:
            Lista de líneas de texto
        """
        lineas = []

        for pagina in self.doc:
            # Extraer bloques de texto
            bloques = pagina.get_text("dict")["blocks"]

            # Ordenar bloques por posición vertical (top to bottom)
            bloques_texto = [b for b in bloques if "lines" in b]
            bloques_texto.sort(key=lambda b: b["bbox"][1])  # Ordenar por Y

            # Extraer texto de cada bloque
            for bloque in bloques_texto:
                for line in bloque["lines"]:
                    texto = " ".join([span["text"] for span in line["spans"]])
                    texto = texto.strip()
                    if texto:
                        lineas.append(texto)

        return lineas

    def _extraer_dos_columnas(self) -> List[str]:
        """
        Extracción respetando orden de 2 columnas

        ESTRATEGIA:
        1. Procesar TODA la columna izquierda de todas las páginas
        2. Luego procesar TODA la columna derecha de todas las páginas

        Returns:
            Lista de líneas de texto en orden correcto
        """
        lineas_normalizadas = []

        for num_pagina, pagina in enumerate(self.doc):
            # Obtener dimensiones
            rect = pagina.rect
            ancho = rect.width
            alto = rect.height
            mitad_x = ancho / 2

            # Márgenes
            margen_superior = alto * 0.05
            margen_inferior = alto * 0.95
            margen_izq = ancho * 0.02
            margen_der = ancho * 0.98

            # Extraer bloques
            bloques = pagina.get_text("dict")["blocks"]

            # Separar bloques por columna
            bloques_izq = []
            bloques_der = []

            for bloque in bloques:
                if "lines" not in bloque:
                    continue

                x0, y0, x1, y1 = bloque["bbox"]

                # Ignorar headers/footers
                if y0 < margen_superior or y0 > margen_inferior:
                    continue
                if x0 < margen_izq or x1 > margen_der:
                    continue

                # Clasificar por columna (usar centro del bloque)
                centro_x = (x0 + x1) / 2

                if centro_x < mitad_x:
                    bloques_izq.append(bloque)
                else:
                    bloques_der.append(bloque)

            # Ordenar cada columna verticalmente
            bloques_izq.sort(key=lambda b: b["bbox"][1])
            bloques_der.sort(key=lambda b: b["bbox"][1])

            # Procesar TODA la columna izquierda primero
            for bloque in bloques_izq:
                for line in bloque["lines"]:
                    texto = " ".join([span["text"] for span in line["spans"]])
                    texto = texto.strip()
                    if texto:
                        lineas_normalizadas.append(texto)

            # Luego procesar TODA la columna derecha
            for bloque in bloques_der:
                for line in bloque["lines"]:
                    texto = " ".join([span["text"] for span in line["spans"]])
                    texto = texto.strip()
                    if texto:
                        lineas_normalizadas.append(texto)

            logger.debug(f"Página {num_pagina + 1}: {len(bloques_izq)} bloques izq, {len(bloques_der)} bloques der")

        return lineas_normalizadas


# Función de utilidad
def normalizar_pdf(pdf_path: str, layout: LayoutType) -> List[str]:
    """
    Normaliza un PDF a flujo de texto lineal

    Args:
        pdf_path: Ruta al PDF
        layout: Tipo de layout

    Returns:
        Lista de líneas de texto

    Example:
        >>> lineas = normalizar_pdf("proyecto.pdf", "double_column")
        >>> print(f"Total líneas: {len(lineas)}")
    """
    with LayoutNormalizer(pdf_path) as normalizer:
        return normalizer.normalizar(layout)


if __name__ == "__main__":
    # Test
    import sys
    from layout_detector import detectar_layout_pdf

    logging.basicConfig(level=logging.DEBUG)

    if len(sys.argv) < 2:
        print("Uso: python layout_normalizer.py <pdf_path>")
        sys.exit(1)

    pdf_path = sys.argv[1]

    # Detectar layout
    layout = detectar_layout_pdf(pdf_path)
    print(f"\nLayout: {layout}")

    # Normalizar
    lineas = normalizar_pdf(pdf_path, layout)

    print(f"\nTotal líneas: {len(lineas)}")
    print("\nPrimeras 20 líneas:")
    print("="*60)
    for i, linea in enumerate(lineas[:20], 1):
        print(f"{i:3}. {linea[:80]}")
