# Fix: Detección de solapamiento entre código y unidad en partidas

## Fecha
2026-01-14

## Problema detectado

En algunos PDFs, cuando existe solapamiento visual entre el código de partida y la unidad (representada por símbolos como ■), la extracción de texto puede omitir la unidad completamente, causando que el parser no pueda procesar correctamente la partida.

### Ejemplo real del problema (basado en imagen adjunta)

**En el PDF visualmente:**
```
Código: APUDes23UA014e
Unidad: ■ (símbolo visual)
Título: LEVANTADO DE BORDILLO DE GRANITO CON RECUPERACIÓN
```

**Pero por solapamiento del símbolo ■, el texto extraído es:**
```
APUDes23UA014e LEVANTADO DE BORDILLO DE GRANITO CON RECUPERACIÓN 95,00 9,17 869,32
```

**El parser NO podía procesarlo porque:**
- El patrón esperaba: `CODIGO UNIDAD TITULO CANTIDAD PRECIO IMPORTE`
- Pero recibía: `CODIGO TITULO CANTIDAD PRECIO IMPORTE` (falta la UNIDAD)
- Al no coincidir con el patrón `PATRON_PARTIDA`, se clasificaba como `PARTIDA_DATOS` y se descartaba

**Resultado:** La partida no se procesaba y se perdían datos válidos.

---

## Problema crítico adicional detectado

**Caso real que causaba pérdida de partidas:**

```
m23E01DKW010 ■ LEVANTADO BARANDILLAS/VALLAS C/MEDIOS MANUALES 153,00 11,89 1.819,17
(05/2008. Medición de longitud realmente ejecutada)
APUDm23E01DKAm0220 LEVANTADO CARPINTERÍA METÁLICA C/MEDIOS MANUALES 327,00 12,74 4.165,98
```

**Lo que pasaba ANTES del fix:**

1. Primera partida `m23E01DKW010` → ✓ Se procesaba correctamente con números 153,00 11,89 1.819,17
2. Línea de descripción `(05/2008...)` → ✓ Se añadía a descripción
3. Segunda partida `APUDm23E01DKAm0220...` → ❌ **NO se detectaba como nueva partida**
4. Sus números `327,00 12,74 4.165,98` se asignaban a la partida anterior (`m23E01DKW010`)
5. **Resultado**: La partida `m23E01DKW010` quedaba con datos INCORRECTOS (327,00 en lugar de 153,00)
6. **Resultado**: La partida `APUDm23E01DKAm0220` se PERDÍA completamente

**Causa raíz:** El patrón de detección de solapamiento **NO permitía códigos con letras minúsculas**:

```python
# ANTES (patrón incorrecto):
patron_sin_unidad = re.compile(r'^([A-Z][A-Z0-9]{4,})\s+...')
#                                       ^^^^^^ Solo mayúsculas
```

El código `APUDm23E01DKAm0220` tiene letras minúsculas (`m`, `m`) que NO matcheaban con `[A-Z0-9]`, por lo que:
- NO se detectaba como `PARTIDA_HEADER`
- Se clasificaba como `PARTIDA_DATOS` (solo números)
- Los números se asignaban a la partida anterior
- La partida se perdía

---

## Solución implementada

Se corrigió el patrón regex para **permitir mayúsculas Y minúsculas** en los códigos de partida.

### Cómo funciona ahora

El patrón actualizado detecta códigos con formato mixto (mayúsculas/minúsculas):

```python
# DESPUÉS (patrón corregido):
patron_sin_unidad = re.compile(r'^([A-Z][A-Za-z0-9]{4,})\s+([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑa-záéíóúñ\s]+.*)$')
#                                       ^^^^^^^^^^^ Ahora permite mayús Y minús
```

**Cambios aplicados:**

1. **Partidas CON números** (línea 199):
   - Antes: `[A-Z0-9]{4,}` (solo mayúsculas + números)
   - Ahora: `[A-Za-z0-9]{4,}` (mayúsculas + minúsculas + números)

2. **Partidas SIN números** (línea 268):
   - Antes: `[A-Z0-9]{4,}` (solo mayúsculas + números)
   - Ahora: `[A-Za-z0-9]{4,}` (mayúsculas + minúsculas + números)

**Implementado en:**
- [src/parser/line_classifier.py:199](src/parser/line_classifier.py#L199) - Partidas completas (con números)
- [src/parser/line_classifier.py:268](src/parser/line_classifier.py#L268) - Headers de partida (sin números)

### Validaciones que se mantienen

La solución sigue siendo **estricta** para evitar falsos positivos:

1. **Patrón de código**: Debe empezar con letra mayúscula, luego al menos 4 caracteres alfanuméricos
2. **Rechaza referencias a normativas**: Detecta puntos finales (`105/2008.`, `NTE-ADD.`)
3. **Rechaza códigos con guiones**: Evita capturas de referencias como `NTE-ADD`
4. **Valida longitud mínima**: Códigos < 5 caracteres se rechazan
5. **Valida título**: Debe tener al menos 2 palabras para ser una descripción válida
6. **Excluye unidades**: No procesa si detecta que es una unidad común (m2, ud, kg, etc.)

---

## Ejemplos de casos manejados

### Caso 1: Código con minúsculas, falta unidad CON números (caso real corregido)

**Entrada extraída del PDF:**
```
APUDm23E01DKAm0220 LEVANTADO CARPINTERÍA METÁLICA C/MEDIOS MANUALES 327,00 12,74 4.165,98
```

**ANTES del fix:**
```
❌ NO matchea con patrón (minúsculas no permitidas)
❌ Se clasifica como PARTIDA_DATOS
❌ Los números se asignan a la partida anterior
❌ La partida se pierde
```

**DESPUÉS del fix:**
```
✅ Matchea con patrón actualizado (permite minúsculas)
codigo: "APUDm23E01DKAm0220"  ✅ Código original preservado
unidad: "X"  ✅ Marcada como desconocida
resumen: "LEVANTADO CARPINTERÍA METÁLICA C/MEDIOS MANUALES"  ✅ Título completo
cantidad: 327,00
precio: 12,74
importe: 4.165,98
✅ Se procesa correctamente como NUEVA partida
solapamiento_detectado: True
```

---

### Caso 2: Código válido, falta unidad CON números (caso original)

**Entrada extraída del PDF:**
```
APUDes23UA014e LEVANTADO DE BORDILLO DE GRANITO CON RECUPERACIÓN 95,00 9,17 869,32
```

**ANTES del fix:**
```
❌ No matchea con PATRON_PARTIDA (falta unidad)
❌ Se clasifica como PARTIDA_DATOS
❌ Se descarta la partida completa
```

**DESPUÉS del fix:**
```
codigo: "APUDes23UA014e"  ✅ Código original preservado
unidad: "X"  ✅ Marcada como desconocida
resumen: "LEVANTADO DE BORDILLO DE GRANITO CON RECUPERACIÓN"  ✅ Título completo
cantidad: 95,00
precio: 9,17
importe: 869,32
✅ Se procesa correctamente
solapamiento_detectado: True
```

---

### Caso 3: Código válido, falta unidad SIN números

**Entrada extraída del PDF:**
```
APUDes23UA014e2 LEVANTADO DE BORDILLO SIN RECUPERACIÓN
```

**ANTES del fix:**
```
❌ No matchea con PATRON_PARTIDA
❌ Se clasifica como IGNORAR
❌ Se descarta
```

**DESPUÉS del fix:**
```
codigo: "APUDes23UA014e2"
unidad: "X"
resumen: "LEVANTADO DE BORDILLO SIN RECUPERACIÓN"
✅ Se procesa correctamente
solapamiento_detectado: True
```

---

### Caso 4: Sin solapamiento (funcionamiento normal)

**Entrada extraída del PDF:**
```
m23U01A010 ■ LEVANTADO DE BORDILLO 1,00 3,95 3,95
```

**Procesamiento (sin cambios):**
```
codigo: "m23U01A010"
unidad: "■"
resumen: "LEVANTADO DE BORDILLO"
cantidad: 1,00
precio: 3,95
importe: 3,95
✅ Procesamiento normal sin detección de solapamiento
```

---

## Códigos soportados

### Ejemplos de códigos VÁLIDOS (ahora detectados correctamente):

- `APUDm23E01DKAm0220` ✅ (mayúsculas + minúsculas + números)
- `APUDes23UA014e` ✅ (mayúsculas + minúsculas + números)
- `m23U01A010` ✅ (empieza minúscula pero se captura en otro patrón)
- `M23E01DKW010` ✅ (mayúsculas + números)
- `APU123ABC` ✅ (mayúsculas + números)
- `Abcd12345` ✅ (minúsculas + números)

### Ejemplos de códigos RECHAZADOS (no son partidas):

- `105/2008.` ❌ (termina en punto - es referencia)
- `NTE-ADD.` ❌ (termina en punto - es referencia)
- `NTE-ADD` ❌ (guion cerca del final - es referencia)
- `ABC` ❌ (muy corto, < 5 caracteres)
- `m2` ❌ (es una unidad)
- `ud` ❌ (es una unidad)
- `kg` ❌ (es una unidad)

---

## Unidades detectadas

El sistema detecta las siguientes unidades comunes cuando aparecen en la posición de "código":

- **Superficie**: `m2`, `m²`, `m3`, `m³`, `M2`, `M3`
- **Longitud**: `m`, `ml`, `Ml`, `M`
- **Unidades**: `ud`, `u`, `UD`, `U`, `uf`, `UF`
- **Peso**: `kg`, `Kg`, `KG`, `t`, `T`
- **Volumen**: `l`, `L`
- **Otros**: `h`, `H` (horas)
- **Partidas alzadas**: `pa`, `PA`, `Pa`, `P.A.`, `P:A:`

---

## Impacto

### Ventajas
- ✅ **Recuperación de partidas**: Partidas que antes se descartaban ahora se procesan
- ✅ **Código original preservado**: El código real del presupuesto se mantiene intacto (incluyendo minúsculas)
- ✅ **Trazabilidad**: Flag `solapamiento_detectado: True` permite auditoría
- ✅ **Logging explícito**: Warnings informativos cuando se detecta solapamiento
- ✅ **Título completo**: Se preserva el título completo de la partida
- ✅ **Conservador**: Solo actúa cuando falta la unidad, no introduce cambios innecesarios
- ✅ **Previene pérdida de datos**: Las partidas se procesan correctamente en lugar de perderse

### Consideraciones
- ⚠️ **Unidad desconocida**: Se marca como `"X"` para indicar que la unidad real se perdió por solapamiento
- ℹ️ **Revisión recomendada**: Las partidas con `unidad: "X"` y `solapamiento_detectado: True` pueden requerir revisión manual para determinar la unidad correcta

---

## Archivos modificados

- [src/parser/line_classifier.py](src/parser/line_classifier.py):
  - **Línea 199**: Patrón actualizado para partidas completas sin unidad (con números) - ahora soporta mayúsculas/minúsculas
  - **Línea 268**: Patrón actualizado para headers de partida sin unidad (sin números) - ahora soporta mayúsculas/minúsculas

---

## Testing recomendado

### Test 1: Verificar detección de códigos con minúsculas
1. Procesar un PDF con partidas como `APUDm23E01DKAm0220`
2. Verificar en logs: `"⚠️  Partida sin unidad detectada: código='APUDm23E01DKAm0220'"`
3. Verificar que las partidas se procesaron con:
   - Código original preservado (ej: `APUDm23E01DKAm0220` con minúsculas)
   - Unidad = `"X"`
   - Título completo preservado
   - Números correctos asignados

### Test 2: Verificar no pérdida de partidas
1. Procesar un PDF con múltiples partidas consecutivas sin unidad
2. Confirmar que TODAS las partidas aparecen en BD (ninguna se pierde)
3. Verificar que los números de cada partida son correctos (no se cruzan)

### Test 3: Verificar funcionamiento normal
1. Procesar un PDF normal sin solapamiento
2. Confirmar que las partidas normales NO se ven afectadas
3. Verificar que NO aparecen warnings de solapamiento innecesarios

### Test 4: Verificar flag en base de datos
1. Después de procesar, consultar partidas en BD
2. Buscar partidas con `solapamiento_detectado: True` y `unidad: "X"`
3. Revisar manualmente estas partidas para confirmar la corrección

---

## Notas adicionales

### Mejoras futuras
1. **OCR mejorado**: Usar librerías de OCR más avanzadas que detecten solapamientos
2. **Análisis de posición**: Usar coordenadas X/Y para detectar superposición visual
3. **Corrección con LLM**: Enviar casos detectados al LLM para recuperar la unidad real
4. **Base de conocimiento**: Mantener un diccionario de códigos comunes por tipo de unidad

### Compatibilidad
- ✅ **Retrocompatible**: No afecta el procesamiento de PDFs correctos
- ✅ **Automático**: Se aplica sin configuración adicional
- ✅ **Seguro**: Mejor procesar con unidad sintética que descartar o perder la partida
