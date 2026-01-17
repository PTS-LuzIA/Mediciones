"""
Exportador a formato CSV.
Genera archivos CSV con las partidas extraídas.
"""

import csv
import logging
from pathlib import Path
from typing import List, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CSVExporter:
    """Exporta partidas a CSV"""

    @staticmethod
    def exportar(partidas: List[Dict], output_path: str, incluir_jerarquia: bool = True) -> None:
        """
        Exporta lista de partidas a CSV

        Args:
            partidas: lista de dicts con partidas
            output_path: ruta del archivo de salida
            incluir_jerarquia: incluir columnas de capítulo/subcapítulo/apartado
        """
        # Asegurar que el directorio existe
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # Definir mapeo de columnas (campo interno -> nombre exportado)
        if incluir_jerarquia:
            mapeo_columnas = {
                'capitulo': 'Capítulo',
                'subcapitulo': 'Subcapítulo',
                'codigo': 'Código Partida',
                'unidad': 'Unidad',
                'resumen': 'Título Partida',
                'descripcion': 'Descripción Partida',
                'cantidad': 'Unidades',
                'precio': 'Precio',
                'importe': 'Total'
            }
        else:
            mapeo_columnas = {
                'codigo': 'Código Partida',
                'unidad': 'Unidad',
                'resumen': 'Título Partida',
                'descripcion': 'Descripción Partida',
                'cantidad': 'Unidades',
                'precio': 'Precio',
                'importe': 'Total'
            }

        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                # Usar nombres de columnas descriptivos en español
                writer = csv.DictWriter(csvfile, fieldnames=mapeo_columnas.values(), extrasaction='ignore')
                writer.writeheader()

                for partida in partidas:
                    # Mapear campos internos a nombres de columnas
                    fila = {mapeo_columnas[k]: v for k, v in partida.items() if k in mapeo_columnas}
                    writer.writerow(fila)

            logger.info(f"✓ CSV exportado: {output_path} ({len(partidas)} partidas)")

        except Exception as e:
            logger.error(f"Error exportando CSV: {e}")
            raise

    @staticmethod
    def exportar_jerarquico(estructura: Dict, output_path: str) -> None:
        """
        Exporta estructura jerárquica completa a CSV con niveles

        Args:
            estructura: dict con estructura completa
            output_path: ruta del archivo de salida
        """
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        campos = [
            'nivel', 'tipo', 'codigo', 'nombre',
            'unidad', 'resumen', 'descripcion',
            'cantidad', 'precio', 'importe'
        ]

        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=campos)
                writer.writeheader()

                # Iterar estructura jerárquica
                for capitulo in estructura.get('capitulos', []):
                    # Escribir capítulo
                    writer.writerow({
                        'nivel': 1,
                        'tipo': 'CAPITULO',
                        'codigo': capitulo['codigo'],
                        'nombre': capitulo['nombre']
                    })

                    for subcapitulo in capitulo.get('subcapitulos', []):
                        # Escribir subcapítulo
                        writer.writerow({
                            'nivel': 2,
                            'tipo': 'SUBCAPITULO',
                            'codigo': subcapitulo['codigo'],
                            'nombre': subcapitulo['nombre']
                        })

                        # Escribir partidas del subcapítulo
                        for partida in subcapitulo.get('partidas', []):
                            writer.writerow({
                                'nivel': 3,
                                'tipo': 'PARTIDA',
                                'codigo': partida['codigo'],
                                'nombre': '',
                                'unidad': partida['unidad'],
                                'resumen': partida['resumen'],
                                'descripcion': partida.get('descripcion', ''),
                                'cantidad': partida['cantidad'],
                                'precio': partida['precio'],
                                'importe': partida['importe']
                            })

                        # Escribir apartados
                        for apartado in subcapitulo.get('apartados', []):
                            writer.writerow({
                                'nivel': 3,
                                'tipo': 'APARTADO',
                                'codigo': apartado['codigo'],
                                'nombre': apartado['nombre']
                            })

                            # Escribir partidas del apartado
                            for partida in apartado.get('partidas', []):
                                writer.writerow({
                                    'nivel': 4,
                                    'tipo': 'PARTIDA',
                                    'codigo': partida['codigo'],
                                    'nombre': '',
                                    'unidad': partida['unidad'],
                                    'resumen': partida['resumen'],
                                    'descripcion': partida.get('descripcion', ''),
                                    'cantidad': partida['cantidad'],
                                    'precio': partida['precio'],
                                    'importe': partida['importe']
                                })

            logger.info(f"✓ CSV jerárquico exportado: {output_path}")

        except Exception as e:
            logger.error(f"Error exportando CSV jerárquico: {e}")
            raise


if __name__ == "__main__":
    # Test
    partidas_test = [
        {
            'capitulo': 'C01',
            'subcapitulo': 'C08.01',
            'apartado': None,
            'codigo': 'DEM06',
            'unidad': 'm',
            'resumen': 'CORTE PAVIMENTO EXISTENTE',
            'descripcion': 'Corte de pavimento de aglomerado asfáltico u hormigón...',
            'cantidad': 630.0,
            'precio': 1.12,
            'importe': 705.60
        },
        {
            'capitulo': 'C01',
            'subcapitulo': 'C08.01',
            'apartado': None,
            'codigo': 'U01AB100',
            'unidad': 'm',
            'resumen': 'DEMOLICIÓN Y LEVANTADO DE BORDILLO AISLADO',
            'descripcion': 'Demolición y levantado de bordillo...',
            'cantidad': 630.0,
            'precio': 5.40,
            'importe': 3402.00
        }
    ]

    CSVExporter.exportar(partidas_test, 'data/test_export.csv')
    print("✓ Test CSV completado")
