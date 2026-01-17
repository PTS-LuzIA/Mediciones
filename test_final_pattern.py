"""
Testar patrón final: código case-sensitive (mayúsculas), unidad explícita
"""
import re

# Patrón FINAL: código case-sensitive, todas las variaciones de unidad explícitas
PATRON_FINAL = re.compile(r'^([A-Z0-9][A-Z0-9\.\s_]{0,15}?)\s+(m[2-3]?|M[2-3]?|Ml|ml|M\.?|m\.|[Uu][Dd]?|PA|Pa|pa|[Pp][\.:][Aa][\.::]?)\s*(.+)')

lineas_test = [
    # Válidas (código TODO MAYÚSCULAS)
    ("03.02.01 M3 RELLENO MORRO", True),
    ("03.02.02 P:A:REPARACIONES FÁBRICAS", True),
    ("03.02.02 P.A. REPARACIONES", True),
    ("03.02.02 PA REPARACIONES", True),
    ("REC POZ ud PUESTA A PUNTO", True),
    ("REC POZ Ud PUESTA A PUNTO", True),
    ("REC POZ UD PUESTA A PUNTO", True),
    ("C08.01 m DEMOLICIÓN", True),
    ("C08.01 M DEMOLICIÓN", True),
    ("DEM06 Ml CORTE", True),
    ("DEM06 ml CORTE", True),

    # Inválidas (código con minúsculas = descripción)
    ("Relleno de lecho de cauce con morro de gravera", False),
    ("Partida alzada para reparaciónes de fábricas", False),
    ("hasta rasante de lecho antiguo.", False),
]

print("=== TEST PATRÓN FINAL ===\n")

todos_ok = True
for linea, debe_coincidir in lineas_test:
    match = PATRON_FINAL.match(linea)

    es_correcto = (match is not None) == debe_coincidir
    simbolo = "✓" if es_correcto else "✗"
    resultado = "MATCH" if match else "NO MATCH"
    esperado = "esperado" if debe_coincidir else "no esperado"

    print(f"{simbolo} {resultado:10s} ({esperado:12s}): {linea[:60]}")

    if match and debe_coincidir:
        print(f"    Código: {repr(match.group(1)):20s} Unidad: {repr(match.group(2)):8s}")

    if not es_correcto:
        todos_ok = False
        print("    ^^^ ERROR")

print()
if todos_ok:
    print("✓ ¡TODOS LOS TESTS PASADOS!")
else:
    print("✗ Algunos tests fallaron")
