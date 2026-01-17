#!/usr/bin/env python3
"""
Test rápido del parser de mediciones
"""
import sys
sys.path.insert(0, 'src')

from parser.partida_parser import PartidaParser

def test_parser():
    print("=" * 80)
    print("TEST DE PARSER DE MEDICIONES")
    print("=" * 80)

    pdf_path = "ejemplo/PROYECTO CALYPOFADO_extract.pdf"

    try:
        print(f"\n1. Creando parser para: {pdf_path}")
        parser = PartidaParser(pdf_path)

        print("2. Parseando PDF...")
        resultado = parser.parsear()

        print("3. Imprimiendo resumen...")
        parser.imprimir_resumen()

        print("\n4. Extrayendo primeras partidas...")
        partidas = parser.obtener_todas_partidas()

        if len(partidas) > 0:
            print(f"\n✓ Primera partida extraída:")
            p = partidas[0]
            print(f"   Código: {p['codigo']}")
            print(f"   Resumen: {p['resumen'][:60]}...")
            print(f"   Unidad: {p['unidad']}")
            print(f"   Cantidad: {p['cantidad']}")
            print(f"   Precio: {p['precio']}")
            print(f"   Importe: {p['importe']}")

        print("\n" + "=" * 80)
        print("✓ TEST COMPLETADO EXITOSAMENTE")
        print("=" * 80)
        return True

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_parser()
    sys.exit(0 if success else 1)
