"""
Testar patrón con código case-sensitive
"""
import re

# Patrón NUEVO: código case-sensitive, unidad case-insensitive
PATRON_NUEVO = re.compile(r'^([A-Z0-9][A-Z0-9\.\s_]{0,15}?)\s+(?i)(m[2-3]?|M[2-3]?|Ml|ml|M|m\.|ud|Ud|UD|[Pp][\.:][Aa][\.::]?|pa|Pa|u)\s*(.+)')

lineas_test = [
    # Válidas (código TODO MAYÚSCULAS)
    ("03.02.01 M3 RELLENO MORRO", True),
    ("03.02.02 P:A:REPARACIONES FÁBRICAS", True),
    ("REC POZ ud PUESTA A PUNTO", True),
    ("C08.01 m DEMOLICIÓN", True),
    ("DEM06 Ml CORTE", True),

    # Inválidas (código con minúsculas = descripción)
    ("Relleno de lecho de cauce con morro de gravera", False),
    ("Partida alzada para reparaciónes de fábricas", False),
]

print("=== TEST PATRÓN CASE-SENSITIVE PARA CÓDIGO ===\n")

todos_ok = True
for linea, debe_coincidir in lineas_test:
    match = PATRON_NUEVO.match(linea)

    es_correcto = (match is not None) == debe_coincidir
    simbolo = "✓" if es_correcto else "✗"
    resultado = "MATCH" if match else "NO MATCH"
    esperado = "esperado" if debe_coincidir else "no esperado"

    print(f"{simbolo} {resultado:10s} ({esperado:12s}): {linea[:60]}")

    if match and debe_coincidir:
        print(f"    Código: {repr(match.group(1)):20s} Unidad: {repr(match.group(2)):8s}")

    if not es_correcto:
        todos_ok = False

if todos_ok:
    print("\n✓ ¡TODOS LOS TESTS PASADOS!")
else:
    print("\n✗ Algunos tests fallaron")
