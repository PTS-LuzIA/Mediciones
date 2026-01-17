"""
Debug: verificar qué grupos captura el patrón
"""
import re

PATRON = re.compile(r'^([A-Z0-9][A-Z0-9\.\s_]+?)\s+(m[2-3]?|M[2-3]?|Ml|ml|M|m\.|ud|Ud|UD|[Pp][\.:][Aa][\.::]?|pa|Pa|u)\s*(.+)', re.IGNORECASE)

lineas_test = [
    "03.02.01 M3 RELLENO MORRO",
    "03.02.02 P:A:REPARACIONES FÁBRICAS",
]

for linea in lineas_test:
    print(f"\nLínea: {repr(linea)}")
    match = PATRON.match(linea)
    if match:
        print(f"  ✓ MATCH")
        print(f"    Grupo 1 (código):  {repr(match.group(1))}")
        print(f"    Grupo 2 (unidad):  {repr(match.group(2))}")
        print(f"    Grupo 3 (resumen): {repr(match.group(3))}")
    else:
        print(f"  ✗ NO MATCH")

# Verificar qué pasa con el no-greedy
print("\n" + "="*80)
print("ANÁLISIS DEL PROBLEMA")
print("="*80)

print("\nEl patrón ([A-Z0-9][A-Z0-9\\.\\s_]+?) es NO-GREEDY (termina en ?)")
print("Esto significa que intenta capturar lo MÍNIMO posible")
print("\nPara '03.02.01 M3 RELLENO MORRO':")
print("  El patrón intenta: '03.02.01' -> ¿coincide M3? SÍ")
print("  Resultado: código='03.02.01', unidad='M3', resumen='RELLENO MORRO'")

print("\nPara '03.02.02 P:A:REPARACIONES':")
print("  El patrón intenta: '03.02.02' -> ¿coincide P:A:? SÍ")
print("  Resultado: código='03.02.02', unidad='P:A:', resumen='REPARACIONES FÁBRICAS'")

print("\n✓ El patrón funciona correctamente!")
print("\nEl problema debe estar en otro lugar del código...")
