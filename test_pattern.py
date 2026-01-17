"""
Testar el nuevo patrón directamente
"""
import re

# Patrón NUEVO - con \s* (0 o más espacios)
PATRON_NUEVO = re.compile(r'^([A-Z0-9][A-Z0-9\.\s_]+?)\s+(m[2-3]?|M[2-3]?|Ml|ml|M|m\.|ud|Ud|UD|[Pp][\.:][Aa][\.::]?|pa|Pa|u)\s*(.+)', re.IGNORECASE)

# Patrón VIEJO - con \s+ (1 o más espacios)
PATRON_VIEJO = re.compile(r'^([A-Z0-9][A-Z0-9\.\s_]+?)\s+(m[2-3]?|M[2-3]?|Ml|ml|M|m\.|ud|Ud|UD|[Pp][\.:][Aa][\.::]?|pa|Pa|u)\s+(.+)', re.IGNORECASE)

# Línea real del PDF
linea_real = '03.02.02 P:A:REPARACIONES FÁBRICAS'

print("=== TEST DE PATRONES ===\n")
print(f"Línea: {repr(linea_real)}\n")

print("Patrón VIEJO (\\s+ después de unidad):")
match = PATRON_VIEJO.match(linea_real)
if match:
    print(f"  ✓ MATCH")
    print(f"    Código: {match.group(1)}")
    print(f"    Unidad: {match.group(2)}")
    print(f"    Resumen: {match.group(3)}")
else:
    print(f"  ✗ NO MATCH")

print("\nPatrón NUEVO (\\s* después de unidad):")
match = PATRON_NUEVO.match(linea_real)
if match:
    print(f"  ✓ MATCH")
    print(f"    Código: {match.group(1)}")
    print(f"    Unidad: {match.group(2)}")
    print(f"    Resumen: {match.group(3)}")
else:
    print(f"  ✗ NO MATCH")

# Analizar por qué
print("\n=== ANÁLISIS ===\n")
print("Dividiendo la línea manualmente:")
partes = linea_real.split()
print(f"  Parte 1 (código): {partes[0]}")
print(f"  Parte 2 (unidad+resumen): {partes[1]}")

# Intentar match del patrón de unidad
patron_unidad = re.compile(r'^([Pp][\.:][Aa][\.::]?)(.*)$')
match_unidad = patron_unidad.match(partes[1])
if match_unidad:
    print(f"\n  Unidad capturada: {match_unidad.group(1)}")
    print(f"  Resumen pegado: {match_unidad.group(2)}")
