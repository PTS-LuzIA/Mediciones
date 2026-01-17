"""
Normalizador de datos extraídos.
Convierte strings a números, limpia textos, maneja formatos españoles.
"""

import re
import logging
from typing import Optional, Union

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Normalizer:
    """Normaliza datos de mediciones"""

    @staticmethod
    def limpiar_numero_espanol(texto: str) -> Optional[float]:
        """
        Convierte números en formato español a float

        Ejemplos:
            "1.605,90" -> 1605.90
            "630,00" -> 630.0
            "14,24" -> 14.24

        Args:
            texto: string con número en formato español

        Returns:
            float o None si no se puede convertir
        """
        if not texto:
            return None

        try:
            # Eliminar espacios
            texto = texto.strip()

            # Reemplazar punto (separador de miles) por nada
            texto = texto.replace('.', '')

            # Reemplazar coma (decimal) por punto
            texto = texto.replace(',', '.')

            return float(texto)

        except (ValueError, AttributeError):
            logger.warning(f"No se pudo convertir '{texto}' a número")
            return None

    @staticmethod
    def extraer_numeros_linea(linea: str) -> list:
        """
        Extrae todos los números de una línea

        Args:
            linea: string con posibles números

        Returns:
            lista de floats
        """
        # Patrón para números españoles: 1.234,56 o 234,56
        patron = r'\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2}|\d+,\d+|\d+'

        matches = re.findall(patron, linea)
        numeros = []

        for match in matches:
            num = Normalizer.limpiar_numero_espanol(match)
            if num is not None:
                numeros.append(num)

        return numeros

    @staticmethod
    def extraer_tres_numeros_finales(linea: str) -> tuple:
        """
        Extrae los últimos 3 números de una línea (cantidad, precio, importe)

        Args:
            linea: string que termina con números

        Returns:
            tuple (cantidad, precio, importe) o (None, None, None)
        """
        numeros = Normalizer.extraer_numeros_linea(linea)

        if len(numeros) >= 3:
            # Los últimos 3 números
            return (numeros[-3], numeros[-2], numeros[-1])

        return (None, None, None)

    @staticmethod
    def limpiar_texto(texto: str) -> str:
        """
        Limpia y normaliza texto de descripciones

        Args:
            texto: string a limpiar

        Returns:
            string limpio
        """
        if not texto:
            return ""

        # Eliminar espacios múltiples
        texto = re.sub(r'\s+', ' ', texto)

        # Eliminar guiones finales de línea partida
        texto = texto.replace('- ', '')

        # Strip general
        texto = texto.strip()

        return texto

    @staticmethod
    def normalizar_unidad(unidad: str) -> str:
        """
        Normaliza unidades de medida

        Args:
            unidad: string con unidad (m, m2, Ud, etc.)

        Returns:
            unidad normalizada
        """
        if not unidad:
            return ""

        unidad = unidad.strip()

        # Normalizar variaciones de PA (Partida Alzada)
        # P:A:, P.A., P:A, p.a. -> PA
        if re.match(r'^[Pp][\.:]+[Aa][\.:]*$', unidad):
            return 'PA'

        unidad_lower = unidad.lower()

        # Mapeo de variaciones
        mapeo = {
            'ud': 'Ud',
            'u': 'Ud',
            'ml': 'm',
            'm.': 'm',
            'm2': 'm²',
            'm3': 'm³',
            'pa': 'PA',
        }

        return mapeo.get(unidad_lower, unidad.capitalize())

    @staticmethod
    def extraer_codigo(linea: str) -> Optional[str]:
        """
        Extrae código de partida del inicio de línea

        Ejemplos:
            "DEM06    Ml CORTE..." -> "DEM06"
            "U01AB100 m DEMOLICIÓN..." -> "U01AB100"

        Args:
            linea: string con código al inicio

        Returns:
            código o None
        """
        # Patrón: letras mayúsculas seguidas de números/puntos
        match = re.match(r'^([A-Z][A-Z0-9\.]+)\s+', linea)

        if match:
            return match.group(1).strip()

        return None

    @staticmethod
    def extraer_unidad(linea: str) -> Optional[str]:
        """
        Extrae unidad de medida después del código

        Ejemplos:
            "DEM06    Ml CORTE..." -> "m"
            "U01AB100 m DEMOLICIÓN..." -> "m"
            "REC POZ  ud PUESTA..." -> "Ud"

        Args:
            linea: string con unidad después del código

        Returns:
            unidad normalizada o None
        """
        # Patrón: código + espacios + unidad
        match = re.match(r'^[A-Z][A-Z0-9\.]+\s+(m[2-3]?|Ml|ml|M|ud|Ud|U|pa|Pa)\s+', linea, re.IGNORECASE)

        if match:
            unidad_raw = match.group(1)
            return Normalizer.normalizar_unidad(unidad_raw)

        return None

    @staticmethod
    def es_linea_partida(linea: str) -> bool:
        """
        Detecta si una línea es cabecera de partida

        Args:
            linea: string a evaluar

        Returns:
            True si es cabecera de partida
        """
        # Debe empezar con código
        codigo = Normalizer.extraer_codigo(linea)
        if not codigo:
            return False

        # Debe tener unidad
        unidad = Normalizer.extraer_unidad(linea)
        if not unidad:
            return False

        return True

    @staticmethod
    def es_linea_con_numeros(linea: str) -> bool:
        """
        Detecta si una línea tiene números (cantidad, precio, importe)

        Args:
            linea: string a evaluar

        Returns:
            True si tiene al menos 3 números
        """
        numeros = Normalizer.extraer_numeros_linea(linea)
        return len(numeros) >= 3

    @staticmethod
    def validar_importe(cantidad: float, precio: float, importe: float, tolerancia: float = 0.05) -> bool:
        """
        Valida que cantidad × precio ≈ importe

        Args:
            cantidad: cantidad
            precio: precio unitario
            importe: importe total
            tolerancia: margen de error permitido

        Returns:
            True si la validación pasa
        """
        if cantidad is None or precio is None or importe is None:
            return False

        calculado = round(cantidad * precio, 2)
        diferencia = abs(calculado - importe)

        return diferencia <= tolerancia

    @staticmethod
    def reconstruir_descripcion(lineas: list) -> str:
        """
        Une múltiples líneas de descripción en una sola

        Args:
            lineas: lista de strings

        Returns:
            descripción completa limpia
        """
        # Unir líneas
        descripcion = ' '.join(lineas)

        # Limpiar
        descripcion = Normalizer.limpiar_texto(descripcion)

        return descripcion


if __name__ == "__main__":
    # Tests
    print("=== Tests de Normalizer ===\n")

    # Test números españoles
    print("1. Conversión de números:")
    tests_numeros = ["1.605,90", "630,00", "14,24", "0,00", "110.289,85"]
    for num_str in tests_numeros:
        resultado = Normalizer.limpiar_numero_espanol(num_str)
        print(f"  {num_str:>12} -> {resultado}")

    # Test extracción de 3 números
    print("\n2. Extracción de cantidad, precio, importe:")
    linea_test = "                                                630,00    1,12    705,60"
    cant, prec, imp = Normalizer.extraer_tres_numeros_finales(linea_test)
    print(f"  Línea: '{linea_test}'")
    print(f"  Cantidad: {cant}, Precio: {prec}, Importe: {imp}")

    # Test validación
    print("\n3. Validación de importe:")
    es_valido = Normalizer.validar_importe(cant, prec, imp)
    print(f"  {cant} × {prec} = {cant * prec:.2f} ≈ {imp} -> {'✓ Válido' if es_valido else '✗ Inválido'}")

    # Test detección de partida
    print("\n4. Detección de partida:")
    lineas_test = [
        "DEM06    Ml CORTE PAVIMENTO EXISTENTE",
        "U01AB100 m DEMOLICIÓN Y LEVANTADO DE BORDILLO AISLADO",
        "Corte de pavimento de aglomerado asfáltico u hormigón..."
    ]
    for linea in lineas_test:
        es_partida = Normalizer.es_linea_partida(linea)
        print(f"  {'✓' if es_partida else '✗'} {linea[:50]}")

    # Test extracción código y unidad
    print("\n5. Extracción de código y unidad:")
    linea = "DEM06    Ml CORTE PAVIMENTO EXISTENTE"
    codigo = Normalizer.extraer_codigo(linea)
    unidad = Normalizer.extraer_unidad(linea)
    print(f"  Línea: '{linea}'")
    print(f"  Código: {codigo}, Unidad: {unidad}")
