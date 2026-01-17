"""
Verificar totales por subcapítulo
"""
import requests
import json

# Obtener último proyecto
proyectos = requests.get('http://localhost:3013/proyectos').json()
ultimo_id = proyectos[-1]['id']

print(f'Proyecto ID: {ultimo_id}')

# Obtener detalles
proyecto = requests.get(f'http://localhost:3013/proyectos/{ultimo_id}').json()

print('\n=== TOTALES POR SUBCAPÍTULO ===\n')

esperados = {
    'C08.01': 110289.85,
    'C08.02': 65759.91,
    'C08.03': 78462.51,
    'C08.04': 158602.05,
    'C08.05': 82431.50,
    'C08.06': 56094.94,
    'C08.07': 24435.12,
    'C08.08': 13700.00,  # Incluye apartado
    'C10': 13540.00,  # Seguridad y Salud + Gestión de Residuos
}

total_general = 0

for cap in proyecto['capitulos']:
    # Partidas directas del capítulo
    total_cap_directo = sum(p['importe'] for p in cap.get('partidas', []))
    if total_cap_directo > 0:
        total_general += total_cap_directo
        print(f'{cap["codigo"]:10s} (directo): {total_cap_directo:>12,.2f} €')

    for sub in cap['subcapitulos']:
        total_sub = sum(p['importe'] for p in sub['partidas'])
        for apt in sub['apartados']:
            total_sub += sum(p['importe'] for p in apt['partidas'])

        total_general += total_sub

        codigo = sub['codigo']
        esperado = esperados.get(codigo, 0)
        diferencia = total_sub - esperado

        formato_total = f'{total_sub:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
        formato_esperado = f'{esperado:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
        formato_dif = f'{diferencia:+,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')

        simbolo = '✓' if abs(diferencia) < 1 else '❌'
        print(f'{simbolo} {codigo:10s}: {formato_total:>15s} € | Esperado: {formato_esperado:>15s} € | Dif: {formato_dif:>12s} €')

print(f'\n=== TOTAL GENERAL ===')
formato_total_gen = f'{total_general:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
total_esperado = 603315.73  # Incluye C10
print(f'TOTAL extraído: {formato_total_gen:>15s} €')
print(f'TOTAL esperado: 603.315,73 €')
diferencia_total = total_general - total_esperado
formato_dif_total = f'{diferencia_total:+,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
print(f'Diferencia:     {formato_dif_total:>15s} €')
