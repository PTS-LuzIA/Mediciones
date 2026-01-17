"""
Test para verificar que la validación de códigos de partida rechaza códigos que no terminan en número.
Este test simula la validación que se aplica en partida_extraction_agent.py
"""

import re

def validar_codigo_partida(codigo: str, importe: float = 100.0) -> tuple[bool, str]:
    """
    Valida un código de partida según las reglas del sistema

    Args:
        codigo: Código a validar
        importe: Importe de la partida (default 100.0 para tests)

    Returns:
        (es_valido, razon) - Tupla con resultado y razón del rechazo
    """
    # Patrón para códigos válidos
    patron_valido = re.compile(r'^[a-zA-Z0-9]{3,}[a-zA-Z0-9._-]*$')
    patron_subcapitulo = re.compile(r'^\d{2}\.\d{2}(\.\d{2})?(\.\d{2})?$')

    # Validar formato de código
    if not codigo:
        return False, 'código vacío'

    # CRÍTICO: Rechazar palabras comunes que NO son códigos de partida
    palabras_prohibidas = ['ORDEN', 'CODIGO', 'CÓDIGO', 'RESUMEN', 'CANTIDAD', 'PRECIO', 'IMPORTE',
                          'UNIDAD', 'UD', 'TOTAL', 'SUBTOTAL', 'CAPITULO', 'CAPÍTULO',
                          'SUBCAPITULO', 'SUBCAPÍTULO', 'APARTADO', 'FOM', 'NTE', 'RD']
    if codigo.upper() in palabras_prohibidas:
        return False, 'palabra prohibida (no es código)'

    # CRÍTICO: Rechazar códigos que contienen solo letras sin números
    if not any(c.isdigit() for c in codigo):
        return False, 'no contiene números'

    # CRÍTICO: Rechazar partidas con importe 0
    if importe == 0 or importe is None:
        return False, 'importe es 0'

    # Rechazar códigos que parezcan subcapítulos
    if patron_subcapitulo.match(codigo):
        return False, 'parece subcapítulo'

    # Rechazar códigos muy cortos o solo letras/números simples
    if len(codigo) <= 2 or codigo in ['d', 'a', 'b', 'c', '1', '2']:
        return False, 'código inválido'

    # CRÍTICO: Verificar que el último carácter sea un número
    if not codigo[-1].isdigit():
        return False, 'no termina en número'

    # CRÍTICO: Verificar que no termine con unidades pegadas (m2, m3, ml, ud, etc.)
    patron_unidad_pegada = re.compile(r'[a-zA-Z]{1,2}\d$')
    if patron_unidad_pegada.search(codigo):
        ultimos_2 = codigo[-2:].lower()
        ultimos_3 = codigo[-3:].lower()
        unidades_conocidas = ['m2', 'm3', 'ml', 'ud', 'uf', 'pa', 'kg']
        if ultimos_2 in unidades_conocidas or ultimos_3 in unidades_conocidas:
            return False, 'termina con unidad pegada'

    # Validar patrón básico
    if not patron_valido.match(codigo):
        return False, 'formato incorrecto'

    return True, 'válido'


def test_validacion_codigos():
    """Test de validación de códigos de partida"""

    # Códigos VÁLIDOS (deben pasar)
    codigos_validos = [
        "DEM06",
        "U01AB100",
        "m23U01BP010",
        "APUI_003",
        "E08PEA090",
        "PY10AA012",
        "U11SAM020",
    ]

    # Códigos INVÁLIDOS (deben rechazarse)
    codigos_invalidos = {
        "ORDEN": "palabra prohibida (header de tabla)",
        "CODIGO": "palabra prohibida (header de tabla)",
        "RESUMEN": "palabra prohibida (header de tabla)",
        "FOM": "palabra prohibida (sin números)",
        "NTE": "palabra prohibida (sin números)",
        "DEM06m": "termina en letra (unidad mal extraída)",
        "DEM06m2": "termina en número pero incluye unidad",
        "U01ABm": "termina en letra",
        "APUI_003d": "termina en letra (unidad)",
        "m23U01BP010m2": "termina en unidad",
        "01.01": "parece subcapítulo",
        "01.04.01": "parece subcapítulo",
        "d": "código muy corto",
        "ud": "código muy corto",
        "": "código vacío",
        "ab": "código muy corto",
    }

    # Códigos con importe 0 (deben rechazarse)
    codigos_importe_0 = {
        "DEM06": 0.0,
        "U01AB100": 0,
        "ORDEN": 0.0,
    }

    print("=== TEST DE VALIDACIÓN DE CÓDIGOS DE PARTIDA ===\n")

    print("✅ CÓDIGOS VÁLIDOS:")
    errores_validos = 0
    for codigo in codigos_validos:
        valido, razon = validar_codigo_partida(codigo)
        resultado = "✅ PASS" if valido else f"❌ FAIL ({razon})"
        print(f"  {codigo:20s} → {resultado}")
        if not valido:
            errores_validos += 1

    print(f"\n❌ CÓDIGOS INVÁLIDOS:")
    errores_invalidos = 0
    for codigo, razon_esperada in codigos_invalidos.items():
        valido, razon = validar_codigo_partida(codigo)
        resultado = f"✅ PASS (rechazado: {razon})" if not valido else "❌ FAIL (aceptado erróneamente)"
        print(f"  {codigo:20s} → {resultado}")
        if valido:
            errores_invalidos += 1

    print(f"\n❌ CÓDIGOS CON IMPORTE 0 (deben rechazarse):")
    errores_importe_0 = 0
    for codigo, importe in codigos_importe_0.items():
        valido, razon = validar_codigo_partida(codigo, importe)
        resultado = f"✅ PASS (rechazado: {razon})" if not valido else "❌ FAIL (aceptado erróneamente)"
        print(f"  {codigo:20s} (importe={importe}) → {resultado}")
        if valido:
            errores_importe_0 += 1

    print("\n" + "="*60)
    print(f"\nRESULTADO:")
    print(f"  Códigos válidos: {len(codigos_validos) - errores_validos}/{len(codigos_validos)} pasaron")
    print(f"  Códigos inválidos: {len(codigos_invalidos) - errores_invalidos}/{len(codigos_invalidos)} rechazados correctamente")
    print(f"  Códigos con importe 0: {len(codigos_importe_0) - errores_importe_0}/{len(codigos_importe_0)} rechazados correctamente")

    if errores_validos == 0 and errores_invalidos == 0 and errores_importe_0 == 0:
        print("\n✅ TODOS LOS TESTS PASARON")
        return True
    else:
        print(f"\n❌ FALLOS: {errores_validos + errores_invalidos + errores_importe_0} test(s) fallaron")
        return False


if __name__ == "__main__":
    test_validacion_codigos()
