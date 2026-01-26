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

    def __init__(self, pdf_path: str, user_id: int, proyecto_id: int,
                 detect_columns: bool = True, remove_repeated_headers: bool = True):
        """
        Args:
            pdf_path: Ruta al archivo PDF
            user_id: ID del usuario (REQUERIDO, se incluye en nombres de archivos de log)
            proyecto_id: ID del proyecto (REQUERIDO, se incluye en nombres de archivos de log)
            detect_columns: Si True, detecta automáticamente layouts de múltiples columnas
                           y extrae cada columna por separado usando bounding boxes
            remove_repeated_headers: Si True, elimina cabeceras repetidas después de la primera aparición
        """
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF no encontrado: {pdf_path}")

        self.pages_text = []
        self.metadata = {}
        self.detect_columns = detect_columns
        self.remove_repeated_headers = remove_repeated_headers
        self.column_detector = ColumnDetector() if detect_columns else None
        self.layout_info = []  # Información de layout por página
        self.user_id = user_id
        self.proyecto_id = proyecto_id

        # Patrones comunes de cabeceras que se repiten en cada página
        # Se usan patrones genéricos que aplican a la mayoría de presupuestos
        self.header_patterns = [
            'PRESUPUESTO',
            'CÓDIGO RESUMEN CANTIDAD PRECIO IMPORTE',
            # El nombre del proyecto se detectará dinámicamente
        ]

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
        import os

        # CACHÉ: Verificar si ya existe el texto extraído del PDF
        nombre_pdf = self.pdf_path.stem
        cache_dir = Path('logs/extracted_pdfs')

        # Limpiar nombre del PDF: quitar prefijos user_id/proyecto_id si existen
        # Formatos a limpiar:
        # - Nuevo: u{user_id}_p{proyecto_id}_{nombre} → {nombre}
        # - Antiguo: {user_id}_{nombre} → {nombre}
        import re
        nombre_limpio = nombre_pdf

        # Intentar quitar formato nuevo: u{user_id}_p{proyecto_id}_
        match = re.match(r'u\d+_p\d+_(.+)', nombre_pdf)
        if match:
            nombre_limpio = match.group(1)
        else:
            # Intentar quitar formato antiguo: {user_id}_
            if '_' in nombre_pdf:
                first_part = nombre_pdf.split('_')[0]
                if first_part.isdigit() and int(first_part) == self.user_id:
                    nombre_limpio = '_'.join(nombre_pdf.split('_')[1:])

        # Construir nombre de archivo de caché SIEMPRE incluyendo user_id y proyecto_id
        # Formato: u{user_id}_p{proyecto_id}_{nombre_limpio}_extracted.txt
        cache_filename = f"u{self.user_id}_p{self.proyecto_id}_{nombre_limpio}_extracted.txt"
        cache_file = cache_dir / cache_filename

        if cache_file.exists():
            logger.info(f"✓ Usando texto cacheado: {cache_file}")
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    lineas = [linea.rstrip('\n') for linea in f.readlines()]

                # Detectar título del proyecto desde caché
                titulo_proyecto = None
                for linea in lineas[:10]:
                    linea_limpia = linea.strip()
                    # Buscar línea larga que parezca título (no es cabecera estándar ni código)
                    if (len(linea_limpia) > 30 and
                        not linea_limpia.startswith(('CÓDIGO', 'PRESUPUESTO', 'CÓDIGO RESUMEN', '01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12', '13', '14', '15')) and
                        linea_limpia not in self.header_patterns):
                        titulo_proyecto = linea_limpia
                        logger.info(f"📋 Título del proyecto detectado desde caché: '{titulo_proyecto}'")
                        break

                resultado = {
                    'metadata': {'archivo': self.pdf_path.name, 'from_cache': True},
                    'pages': [],
                    'all_text': '\n'.join(lineas),
                    'all_lines': lineas,
                    'layout_summary': {'total_columnas': 0, 'paginas_multicolumna': 0}
                }

                # Añadir título si se detectó
                if titulo_proyecto:
                    resultado['titulo_proyecto'] = titulo_proyecto

                return resultado
            except Exception as e:
                logger.warning(f"⚠️ Error leyendo caché, extrayendo de nuevo: {e}")

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

                # Filtrar cabeceras repetidas si está habilitado
                if self.remove_repeated_headers:
                    lineas_originales = len(resultado['all_lines'])
                    resultado['all_lines'], titulo_proyecto = self._filtrar_cabeceras_repetidas(resultado['all_lines'])
                    # Guardar el título del proyecto en metadata
                    if titulo_proyecto:
                        resultado['titulo_proyecto'] = titulo_proyecto
                    lineas_filtradas = len(resultado['all_lines'])
                    if lineas_filtradas < lineas_originales:
                        logger.info(f"🧹 Cabeceras repetidas eliminadas: {lineas_originales} → {lineas_filtradas} líneas ({lineas_originales - lineas_filtradas} eliminadas)")

                # Filtrar pies de página con números de paginación
                lineas_antes_footer = len(resultado['all_lines'])
                resultado['all_lines'] = self._filtrar_pies_pagina(resultado['all_lines'])
                lineas_despues_footer = len(resultado['all_lines'])
                if lineas_despues_footer < lineas_antes_footer:
                    logger.info(f"🗑️  Pies de página eliminados: {lineas_antes_footer - lineas_despues_footer} líneas")

                resultado['all_text'] = '\n'.join(resultado['all_lines'])

                # Log de información de columnas
                if resultado['layout_summary']['paginas_multicolumna'] > 0:
                    logger.info(
                        f"⚡ Detectadas {resultado['layout_summary']['paginas_multicolumna']} "
                        f"página(s) con múltiples columnas (máx: {resultado['layout_summary']['total_columnas']} columnas)"
                    )

                logger.info(f"✓ Extraídas {len(resultado['all_lines'])} líneas")

                # GUARDAR EN CACHÉ para reutilización
                try:
                    cache_dir.mkdir(parents=True, exist_ok=True)
                    with open(cache_file, 'w', encoding='utf-8') as f:
                        for linea in resultado['all_lines']:
                            f.write(linea + '\n')
                    logger.info(f"💾 Texto guardado en caché: {cache_file}")
                except Exception as e:
                    logger.warning(f"⚠️ No se pudo guardar caché: {e}")

        except Exception as e:
            logger.error(f"Error extrayendo PDF: {e}")
            raise

        return resultado

    def _filtrar_cabeceras_repetidas(self, lineas: List[str]):
        """
        Filtra líneas de cabecera que se repiten en múltiples páginas.
        Mantiene solo la primera aparición de cada patrón de cabecera.

        Args:
            lineas: Lista de líneas de texto extraídas

        Returns:
            Tupla (lista de líneas filtradas, título del proyecto o None)
        """
        # Detectar dinámicamente el nombre del proyecto en las primeras 10 líneas
        # Típicamente aparece después de "PRESUPUESTO" y antes de "CÓDIGO RESUMEN..."
        patrones_dinamicos = list(self.header_patterns)
        titulo_proyecto = None  # Variable para guardar el título

        for i, linea in enumerate(lineas[:10]):
            linea_limpia = linea.strip()
            # Si es una línea larga que parece nombre de proyecto (no es capítulo ni código)
            if len(linea_limpia) > 30 and not linea_limpia.startswith(('CÓDIGO', 'PRESUPUESTO', '01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12', '13', '14', '15')):
                # Verificar que no sea ya una cabecera conocida
                if linea_limpia not in patrones_dinamicos:
                    # Es probable que sea el nombre del proyecto
                    if titulo_proyecto is None:  # Capturar solo el primer título detectado
                        titulo_proyecto = linea_limpia
                        logger.info(f"📋 Título del proyecto detectado: '{titulo_proyecto}'")
                    patrones_dinamicos.append(linea_limpia)
                    logger.debug(f"Detectado nombre de proyecto como cabecera: '{linea_limpia[:60]}...'")

        lineas_filtradas = []
        cabeceras_vistas = set()

        for linea in lineas:
            linea_limpia = linea.strip()

            # IMPORTANTE: NUNCA filtrar líneas que contengan TOTAL (son datos importantes)
            if linea_limpia.upper().startswith('TOTAL'):
                lineas_filtradas.append(linea)
                continue

            # Verificar si es una cabecera conocida
            es_cabecera = False
            for patron in patrones_dinamicos:
                if linea_limpia == patron or (len(patron) > 20 and patron in linea_limpia):
                    es_cabecera = True
                    # Si ya vimos esta cabecera, omitirla
                    if patron in cabeceras_vistas:
                        break
                    else:
                        # Primera vez que vemos esta cabecera, marcarla como vista
                        cabeceras_vistas.add(patron)
                        lineas_filtradas.append(linea)
                    break

            # Si no es cabecera, añadirla siempre
            if not es_cabecera:
                lineas_filtradas.append(linea)

        return lineas_filtradas, titulo_proyecto

    def _filtrar_pies_pagina(self, lineas: List[str]) -> List[str]:
        """
        Filtra líneas de pie de página que contienen solo números de paginación.

        Detecta patrones comunes de paginación como:
        - Número solo: "1", "23", "89"
        - Número con espacios: "  23  "
        - Formatos: "Página 1", "Pág. 23", "- 5 -", etc.

        Args:
            lineas: Lista de líneas de texto extraídas

        Returns:
            Lista de líneas filtradas sin pies de página
        """
        import re

        # Patrones comunes de paginación en pies de página
        patrones_paginacion = [
            r'^\s*\d+\s*$',                    # Solo número: "23"
            r'^\s*-\s*\d+\s*-\s*$',            # Con guiones: "- 23 -"
            r'^\s*página\s+\d+\s*$',           # "Página 23" (case insensitive)
            r'^\s*pág\.?\s+\d+\s*$',           # "Pág. 23" o "Pag 23"
            r'^\s*page\s+\d+\s*$',             # "Page 23"
            r'^\s*p\.\s*\d+\s*$',              # "P. 23"
            r'^\s*\d+\s*/\s*\d+\s*$',          # "23 / 89" (página X de Y)
            r'^\s*\[\s*\d+\s*\]\s*$',          # "[23]"
        ]

        # Compilar patrones (case insensitive)
        patrones_compilados = [re.compile(p, re.IGNORECASE) for p in patrones_paginacion]

        lineas_filtradas = []

        for linea in lineas:
            linea_limpia = linea.strip()

            # Verificar si coincide con algún patrón de paginación
            es_pie_pagina = False
            for patron in patrones_compilados:
                if patron.match(linea_limpia):
                    es_pie_pagina = True
                    logger.debug(f"Pie de página detectado y eliminado: '{linea_limpia}'")
                    break

            # Solo añadir la línea si NO es pie de página
            if not es_pie_pagina:
                lineas_filtradas.append(linea)

        return lineas_filtradas

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
