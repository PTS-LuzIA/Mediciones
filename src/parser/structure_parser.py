"""
Parser especializado SOLO para extraer estructura jerárquica (Fase 1).

Este parser es diferente al de Fase 2:
- NO extrae partidas individuales
- SOLO busca capítulos/subcapítulos multinivel
- Crea niveles intermedios automáticamente si faltan
- Busca líneas TOTAL para asignar importes

Autor: Claude Code
Fecha: 2026-01-14
"""

import re
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class StructureParser:
    """
    Parser especializado para extraer SOLO la estructura jerárquica.
    Mucho más simple que el parser de partidas.
    """

    # Patrones para identificar capítulos/subcapítulos
    # Formato: "01 NOMBRE" o "CAPÍTULO 01 NOMBRE"
    # Acepta con o sin espacio: "01 NOMBRE" o "01NOMBRE"
    PATRON_CAPITULO = re.compile(r'^(?:CAPÍTULO\s+)?(\d{1,2})\s*([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑa-záéíóúñ0-9\s\-/\.,:;()]+)$')

    # Formato: "01.04 NOMBRE" o "SUBCAPÍTULO 01.04 NOMBRE"
    # Acepta cualquier número de niveles: 01.04, 01.04.01, 01.04.01.01, etc.
    # Acepta con o sin espacio: "01.04 NOMBRE" o "01.04NOMBRE"
    PATRON_SUBCAPITULO = re.compile(r'^(?:SUBCAPÍTULO\s+|APARTADO\s+)?(\d{1,2}(?:\.\d{1,2})+)\s*([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑa-záéíóúñ0-9\s\-/\.,:;()]+)$')

    # Patrón para líneas TOTAL con código explícito (formato estándar)
    # Ejemplos: "TOTAL SUBCAPÍTULO 01.04.01  12.345,67", "TOTAL CAPÍTULO 01  98.765,43"
    PATRON_TOTAL_CON_CODIGO = re.compile(
        r'^TOTAL\s+(SUBCAPÍTULO|CAPÍTULO|APARTADO)\s+([\d\.]+)\s+([\d.,]+)\s*$',
        re.IGNORECASE
    )

    # Patrón para líneas TOTAL con código y puntos suspensivos (formato común en PDFs)
    # Ejemplos: "TOTAL 01.04.01....... 49.578,18", "TOTAL 03.06.02.02.01... 8.058,17"
    #           "TOTAL 01............ 123.456,78" (capítulo sin punto)
    # El código puede ser con o sin puntos: "01" o "01.04.01"
    # Luego vienen puntos/espacios de relleno, luego el importe
    PATRON_TOTAL_CON_PUNTOS = re.compile(
        r'^TOTAL\s+(\d{1,2}(?:\.\d{1,2})*)[\s\.]+(\d{1,3}(?:\.\d{3})*,\d{2})\s*$',
        re.IGNORECASE
    )

    # Patrón para líneas TOTAL sin código explícito (usa último_codigo)
    # Ejemplos: "TOTAL  123.456,78", "TOTAL ........ 123.456,78"
    PATRON_TOTAL_SIN_CODIGO = re.compile(
        r'^TOTAL\s+([\d.,]+)\s*$',
        re.IGNORECASE
    )

    def __init__(self):
        self.estructura = {'capitulos': []}
        self.capitulo_actual = None
        self.ultimo_codigo = None  # Para tracking de TOTALes
        self.mapa_nodos = {}  # Mapa código -> nodo para acceso rápido

    def parsear(self, lineas: List[str]) -> Dict:
        """
        Parsea las líneas y extrae la estructura jerárquica completa.

        Args:
            lineas: Lista de strings del PDF

        Returns:
            Dict con estructura jerárquica
        """
        logger.info(f"🔧 Iniciando parsing de estructura (total líneas: {len(lineas)})")

        self.estructura = {'capitulos': []}
        self.capitulo_actual = None
        self.ultimo_codigo = None
        self.mapa_nodos = {}

        for i, linea in enumerate(lineas):
            linea = linea.strip()
            if not linea:
                continue

            # Intentar detectar capítulo
            match_cap = self.PATRON_CAPITULO.match(linea)
            if match_cap:
                self._procesar_capitulo(match_cap.group(1), match_cap.group(2).strip())
                continue

            # Intentar detectar subcapítulo
            match_sub = self.PATRON_SUBCAPITULO.match(linea)
            if match_sub:
                self._procesar_subcapitulo(match_sub.group(1), match_sub.group(2).strip())
                continue

            # Intentar detectar TOTAL con código explícito (formato estándar)
            match_total_con_codigo = self.PATRON_TOTAL_CON_CODIGO.match(linea)
            if match_total_con_codigo:
                tipo = match_total_con_codigo.group(1)
                codigo = match_total_con_codigo.group(2)
                total_str = match_total_con_codigo.group(3)
                self._procesar_total(total_str, codigo_explicito=codigo)
                continue

            # Intentar detectar TOTAL con puntos suspensivos (formato común)
            match_total_puntos = self.PATRON_TOTAL_CON_PUNTOS.match(linea)
            if match_total_puntos:
                codigo = match_total_puntos.group(1)
                total_str = match_total_puntos.group(2)
                self._procesar_total(total_str, codigo_explicito=codigo)
                continue

            # Intentar detectar TOTAL sin código (usa último_codigo)
            match_total_sin_codigo = self.PATRON_TOTAL_SIN_CODIGO.match(linea)
            if match_total_sin_codigo:
                total_str = match_total_sin_codigo.group(1)
                self._procesar_total(total_str, codigo_explicito=None)
                continue

        # Calcular totales de nodos que no tienen total explícito
        self._calcular_totales_faltantes()

        logger.info(f"✓ Parsing completado: {len(self.estructura['capitulos'])} capítulos")
        return self.estructura

    def _procesar_capitulo(self, codigo: str, nombre: str):
        """Procesa un capítulo principal"""
        logger.debug(f"  📁 Capítulo detectado: {codigo} - {nombre}")

        capitulo = {
            'codigo': codigo,
            'nombre': nombre,
            'subcapitulos': [],
            'total': None,  # Se llenará con TOTAL o calculando
            'orden': len(self.estructura['capitulos'])
        }

        self.estructura['capitulos'].append(capitulo)
        self.capitulo_actual = capitulo
        self.ultimo_codigo = codigo
        self.mapa_nodos[codigo] = capitulo

    def _procesar_subcapitulo(self, codigo: str, nombre: str):
        """
        Procesa un subcapítulo de cualquier nivel.
        Crea automáticamente niveles intermedios si faltan.
        """
        if not self.capitulo_actual:
            logger.warning(f"⚠️  Subcapítulo {codigo} sin capítulo padre - ignorado")
            return

        logger.debug(f"  📂 Subcapítulo detectado: {codigo} - {nombre}")

        # Asegurar que todos los niveles padres existen
        self._asegurar_niveles_intermedios(codigo)

        # Crear el nuevo subcapítulo
        nuevo_sub = {
            'codigo': codigo,
            'nombre': nombre,
            'subcapitulos': [],
            'total': None,
            'orden': 0  # Se ajustará al agregarlo
        }

        # Determinar dónde agregarlo según el nivel
        partes = codigo.split('.')

        if len(partes) == 2:
            # Nivel 1: agregar directamente al capítulo
            nuevo_sub['orden'] = len(self.capitulo_actual['subcapitulos'])
            self.capitulo_actual['subcapitulos'].append(nuevo_sub)
        else:
            # Nivel 2+: agregar al padre correspondiente
            codigo_padre = '.'.join(partes[:-1])

            if codigo_padre in self.mapa_nodos:
                padre = self.mapa_nodos[codigo_padre]
                nuevo_sub['orden'] = len(padre['subcapitulos'])
                padre['subcapitulos'].append(nuevo_sub)
            else:
                logger.warning(f"⚠️  Padre {codigo_padre} no encontrado para {codigo}")
                # Fallback: agregar a capítulo
                nuevo_sub['orden'] = len(self.capitulo_actual['subcapitulos'])
                self.capitulo_actual['subcapitulos'].append(nuevo_sub)

        # Registrar en el mapa
        self.mapa_nodos[codigo] = nuevo_sub
        self.ultimo_codigo = codigo

    def _asegurar_niveles_intermedios(self, codigo: str):
        """
        Asegura que todos los niveles padres existen.
        Por ejemplo, si encontramos 01.04.01, asegura que existe 01.04.
        """
        partes = codigo.split('.')

        # Verificar cada nivel intermedio
        for i in range(2, len(partes)):
            codigo_intermedio = '.'.join(partes[:i])

            if codigo_intermedio not in self.mapa_nodos:
                # Crear el nivel intermedio
                logger.info(f"  🔧 Creando nivel intermedio: {codigo_intermedio}")

                # Generar un nombre genérico
                nombre_generico = f"SUBCAPÍTULO {codigo_intermedio}"

                nuevo_nivel = {
                    'codigo': codigo_intermedio,
                    'nombre': nombre_generico,
                    'subcapitulos': [],
                    'total': None,
                    'orden': 0,
                    '_generado': True  # Marca para saber que fue autogenerado
                }

                # Determinar dónde agregarlo
                if i == 2:
                    # Nivel 1: agregar al capítulo
                    nuevo_nivel['orden'] = len(self.capitulo_actual['subcapitulos'])
                    self.capitulo_actual['subcapitulos'].append(nuevo_nivel)
                else:
                    # Nivel 2+: agregar al padre
                    codigo_padre = '.'.join(partes[:i-1])
                    if codigo_padre in self.mapa_nodos:
                        padre = self.mapa_nodos[codigo_padre]
                        nuevo_nivel['orden'] = len(padre['subcapitulos'])
                        padre['subcapitulos'].append(nuevo_nivel)

                # Registrar en el mapa
                self.mapa_nodos[codigo_intermedio] = nuevo_nivel

    def _procesar_total(self, total_str: str, codigo_explicito: Optional[str] = None):
        """
        Procesa una línea TOTAL y la asigna al código correspondiente.

        Args:
            total_str: String con el importe (formato español: 1.234,56)
            codigo_explicito: Si se proporciona, usa este código; si no, usa ultimo_codigo
        """
        # Determinar a qué código asignar
        codigo_target = codigo_explicito if codigo_explicito else self.ultimo_codigo

        if not codigo_target:
            logger.warning(f"⚠️  TOTAL encontrado pero no hay código al que asignarlo")
            return

        # Limpiar y convertir a número
        total_limpio = total_str.replace('.', '').replace(',', '.')
        try:
            total = float(total_limpio)
        except ValueError:
            logger.warning(f"⚠️  No se pudo convertir total: {total_str}")
            return

        # Asignar al nodo correcto
        if codigo_target in self.mapa_nodos:
            nodo = self.mapa_nodos[codigo_target]
            nodo['total'] = total
            logger.debug(f"  💰 Total asignado a {codigo_target}: {total:.2f} €")
        else:
            logger.warning(f"⚠️  No se encontró nodo para código {codigo_target}")

    def _calcular_totales_faltantes(self):
        """
        Calcula totales de nodos que no tienen total explícito,
        sumando los totales de sus hijos.
        """
        for capitulo in self.estructura['capitulos']:
            self._calcular_total_nodo(capitulo)

    def _calcular_total_nodo(self, nodo: Dict) -> float:
        """
        Calcula el total de un nodo recursivamente.

        Estrategia:
        1. Primero calcula totales de hijos recursivamente
        2. Si el nodo YA tiene total explícito, lo respeta
        3. Si NO tiene total, suma los totales de sus hijos

        Returns:
            float: Total del nodo
        """
        # Primero calcular totales de hijos recursivamente
        for hijo in nodo.get('subcapitulos', []):
            self._calcular_total_nodo(hijo)

        # Si ya tiene total asignado explícitamente, usarlo (tiene prioridad)
        if nodo.get('total') is not None:
            return nodo['total']

        # Si no tiene total explícito, calcular sumando hijos
        if nodo.get('subcapitulos'):
            total_calculado = sum(
                hijo.get('total', 0.0) for hijo in nodo['subcapitulos']
            )
            nodo['total'] = total_calculado

            if total_calculado > 0:
                logger.debug(f"  🧮 Total calculado para {nodo['codigo']}: {total_calculado:.2f} €")

            return total_calculado

        # Si no tiene hijos ni total, es 0
        nodo['total'] = 0.0
        return 0.0

    def extraer_estadisticas(self) -> Dict:
        """
        Extrae estadísticas de la estructura parseada.

        Returns:
            Dict con estadísticas
        """
        total_capitulos = len(self.estructura['capitulos'])
        total_subcapitulos = 0
        niveles_max = 1  # Mínimo 1 (capítulos)

        for capitulo in self.estructura['capitulos']:
            subcaps, nivel = self._contar_subcapitulos_recursivo(capitulo)
            total_subcapitulos += subcaps
            niveles_max = max(niveles_max, nivel + 1)

        return {
            'total_capitulos': total_capitulos,
            'total_subcapitulos': total_subcapitulos,
            'niveles_maximos': niveles_max,
            'nodos_totales': total_capitulos + total_subcapitulos
        }

    def _contar_subcapitulos_recursivo(self, nodo: Dict) -> Tuple[int, int]:
        """
        Cuenta subcapítulos y determina nivel máximo recursivamente.

        Returns:
            Tuple[int, int]: (cantidad_subcapitulos, nivel_maximo)
        """
        subcaps = nodo.get('subcapitulos', [])
        count = len(subcaps)
        max_nivel = 1

        for sub in subcaps:
            sub_count, sub_nivel = self._contar_subcapitulos_recursivo(sub)
            count += sub_count
            max_nivel = max(max_nivel, sub_nivel + 1)

        return count, max_nivel


def parsear_estructura(lineas: List[str]) -> Dict:
    """
    Función helper para parsear estructura de forma simple.

    Args:
        lineas: Lista de strings del PDF

    Returns:
        Dict con estructura jerárquica
    """
    parser = StructureParser()
    return parser.parsear(lineas)


if __name__ == "__main__":
    # Test básico - Simula un presupuesto real con niveles intermedios sin TOTAL explícito
    lineas_test = [
        "01 FASE 2",
        "01.03 MOVIMIENTO DE TIERRAS",
        "TOTAL SUBCAPÍTULO 01.03                5000,00",
        "01.04 PAVIMENTACIÓN",  # Este nivel NO tiene TOTAL explícito
        "01.04.01 PAVIMENTO PERMEABLE",
        "TOTAL SUBCAPÍTULO 01.04.01             2500,50",
        "01.04.02 PAVIMENTO IMPERMEABLE",
        "TOTAL SUBCAPÍTULO 01.04.02             3000,75",
        "01.04.03 JUNTAS",
        "TOTAL SUBCAPÍTULO 01.04.03             1500,25",
        # NO hay TOTAL para 01.04 - debe calcularse como suma: 7001,50
        "01.05 MUROS",  # Este nivel tampoco tiene TOTAL
        "01.05.01 MUROS DE SUELO",  # Nivel intermedio sin TOTAL
        "01.05.01.01 MURO TIPO 1",
        "TOTAL SUBCAPÍTULO 01.05.01.01          1200,00",
        "01.05.01.02 MURO TIPO 2",
        "TOTAL SUBCAPÍTULO 01.05.01.02          1800,00",
        # NO hay TOTAL para 01.05.01 - debe calcularse como suma: 3000,00
        # NO hay TOTAL para 01.05 - debe calcularse como suma: 3000,00
        "TOTAL CAPÍTULO 01                     15001,50",  # Total explícito (tiene prioridad)
        "02 CIMENTACIÓN",
        "02.01 ZAPATAS",
        "TOTAL SUBCAPÍTULO 02.01               10000,00",
        "TOTAL CAPÍTULO 02                     10000,00"
    ]

    parser = StructureParser()
    estructura = parser.parsear(lineas_test)

    print("\n" + "="*80)
    print("TEST DE STRUCTURE PARSER")
    print("="*80)

    # Estadísticas
    stats = parser.extraer_estadisticas()
    print(f"\nEstadísticas:")
    print(f"  Capítulos: {stats['total_capitulos']}")
    print(f"  Subcapítulos: {stats['total_subcapitulos']}")
    print(f"  Niveles máximos: {stats['niveles_maximos']}")
    print(f"  Nodos totales: {stats['nodos_totales']}")

    # Mostrar estructura
    print(f"\nEstructura extraída:")
    print("-"*80)

    def imprimir_nodo(nodo, nivel=0):
        indent = "  " * nivel
        total_str = f"{nodo['total']:.2f} €" if nodo['total'] else "Sin total"
        generado = " [GENERADO]" if nodo.get('_generado') else ""
        print(f"{indent}{nodo['codigo']} - {nodo['nombre']}{generado}")
        print(f"{indent}  Total: {total_str}")

        for sub in nodo.get('subcapitulos', []):
            imprimir_nodo(sub, nivel + 1)

    for capitulo in estructura['capitulos']:
        imprimir_nodo(capitulo)
        print()

    print("="*80)
