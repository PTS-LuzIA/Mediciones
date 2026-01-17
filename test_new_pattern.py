"""
Testar nuevo patrón con límite de 15 caracteres
"""
import re

# Patrón con límite de 15 caracteres
PATRON_NUEVO = re.compile(r'^([A-Z0-9][A-Z0-9\.\s_]{0,15}?)\s+(m[2-3]?|M[2-3]?|Ml|ml|M|m\.|ud|Ud|UD|[Pp][\.:][Aa][\.::]?|pa|Pa|u)\s*(.+)', re.IGNORECASE)

lineas_test = [
    # Válidas
    ("03.02.01 M3 RELLENO MORRO", True),
    ("03.02.02 P:A:REPARACIONES FÁBRICAS", True),
    ("REC POZ ud PUESTA A PUNTO", True),
    ("C08.01 m DEMOLICIÓN", True),

    # Inválidas (descripciones)
    ("Relleno de lecho de cauce con morro de gravera", False),
    ("Partida alzada para reparaciónes de fábricas", False),
]

print("=== TEST PATRÓN CON LÍMITE 15 CARACTERES ===\n")

for linea, debe_coincidir in lineas_test:
    match = PATRON_NUEVO.match(linea)

    simbolo = "✓" if (match is not None) == debe_coincidir else "✗"
    resultado = "MATCH" if match else "NO MATCH"
    esperado = "esperado" if debe_coincidir else "no esperado"

    print(f"{simbolo} {resultado:10s} ({esperado:12s}): {linea[:50]}")

    if match:
        print(f"    Código: {repr(match.group(1)):20s} Unidad: {repr(match.group(2)):8s}")
