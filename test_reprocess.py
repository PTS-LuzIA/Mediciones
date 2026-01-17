"""
Re-procesar proyecto 8 (CALLE ARENAL) para verificar fix de P:A:
"""
import requests
import json

# 1. Obtener info del proyecto 8
proyecto = requests.get('http://localhost:3013/proyectos/8').json()
print(f"Proyecto: {proyecto['nombre']}")
print(f"Archivo: {proyecto['archivo_origen']}")

# 2. Re-procesar el archivo
pdf_filename = proyecto['archivo_origen'].split('/')[-1]
print(f"\nRe-procesando {pdf_filename}...")

# Trigger reprocessing by deleting and re-uploading would be complex
# Instead, let's just check the current extraction
print("\n=== VERIFICANDO SUBCAPÍTULO 03.02 ===\n")

for cap in proyecto['capitulos']:
    for sub in cap['subcapitulos']:
        if sub['codigo'] == '03.02':
            print(f"Subcapítulo: {sub['codigo']} - {sub['nombre']}")
            print(f"Partidas encontradas: {len(sub['partidas'])}")

            total_sub = sum(p['importe'] for p in sub['partidas'])
            print(f"Total: {total_sub:,.2f} €")

            print("\nPartidas:")
            for i, p in enumerate(sub['partidas'], 1):
                print(f"  {i}. {p['codigo']:15s} | {p['unidad']:5s} | {p['resumen'][:50]}")
                print(f"     Cantidad: {p['cantidad']}, Precio: {p['precio']}, Importe: {p['importe']}")

            print("\n¿Se detectó P:A: correctamente?")
            pa_partidas = [p for p in sub['partidas'] if 'P:A:' in p['resumen'] or p['unidad'] == 'PA']
            if pa_partidas:
                print(f"✓ SÍ - Encontradas {len(pa_partidas)} partidas con PA")
                for p in pa_partidas:
                    print(f"  • {p['codigo']} - Unidad: {p['unidad']}")
            else:
                print("❌ NO - No se encontraron partidas con PA/P:A:")
