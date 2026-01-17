# Mejora de la Fase 1: Parser Especializado de Estructura

**Fecha:** 2026-01-14
**Objetivo:** Separar completamente la extracción de estructura (Fase 1) de la extracción de partidas (Fase 2)

## Problema Identificado

La Fase 1 (extracción de estructura) estaba usando el mismo `LineClassifier` y lógica que la Fase 2 (extracción de partidas), lo cual era incorrecto porque:

1. **Fase 1** solo debe extraer capítulos y subcapítulos (estructura jerárquica)
2. **Fase 2** extrae las partidas individuales dentro de esa estructura
3. Ambas fases necesitan parsers completamente diferentes

### Problemas específicos:

- ❌ No creaba niveles intermedios automáticamente (ej: si encontraba `01.04.01`, no creaba `01.04`)
- ❌ No creaba algunos subcapítulos como `01.04.02`, `01.04.03`
- ❌ Usaba lógica de partidas para detectar estructura
- ❌ Complejidad innecesaria para una tarea simple

## Solución Implementada

### 1. Nuevo Parser Especializado: `structure_parser.py`

Se creó un parser completamente nuevo y mucho más simple que:

#### Características principales:

- ✅ **Solo busca capítulos y subcapítulos** usando patrones simples:
  - Capítulos: `01 NOMBRE`, `02 NOMBRE`, etc.
  - Subcapítulos: `01.04 NOMBRE`, `01.04.01 NOMBRE`, `01.04.01.02 NOMBRE`, etc.

- ✅ **Crea niveles intermedios automáticamente**:
  - Si encuentra `01.04.01` pero no existe `01.04`, lo crea automáticamente

- ✅ **Detecta líneas TOTAL con código explícito**:
  ```
  TOTAL SUBCAPÍTULO 01.04.01    5000,00  → Asigna a 01.04.01
  TOTAL CAPÍTULO 01            15000,00  → Asigna a 01
  ```

- ✅ **Calcula totales faltantes**:
  - Si un nivel no tiene TOTAL explícito, suma los totales de sus hijos

- ✅ **Multinivel completo**:
  - Soporta cualquier nivel de anidación: `01`, `01.04`, `01.04.01`, `01.04.01.02`, etc.

#### Patrones de detección:

```python
# Capítulos: "01 FASE 2", "02 CIMENTACIÓN"
PATRON_CAPITULO = r'^(?:CAPÍTULO\s+)?(\d{1,2})\s+([A-Z][...]+)$'

# Subcapítulos: "01.04 PAVIMENTACIÓN", "01.04.01 PAVIMENTO PERMEABLE"
PATRON_SUBCAPITULO = r'^(?:SUBCAPÍTULO\s+)?(\d{1,2}(?:\.\d{1,2})+)\s+([A-Z][...]+)$'

# Totales con código: "TOTAL SUBCAPÍTULO 01.04  5000,00"
PATRON_TOTAL_CON_CODIGO = r'^TOTAL\s+(SUBCAPÍTULO|CAPÍTULO)\s+([\d\.]+)\s+([\d.,]+)$'
```

### 2. Modificación de `local_structure_extractor.py`

Se simplificó el extractor local para usar el nuevo parser:

**ANTES:**
```python
# Clasificar líneas con LineClassifier (Fase 2)
clasificaciones = LineClassifier.clasificar_bloque(lineas)
# Construir estructura con lógica compleja de partidas
estructura_interna = self._construir_estructura(clasificaciones)
# Calcular totales recursivamente
self._calcular_totales_recursivo(estructura_interna)
```

**DESPUÉS:**
```python
# Parsear estructura con el parser especializado de Fase 1
parser = StructureParser()
estructura_interna = parser.parsear(lineas)
# ¡Los totales ya están calculados!
```

### 3. Separación clara de responsabilidades

| Componente | Responsabilidad | Cuándo se usa |
|-----------|----------------|---------------|
| `structure_parser.py` | Extraer SOLO estructura (capítulos/subcapítulos) | **Fase 1** |
| `line_classifier.py` + `partida_parser.py` | Extraer partidas individuales | **Fase 2** |
| `structure_extraction_agent.py` | Extracción con IA (alternativa) | **Fase 1 con IA** |

## Ejemplo de Funcionamiento

### Entrada (líneas del PDF):
```
01 FASE 2
01.03 MOVIMIENTO DE TIERRAS
TOTAL SUBCAPÍTULO 01.03                5000,00
01.04 PAVIMENTACIÓN
01.04.01 PAVIMENTO PERMEABLE
TOTAL SUBCAPÍTULO 01.04.01             2500,50
01.04.02 PAVIMENTO IMPERMEABLE
TOTAL SUBCAPÍTULO 01.04.02             3000,75
01.04.03 JUNTAS
TOTAL SUBCAPÍTULO 01.04.03             1500,25
01.05 MUROS
01.05.01 MUROS DE SUELO
01.05.01.01 MURO TIPO 1
TOTAL SUBCAPÍTULO 01.05.01.01          1200,00
01.05.01.02 MURO TIPO 2
TOTAL SUBCAPÍTULO 01.05.01.02          1800,00
TOTAL CAPÍTULO 01                     15001,50
```

### Salida (estructura detectada):
```
01 - FASE 2 [Total: 15001.50 €]
├─ 01.03 - MOVIMIENTO DE TIERRAS [Total: 5000.00 €]
├─ 01.04 - PAVIMENTACIÓN [Total: 7001.50 € - CALCULADO]
│  ├─ 01.04.01 - PAVIMENTO PERMEABLE [Total: 2500.50 €]
│  ├─ 01.04.02 - PAVIMENTO IMPERMEABLE [Total: 3000.75 €]
│  └─ 01.04.03 - JUNTAS [Total: 1500.25 €]
└─ 01.05 - MUROS [Total: 3000.00 € - CALCULADO]
   └─ 01.05.01 - MUROS DE SUELO [Total: 3000.00 € - CALCULADO]
      ├─ 01.05.01.01 - MURO TIPO 1 [Total: 1200.00 €]
      └─ 01.05.01.02 - MURO TIPO 2 [Total: 1800.00 €]
```

### Observaciones:

- ✅ **01.04** fue creado automáticamente (no tenía TOTAL explícito)
- ✅ **01.04.02** y **01.04.03** fueron detectados correctamente
- ✅ **01.05** y **01.05.01** fueron creados como niveles intermedios
- ✅ Los totales sin línea TOTAL explícita se calcularon sumando hijos

## Ventajas del Nuevo Sistema

1. **Simplicidad**: Parser especializado mucho más simple y directo
2. **Corrección**: Crea todos los niveles intermedios automáticamente
3. **Robustez**: Calcula totales faltantes de forma inteligente
4. **Separación**: Fase 1 y Fase 2 completamente independientes
5. **Mantenibilidad**: Código más fácil de entender y mantener
6. **Performance**: Más rápido al no procesar partidas innecesariamente

## Archivos Modificados

1. ✅ **NUEVO:** `src/parser/structure_parser.py` - Parser especializado para Fase 1
2. ✅ **MODIFICADO:** `src/parser/local_structure_extractor.py` - Usa el nuevo parser
3. ✅ **SIN CAMBIOS:** `src/parser/line_classifier.py` - Se mantiene para Fase 2
4. ✅ **SIN CAMBIOS:** `src/parser/partida_parser.py` - Se mantiene para Fase 2

## Testing

### Pruebas con datos sintéticos:
El parser ha sido probado inicialmente con casos que incluyen:
- ✅ Múltiples niveles de anidación (hasta 5 niveles)
- ✅ Niveles intermedios sin TOTAL explícito
- ✅ Creación automática de niveles faltantes
- ✅ Cálculo de totales recursivos
- ✅ Asignación correcta de TOTALes con código explícito

### Pruebas con PDF real (PRESUPUESTOS PARCIALES NAVAS DE TOLOSA):

**Estadísticas extraídas:**
- ✅ 4 capítulos principales (nivel 0)
- ✅ 46 subcapítulos nivel 1
- ✅ 94 subcapítulos nivel 2
- ✅ 29 subcapítulos nivel 3
- ✅ 2 subcapítulos nivel 4
- ✅ **Total: 175 nodos** en la jerarquía

**Casos especiales detectados:**
- ✅ Códigos sin espacio: `03.06.02.02.01CIMENTACIONES` → Detectado correctamente
- ✅ Niveles profundos: `03.06.02.02.01` y `03.06.02.02.02` (5 niveles)
- ✅ Subcapítulos con nombres largos y caracteres especiales

**Corrección aplicada:**
El regex fue modificado de `\s+` (espacio obligatorio) a `\s*` (espacio opcional) para capturar códigos pegados al nombre.

## Issues Encontrados y Resueltos

### Issue #1: Códigos sin espacio
**Problema:** Algunos PDFs tienen códigos pegados al nombre sin espacio:
```
03.06.02.02.01CIMENTACIONES
03.06.02.02.02CERRAJERÍA
```

**Solución:** Modificar regex de `\s+` a `\s*` para aceptar cero o más espacios.

**Estado:** ✅ Resuelto

### Issue #2: Caché de estructura obsoleto
**Problema:** El sistema cacheaba la estructura procesada, por lo que las mejoras del parser no se aplicaban.

**Solución:** Eliminar completamente el caché de estructura. Solo cachear el texto extraído del PDF.

**Estado:** ✅ Resuelto

### Issue #3: Totales no detectados
**Problema:** El parser no detectaba los totales del PDF. Todos los importes aparecían en 0.00 €.

**Causa raíz:** El formato de líneas TOTAL en el PDF es diferente al esperado:
```
Formato en PDF:    TOTAL 01.04.01....... 49.578,18
Formato esperado:  TOTAL SUBCAPÍTULO 01.04.01  49.578,18
```

**Solución:** Agregar nuevo patrón regex `PATRON_TOTAL_CON_PUNTOS` que detecta:
- Totales con puntos suspensivos como relleno
- Códigos sin la palabra "SUBCAPÍTULO" o "CAPÍTULO"
- Formato: `TOTAL [código]....[importe]`

**Regex implementado:**
```python
PATRON_TOTAL_CON_PUNTOS = re.compile(
    r'^TOTAL\s+(\d{1,2}(?:\.\d{1,2})*)[\s\.]+(\d{1,3}(?:\.\d{3})*,\d{2})\s*$',
    re.IGNORECASE
)
```

**Estado:** ✅ Resuelto

**Resultados verificados:**
- ✅ Capítulo 01: 1,174,151.99 €
- ✅ Capítulo 02: 644,844.20 €
- ✅ Capítulo 03: 991,125.90 €
- ✅ Capítulo 04: 70,890.19 €
- ✅ **Total general: 2,881,012.28 €**

## Próximos Pasos

1. ✅ ~~Probar con PDFs reales~~ - Completado
2. Validar que no hay regresiones en la Fase 2
3. Monitorear casos edge adicionales

## Conclusión

La Fase 1 ahora tiene su propio parser especializado que solo se preocupa de extraer la estructura jerárquica, dejando la extracción de partidas para la Fase 2. Esto hace el código más simple, correcto y mantenible.
