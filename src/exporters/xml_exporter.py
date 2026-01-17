"""
Exportador a formato XML.
Genera XML estructurado con la jerarquía completa.
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom
import logging
from pathlib import Path
from typing import List, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class XMLExporter:
    """Exporta estructura a XML"""

    @staticmethod
    def exportar(estructura: Dict, output_path: str) -> None:
        """
        Exporta estructura completa a XML

        Args:
            estructura: dict con estructura jerárquica
            output_path: ruta del archivo de salida
        """
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        try:
            # Crear elemento raíz
            root = ET.Element('presupuesto')

            # Metadata
            if estructura.get('nombre'):
                ET.SubElement(root, 'nombre').text = estructura['nombre']
            if estructura.get('descripcion'):
                ET.SubElement(root, 'descripcion').text = estructura['descripcion']
            if estructura.get('archivo_origen'):
                ET.SubElement(root, 'archivo_origen').text = estructura['archivo_origen']

            # Capitulos
            capitulos_elem = ET.SubElement(root, 'capitulos')

            for capitulo in estructura.get('capitulos', []):
                cap_elem = ET.SubElement(capitulos_elem, 'capitulo')
                ET.SubElement(cap_elem, 'codigo').text = capitulo['codigo']
                ET.SubElement(cap_elem, 'nombre').text = capitulo['nombre']

                # Subcapitulos
                subcaps_elem = ET.SubElement(cap_elem, 'subcapitulos')
                for subcapitulo in capitulo.get('subcapitulos', []):
                    sub_elem = ET.SubElement(subcaps_elem, 'subcapitulo')
                    ET.SubElement(sub_elem, 'codigo').text = subcapitulo['codigo']
                    ET.SubElement(sub_elem, 'nombre').text = subcapitulo['nombre']

                    # Partidas directas
                    partidas_elem = ET.SubElement(sub_elem, 'partidas')
                    for partida in subcapitulo.get('partidas', []):
                        XMLExporter._agregar_partida(partidas_elem, partida)

                    # Apartados
                    if subcapitulo.get('apartados'):
                        apts_elem = ET.SubElement(sub_elem, 'apartados')
                        for apartado in subcapitulo['apartados']:
                            apt_elem = ET.SubElement(apts_elem, 'apartado')
                            ET.SubElement(apt_elem, 'codigo').text = apartado['codigo']
                            ET.SubElement(apt_elem, 'nombre').text = apartado['nombre']

                            # Partidas del apartado
                            part_apt_elem = ET.SubElement(apt_elem, 'partidas')
                            for partida in apartado.get('partidas', []):
                                XMLExporter._agregar_partida(part_apt_elem, partida)

            # Convertir a string con formato bonito
            xml_string = XMLExporter._prettify(root)

            # Guardar
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(xml_string)

            logger.info(f"✓ XML exportado: {output_path}")

        except Exception as e:
            logger.error(f"Error exportando XML: {e}")
            raise

    @staticmethod
    def _agregar_partida(parent: ET.Element, partida: Dict) -> None:
        """Agrega una partida al elemento padre"""
        part_elem = ET.SubElement(parent, 'partida')

        ET.SubElement(part_elem, 'codigo').text = partida['codigo']
        ET.SubElement(part_elem, 'unidad').text = partida['unidad']
        ET.SubElement(part_elem, 'resumen').text = partida['resumen']

        if partida.get('descripcion'):
            ET.SubElement(part_elem, 'descripcion').text = partida['descripcion']

        ET.SubElement(part_elem, 'cantidad').text = str(partida['cantidad'])
        ET.SubElement(part_elem, 'precio').text = str(partida['precio'])
        ET.SubElement(part_elem, 'importe').text = str(partida['importe'])

    @staticmethod
    def _prettify(elem: ET.Element) -> str:
        """Formatea XML con indentación"""
        rough_string = ET.tostring(elem, encoding='utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ", encoding='utf-8').decode('utf-8')


if __name__ == "__main__":
    # Test
    estructura_test = {
        'nombre': 'PROYECTO TEST',
        'descripcion': 'Proyecto de prueba',
        'archivo_origen': 'test.pdf',
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
                                'resumen': 'CORTE PAVIMENTO',
                                'descripcion': 'Corte de pavimento...',
                                'cantidad': 630.0,
                                'precio': 1.12,
                                'importe': 705.60
                            }
                        ]
                    }
                ]
            }
        ]
    }

    XMLExporter.exportar(estructura_test, 'data/test_export.xml')
    print("✓ Test XML completado")
