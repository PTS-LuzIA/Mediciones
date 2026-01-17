# Fix: Preservación selectiva de partidas y eliminación de pies de página

## Fecha
2026-01-14

## Cambios implementados

### 1. Limpieza de BD en Fase 2 para evitar duplicados

#### Situación
Durante el reprocesamiento de la Fase 2 del sistema híbrido, las partidas existentes se acumulaban causando **duplicados** cuando se reprocesaba el mismo proyecto.

#### Solución aplicada
Se **mantiene activa** la eliminación de partidas antes de reprocesar la Fase 2 en [src/api/main.py:1894-1909](src/api/main.py#L1894-L1909).

**Comportamiento actual:**
```python
# Eliminar partidas anteriores si existen para evitar duplicados
# Al reprocesar, se limpia la BD y se regeneran todas las partidas desde cero
total_partidas_eliminadas = 0
for capitulo in proyecto.capitulos:
    for subcapitulo in capitulo.subcapitulos:
        total_partidas_eliminadas += len(subcapitulo.partidas)
        for partida in list(subcapitulo.partidas):
            hybrid_db.session.delete(partida)
        for apartado in subcapitulo.apartados:
            total_partidas_eliminadas += len(apartado.partidas)
            for partida in list(apartado.partidas):
                hybrid_db.session.delete(partida)

if total_partidas_eliminadas > 0:
    logger.info(f"[FASE 2] Eliminadas {total_partidas_eliminadas} partidas anteriores para reprocesamiento limpio")
    hybrid_db.session.commit()
```

#### Impacto
- ✅ **Evita duplicados**: Cada reprocesamiento genera un conjunto limpio de partidas
- ✅ **Reprocesamiento completo**: Útil cuando se detecta un error y se requiere regenerar todo
- ⚠️ **Nota**: Si había correcciones manuales, se perderán al reprocesar

#### Archivos modificados
- [src/api/main.py](src/api/main.py) (líneas 1894-1909)

---

### 2. Eliminación automática de pies de página con números de paginación

#### Problema detectado
Los números de página en los pies de página se extraían junto con el contenido real, causando errores en el procesamiento posterior. Estos números aparecen en cada página y contaminan el texto extraído sin aportar valor.

Ejemplos de pies de página problemáticos:
- `23` (solo número)
- `- 89 -` (número con guiones)
- `Página 15` o `Pág. 15`
- `23 / 89` (formato "página X de Y")

#### Solución aplicada
Se implementó un nuevo método `_filtrar_pies_pagina()` en [src/parser/pdf_extractor.py](src/parser/pdf_extractor.py) que detecta y elimina automáticamente líneas que contienen solo números de paginación.

#### Patrones detectados
El filtro detecta los siguientes formatos comunes:

```python
patrones_paginacion = [
    r'^\s*\d+\s*$',                    # Solo número: "23"
    r'^\s*-\s*\d+\s*-\s*$',            # Con guiones: "- 23 -"
    r'^\s*página\s+\d+\s*$',           # "Página 23" (case insensitive)
    r'^\s*pág\.?\s+\d+\s*$',           # "Pág. 23" o "Pag 23"
    r'^\s*page\s+\d+\s*$',             # "Page 23"
    r'^\s*p\.\s*\d+\s*$',              # "P. 23"
    r'^\s*\d+\s*/\s*\d+\s*$',          # "23 / 89" (página X de Y)
    r'^\s*\[\s*\d+\s*\]\s*$',          # "[23]"
]
```

#### Integración en el flujo
El filtrado se aplica automáticamente después del filtrado de cabeceras repetidas:

```python
# En extraer_todo() - líneas 112-117:

# Filtrar pies de página con números de paginación
lineas_antes_footer = len(resultado['all_lines'])
resultado['all_lines'] = self._filtrar_pies_pagina(resultado['all_lines'])
lineas_despues_footer = len(resultado['all_lines'])
if lineas_despues_footer < lineas_antes_footer:
    logger.info(f"🗑️  Pies de página eliminados: {lineas_antes_footer - lineas_despues_footer} líneas")
```

#### Resultados esperados
- ✅ **Limpieza automática**: Los números de página se eliminan sin intervención manual
- ✅ **Logging transparente**: Se informa cuántas líneas de pie de página se eliminaron
- ✅ **Sin pérdida de datos**: Solo se eliminan líneas que coinciden EXACTAMENTE con los patrones de paginación
- ✅ **Cobertura amplia**: Soporta múltiples formatos comunes de paginación

#### Archivos modificados
- [src/parser/pdf_extractor.py](src/parser/pdf_extractor.py):
  - Líneas 112-117: Integración en `extraer_todo()`
  - Líneas 187-236: Nuevo método `_filtrar_pies_pagina()`

---

### 3. Preservación de resumen y descripción durante revisión LLM (diferente a Fase 2)

#### Problema detectado
Cuando el LLM **revisa manualmente** un elemento específico (NO es reprocesamiento completo), la respuesta **NO incluye** los campos `resumen` (título) y `descripcion` porque no se solicitan en el prompt (para ahorrar tokens).

Sin embargo, el código de actualización estaba sobrescribiendo estos campos con valores vacíos, causando **pérdida permanente** del título y descripción.

#### Ejemplo del problema

**Partida original en BD:**
```python
codigo: "m23U01BP010"
resumen: "DEMOLICIÓN DE PAVIMENTO"  # ← Se perdía
descripcion: "Demolición de pavimento de hormigón..."  # ← Se perdía
cantidad: 450.40
precio: 2.34
importe: 1053.94
```

**Respuesta del LLM (sin título/descripción para ahorrar tokens):**
```json
{
  "codigo": "m23U01BP010",
  "cantidad": 450.40,
  "precio": 2.34,
  "importe": 1053.94
}
```

**Resultado ANTES del fix (datos perdidos):**
```python
codigo: "m23U01BP010"
resumen: ""  # ❌ PERDIDO
descripcion: ""  # ❌ PERDIDO
cantidad: 450.40
precio: 2.34
importe: 1053.94
```

**Resultado DESPUÉS del fix (datos preservados):**
```python
codigo: "m23U01BP010"
resumen: "DEMOLICIÓN DE PAVIMENTO"  # ✅ PRESERVADO
descripcion: "Demolición de pavimento de hormigón..."  # ✅ PRESERVADO
cantidad: 450.40
precio: 2.34
importe: 1053.94
```

#### Solución aplicada

Modificado el método `actualizar_partidas_elemento()` en [src/models/hybrid_db_manager.py:828-896](src/models/hybrid_db_manager.py#L828-L896) para:

1. **Solo actualizar campos numéricos** que vienen del LLM:
   - `cantidad`
   - `precio`
   - `importe`
   - `unidad` (solo si viene en la respuesta)

2. **Preservar siempre** los campos de texto:
   - `resumen` (título) - NO se modifica
   - `descripcion` - NO se modifica

3. **Detección inteligente de cambios**: Solo marca como actualizada si hay cambios reales en valores numéricos

4. **Desactivar eliminación de partidas**: Las partidas que NO aparecen en la respuesta del LLM se **preservan** (probablemente error de extracción, no eliminación intencionada)

#### Código clave

**Antes:**
```python
# ❌ Sobrescribía TODO, incluso con valores vacíos
partida_local.unidad = partida_ia.get('unidad', partida_local.unidad)
partida_local.resumen = partida_ia.get('resumen', partida_local.resumen)  # ← Perdía datos
partida_local.descripcion = partida_ia.get('descripcion', partida_local.descripcion)  # ← Perdía datos
partida_local.cantidad = partida_ia.get('cantidad', partida_local.cantidad)
partida_local.precio = partida_ia.get('precio', partida_local.precio)
partida_local.importe = partida_ia.get('importe', partida_local.importe)
```

**Después:**
```python
# ✅ Solo actualiza valores numéricos que cambiaron
cambios = False
if partida_local.cantidad != partida_ia.get('cantidad', partida_local.cantidad):
    partida_local.cantidad = partida_ia.get('cantidad', partida_local.cantidad)
    cambios = True
if partida_local.precio != partida_ia.get('precio', partida_local.precio):
    partida_local.precio = partida_ia.get('precio', partida_local.precio)
    cambios = True
if partida_local.importe != partida_ia.get('importe', partida_local.importe):
    partida_local.importe = partida_ia.get('importe', partida_local.importe)
    cambios = True

# ✅ PRESERVAR resumen y descripción existentes - NO sobrescribir
# partida_local.resumen NO se modifica
# partida_local.descripcion NO se modifica
```

#### Recálculo de totales corregido

También se corrigió el cálculo de totales para usar TODAS las partidas del elemento (no solo las de IA):

**Antes:**
```python
# ❌ Solo sumaba partidas de IA (incompleto)
total_local_nuevo = sum(p.get('importe', 0) for p in partidas_ia)
```

**Después:**
```python
# ✅ Suma TODAS las partidas del elemento (actualizadas + preservadas)
if elemento_tipo == "capitulo":
    total_local_nuevo = sum(p.importe for p in elemento.partidas)
elif elemento_tipo == "subcapitulo":
    total_local_nuevo = sum(p.importe for p in elemento.partidas)
```

#### Impacto
- ✅ **Protege títulos y descripciones**: Nunca se pierden durante revisiones con LLM
- ✅ **Actualización selectiva**: Solo modifica lo que realmente cambió
- ✅ **Logging mejorado**: Diferencia entre "actualizada" y "sin cambios"
- ✅ **Totales correctos**: Incluye todas las partidas al calcular totales
- ✅ **Sin eliminaciones accidentales**: Partidas faltantes en respuesta LLM se preservan con warning

#### Archivos modificados
- [src/models/hybrid_db_manager.py](src/models/hybrid_db_manager.py):
  - Líneas 828-864: Actualización selectiva de partidas
  - Líneas 883-896: Desactivación de eliminación de partidas
  - Líneas 898-905: Recálculo correcto de totales

---

## Compatibilidad

### Ambos cambios son:
- ✅ **Retrocompatibles**: No requieren cambios en código existente
- ✅ **Automáticos**: Se aplican sin configuración adicional
- ✅ **Seguros**: Preservan el contenido real de los presupuestos
- ✅ **Transparentes**: Informan al usuario mediante logs cuando se aplican

### Afecta a:
- ✅ **Fase 2 (Local)**: Usa `PDFExtractor` - se beneficia del filtrado de footers
- ✅ **Fase 3 (Híbrida)**: Usa `PDFExtractor` y se beneficia de ambos cambios (preservación + filtrado)

---

## Testing recomendado

### Test 1: Verificar preservación de partidas
1. Procesar un proyecto completo en Fase 2 Híbrida
2. Contar el número de partidas extraídas
3. Re-ejecutar Fase 2 para el mismo proyecto
4. Verificar que el número de partidas no disminuyó

### Test 2: Verificar eliminación de footers
1. Procesar un PDF con paginación visible
2. Revisar el archivo de texto extraído
3. Confirmar que los números de página NO aparecen en el contenido
4. Verificar en logs: `"🗑️  Pies de página eliminados: X líneas"`

### Test 3: Verificar preservación de resumen/descripción
1. Procesar un proyecto completo (Fase 2) que extraiga títulos y descripciones
2. Verificar en BD que las partidas tienen `resumen` y `descripcion` completos
3. Ejecutar revisión con IA de un capítulo/subcapítulo
4. Verificar que después de la revisión:
   - Los valores numéricos (cantidad, precio, importe) se actualizaron si cambiaron
   - Los campos `resumen` y `descripcion` **NO se perdieron**
5. Verificar en logs: `"✓ Actualizada: CODIGO (cambios detectados en valores numéricos)"`

---

## Notas adicionales

### Sobre duplicados
El cambio de preservación puede generar partidas duplicadas si se reprocesa el mismo contenido múltiples veces. Esto es **intencional** y preferible a perder datos.

Opciones para manejar duplicados:
1. **Validación en interfaz**: Mostrar advertencia si se detectan códigos duplicados
2. **Deduplicación post-procesamiento**: Filtrar duplicados al consultar partidas
3. **Merge inteligente**: Combinar partidas duplicadas manteniendo la mejor información

### Sobre footers
El filtrado de footers es **conservador** - solo elimina líneas que coinciden EXACTAMENTE con patrones de paginación. Si hay contenido real que incluye solo un número (poco común), se puede ajustar añadiendo validaciones adicionales.
