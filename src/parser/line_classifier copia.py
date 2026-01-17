"""
Clasificador de líneas de presupuesto.
Identifica el tipo de cada línea: CAPÍTULO, SUBCAPÍTULO, PARTIDA, etc.
"""

import re
import logging
from enum import Enum
from typing import Optional, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TipoLinea(Enum):
    """Tipos de línea en un presupuesto"""
    CAPITULO = "capitulo"
    SUBCAPITULO = "subcapitulo"
    APARTADO = "apartado"
    PARTIDA_HEADER = "partida_header"
    PARTIDA_DESCRIPCION = "partida_descripcion"
    PARTIDA_DATOS = "partida_datos"
    TOTAL = "total"
    HEADER_TABLA = "header_tabla"
    IGNORAR = "ignorar"


class LineClassifier:
    """Clasificador inteligente de líneas de presupuesto"""

    # Patrones regex compilados - Soportan códigos alfanuméricos (C01) y numéricos (01)
    PATRON_CAPITULO = re.compile(r'^CAPÍTULO\s+([A-Z]?\d+)\s+(.+)', re.IGNORECASE)
    PATRON_SUBCAPITULO = re.compile(r'^SUBCAPÍTULO\s+([A-Z]?\d+(?:\.\d+)+)\s+(.+)', re.IGNORECASE)
    PATRON_APARTADO = re.compile(r'^APARTADO\s+([A-Z]?\d+(?:\.\d+)+)\s+(.+)', re.IGNORECASE)

    # Patrones alternativos para formatos implícitos (sin palabra CAPÍTULO/SUBCAPÍTULO)
    # IMPORTANTE: Ya NO distinguimos entre SUBCAPÍTULO y APARTADO por número de puntos
    # Un código con 1+ puntos (01.01, 01.04.01, 01.04.01.01) es SUBCAPÍTULO
    # Formato: "01 FASE 2" → Capítulo
    # Formato: "01.01 LEVANTANDO DE ELEMENTOS" → Subcapítulo
    # Formato: "01.04.01 DESCRIPCIÓN" → Subcapítulo (no apartado)
    # Permite letras, números y espacios en el nombre (FASE 2, FASE II, etc.)
    PATRON_CAPITULO_IMPLICITO = re.compile(r'^(\d{1,2})\s+([A-Z][A-Z0-9\s]+)$')
    # Patrón subcapítulo generalizado: acepta 1 o más niveles (01.01, 01.04.01, 01.04.01.01, etc.)
    PATRON_SUBCAPITULO_IMPLICITO = re.compile(r'^(\d{1,2}(?:\.\d{1,2})+)\s+([A-Z][A-Z0-9\s]+)$')
    # NOTA: Ya NO usamos PATRON_APARTADO_IMPLICITO - todos los códigos con puntos son subcapítulos
    PATRON_APARTADO_IMPLICITO = None
    # Patrón más flexible: permite espacios limitados en el código, códigos numéricos y alfanuméricos
    # También acepta variaciones de unidades con separadores (P.A., P:A:, etc.)
    # Permite unidad pegada al resumen (P:A:REPARACIONES) usando \s* en vez de \s+
    # Código: DEBE EMPEZAR con MAYÚSCULA o NÚMERO (no minúscula), luego puede tener minúsculas
    # Ejemplos: "01.01", "DEM06", "U11SAM020", "PY10AA012a", "RETIRADA001", "E08PEA090"
    # NO matchea: "rlores a 2" (empieza con minúscula)
    # Unidades: con \b para evitar matches parciales (ej: "pa" no debe matchear "para")
    # Incluye: m, m2, m3, m², m³, ml, ud, u, uf, pa, kg, h, l, t
    # Soporta tanto "m2" como "m²" (superíndice Unicode)
    # Patrón simplificado: CÓDIGO (sin espacios) + UNIDAD + DESCRIPCIÓN
    # Usa \S+ para el código (cualquier secuencia sin espacios)
    PATRON_PARTIDA = re.compile(r'^(\S+)\s+(m[2-3²³]?|M[2-3²³]?|Ml|ml|M\.?|m\.|[Uu][Dd]?|[Uu][Ff]|PA|Pa|pa|[Pp][\.:][Aa][\.::]?|kg|Kg|KG|[HhLlTt])\s+(.+)', re.IGNORECASE)
    # Patrón para partida completa con números al final: CÓDIGO UNIDAD DESCRIPCIÓN CANTIDAD PRECIO IMPORTE
    # Este patrón debe evaluarse ANTES que PATRON_PARTIDA para capturar líneas completas
    # Usa \S+ para código (cualquier secuencia sin espacios) para flexibilidad máxima
    # Patrón de números simplificado: acepta dígitos con comas y puntos (9,00 o 1.234,56)
    PATRON_PARTIDA_COMPLETA = re.compile(
        r'^([A-Z0-9]\S*)\s+(m[2-3²³]?|M[2-3²³]?|Ml|ml|M\.?|m\.|[Uu][Dd]?|[Uu][Ff]|PA|Pa|pa|[Pp][\.:][Aa][\.::]?|kg|Kg|KG|[HhLlTt])\s+(.+?)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s*$'
    )
    PATRON_TOTAL = re.compile(r'^TOTAL\s+(SUBCAPÍTULO|CAPÍTULO|APARTADO)', re.IGNORECASE)
    # Patrón flexible: acepta números enteros o con decimales (formato español con coma)
    # Ejemplos: "1 1", "1,00 400,00 400,00", "2 2,49 4,98", "1 530,00 530,00"
    PATRON_NUMEROS_FINAL = re.compile(r'(\d{1,3}(?:\.\d{3})*(?:,\d{1,2})?)\s+(\d{1,3}(?:\.\d{3})*(?:,\d{1,2})?)\s+(\d{1,3}(?:\.\d{3})*(?:,\d{1,2})?)\s*$')

    @classmethod
    def clasificar(cls, linea: str, contexto: Optional[Dict] = None) -> Dict:
        """
        Clasifica una línea según su tipo

        Args:
            linea: string a clasificar
            contexto: dict opcional con información de líneas anteriores

        Returns:
            dict con tipo y datos extraídos
        """
        if not linea or not linea.strip():
            return {'tipo': TipoLinea.IGNORAR, 'datos': None}

        linea = linea.strip()

        # 1. Verificar si es CAPÍTULO
        match = cls.PATRON_CAPITULO.match(linea)
        if match:
            return {
                'tipo': TipoLinea.CAPITULO,
                'datos': {
                    'codigo': match.group(1),
                    'nombre': match.group(2).strip()
                }
            }

        # 2. Verificar si es SUBCAPÍTULO
        match = cls.PATRON_SUBCAPITULO.match(linea)
        if match:
            return {
                'tipo': TipoLinea.SUBCAPITULO,
                'datos': {
                    'codigo': match.group(1),
                    'nombre': match.group(2).strip()
                }
            }

        # 3. Verificar si es APARTADO
        match = cls.PATRON_APARTADO.match(linea)
        if match:
            return {
                'tipo': TipoLinea.APARTADO,
                'datos': {
                    'codigo': match.group(1),
                    'nombre': match.group(2).strip()
                }
            }

        # 3b. Verificar formatos implícitos (sin palabra CAPÍTULO/SUBCAPÍTULO/APARTADO)
        # CAMBIO: Ya NO distinguimos apartados de subcapítulos por número de puntos
        # Todos los códigos con puntos (01.01, 01.04.01, etc.) se tratan como SUBCAPÍTULOS
        # La jerarquía se determina por el número de niveles en el código

        # Subcapítulo implícito: "01.01 LEVANTANDO DE ELEMENTOS" o "01.04.01 PAVIMENTO PERMEABLE"
        # Acepta cualquier número de niveles (1 o más puntos)
        match = cls.PATRON_SUBCAPITULO_IMPLICITO.match(linea)
        if match:
            return {
                'tipo': TipoLinea.SUBCAPITULO,
                'datos': {
                    'codigo': match.group(1),
                    'nombre': match.group(2).strip()
                }
            }

        # Capítulo implícito: "01 FASE 2"
        match = cls.PATRON_CAPITULO_IMPLICITO.match(linea)
        if match:
            return {
                'tipo': TipoLinea.CAPITULO,
                'datos': {
                    'codigo': match.group(1),
                    'nombre': match.group(2).strip()
                }
            }

        # 4. Verificar si es línea TOTAL
        match = cls.PATRON_TOTAL.match(linea)
        if match:
            return {
                'tipo': TipoLinea.TOTAL,
                'datos': {'nivel': match.group(1)}
            }

        # 4b. Ignorar líneas de mediciones especiales (no son partidas)
        # Estas líneas contienen mediciones intermedias o ajustes
        if linea.upper().startswith('A DEDUCIR') or linea.upper().startswith('A DESCONTAR'):
            return {'tipo': TipoLinea.IGNORAR, 'datos': None}

        # 5. Verificar si es PARTIDA COMPLETA (con números al final)
        # Estrategia de 2 pasos: primero extraer números, luego código/unidad/descripción
        # Esto evita problemas con regex greedy
        numeros_match = cls.PATRON_NUMEROS_FINAL.search(linea)
        if numeros_match:
            # Extraer la parte sin números
            linea_sin_numeros = linea[:numeros_match.start()].strip()

            # Verificar si la parte sin números es una partida (código + unidad + descripción)
            header_match = cls.PATRON_PARTIDA.match(linea_sin_numeros)
            if header_match:
                return {
                    'tipo': TipoLinea.PARTIDA_HEADER,
                    'datos': {
                        'codigo': header_match.group(1).strip(),
                        'unidad': header_match.group(2).strip(),
                        'resumen': header_match.group(3).strip(),
                        'cantidad_str': numeros_match.group(1),
                        'precio_str': numeros_match.group(2),
                        'importe_str': numeros_match.group(3)
                    }
                }
            # Si tiene números pero no es partida, clasificar como PARTIDA_DATOS
            else:
                return {
                    'tipo': TipoLinea.PARTIDA_DATOS,
                    'datos': {
                        'cantidad_str': numeros_match.group(1),
                        'precio_str': numeros_match.group(2),
                        'importe_str': numeros_match.group(3)
                    }
                }

        # 6. Verificar si es header de PARTIDA (sin números)
        match = cls.PATRON_PARTIDA.match(linea)
        if match:
            return {
                'tipo': TipoLinea.PARTIDA_HEADER,
                'datos': {
                    'codigo': match.group(1).strip(),
                    'unidad': match.group(2).strip(),
                    'resumen': match.group(3).strip()
                }
            }

        # 7. Verificar si es header de tabla (CÓDIGO, RESUMEN, CANTIDAD, etc.)
        if cls._es_header_tabla(linea):
            return {'tipo': TipoLinea.HEADER_TABLA, 'datos': None}

        # 8. Si tiene contexto de partida activa, es DESCRIPCIÓN
        if contexto and contexto.get('partida_activa'):
            return {
                'tipo': TipoLinea.PARTIDA_DESCRIPCION,
                'datos': {'texto': linea}
            }

        # 9. Por defecto, IGNORAR
        return {'tipo': TipoLinea.IGNORAR, 'datos': None}

    @staticmethod
    def _es_header_tabla(linea: str) -> bool:
        """Detecta si es una línea de encabezado de tabla"""
        headers = ['CÓDIGO', 'RESUMEN', 'CANTIDAD', 'PRECIO', 'IMPORTE']
        linea_upper = linea.upper()
        coincidencias = sum(1 for h in headers if h in linea_upper)
        return coincidencias >= 3

    @classmethod
    def clasificar_bloque(cls, lineas: list) -> list:
        """
        Clasifica un bloque de líneas con contexto

        Args:
            lineas: lista de strings

        Returns:
            lista de dicts con clasificaciones
        """
        resultados = []
        contexto = {'partida_activa': False}

        for linea in lineas:
            clasificacion = cls.clasificar(linea, contexto)
            resultados.append({
                'linea': linea,
                'tipo': clasificacion['tipo'],
                'datos': clasificacion['datos']
            })

            # Actualizar contexto
            if clasificacion['tipo'] == TipoLinea.PARTIDA_HEADER:
                contexto['partida_activa'] = True
            elif clasificacion['tipo'] == TipoLinea.PARTIDA_DATOS:
                contexto['partida_activa'] = False
            elif clasificacion['tipo'] in [TipoLinea.CAPITULO, TipoLinea.SUBCAPITULO, TipoLinea.APARTADO]:
                contexto['partida_activa'] = False

        return resultados

    @classmethod
    def agrupar_partidas(cls, clasificaciones: list) -> list:
        """
        Agrupa líneas clasificadas en partidas completas

        Args:
            clasificaciones: lista de dicts con clasificaciones

        Returns:
            lista de partidas completas
        """
        partidas = []
        partida_actual = None

        for item in clasificaciones:
            tipo = item['tipo']

            if tipo == TipoLinea.PARTIDA_HEADER:
                # Guardar partida anterior si existe
                if partida_actual:
                    partidas.append(partida_actual)

                # Iniciar nueva partida
                partida_actual = {
                    'codigo': item['datos']['codigo'],
                    'unidad': item['datos']['unidad'],
                    'resumen': item['datos']['resumen'],
                    'descripcion_lineas': [],
                    'cantidad': None,
                    'precio': None,
                    'importe': None
                }

            elif tipo == TipoLinea.PARTIDA_DESCRIPCION and partida_actual:
                partida_actual['descripcion_lineas'].append(item['datos']['texto'])

            elif tipo == TipoLinea.PARTIDA_DATOS and partida_actual:
                partida_actual['cantidad_str'] = item['datos']['cantidad_str']
                partida_actual['precio_str'] = item['datos']['precio_str']
                partida_actual['importe_str'] = item['datos']['importe_str']

                # Cerrar partida
                partidas.append(partida_actual)
                partida_actual = None

        # Guardar última partida si quedó abierta
        if partida_actual:
            partidas.append(partida_actual)

        return partidas


if __name__ == "__main__":
    # Test del clasificador
    print("=== Test de LineClassifier ===\n")

    lineas_test = [
        "CAPÍTULO C01 ACTUACIONES EN CALYPO FADO",
        "SUBCAPÍTULO C08.01 CALLE TENERIFE",
        "DEM06    Ml CORTE PAVIMENTO EXISTENTE",
        "Corte de pavimento de aglomerado asfáltico u hormigón, con cortadora de disco diamante, en calzadas, i/replanteo y p.p. de medios auxiliares.",
        "                                                630,00    1,12    705,60",
        "U01AB100 m DEMOLICIÓN Y LEVANTADO DE BORDILLO AISLADO",
        "Demolición y levantado de bordillo de cualquier tipo en tramos aislados de menos de 10 m de longitud, para reparaciones puntuales.",
        "                                                630,00    5,40    3.402,00",
        "TOTAL SUBCAPÍTULO C08.01 CALLE TENERIFE......................... 110.289,85"
    ]

    clasificaciones = LineClassifier.clasificar_bloque(lineas_test)

    print("Clasificación línea por línea:")
    print("-" * 80)
    for item in clasificaciones:
        tipo_str = item['tipo'].value
        linea_corta = item['linea'][:60] + "..." if len(item['linea']) > 60 else item['linea']
        print(f"{tipo_str:20s} | {linea_corta}")

    print("\n\nPartidas agrupadas:")
    print("-" * 80)
    partidas = LineClassifier.agrupar_partidas(clasificaciones)

    for i, partida in enumerate(partidas, 1):
        print(f"\nPartida {i}:")
        print(f"  Código: {partida['codigo']}")
        print(f"  Unidad: {partida['unidad']}")
        print(f"  Resumen: {partida['resumen']}")
        if partida.get('cantidad_str'):
            print(f"  Cantidad: {partida['cantidad_str']}")
            print(f"  Precio: {partida['precio_str']}")
            print(f"  Importe: {partida['importe_str']}")
