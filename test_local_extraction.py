"""
Script de prueba para el extractor de estructura local.
Compara la extracción local vs IA para validar precisión.

Uso:
    python test_local_extraction.py [ruta_al_pdf]
"""

import sys
import asyncio
import json
import time
from pathlib import Path

# Añadir src al path
src_path = str(Path(__file__).parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from parser.local_structure_extractor import LocalStructureExtractor
from llm.structure_extraction_agent import StructureExtractionAgent


def imprimir_estructura(estructura: dict, nombre: str):
    """Imprime resumen de la estructura extraída"""
    print(f"\n{'='*80}")
    print(f"ESTRUCTURA EXTRAÍDA CON {nombre}")
    print(f"{'='*80}")
    print(f"Proyecto: {estructura.get('nombre', 'N/A')}")
    print(f"Método: {estructura.get('metodo_extraccion', estructura.get('modelo_usado', 'N/A'))}")
    print(f"Tiempo: {estructura.get('tiempo_procesamiento', 0):.2f}s")
    print(f"Confianza: {estructura.get('confianza_general', 'N/A')}")
    print(f"\nCapítulos: {len(estructura.get('capitulos', []))}")

    total_general = 0.0
    total_partidas = 0

    for cap in estructura.get('capitulos', []):
        total_general += cap.get('total', 0)
        total_partidas += cap.get('num_partidas', 0)
        print(f"\n  {cap['codigo']} - {cap['nombre']}")
        print(f"    Total: {cap.get('total', 0):,.2f} €")
        print(f"    Partidas: {cap.get('num_partidas', 0)}")
        print(f"    Subcapítulos: {len(cap.get('subcapitulos', []))}")

        # Mostrar primeros 2 subcapítulos
        for i, sub in enumerate(cap.get('subcapitulos', [])[:2]):
            print(f"      └─ {sub['codigo']} - {sub['nombre']}")
            print(f"         Total: {sub.get('total', 0):,.2f} €, Partidas: {sub.get('num_partidas', 0)}")

        if len(cap.get('subcapitulos', [])) > 2:
            print(f"      └─ ... y {len(cap['subcapitulos']) - 2} más")

    print(f"\n{'─'*80}")
    print(f"TOTAL GENERAL: {total_general:,.2f} €")
    print(f"PARTIDAS TOTALES: {total_partidas}")

    # Validación (si existe)
    if 'validacion_local' in estructura:
        val = estructura['validacion_local']
        if val['valido']:
            print(f"✓ Validación: Todos los totales cuadran")
        else:
            print(f"⚠️ Validación: {len(val['inconsistencias'])} inconsistencias")
            for inc in val['inconsistencias'][:3]:
                print(f"  - {inc['codigo']}: diff = {inc['diferencia']:.2f} €")

    print(f"{'='*80}\n")


def comparar_estructuras(local: dict, ia: dict):
    """Compara estructuras local vs IA"""
    print(f"\n{'='*80}")
    print("COMPARACIÓN LOCAL vs IA")
    print(f"{'='*80}")

    # Comparar totales generales
    total_local = sum(cap.get('total', 0) for cap in local.get('capitulos', []))
    total_ia = sum(cap.get('total', 0) for cap in ia.get('capitulos', []))
    diferencia = abs(total_local - total_ia)
    porcentaje = (diferencia / total_ia * 100) if total_ia > 0 else 0

    print(f"\nTOTALES GENERALES:")
    print(f"  Local: {total_local:,.2f} €")
    print(f"  IA:    {total_ia:,.2f} €")
    print(f"  Diferencia: {diferencia:,.2f} € ({porcentaje:.2f}%)")

    if porcentaje < 1:
        print(f"  ✓ Coincidencia excelente (< 1%)")
    elif porcentaje < 5:
        print(f"  ⚠️ Coincidencia aceptable (< 5%)")
    else:
        print(f"  ❌ Discrepancia significativa (> 5%)")

    # Comparar número de capítulos
    num_caps_local = len(local.get('capitulos', []))
    num_caps_ia = len(ia.get('capitulos', []))

    print(f"\nNÚMERO DE CAPÍTULOS:")
    print(f"  Local: {num_caps_local}")
    print(f"  IA:    {num_caps_ia}")

    if num_caps_local == num_caps_ia:
        print(f"  ✓ Coinciden")
    else:
        print(f"  ⚠️ No coinciden (diferencia: {abs(num_caps_local - num_caps_ia)})")

    # Comparar capítulo por capítulo
    print(f"\nCOMPARACIÓN POR CAPÍTULO:")
    caps_local = {cap['codigo']: cap for cap in local.get('capitulos', [])}
    caps_ia = {cap['codigo']: cap for cap in ia.get('capitulos', [])}

    todos_codigos = set(caps_local.keys()) | set(caps_ia.keys())

    for codigo in sorted(todos_codigos):
        cap_local = caps_local.get(codigo)
        cap_ia = caps_ia.get(codigo)

        if cap_local and cap_ia:
            total_l = cap_local.get('total', 0)
            total_i = cap_ia.get('total', 0)
            diff = abs(total_l - total_i)
            pct = (diff / total_i * 100) if total_i > 0 else 0

            estado = "✓" if pct < 1 else ("⚠️" if pct < 5 else "❌")
            print(f"  {estado} {codigo}: Local={total_l:,.2f} €, IA={total_i:,.2f} € (diff: {diff:.2f} €, {pct:.2f}%)")
        elif cap_local:
            print(f"  ❌ {codigo}: Solo en LOCAL (total: {cap_local.get('total', 0):,.2f} €)")
        else:
            print(f"  ❌ {codigo}: Solo en IA (total: {cap_ia.get('total', 0):,.2f} €)")

    # Resumen de velocidad
    tiempo_local = local.get('tiempo_procesamiento', 0)
    tiempo_ia = ia.get('tiempo_procesamiento', 0)

    print(f"\nTIEMPOS DE PROCESAMIENTO:")
    print(f"  Local: {tiempo_local:.2f}s")
    print(f"  IA:    {tiempo_ia:.2f}s")

    if tiempo_local < tiempo_ia:
        mejora = ((tiempo_ia - tiempo_local) / tiempo_ia * 100)
        print(f"  ✓ Local es {mejora:.1f}% más rápido")
    else:
        print(f"  ⚠️ IA es más rápido")

    print(f"{'='*80}\n")


async def test_local_extraction(pdf_path: str):
    """Prueba la extracción local y la compara con IA"""

    if not Path(pdf_path).exists():
        print(f"❌ Error: Archivo no encontrado: {pdf_path}")
        return

    print(f"\n🧪 INICIANDO PRUEBAS DE EXTRACCIÓN")
    print(f"📄 PDF: {pdf_path}")
    print(f"{'='*80}\n")

    # 1. Extracción LOCAL
    print("🔧 Extrayendo estructura con PARSER LOCAL...")
    extractor_local = LocalStructureExtractor(pdf_path)
    estructura_local = extractor_local.extraer_estructura(force_refresh=True)
    imprimir_estructura(estructura_local, "LOCAL (Parser determinista)")

    # 2. Extracción IA
    print("\n🤖 Extrayendo estructura con IA...")
    try:
        extractor_ia = StructureExtractionAgent()
        estructura_ia = await extractor_ia.extraer_estructura(pdf_path)
        imprimir_estructura(estructura_ia, "IA (LLM)")

        # 3. Comparación
        comparar_estructuras(estructura_local, estructura_ia)

    except Exception as e:
        print(f"⚠️ No se pudo completar extracción con IA: {e}")
        print(f"   (Verifica que OPENROUTER_API_KEY esté configurada)")

    # 4. Guardar resultados
    output_dir = Path("logs/extraction_comparison")
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = int(time.time())
    pdf_name = Path(pdf_path).stem

    local_file = output_dir / f"local_{pdf_name}_{timestamp}.json"
    with open(local_file, 'w', encoding='utf-8') as f:
        json.dump(estructura_local, f, indent=2, ensure_ascii=False)
    print(f"💾 Estructura local guardada: {local_file}")

    if 'estructura_ia' in locals():
        ia_file = output_dir / f"ia_{pdf_name}_{timestamp}.json"
        with open(ia_file, 'w', encoding='utf-8') as f:
            json.dump(estructura_ia, f, indent=2, ensure_ascii=False)
        print(f"💾 Estructura IA guardada: {ia_file}")

    print(f"\n✅ Pruebas completadas")


if __name__ == "__main__":
    # PDF de prueba por defecto
    default_pdf = "ejemplo/PROYECTO CALYPOFADO_extract.pdf"

    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        pdf_path = default_pdf
        print(f"ℹ️  Usando PDF por defecto: {pdf_path}")
        print(f"   Para usar otro PDF: python {sys.argv[0]} <ruta_al_pdf>\n")

    asyncio.run(test_local_extraction(pdf_path))
