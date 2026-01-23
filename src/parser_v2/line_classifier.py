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
    # MEJORADO: Permite también SIN espacio entre código y nombre: "01.04.06REPOSICIÓN"
    # Permite letras, números y espacios en el nombre (FASE 2, FASE II, etc.)
    # INCLUYE: Ñ, vocales con tilde (ÁÉÍÓÚ), y otros caracteres especiales
    # PERMITE: puntos, guiones, barras y paréntesis en nombres (ej: "MURO 1.1", "SECCIÓN A-A", "ÁREA 1/2")
    PATRON_CAPITULO_IMPLICITO = re.compile(r'^(\d{1,2})(?:\s+|(?=[A-ZÁÉÍÓÚÑ]))([A-ZÁÉÍÓÚÑ0-9\s./()\-]+)$')
    # Patrón subcapítulo generalizado: acepta 1 o más niveles (01.01, 01.04.01, 01.04.01.01, etc.)
    # MEJORADO: Detecta también códigos SIN espacio: "01.04.06REPOSICIÓN PAVIMENTO"
    # Usa lookahead (?=...) para permitir transición directa a mayúscula sin espacio
    # INCLUYE: Ñ, vocales con tilde (ÁÉÍÓÚ), y otros caracteres especiales
    # PERMITE: puntos, guiones, barras y paréntesis en nombres (ej: "MURO 1.1", "SECCIÓN A-A", "ÁREA 1/2")
    PATRON_SUBCAPITULO_IMPLICITO = re.compile(r'^(\d{1,2}(?:\.\d{1,2})+)(?:\s+|(?=[A-ZÁÉÍÓÚÑ]))([A-ZÁÉÍÓÚÑ0-9\s./()\-]+)$')
    # NOTA: Ya NO usamos PATRON_APARTADO_IMPLICITO - todos los códigos con puntos son subcapítulos
    PATRON_APARTADO_IMPLICITO = None
    # Patrón más flexible: permite espacios limitados en el código, códigos numéricos y alfanuméricos
    # También acepta variaciones de unidades con separadores (P.A., P:A:, etc.)
    # Permite unidad pegada al resumen (P:A:REPARACIONES) usando \s* en vez de \s+
    # Código: DEBE EMPEZAR con MAYÚSCULA o NÚMERO (no minúscula), luego puede tener minúsculas
    # Ejemplos: "01.01", "DEM06", "U11SAM020", "PY10AA012a", "RETIRADA001", "E08PEA090"
    # NO matchea: "rlores a 2" (empieza con minúscula)
    # Unidades: con \b para evitar matches parciales (ej: "pa" no debe matchear "para")
    # Incluye: m, m2, m3, m², m³, ml, ud, u, uf, pa, kg, h, l, t, ud/d, mes, día, año, sem, sm, d
    # Soporta tanto "m2" como "m²" (superíndice Unicode)
    # Soporta unidades compuestas con barra: ud/d, m/d, etc.
    # Patrón simplificado: CÓDIGO (sin espacios) + UNIDAD + DESCRIPCIÓN
    # Usa \S+ para el código (cualquier secuencia sin espacios)
    PATRON_PARTIDA = re.compile(r'^(\S+)\s+(m[2-3²³]?(?:/[a-z]+)?|M[2-3²³]?|Ml|ml|M\.?|m\.|[Uu][Dd]?(?:/[a-z]+)?|[Uu][Ff]|PA|Pa|pa|[Pp][\.:][Aa][\.::]?|kg|Kg|KG|[HhLlTt]|d|D|sm|SM|Sm|mes|MES|Mes|día|dia|Día|Dia|año|Año|sem|Sem)\s+(.+)', re.IGNORECASE)
    # Patrón para partida completa con números al final: CÓDIGO UNIDAD DESCRIPCIÓN CANTIDAD PRECIO IMPORTE
    # Este patrón debe evaluarse ANTES que PATRON_PARTIDA para capturar líneas completas
    # Usa \S+ para código (cualquier secuencia sin espacios) para flexibilidad máxima
    # Patrón de números simplificado: acepta dígitos con comas y puntos (9,00 o 1.234,56)
    PATRON_PARTIDA_COMPLETA = re.compile(
        r'^([A-Z0-9]\S*)\s+(m[2-3²³]?(?:/[a-z]+)?|M[2-3²³]?|Ml|ml|M\.?|m\.|[Uu][Dd]?(?:/[a-z]+)?|[Uu][Ff]|PA|Pa|pa|[Pp][\.:][Aa][\.::]?|kg|Kg|KG|[HhLlTt]|d|D|sm|SM|Sm|mes|MES|Mes|día|dia|Día|Dia|año|Año|sem|Sem)\s+(.+?)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s*$'
    )
    # Patrón para partida SIN unidad explícita: CÓDIGO DESCRIPCIÓN CANTIDAD PRECIO IMPORTE
    # Para partidas donde la unidad está implícita en el código o simplemente no aparece
    # Ejemplo: "APUDm23E27HE01m02.1 ESMALTE-LACA SATINADO S/METAL 808,50 13,17 10.647,95"
    # Ejemplo: "APUDm23E05AP02u0dA PLACA ANCLAJE S275 40x25x2cm SIN GARROTAS 95,00 51,55 4.897,25"
    # Se asignará unidad "X" por defecto
    # IMPORTANTE: La descripción debe empezar con letra mayúscula (permite números después)
    # Usa .+? (lazy) para capturar todo hasta encontrar los 3 números finales
    PATRON_PARTIDA_SIN_UNIDAD = re.compile(
        r'^([A-Z0-9]\S*)\s+([A-ZÁÉÍÓÚÑ].+?)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s*$'
    )
    # Patrón para TOTAL con código explícito: "TOTAL SUBCAPÍTULO 01.04.01  12.345,67"
    PATRON_TOTAL = re.compile(r'^TOTAL\s+(SUBCAPÍTULO|CAPÍTULO|APARTADO)\s+([\d\.]+)', re.IGNORECASE)
    # Patrón alternativo para TOTAL con puntos: "TOTAL 01.04.01....... 49.578,18"
    PATRON_TOTAL_ALTERNATIVO = re.compile(
        r'^TOTAL\s+(\d{1,2}(?:\.\d{1,2})*)[\s\.]+[\d.,]+\s*$',
        re.IGNORECASE
    )
    # Patrón flexible: acepta números enteros o con decimales (formato español con coma)
    # Ejemplos: "1 1", "1,00 400,00 400,00", "2 2,49 4,98", "1 530,00 530,00"
    # Soporta AMBOS formatos:
    #   - Con punto de miles: 10.653,50
    #   - Sin punto de miles: 10653,50 (común en algunos presupuestos)
    # Estrategia: \d+ acepta cualquier cantidad de dígitos, opcionalmente seguido de punto de miles
    PATRON_NUMEROS_FINAL = re.compile(r'(\d+(?:\.\d{3})*(?:,\d{1,4})?)\s+(\d+(?:\.\d{3})*(?:,\d{1,4})?)\s+(\d+(?:\.\d{3})*(?:,\d{1,4})?)\s*$')

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

        # 0. FILTRO: Ignorar líneas de paginación (solo números y espacios)
        # Ejemplos: "62", "63 63", "1 2", "123"
        # Esto evita que "63 63" se clasifique incorrectamente como capítulo
        if re.match(r'^\d+(?:\s+\d+)*\s*$', linea):
            return {'tipo': TipoLinea.IGNORAR, 'datos': None}

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

        # 4. Verificar si es línea TOTAL con formato estándar
        match = cls.PATRON_TOTAL.match(linea)
        if match:
            return {
                'tipo': TipoLinea.TOTAL,
                'datos': {
                    'nivel': match.group(1),
                    'codigo': match.group(2) if len(match.groups()) > 1 else None
                }
            }

        # 4b. Verificar formato alternativo de TOTAL (con puntos suspensivos)
        match = cls.PATRON_TOTAL_ALTERNATIVO.match(linea)
        if match:
            return {
                'tipo': TipoLinea.TOTAL,
                'datos': {
                    'nivel': 'SUBCAPÍTULO',
                    'codigo': match.group(1)
                }
            }

        # 4c. Ignorar líneas de mediciones especiales (no son partidas)
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
                codigo = header_match.group(1).strip()
                unidad = header_match.group(2).strip()
                resumen = header_match.group(3).strip()

                # Caso normal: partida con código + unidad + resumen
                return {
                    'tipo': TipoLinea.PARTIDA_HEADER,
                    'datos': {
                        'codigo': codigo,
                        'unidad': unidad,
                        'resumen': resumen,
                        'cantidad_str': numeros_match.group(1),
                        'precio_str': numeros_match.group(2),
                        'importe_str': numeros_match.group(3)
                    }
                }
            # Si tiene números pero no matchea con PATRON_PARTIDA (no hay unidad detectada)
            # probar primero con el patrón de partida sin unidad explícita
            else:
                # PRIMERO: Probar patrón de partida sin unidad (SOLUCIÓN 2 - Opción A)
                # Ejemplo: "APUDm23E27HE01m02.1 ESMALTE-LACA SATINADO S/METAL 808,50 13,17 10.647,95"
                partida_sin_unidad_match = cls.PATRON_PARTIDA_SIN_UNIDAD.match(linea)
                if partida_sin_unidad_match:
                    codigo = partida_sin_unidad_match.group(1).strip()
                    resumen = partida_sin_unidad_match.group(2).strip()
                    cantidad = partida_sin_unidad_match.group(3).strip()
                    precio = partida_sin_unidad_match.group(4).strip()
                    importe = partida_sin_unidad_match.group(5).strip()

                    # VALIDACIÓN: Rechazar si el código es un número con formato de importe
                    # Ejemplo: "29.672,05" NO es un código válido, es un TOTAL
                    patron_importe = re.compile(r'^\d+(?:\.\d{3})*,\d{2}$')
                    if patron_importe.match(codigo):
                        logger.debug(f"Código rechazado (formato de importe): '{codigo}'")
                        # No es una partida, continuar con otras clasificaciones
                    else:
                        logger.info(f"🔍 Partida sin unidad detectada: '{codigo}' - '{resumen[:40]}...' → Unidad='X'")

                        return {
                            'tipo': TipoLinea.PARTIDA_HEADER,
                            'datos': {
                                'codigo': codigo,
                                'unidad': 'X',  # Unidad por defecto
                                'resumen': resumen,
                                'cantidad_str': cantidad,
                                'precio_str': precio,
                                'importe_str': importe
                            }
                        }

                # Si no matchea con PATRON_PARTIDA_SIN_UNIDAD, intentar extraer CODIGO + TITULO (sin unidad en el medio)
                # Formato: "APUDes23UA014e LEVANTADO DE BORDILLO... 95,00 9,17 869,32"
                # Formato PEGADO: "APUI_V_mU16NROU822SUMINISTRO E INSTALACIÓN... 5,00 603,54 3.017,70"
                # IMPORTANTE: Ser MUY estricto para evitar falsos positivos
                # Código válido: letras+números (mayús/minús), mínimo 5 caracteres, sin puntos ni guiones al final
                # Título: DEBE empezar con MAYÚSCULA y tener palabras completas

                # IMPORTANTE: Primero probar PATRÓN 2 (código pegado) ANTES que PATRÓN 1
                # porque PATRÓN 1 es demasiado greedy y matchearía códigos pegados incorrectamente

                match_sin_unidad = None

                # PATRÓN 2 (NUEVO): Código PEGADO a título (sin espacio)
                # Buscar transición de minúscula/número a MAYÚSCULA que indica inicio de palabra descriptiva
                # Ejemplo: "APUI_V_mU16NROU822SUMINISTRO" → código="APUI_V_mU16NROU822", título="SUMINISTRO..."
                logger.debug(f"Probando detección de código pegado en '{linea_sin_numeros[:50]}'...")
                # Primero verificar si hay un patrón de código pegado
                # Buscar la transición (minúscula|número|_) → MAYÚSCULA
                # que indique inicio de palabra descriptiva (5+ letras mayúsculas)
                mejor_corte = -1
                mejor_puntuacion = 0  # Puntuación para elegir la mejor transición
                linea_candidata = linea_sin_numeros

                for i in range(len(linea_candidata) - 1):
                    char_actual = linea_candidata[i]
                    char_siguiente = linea_candidata[i + 1]

                    # Detectar transición: (minúscula|número|guión_bajo) → MAYÚSCULA
                    if (char_actual.islower() or char_actual.isdigit() or char_actual == '_') and char_siguiente.isupper():
                        # Verificar si lo que sigue es una palabra completa
                        resto = linea_candidata[i + 1:]

                        # Contar letras mayúsculas CONSECUTIVAS desde el inicio (sin números)
                        letras_consecutivas = 0
                        for c in resto:
                            if c.isupper():
                                letras_consecutivas += 1
                            else:
                                break

                        # También contar total de letras en la primera palabra
                        primera_palabra = resto.split(' ')[0] if ' ' in resto else resto[:20]
                        letras_total = sum(1 for c in primera_palabra if c.isupper())

                        # Verificar que haya espacio después
                        tiene_espacio = ' ' in resto[:30]

                        # Estrategia de puntuación:
                        # Preferir la PRIMERA palabra válida (con 5+ letras total)
                        # Esto toma "S2UMINISTRO" completo en lugar de solo "UMINISTRO"
                        # La puntuación es simplemente el índice invertido (primero = mayor puntuación)
                        puntuacion = 10000 - i  # Primeras transiciones tienen mayor puntuación

                        # Validar: debe tener >= 5 letras totales Y espacio
                        if letras_total >= 5 and tiene_espacio and puntuacion > mejor_puntuacion:
                            mejor_puntuacion = puntuacion
                            mejor_corte = i + 1

                if mejor_corte > 0:
                    codigo_detectado = linea_candidata[:mejor_corte]
                    titulo_detectado = linea_candidata[mejor_corte:]

                    # Validar que el código sea razonable (8-25 caracteres)
                    logger.debug(f"Código candidato detectado: '{codigo_detectado}' (longitud={len(codigo_detectado)})")
                    if 8 <= len(codigo_detectado) <= 25:
                        class MockMatch:
                            def __init__(self, cod, tit):
                                self.cod = cod
                                self.tit = tit
                            def group(self, n):
                                return self.cod if n == 1 else self.tit

                        match_sin_unidad = MockMatch(codigo_detectado, titulo_detectado)
                        logger.info(f"🔍 Código pegado detectado: '{codigo_detectado}' + '{titulo_detectado[:30]}...'")
                    else:
                        logger.debug(f"Código candidato rechazado (longitud: {len(codigo_detectado)})")

                # PATRÓN 1: Código seguido de espacio y título (solo si PATRÓN 2 no matcheó)
                if not match_sin_unidad:
                    # FLEXIBILIZADO: Acepta cualquier contenido después del código
                    # Esto permite referencias como "R5206 - TRIPLE BARRA..." que tienen números y guiones
                    patron_sin_unidad = re.compile(r'^([A-Z][A-Za-z0-9_]{4,})\s+(.+)$')
                    match_sin_unidad = patron_sin_unidad.match(linea_sin_numeros)

                if match_sin_unidad:
                    # Extraer usando el método .group() del match (funciona tanto para regex match como MockMatch)
                    codigo_detectado = match_sin_unidad.group(1).strip()
                    titulo_detectado = match_sin_unidad.group(2).strip()

                    # Validaciones adicionales MUY estrictas
                    unidades_comunes = re.compile(r'^(m[2-3²³]?|M[2-3²³]?|Ml|ml|M\.?|m\.|[Uu][Dd]?|[Uu][Ff]|PA|Pa|pa|[Pp][\.:][Aa][\.::]?|kg|Kg|KG|[HhLlTt])$', re.IGNORECASE)

                    # Patrón para detectar números con formato de importe español (ej: 29.672,05)
                    patron_importe = re.compile(r'^\d+(?:\.\d{3})*,\d{2}$')

                    # NO procesar si:
                    # - El código termina en punto (105/2008.)
                    # - El código tiene guion seguido de mayúscula (NTE-ADD)
                    # - El código es demasiado corto (< 5 chars)
                    # - El código es una unidad
                    # - El código es un número con formato de importe (ej: 29.672,05)
                    # - El título no tiene al menos 2 palabras
                    if (len(codigo_detectado) >= 5 and
                        not codigo_detectado.endswith('.') and
                        '-' not in codigo_detectado[-4:] and
                        not unidades_comunes.match(codigo_detectado) and
                        not patron_importe.match(codigo_detectado) and
                        len(titulo_detectado.split()) >= 2):

                        # Parece una partida válida con unidad solapada/faltante
                        logger.warning(f"⚠️  Partida sin unidad detectada: código='{codigo_detectado}', título='{titulo_detectado[:30]}...'")
                        logger.warning(f"   Probable solapamiento visual - asignando unidad='X'")

                        return {
                            'tipo': TipoLinea.PARTIDA_HEADER,
                            'datos': {
                                'codigo': codigo_detectado,
                                'unidad': 'X',  # Unidad desconocida por solapamiento
                                'resumen': titulo_detectado,
                                'cantidad_str': numeros_match.group(1),
                                'precio_str': numeros_match.group(2),
                                'importe_str': numeros_match.group(3),
                                'solapamiento_detectado': True
                            }
                        }

                # Si no matchea ningún patrón, clasificar como PARTIDA_DATOS
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
            codigo = match.group(1).strip()
            unidad = match.group(2).strip()
            resumen = match.group(3).strip()

            # Caso normal: partida con código + unidad + resumen
            return {
                'tipo': TipoLinea.PARTIDA_HEADER,
                'datos': {
                    'codigo': codigo,
                    'unidad': unidad,
                    'resumen': resumen
                }
            }

        # 6b. Verificar si es partida SIN UNIDAD (solapamiento) y sin números
        # Formato: "APUDes23UA014e LEVANTADO DE BORDILLO" (sin números al final)
        # FLEXIBILIZADO: Acepta cualquier contenido después del código
        patron_sin_unidad = re.compile(r'^([A-Z][A-Za-z0-9_]{4,})\s+(.+)$')
        match_sin_unidad = patron_sin_unidad.match(linea)

        if match_sin_unidad:
            codigo_detectado = match_sin_unidad.group(1).strip()
            titulo_detectado = match_sin_unidad.group(2).strip()

            # Validaciones adicionales MUY estrictas
            unidades_comunes = re.compile(r'^(m[2-3²³]?|M[2-3²³]?|Ml|ml|M\.?|m\.|[Uu][Dd]?|[Uu][Ff]|PA|Pa|pa|[Pp][\.:][Aa][\.::]?|kg|Kg|KG|[HhLlTt])$', re.IGNORECASE)

            # Patrón para detectar números con formato de importe español (ej: 29.672,05)
            patron_importe = re.compile(r'^\d+(?:\.\d{3})*,\d{2}$')

            # NO procesar si:
            # - El código es demasiado corto (< 5 chars)
            # - El código termina en punto (105/2008.)
            # - El código tiene guion seguido de mayúscula (NTE-ADD)
            # - El código es una unidad
            # - El código es un número con formato de importe (ej: 29.672,05)
            # - El título no tiene al menos 2 palabras
            if (len(codigo_detectado) >= 5 and
                not codigo_detectado.endswith('.') and
                '-' not in codigo_detectado[-4:] and
                not unidades_comunes.match(codigo_detectado) and
                not patron_importe.match(codigo_detectado) and
                len(titulo_detectado.split()) >= 2):

                logger.warning(f"⚠️  Partida sin unidad (sin números): código='{codigo_detectado}', título='{titulo_detectado[:30]}...'")
                logger.warning(f"   Probable solapamiento visual - asignando unidad='X'")

                return {
                    'tipo': TipoLinea.PARTIDA_HEADER,
                    'datos': {
                        'codigo': codigo_detectado,
                        'unidad': 'X',
                        'resumen': titulo_detectado,
                        'solapamiento_detectado': True
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
    def _unir_descripciones_continuadas(cls, clasificaciones: list) -> list:
        """
        Detecta y une líneas de descripción que continúan en la siguiente línea.

        Estrategia MEJORADA para códigos largos:
        1. Detecta PARTIDA_HEADER (independientemente del formato del resumen)
        2. Si la siguiente línea:
           - Está clasificada como IGNORAR o PARTIDA_DESCRIPCION
           - NO tiene código de partida al inicio
           - NO tiene números al final (cantidad/precio/importe)
           - Tiene texto descriptivo con ALGUNA mayúscula
           - NO es un header de tabla
           → Es continuación del resumen
        3. Une ambas líneas en la partida original

        Args:
            clasificaciones: lista de dicts con clasificaciones

        Returns:
            lista de clasificaciones con descripciones unidas
        """
        import re

        # Patrón para detectar código de partida al inicio
        patron_codigo_partida = re.compile(r'^[A-Z0-9]\S{4,}\s+')

        # Patrón para detectar números al final (cantidad/precio/importe)
        patron_numeros_final = re.compile(r'(\d+(?:\.\d{3})*(?:,\d{1,4})?)\s+(\d+(?:\.\d{3})*(?:,\d{1,4})?)\s+(\d+(?:\.\d{3})*(?:,\d{1,4})?)\s*$')

        resultados = []
        i = 0
        lineas_unidas = 0

        while i < len(clasificaciones):
            item_actual = clasificaciones[i]
            tipo_actual = item_actual['tipo']

            # Buscar PARTIDA_HEADER (cualquier formato de resumen)
            if tipo_actual == TipoLinea.PARTIDA_HEADER:
                datos_partida = item_actual['datos']
                resumen_actual = datos_partida.get('resumen', '')

                # Buscar siguiente línea (potencial continuación)
                if i + 1 < len(clasificaciones):
                    item_siguiente = clasificaciones[i + 1]
                    tipo_siguiente = item_siguiente['tipo']
                    linea_siguiente = item_siguiente['linea'].strip()

                    # Verificar si es continuación del resumen:
                    # 1. Línea clasificada como IGNORAR o PARTIDA_DESCRIPCION
                    # 2. NO tiene código de partida al inicio
                    # 3. NO tiene números al final (cantidad/precio/importe)
                    # 4. Tiene texto descriptivo (letras)
                    # 5. Tiene ALGUNA letra en MAYÚSCULAS (no todo minúsculas)
                    # 6. NO es header de tabla
                    # 7. Longitud razonable (no demasiado larga)
                    if (tipo_siguiente in [TipoLinea.IGNORAR, TipoLinea.PARTIDA_DESCRIPCION] and
                        linea_siguiente and
                        len(linea_siguiente) < 150 and
                        not patron_codigo_partida.match(linea_siguiente) and
                        not patron_numeros_final.search(linea_siguiente) and
                        not cls._es_header_tabla(linea_siguiente)):

                        # Verificar que tiene letras y TODAS están en mayúsculas
                        letras = [c for c in linea_siguiente if c.isalpha()]
                        if letras:
                            mayusculas = sum(1 for c in letras if c.isupper())

                            # Si TODAS las letras están en mayúsculas (100%)
                            # esto indica que es continuación del resumen
                            if mayusculas == len(letras):
                                # UNIR las líneas
                                resumen_unido = resumen_actual + ' ' + linea_siguiente
                                datos_partida['resumen'] = resumen_unido

                                # Actualizar también la línea completa del item
                                linea_original = item_actual['linea']
                                item_actual['linea'] = linea_original + ' ' + linea_siguiente

                                lineas_unidas += 1
                                logger.info(f"✓ Descripción continuada unida: '{resumen_actual[:40]}...' + '{linea_siguiente[:30]}...'")

                                # Saltar la siguiente línea (ya fue procesada)
                                resultados.append(item_actual)
                                i += 2
                                continue

            # Si no se unió, agregar normalmente
            resultados.append(item_actual)
            i += 1

        if lineas_unidas > 0:
            logger.info(f"✓ Total de {lineas_unidas} descripciones continuadas unidas correctamente")

        return resultados

    @classmethod
    def clasificar_bloque(cls, lineas: list) -> list:
        """
        Clasifica un bloque de líneas con contexto

        Args:
            lineas: lista de strings

        Returns:
            lista de dicts con clasificaciones (incluye numero_linea)
        """
        resultados = []
        contexto = {'partida_activa': False}

        for idx, linea in enumerate(lineas):
            clasificacion = cls.clasificar(linea, contexto)
            resultados.append({
                'linea': linea,
                'numero_linea': idx,  # ← NUEVO: Añadir índice de línea
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

        # POST-PROCESAMIENTO: Unir líneas de descripción continuadas
        resultados = cls._unir_descripciones_continuadas(resultados)

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
