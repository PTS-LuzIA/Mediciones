#!/usr/bin/env python3
"""
Script para analizar los resultados de extracción de partidas.
Muestra estadísticas sobre cuántas partidas se procesaron exitosamente
y cuántos caracteres/tokens se usaron.
"""

import json
import os
from pathlib import Path
from typing import List, Dict

def analyze_extraction_files():
    """Analiza todos los archivos de extracción en logs/"""
    logs_dir = Path("logs")

    if not logs_dir.exists():
        print("❌ No existe el directorio logs/")
        return

    # Buscar archivos de extracción
    success_files = list(logs_dir.glob("partida_extraction_success_*.json"))
    error_files = list(logs_dir.glob("partida_extraction_error_*.json"))

    print("=" * 70)
    print("  ANÁLISIS DE EXTRACCIÓN DE PARTIDAS")
    print("=" * 70)
    print()

    # Analizar extracciones exitosas
    if success_files:
        print(f"✓ Extracciones exitosas: {len(success_files)}")
        print()

        total_partidas = 0
        total_caracteres = 0

        for file in sorted(success_files):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                capitulo = data.get('capitulo_codigo', '??')
                num_partidas = data.get('num_partidas', 0)
                total = data.get('total_extraido', 0)
                tiempo = data.get('tiempo_procesamiento', 0)

                # Calcular tamaño del JSON
                json_size = len(json.dumps(data, ensure_ascii=False))

                total_partidas += num_partidas
                total_caracteres += json_size

                print(f"  Capítulo {capitulo}:")
                print(f"    - Partidas: {num_partidas}")
                print(f"    - Total: {total:,.2f} €")
                print(f"    - Tiempo: {tiempo:.2f}s")
                print(f"    - Tamaño JSON: {json_size:,} caracteres (~{json_size//4} tokens)")
                print(f"    - Archivo: {file.name}")
                print()

            except Exception as e:
                print(f"  ⚠️ Error leyendo {file.name}: {e}")

        print(f"📊 TOTALES:")
        print(f"   - Total partidas: {total_partidas}")
        print(f"   - Total caracteres: {total_caracteres:,} (~{total_caracteres//4:,} tokens)")
        print(f"   - Promedio por capítulo: {total_partidas//len(success_files) if success_files else 0} partidas")
        print()
    else:
        print("❌ No hay extracciones exitosas")
        print()

    # Analizar errores
    if error_files:
        print(f"❌ Extracciones con error: {len(error_files)}")
        print()

        for file in sorted(error_files):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Extraer capítulo del nombre del archivo
                parts = file.stem.split('_')
                capitulo = parts[3] if len(parts) > 3 else '??'

                size = len(content)

                print(f"  Capítulo {capitulo}:")
                print(f"    - Tamaño: {size:,} caracteres (~{size//4:,} tokens)")
                print(f"    - Archivo: {file.name}")

                # Intentar detectar dónde se truncó
                if content.strip().endswith('}'):
                    print(f"    - ⚠️ JSON parece completo pero tiene error de sintaxis")
                else:
                    print(f"    - ⚠️ JSON truncado (no termina con '}}' )")

                # Contar llaves para ver balance
                open_braces = content.count('{')
                close_braces = content.count('}')
                print(f"    - Balance llaves: {open_braces} abiertas, {close_braces} cerradas")
                print()

            except Exception as e:
                print(f"  ⚠️ Error leyendo {file.name}: {e}")
        print()
    else:
        print("✓ No hay errores de extracción")
        print()

    print("=" * 70)
    print()

    # Recomendaciones
    if error_files:
        print("💡 RECOMENDACIONES:")
        print()
        if total_caracteres > 0:
            print(f"   - Las extracciones exitosas usan ~{total_caracteres//len(success_files)//4:,} tokens en promedio")
            print(f"   - Límite seguro recomendado: {(total_caracteres//len(success_files)//4) * 2:,} tokens por capítulo")
        print(f"   - Considera dividir capítulos grandes en subcapítulos")
        print(f"   - O procesar partidas en lotes más pequeños")
        print()

if __name__ == "__main__":
    analyze_extraction_files()
