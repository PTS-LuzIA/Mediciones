"""
Script de prueba para verificar el PartidaCountAgent
"""

import asyncio
import json
import sys
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from llm.structure_extraction_agent import StructureExtractionAgent
from llm.partida_count_agent import PartidaCountAgent


async def test_conteo():
    # PDF de prueba (ajusta la ruta según tu sistema)
    pdf_path = "/Volumes/DATOS_IA/G_Drive_LuzIA/PRUEBAS/PLIEGOS/PRESUPUESTOS PARCIALES NAVAS DE TOLOSA.pdf"

    if not Path(pdf_path).exists():
        print(f"❌ PDF no encontrado: {pdf_path}")
        print("Por favor, ajusta la ruta del PDF en el script")
        return

    print("="*80)
    print("TEST: Conteo de Partidas con LLM")
    print("="*80)

    # Paso 1: Extraer estructura
    print("\n[PASO 1] Extrayendo estructura del presupuesto...")
    structure_agent = StructureExtractionAgent()
    estructura = await structure_agent.extraer_estructura(pdf_path)

    print(f"✓ Estructura extraída:")
    print(f"  - Capítulos: {len(estructura.get('capitulos', []))}")
    print(f"  - Nombre proyecto: {estructura.get('nombre', 'N/A')}")

    # Mostrar estructura básica
    for i, cap in enumerate(estructura.get('capitulos', [])[:3], 1):
        print(f"\n  Capítulo {i}: {cap['codigo']} - {cap['nombre']}")
        print(f"    Total IA: {cap.get('total', 0):.2f} €")
        if cap.get('subcapitulos'):
            print(f"    Subcapítulos: {len(cap['subcapitulos'])}")

    # Paso 2: Contar partidas
    print("\n" + "="*80)
    print("[PASO 2] Contando partidas con LLM...")
    count_agent = PartidaCountAgent()
    conteo = await count_agent.contar_partidas(pdf_path, estructura)

    print(f"✓ Conteo completado en {conteo.get('tiempo_conteo', 0):.2f}s")

    # Mostrar conteo
    total_partidas = 0
    for i, cap in enumerate(conteo.get('capitulos', [])[:3], 1):
        num_partidas = cap.get('num_partidas', 0)
        total_partidas += num_partidas
        print(f"\n  Capítulo {i}: {cap['codigo']}")
        print(f"    Partidas directas: {num_partidas}")

        if cap.get('subcapitulos'):
            for j, sub in enumerate(cap['subcapitulos'][:2], 1):
                sub_partidas = sub.get('num_partidas', 0)
                total_partidas += sub_partidas
                print(f"      Subcap {sub['codigo']}: {sub_partidas} partidas")

    print(f"\n  Total de partidas contadas (primeros capítulos): {total_partidas}")

    # Paso 3: Fusionar conteo con estructura
    print("\n" + "="*80)
    print("[PASO 3] Fusionando conteo con estructura original...")
    estructura_completa = count_agent.fusionar_conteo_con_estructura(estructura, conteo)

    print("✓ Fusión completada")

    # Verificar que todos los capítulos tengan num_partidas
    for cap in estructura_completa.get('capitulos', [])[:2]:
        print(f"\n  {cap['codigo']} - {cap['nombre']}")
        print(f"    Total IA: {cap.get('total', 0):.2f} €")
        print(f"    Num partidas: {cap.get('num_partidas', '???')}")

        if cap.get('subcapitulos'):
            for sub in cap['subcapitulos'][:2]:
                print(f"      {sub['codigo']}: {sub.get('num_partidas', '???')} partidas, {sub.get('total', 0):.2f} €")

    # Guardar resultado en archivo JSON para inspección
    output_file = "test_conteo_resultado.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(estructura_completa, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Resultado guardado en: {output_file}")
    print("\n" + "="*80)
    print("TEST COMPLETADO")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(test_conteo())
