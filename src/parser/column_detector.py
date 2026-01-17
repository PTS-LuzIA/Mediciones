"""
Detector de columnas en PDFs.
Analiza la distribución espacial del texto para detectar layouts de múltiples columnas.
"""

import logging
from typing import List, Dict, Tuple, Optional
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ColumnDetector:
    """Detecta y procesa layouts de múltiples columnas en PDFs"""

    def __init__(self, threshold_gap: float = 50.0, min_column_width: float = 150.0):
        """
        Args:
            threshold_gap: Espacio mínimo (en puntos) para considerar separación de columnas
            min_column_width: Ancho mínimo de una columna válida
        """
        self.threshold_gap = threshold_gap
        self.min_column_width = min_column_width

    def detectar_columnas(self, words: List[Dict]) -> Tuple[int, List[Tuple[float, float]]]:
        """
        Detecta el número de columnas y sus rangos X

        Args:
            words: Lista de palabras extraídas con pdfplumber (con coordenadas x0, x1, etc.)

        Returns:
            (num_columnas, [(x_min, x_max), ...]) - Número de columnas y sus rangos
        """
        if not words:
            return 1, []

        # Agrupar palabras por posición X (inicio de palabra)
        x_positions = [w['x0'] for w in words]

        # Calcular histograma de posiciones X
        # Agrupar en bins de 10 puntos para suavizar
        bin_size = 10
        x_min = min(x_positions)
        # FIXED: Usar x1 (fin de palabra) para x_max para no cortar dígitos decimales al final
        x_max = max(w['x1'] for w in words)

        bins = defaultdict(int)
        for x in x_positions:
            bin_key = int((x - x_min) / bin_size)
            bins[bin_key] += 1

        # Detectar gaps (espacios sin texto)
        sorted_bins = sorted(bins.keys())
        gaps = []

        for i in range(len(sorted_bins) - 1):
            current_bin = sorted_bins[i]
            next_bin = sorted_bins[i + 1]

            # Si hay un gap grande entre bins
            gap_size = (next_bin - current_bin) * bin_size
            if gap_size > self.threshold_gap:
                gap_center = x_min + (current_bin + next_bin) / 2 * bin_size
                gaps.append(gap_center)

        # Si no hay gaps, es una sola columna
        if not gaps:
            return 1, [(x_min, x_max)]

        # Definir rangos de columnas basados en gaps
        column_ranges = []
        prev_x = x_min

        for gap_x in gaps:
            # Verificar que la columna tenga ancho mínimo
            if gap_x - prev_x >= self.min_column_width:
                column_ranges.append((prev_x, gap_x))
                prev_x = gap_x

        # Última columna
        if x_max - prev_x >= self.min_column_width:
            column_ranges.append((prev_x, x_max))

        num_columnas = len(column_ranges)

        logger.info(f"Detectadas {num_columnas} columna(s): {column_ranges}")

        return num_columnas, column_ranges

    def extraer_por_columnas(self, words: List[Dict]) -> List[str]:
        """
        Extrae texto ordenado por columnas (izquierda a derecha, arriba a abajo)

        Args:
            words: Lista de palabras con coordenadas

        Returns:
            Lista de líneas de texto ordenadas correctamente
        """
        if not words:
            return []

        # Detectar columnas
        num_columnas, column_ranges = self.detectar_columnas(words)

        if num_columnas == 1:
            # Layout vertical normal, procesar directamente
            return self._procesar_columna_simple(words)

        # Layout de múltiples columnas
        logger.info(f"Procesando PDF con {num_columnas} columnas")

        # Separar palabras por columna
        columnas = [[] for _ in range(num_columnas)]

        for word in words:
            word_x = word['x0']

            # Asignar palabra a la columna correcta
            for i, (x_min, x_max) in enumerate(column_ranges):
                if x_min <= word_x < x_max:
                    columnas[i].append(word)
                    break

        # Procesar cada columna por separado y combinar
        all_lines = []
        for i, col_words in enumerate(columnas):
            if col_words:
                logger.debug(f"Procesando columna {i+1} con {len(col_words)} palabras")
                col_lines = self._procesar_columna_simple(col_words)
                all_lines.extend(col_lines)

        return all_lines

    def _procesar_columna_simple(self, words: List[Dict]) -> List[str]:
        """
        Procesa una columna simple: agrupa palabras en líneas por posición Y

        Args:
            words: Lista de palabras de una columna

        Returns:
            Lista de líneas de texto
        """
        if not words:
            return []

        # Agrupar palabras por línea (posición Y similar)
        # Tolerancia: palabras en el mismo rango Y (±5 puntos) van en la misma línea
        # Aumentado de 3 a 5 para manejar mejor PDFs con texto ligeramente desalineado
        y_tolerance = 5

        # Ordenar palabras por Y (arriba a abajo), luego por X (izquierda a derecha)
        sorted_words = sorted(words, key=lambda w: (w['top'], w['x0']))

        lines = []
        current_line = []
        current_y = None

        for word in sorted_words:
            word_y = word['top']
            word_text = word['text']

            # Si es la primera palabra o está en una nueva línea
            if current_y is None or abs(word_y - current_y) > y_tolerance:
                # Guardar línea anterior si existe
                if current_line:
                    line_text = ' '.join(current_line)
                    lines.append(line_text)

                # Iniciar nueva línea
                current_line = [word_text]
                current_y = word_y
            else:
                # Añadir a línea actual
                current_line.append(word_text)

        # Guardar última línea
        if current_line:
            line_text = ' '.join(current_line)
            lines.append(line_text)

        return lines

    def analizar_layout(self, words: List[Dict]) -> Dict:
        """
        Analiza el layout de la página y retorna información detallada

        Args:
            words: Lista de palabras con coordenadas

        Returns:
            dict con información del layout
        """
        if not words:
            return {
                'num_columnas': 0,
                'tipo': 'vacio',
                'orientacion': None,
                'columnas': []
            }

        num_columnas, column_ranges = self.detectar_columnas(words)

        # Determinar orientación (vertical vs apaisado)
        page_width = max(w['x1'] for w in words) - min(w['x0'] for w in words)
        page_height = max(w['bottom'] for w in words) - min(w['top'] for w in words)
        orientacion = 'apaisado' if page_width > page_height else 'vertical'

        return {
            'num_columnas': num_columnas,
            'tipo': 'multicolumna' if num_columnas > 1 else 'columna_simple',
            'orientacion': orientacion,
            'columnas': [
                {
                    'num': i + 1,
                    'x_min': x_min,
                    'x_max': x_max,
                    'ancho': x_max - x_min
                }
                for i, (x_min, x_max) in enumerate(column_ranges)
            ],
            'dimensiones': {
                'ancho': page_width,
                'alto': page_height
            }
        }


# Función helper para uso rápido
def extraer_con_columnas(words: List[Dict]) -> List[str]:
    """
    Extrae líneas de texto detectando automáticamente columnas

    Args:
        words: Lista de palabras de pdfplumber

    Returns:
        Lista de líneas ordenadas correctamente
    """
    detector = ColumnDetector()
    return detector.extraer_por_columnas(words)


if __name__ == "__main__":
    # Test básico
    print("=== Test de ColumnDetector ===\n")

    # Simular palabras de 2 columnas
    test_words = [
        # Columna izquierda
        {'text': 'CAPÍTULO', 'x0': 50, 'x1': 120, 'top': 100, 'bottom': 115},
        {'text': '01', 'x0': 130, 'x1': 150, 'top': 100, 'bottom': 115},
        {'text': 'Partida', 'x0': 50, 'x1': 100, 'top': 120, 'bottom': 135},
        {'text': 'A', 'x0': 110, 'x1': 120, 'top': 120, 'bottom': 135},

        # Columna derecha (gap de ~200 puntos)
        {'text': 'CAPÍTULO', 'x0': 350, 'x1': 420, 'top': 100, 'bottom': 115},
        {'text': '02', 'x0': 430, 'x1': 450, 'top': 100, 'bottom': 115},
        {'text': 'Partida', 'x0': 350, 'x1': 400, 'top': 120, 'bottom': 135},
        {'text': 'D', 'x0': 410, 'x1': 420, 'top': 120, 'bottom': 135},
    ]

    detector = ColumnDetector()

    # Analizar layout
    layout = detector.analizar_layout(test_words)
    print("Layout detectado:")
    print(f"  Tipo: {layout['tipo']}")
    print(f"  Número de columnas: {layout['num_columnas']}")
    print(f"  Orientación: {layout['orientacion']}")
    print(f"\nColumnas:")
    for col in layout['columnas']:
        print(f"  - Columna {col['num']}: X=[{col['x_min']:.1f}, {col['x_max']:.1f}], Ancho={col['ancho']:.1f}")

    # Extraer líneas
    print("\nLíneas extraídas:")
    lines = detector.extraer_por_columnas(test_words)
    for i, line in enumerate(lines, 1):
        print(f"  {i}. {line}")
