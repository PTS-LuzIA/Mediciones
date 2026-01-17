# 🚀 MEJORAS AL SISTEMA HÍBRIDO - CONTADOR DE PARTIDAS

**Fecha**: 2026-01-13
**Autor**: Claude Code
**Propuesta original**: Usuario

---

## 📋 RESUMEN DE CAMBIOS

Se ha implementado un **sistema de conteo de partidas** que mejora significativamente la validación del sistema híbrido. Ahora la IA cuenta cuántas partidas tiene cada subcapítulo en Fase 1, y el sistema valida que el parser local extraiga el número correcto de partidas en Fase 2.

---

## ✅ CAMBIOS IMPLEMENTADOS

### 1️⃣ **Modificación del Prompt de Fase 1**
**Archivo**: `src/llm/structure_extraction_agent.py`

**Cambio**: Se agregó el campo `num_partidas` al JSON que devuelve la IA.

**Ejemplo**:
```json
{
  "codigo": "01.02",
  "nombre": "RELLENOS",
  "total": 10000.25,
  "num_partidas": 8,  // 👈 NUEVO CAMPO
  "confianza": 0.99,
  "orden": 2,
  "subcapitulos": []
}
```

**Instrucciones a la IA**:
- Para subcapítulos HOJA (sin hijos): contar las partidas individuales
- Para subcapítulos intermedios (con hijos): poner `num_partidas: 0`
- Las partidas son las líneas con códigos alfanuméricos (ej: "m23U01C190", "U01AB100")

---

### 2️⃣ **Actualización de Modelos de BD**
**Archivo**: `src/models/hybrid_models.py`

**Cambios**:
- Agregado campo `num_partidas_ia` (Integer) en `HybridCapitulo`
- Agregado campo `num_partidas_local` (Integer) en `HybridCapitulo`
- Agregado campo `num_partidas_ia` (Integer) en `HybridSubcapitulo`
- Agregado campo `num_partidas_local` (Integer) en `HybridSubcapitulo`

**Propósito**:
- `num_partidas_ia`: Cuántas partidas dijo la IA que hay (Fase 1)
- `num_partidas_local`: Cuántas partidas extrajo el parser local (Fase 2)

---

### 3️⃣ **Actualización del Gestor de BD**
**Archivo**: `src/models/hybrid_db_manager.py`

#### **Fase 1 - Guardado de estructura**:
```python
# Ahora se guarda num_partidas desde la IA
capitulo = HybridCapitulo(
    ...
    num_partidas_ia=cap_data.get('num_partidas', 0),  # 👈 NUEVO
    ...
)

subcapitulo = HybridSubcapitulo(
    ...
    num_partidas_ia=sub_data.get('num_partidas', 0),  # 👈 NUEVO
    ...
)
```

#### **Fase 2 - Cálculo de totales locales**:
La función `_calcular_totales_locales()` ahora también cuenta partidas:
```python
def _calcular_total_subcapitulo_recursivo(self, subcapitulo) -> tuple:
    """
    Returns:
        tuple: (total_euros, num_partidas)  # 👈 Ahora devuelve ambos
    """
    total = 0.0
    num_partidas = 0  # 👈 Contador de partidas

    # Contar partidas directas
    for partida in subcapitulo.partidas:
        total += partida.importe
        num_partidas += 1  # 👈 Incrementar contador

    subcapitulo.num_partidas_local = num_partidas  # 👈 Guardar conteo
    return total, num_partidas
```

---

### 4️⃣ **Mejora de la Validación en Fase 3**
**Archivo**: `src/models/hybrid_db_manager.py`

La función `_validar_elemento()` ahora valida **DOS criterios**:

#### **Validación 1: Total en euros** (como antes)
```python
diferencia_euros = abs(total_ia - total_local)
diferencia_porcentaje = (diferencia_euros / total_ia) * 100
```

#### **Validación 2: Conteo de partidas** (NUEVO)
```python
diferencia_conteo = abs(num_partidas_ia - num_partidas_local)

# Tolerancia: 2 partidas o 10% del total (lo que sea mayor)
tolerancia_conteo = max(2, int(num_partidas_ia * 0.1))
conteo_valido = diferencia_conteo <= tolerancia_conteo
```

#### **Resultado**:
- ✅ **VALIDADO**: Si ambos criterios pasan (total Y conteo)
- ❌ **DISCREPANCIA**: Si alguno de los dos falla

#### **Logs mejorados**:
```python
logger.warning(f"[VALIDACIÓN] 01.05.02 - Discrepancia en CONTEO: IA=25, Local=18")
logger.warning(f"[VALIDACIÓN] 01.05.02 - Discrepancia en TOTAL: 8.5% (€1250.50)")
```

---

### 5️⃣ **Reporte de Elementos a Revisar**
Los elementos con discrepancias ahora incluyen información del conteo:

```python
{
    "tipo": "subcapitulo",
    "codigo": "01.05.02",
    "nombre": "MURO TIPO 2",
    "total_ia": 15000.50,
    "total_local": 13750.25,
    "num_partidas_ia": 25,      # 👈 NUEVO
    "num_partidas_local": 18,   # 👈 NUEVO
    "diferencia_euros": 1250.25,
    "diferencia_porcentaje": 8.33,
    "subcapitulo_id": 142
}
```

---

## 🎯 VENTAJAS DEL SISTEMA DE CONTEO

### ✅ **1. Validación Robusta**
- Antes: Solo validábamos el total en €
- Ahora: Validamos total € + número de partidas
- **Resultado**: Detectamos si faltan partidas aunque el total cuadre

### ✅ **2. Detección de Problemas del Parser Local**
Si la IA dice "25 partidas" pero el parser local solo extrae 18:
- Sabemos que el parser local tiene un problema
- Podemos identificar QUÉ subcapítulos tienen problemas
- Podemos priorizar cuáles revisar con IA

### ✅ **3. Preparación para Re-extracción con IA**
Cuando implementemos la re-extracción, podemos decirle a la IA:
```
"Extrae las 25 partidas del subcapítulo 01.05.02"
```
Y validar que devuelve exactamente 25 partidas.

### ✅ **4. Mejor Depuración**
Los logs ahora muestran:
```
[VALIDACIÓN] 01.05.02 - Discrepancia en CONTEO: IA=25, Local=18
```
Esto nos permite identificar rápidamente qué subcapítulos tienen problemas.

---

## 📊 EJEMPLO DE FLUJO COMPLETO

### **Fase 1 - IA Extrae Estructura**:
```json
{
  "codigo": "01.05.02",
  "nombre": "MURO TIPO 2",
  "total": 15000.50,
  "num_partidas": 25,  // 👈 IA cuenta 25 partidas
  "subcapitulos": []
}
```

### **Fase 2 - Parser Local Extrae Partidas**:
```
Partidas extraídas: 18
Total calculado: 13750.25 €
```

### **Fase 3 - Validación**:
```
❌ DISCREPANCIA DETECTADA:
  - Total: IA=15000.50€ vs Local=13750.25€ (diff=8.33%)
  - Conteo: IA=25 partidas vs Local=18 partidas (faltan 7)

→ Subcapítulo marcado para revisión con IA
```

---

## 🔧 PRÓXIMOS PASOS SUGERIDOS

### **1. Mejorar Parser Local (Prioridad Alta)**
- Procesar subcapítulos de forma más granular
- Mejorar detección de partidas en formatos complejos
- Agregar logs detallados por subcapítulo

### **2. Implementar Re-extracción con IA (Prioridad Media)**
En `hybrid_orchestrator.py`, completar:
```python
async def revisar_discrepancias_con_ia(self, proyecto_id, subcapitulos):
    """
    Re-extrae con IA solo los subcapítulos con discrepancias
    """
    for subcap in subcapitulos:
        # Usar PartidaExtractionAgent para re-extraer
        partidas_ia = await self.partida_agent.extraer_partidas_capitulo(
            pdf_path,
            capitulo_data,
            subcapitulos_filtrados=[subcap.codigo]
        )

        # Validar que el número de partidas coincide con lo esperado
        if len(partidas_ia) == subcap.num_partidas_ia:
            # ✓ Correcto, actualizar BD
        else:
            # ⚠️ Discrepancia también con IA
```

### **3. Dashboard de Validación (Prioridad Baja)**
Crear una vista que muestre:
- Subcapítulos validados (verde)
- Subcapítulos con discrepancia en total (amarillo)
- Subcapítulos con discrepancia en conteo (rojo)
- Subcapítulos con ambas discrepancias (rojo oscuro)

---

## ⚠️ NOTAS IMPORTANTES

### **Migración de BD**
Los cambios en los modelos requieren que se recree la base de datos o se ejecute una migración.

**Opción 1 - Recrear BD** (desarrollo):
```bash
rm data/mediciones.db
# La BD se recreará automáticamente en la próxima ejecución
```

**Opción 2 - Migración con Alembic** (producción):
```bash
alembic revision --autogenerate -m "Agregar campos num_partidas_ia y num_partidas_local"
alembic upgrade head
```

### **Compatibilidad**
- Los proyectos existentes tendrán `num_partidas_ia = 0` por defecto
- El sistema seguirá funcionando sin el conteo (validación solo por total €)
- Solo los nuevos proyectos aprovecharán la validación de conteo

### **Límites de la IA**
La IA puede equivocarse al contar partidas, especialmente si:
- El PDF tiene formato complejo o mal escaneado
- Hay partidas con códigos no estándar
- Las partidas están en tablas multi-columna

**Solución**: La confianza de la IA nos indica qué tan segura está del conteo.

---

## 📝 ARCHIVOS MODIFICADOS

1. ✅ `src/llm/structure_extraction_agent.py` - Prompt con `num_partidas`
2. ✅ `src/models/hybrid_models.py` - Campos BD nuevos
3. ✅ `src/models/hybrid_db_manager.py` - Guardado y validación
4. ✅ `CAMBIOS_FASE_HIBRIDA.md` - Este documento

---

## 🎉 CONCLUSIÓN

El sistema híbrido ahora tiene una **validación mucho más robusta** que detecta no solo discrepancias en los totales, sino también en el número de partidas extraídas. Esto nos permite:

1. ✅ Identificar subcapítulos problemáticos con precisión
2. ✅ Priorizar qué extraer con IA (costoso) vs local (rápido)
3. ✅ Tener métricas claras de calidad de extracción
4. ✅ Preparar el terreno para re-extracción inteligente con IA

**Estado**: ✅ Implementado y listo para probar

**Próximo paso**: Probar con un PDF real y verificar que la IA cuenta correctamente las partidas.
