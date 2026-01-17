"""
Exportador a formato BC3 (FIEBDC-3).
Formato estándar español para intercambio de presupuestos de construcción.
Especificación: http://www.fiebdc.org
"""

import logging
from pathlib import Path
from typing import List, Dict
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BC3Exporter:
    """
    Exporta estructura a formato BC3/FIEBDC-3

    Estructura básica BC3:
    ~V|versión|
    ~C|código|resumen|
    ~D|código|texto descriptivo|
    ~M|código|tipo|cantidad|precio|importe|
    """

    SEPARADOR = '|'
    VERSION = 'FIEBDC-3/2016'

    @staticmethod
    def exportar(estructura: Dict, output_path: str) -> None:
        """
        Exporta estructura completa a BC3

        Args:
            estructura: dict con estructura jerárquica
            output_path: ruta del archivo de salida .bc3
        """
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        try:
            lineas = []

            # Cabecera del archivo
            lineas.append(BC3Exporter._linea_version())
            lineas.append(BC3Exporter._linea_archivo_info(estructura))

            # Procesar estructura jerárquica
            for capitulo in estructura.get('capitulos', []):
                # Agregar capítulo
                lineas.append(BC3Exporter._linea_capitulo(capitulo))

                for subcapitulo in capitulo.get('subcapitulos', []):
                    # Agregar subcapítulo
                    lineas.append(BC3Exporter._linea_subcapitulo(subcapitulo))

                    # Agregar partidas directas del subcapítulo
                    for partida in subcapitulo.get('partidas', []):
                        lineas.extend(BC3Exporter._lineas_partida(partida))

                    # Agregar apartados
                    for apartado in subcapitulo.get('apartados', []):
                        lineas.append(BC3Exporter._linea_apartado(apartado))

                        # Agregar partidas del apartado
                        for partida in apartado.get('partidas', []):
                            lineas.extend(BC3Exporter._lineas_partida(partida))

            # Guardar archivo
            contenido = '\r\n'.join(lineas) + '\r\n'

            with open(output_path, 'w', encoding='latin-1', errors='replace') as f:
                f.write(contenido)

            logger.info(f"✓ BC3 exportado: {output_path}")

        except Exception as e:
            logger.error(f"Error exportando BC3: {e}")
            raise

    @staticmethod
    def _limpiar_texto(texto: str) -> str:
        """Limpia texto para BC3 (eliminar pipes y caracteres conflictivos)"""
        if not texto:
            return ''
        texto = texto.replace('|', ' ')
        texto = texto.replace('\n', ' ')
        texto = texto.replace('\r', ' ')
        return texto.strip()

    @staticmethod
    def _linea_version() -> str:
        """Genera línea de versión"""
        fecha = datetime.now().strftime('%Y-%m-%d')
        return f"~V{BC3Exporter.SEPARADOR}{BC3Exporter.VERSION}{BC3Exporter.SEPARADOR}{fecha}{BC3Exporter.SEPARADOR}"

    @staticmethod
    def _linea_archivo_info(estructura: Dict) -> str:
        """Genera línea de información del archivo"""
        nombre = BC3Exporter._limpiar_texto(estructura.get('nombre', 'SIN NOMBRE'))
        return f"~K{BC3Exporter.SEPARADOR}\\UTF-8\\{BC3Exporter.SEPARADOR}{nombre}{BC3Exporter.SEPARADOR}"

    @staticmethod
    def _linea_capitulo(capitulo: Dict) -> str:
        """Genera línea de capítulo"""
        codigo = BC3Exporter._limpiar_texto(capitulo['codigo'])
        nombre = BC3Exporter._limpiar_texto(capitulo['nombre'])
        return f"~C{BC3Exporter.SEPARADOR}{codigo}{BC3Exporter.SEPARADOR}{nombre}{BC3Exporter.SEPARADOR}0{BC3Exporter.SEPARADOR}"

    @staticmethod
    def _linea_subcapitulo(subcapitulo: Dict) -> str:
        """Genera línea de subcapítulo"""
        codigo = BC3Exporter._limpiar_texto(subcapitulo['codigo'])
        nombre = BC3Exporter._limpiar_texto(subcapitulo['nombre'])
        return f"~C{BC3Exporter.SEPARADOR}{codigo}{BC3Exporter.SEPARADOR}{nombre}{BC3Exporter.SEPARADOR}1{BC3Exporter.SEPARADOR}"

    @staticmethod
    def _linea_apartado(apartado: Dict) -> str:
        """Genera línea de apartado"""
        codigo = BC3Exporter._limpiar_texto(apartado['codigo'])
        nombre = BC3Exporter._limpiar_texto(apartado['nombre'])
        return f"~C{BC3Exporter.SEPARADOR}{codigo}{BC3Exporter.SEPARADOR}{nombre}{BC3Exporter.SEPARADOR}2{BC3Exporter.SEPARADOR}"

    @staticmethod
    def _lineas_partida(partida: Dict) -> List[str]:
        """
        Genera líneas de partida (concepto + descripción + medición)

        Returns:
            lista de líneas BC3
        """
        lineas = []
        codigo = BC3Exporter._limpiar_texto(partida['codigo'])
        unidad = BC3Exporter._limpiar_texto(partida['unidad'])
        resumen = BC3Exporter._limpiar_texto(partida['resumen'])

        # Línea ~C: Concepto
        lineas.append(
            f"~C{BC3Exporter.SEPARADOR}{codigo}{BC3Exporter.SEPARADOR}"
            f"{resumen}{BC3Exporter.SEPARADOR}3{BC3Exporter.SEPARADOR}"
            f"{unidad}{BC3Exporter.SEPARADOR}{partida['precio']:.2f}{BC3Exporter.SEPARADOR}"
        )

        # Línea ~D: Descripción (si existe)
        if partida.get('descripcion'):
            descripcion = BC3Exporter._limpiar_texto(partida['descripcion'])
            lineas.append(
                f"~D{BC3Exporter.SEPARADOR}{codigo}{BC3Exporter.SEPARADOR}{descripcion}{BC3Exporter.SEPARADOR}"
            )

        # Línea ~M: Medición
        lineas.append(
            f"~M{BC3Exporter.SEPARADOR}{codigo}{BC3Exporter.SEPARADOR}"
            f"{partida['cantidad']:.2f}{BC3Exporter.SEPARADOR}"
            f"{partida['precio']:.2f}{BC3Exporter.SEPARADOR}"
            f"{partida['importe']:.2f}{BC3Exporter.SEPARADOR}"
        )

        return lineas

    @staticmethod
    def exportar_simple(partidas: List[Dict], output_path: str, nombre_obra: str = 'OBRA') -> None:
        """
        Exporta lista simple de partidas a BC3 (sin jerarquía)

        Args:
            partidas: lista de partidas
            output_path: ruta de salida
            nombre_obra: nombre del proyecto
        """
        estructura_simple = {
            'nombre': nombre_obra,
            'capitulos': [
                {
                    'codigo': 'CAP01',
                    'nombre': 'MEDICIONES',
                    'subcapitulos': [
                        {
                            'codigo': 'SUB01',
                            'nombre': 'PARTIDAS',
                            'apartados': [],
                            'partidas': partidas
                        }
                    ]
                }
            ]
        }

        BC3Exporter.exportar(estructura_simple, output_path)


if __name__ == "__main__":
    # Test
    estructura_test = {
        'nombre': 'PROYECTO TEST BC3',
        'capitulos': [
            {
                'codigo': 'C01',
                'nombre': 'ACTUACIONES',
                'subcapitulos': [
                    {
                        'codigo': 'C08.01',
                        'nombre': 'CALLE TENERIFE',
                        'apartados': [],
                        'partidas': [
                            {
                                'codigo': 'DEM06',
                                'unidad': 'm',
                                'resumen': 'CORTE PAVIMENTO EXISTENTE',
                                'descripcion': 'Corte de pavimento de aglomerado asfáltico',
                                'cantidad': 630.0,
                                'precio': 1.12,
                                'importe': 705.60
                            },
                            {
                                'codigo': 'U01AB100',
                                'unidad': 'm',
                                'resumen': 'DEMOLICIÓN BORDILLO',
                                'descripcion': 'Demolición y levantado de bordillo',
                                'cantidad': 630.0,
                                'precio': 5.40,
                                'importe': 3402.00
                            }
                        ]
                    }
                ]
            }
        ]
    }

    BC3Exporter.exportar(estructura_test, 'data/test_export.bc3')
    print("✓ Test BC3 completado")
