"""
Extractor de texto desde PDFs de mediciones.
Utiliza pdfplumber para extraer texto línea por línea preservando estructura.
Soporta detección automática de layouts de múltiples columnas.
"""

import pdfplumber
import logging
from pathlib import Path
from typing import List, Dict, Optional

try:
    from .column_detector import ColumnDetector
except ImportError:
    import sys
    from pathlib import Path
    parent_dir = str(Path(__file__).parent.parent)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    from parser.column_detector import ColumnDetector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PDFExtractor:
    """Extrae texto estructurado desde PDFs de mediciones"""

    def __init__(self, pdf_path: str, detect_columns: bool = True):
        """
        Args:
            pdf_path: Ruta al archivo PDF
            detect_columns: Si True, detecta automáticamente layouts de múltiples columnas
                           y extrae cada columna por separado usando bounding boxes
        """
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF no encontrado: {pdf_path}")

        self.pages_text = []
        self.metadata = {}
        self.detect_columns = detect_columns
        self.column_detector = ColumnDetector() if detect_columns else None
        self.layout_info = []  # Información de layout por página

    def extraer_todo(self) -> Dict:
        """
        Extrae todo el contenido del PDF

        Returns:
            dict: {
                'metadata': {...},
                'pages': [{'num': 1, 'text': '...', 'lines': [...], 'layout': {...}}, ...],
                'all_text': 'texto completo',
                'all_lines': ['línea1', 'línea2', ...],
                'layout_summary': {'total_columnas': int, 'paginas_multicolumna': int}
            }
        """
        resultado = {
            'metadata': {},
            'pages': [],
            'all_text': '',
            'all_lines': [],
            'layout_summary': {'total_columnas': 0, 'paginas_multicolumna': 0}
        }

        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                # Extraer metadata
                resultado['metadata'] = {
                    'archivo': self.pdf_path.name,
                    'num_paginas': len(pdf.pages),
                    'info': pdf.metadata
                }

                logger.info(f"Extrayendo {len(pdf.pages)} páginas de {self.pdf_path.name}")

                # Extraer cada página
                for i, page in enumerate(pdf.pages, start=1):
                    page_data = self._extraer_pagina(page, i)
                    resultado['pages'].append(page_data)
                    resultado['all_lines'].extend(page_data['lines'])

                    # Actualizar resumen de layout
                    if page_data.get('layout'):
                        num_cols = page_data['layout'].get('num_columnas', 1)
                        if num_cols > 1:
                            resultado['layout_summary']['paginas_multicolumna'] += 1
                        resultado['layout_summary']['total_columnas'] = max(
                            resultado['layout_summary']['total_columnas'],
                            num_cols
                        )

                resultado['all_text'] = '\n'.join(resultado['all_lines'])

                # Log de información de columnas
                if resultado['layout_summary']['paginas_multicolumna'] > 0:
                    logger.info(
                        f"⚡ Detectadas {resultado['layout_summary']['paginas_multicolumna']} "
                        f"página(s) con múltiples columnas (máx: {resultado['layout_summary']['total_columnas']} columnas)"
                    )

                logger.info(f"✓ Extraídas {len(resultado['all_lines'])} líneas")

        except Exception as e:
            logger.error(f"Error extrayendo PDF: {e}")
            raise

        return resultado

    def _extraer_pagina(self, page, num_pagina: int) -> Dict:
        """
        Extrae el contenido de una página individual con detección de columnas

        Args:
            page: objeto página de pdfplumber
            num_pagina: número de página

        Returns:
            dict con texto, líneas y layout de la página
        """
        # Si la detección de columnas está desactivada, usar método simple
        if not self.detect_columns or not self.column_detector:
            texto = page.extract_text()
            if not texto:
                return {'num': num_pagina, 'text': '', 'lines': [], 'layout': None}

            lineas = [linea.strip() for linea in texto.split('\n')]
            lineas = [l for l in lineas if l]

            return {
                'num': num_pagina,
                'text': texto,
                'lines': lineas,
                'layout': None
            }

        # Extraer palabras con posiciones para analizar layout
        words = page.extract_words()

        if not words:
            return {
                'num': num_pagina,
                'text': '',
                'lines': [],
                'layout': {'num_columnas': 0, 'tipo': 'vacio'}
            }

        # Analizar layout de la página
        layout_info = self.column_detector.analizar_layout(words)
        num_columnas = layout_info.get('num_columnas', 1)

        # ESTRATEGIA 1: Columna simple - Usar método original (extract_text)
        # Más rápido y preserva mejor el orden original del PDF
        if num_columnas == 1:
            texto = page.extract_text()
            if not texto:
                lineas = []
            else:
                lineas = [linea.strip() for linea in texto.split('\n')]
                lineas = [l for l in lineas if l]

            return {
                'num': num_pagina,
                'text': texto or '',
                'lines': lineas,
                'layout': layout_info
            }

        # ESTRATEGIA 2: Múltiples columnas - Dividir página físicamente y extraer cada columna
        # Necesario para preservar el orden correcto en PDFs con columnas
        else:
            logger.info(
                f"  Página {num_pagina}: {num_columnas} columnas detectadas "
                f"({layout_info['orientacion']}) - usando extracción por bbox"
            )

            # Obtener dimensiones de la página
            page_width = page.width
            page_height = page.height

            # Extraer cada columna dividiendo la página físicamente
            all_column_lines = []
            for i, col_info in enumerate(layout_info['columnas']):
                # Usar los rangos X detectados, pero asegurar que cubrimos toda la altura
                x_min = col_info['x_min']
                x_max = col_info['x_max']

                # Definir bounding box para esta columna
                bbox = (x_min, 0, x_max, page_height)

                # Extraer texto de esta región
                col_crop = page.within_bbox(bbox)
                col_text = col_crop.extract_text()

                if col_text:
                    col_lines = [l.strip() for l in col_text.split('\n') if l.strip()]
                    all_column_lines.extend(col_lines)
                    logger.debug(f"    Columna {i+1}: {len(col_lines)} líneas")

            return {
                'num': num_pagina,
                'text': '\n'.join(all_column_lines),
                'lines': all_column_lines,
                'layout': layout_info
            }

    def extraer_lineas(self) -> List[str]:
        """
        Extrae solo las líneas de texto del PDF

        Returns:
            lista de strings con cada línea
        """
        datos = self.extraer_todo()
        return datos['all_lines']

    def extraer_tablas(self) -> List[Dict]:
        """
        Extrae tablas detectadas en el PDF

        Returns:
            lista de tablas (cada tabla es lista de listas)
        """
        tablas = []

        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                for i, page in enumerate(pdf.pages, start=1):
                    page_tables = page.extract_tables()
                    if page_tables:
                        for j, tabla in enumerate(page_tables):
                            tablas.append({
                                'pagina': i,
                                'tabla_num': j + 1,
                                'data': tabla
                            })

                logger.info(f"✓ Extraídas {len(tablas)} tablas")

        except Exception as e:
            logger.error(f"Error extrayendo tablas: {e}")

        return tablas

    def extraer_con_posiciones(self) -> List[Dict]:
        """
        Extrae texto con información de posición (x, y)
        Útil para detectar columnas de números

        Returns:
            lista de diccionarios con texto y coordenadas
        """
        elementos = []

        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    # Extraer palabras con posiciones
                    words = page.extract_words()

                    for word in words:
                        elementos.append({
                            'pagina': page_num,
                            'texto': word['text'],
                            'x0': word['x0'],
                            'y0': word['top'],
                            'x1': word['x1'],
                            'y1': word['bottom'],
                            'width': word['x1'] - word['x0'],
                            'height': word['bottom'] - word['top']
                        })

                logger.info(f"✓ Extraídos {len(elementos)} elementos con posición")

        except Exception as e:
            logger.error(f"Error extrayendo posiciones: {e}")

        return elementos

    def guardar_texto(self, output_path: str) -> None:
        """
        Guarda el texto extraído en un archivo .txt

        Args:
            output_path: ruta del archivo de salida
        """
        datos = self.extraer_todo()

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(datos['all_text'])

        logger.info(f"✓ Texto guardado en {output_path}")


def extraer_pdf(pdf_path: str, output_txt: Optional[str] = None) -> Dict:
    """
    Función helper para extraer rápidamente un PDF

    Args:
        pdf_path: ruta al PDF
        output_txt: ruta opcional para guardar texto

    Returns:
        dict con todos los datos extraídos
    """
    extractor = PDFExtractor(pdf_path)
    datos = extractor.extraer_todo()

    if output_txt:
        extractor.guardar_texto(output_txt)

    return datos


if __name__ == "__main__":
    # Test con el PDF de ejemplo
    pdf_ejemplo = "ejemplo/PROYECTO CALYPOFADO_extract.pdf"

    if Path(pdf_ejemplo).exists():
        print(f"Extrayendo {pdf_ejemplo}...")

        extractor = PDFExtractor(pdf_ejemplo)
        datos = extractor.extraer_todo()

        print(f"\n📄 Archivo: {datos['metadata']['archivo']}")
        print(f"📑 Páginas: {datos['metadata']['num_paginas']}")
        print(f"📝 Líneas totales: {len(datos['all_lines'])}")
        print(f"\n--- Primeras 10 líneas ---")
        for i, linea in enumerate(datos['all_lines'][:10], 1):
            print(f"{i:3d}: {linea}")

        # Guardar texto
        extractor.guardar_texto('data/ejemplo_extraido.txt')
        print("\n✓ Texto guardado en data/ejemplo_extraido.txt")
    else:
        print(f"❌ No se encuentra el archivo {pdf_ejemplo}")
