# Sistema de Guardado Progresivo por Fases

## 🎯 Objetivo

Cada fase del procesamiento guarda sus datos en la base de datos **inmediatamente**, permitiendo ver el progreso en tiempo real.

## 📊 Flujo de Datos

### **FASE 1: Estructura Jerárquica**
- **Entrada**: PDF extraído (texto + layout)
- **Procesamiento**:
  - Detecta capítulos y subcapítulos
  - Extrae totales de cada nivel
  - Detecta número de columnas (layout)
- **Salida BD**:
  ```sql
  INSERT INTO v2.capitulos (codigo, nombre, total, ...)
  INSERT INTO v2.subcapitulos (codigo, nombre, total, nivel, ...)
  UPDATE v2.proyectos SET layout_detectado = 'X Columnas', presupuesto_total = ...
  ```
- **Resultado visible**:
  - Árbol jerárquico con totales
  - Layout detectado
  - Presupuesto total del proyecto

---

### **FASE 2: Extracción de Partidas**
- **Entrada**: Estructura de Fase 1 (desde BD)
- **Procesamiento**:
  - Clasifica cada línea (TipoLinea)
  - Extrae partidas individuales (código, unidad, descripción, cantidad, precio, importe)
  - Asocia partidas a subcapítulos correspondientes
- **Salida BD**:
  ```sql
  INSERT INTO v2.partidas (subcapitulo_id, codigo, unidad, descripcion, cantidad_total, precio, importe, orden, ...)
  ```
- **Resultado visible**:
  - Árbol con conteo de partidas por subcapítulo
  - Todas las partidas guardadas y consultables

---

### **FASE 3: Validación y Recálculo**
- **Entrada**: Estructura con partidas (desde BD)
- **Procesamiento**:
  - Merge de totales (Fase 1 vs suma de partidas)
  - Detecta discrepancias
  - Recalcula totales desde partidas
- **Salida BD**:
  ```sql
  UPDATE v2.subcapitulos SET total = (SUM partidas.importe)
  UPDATE v2.capitulos SET total = (SUM subcapitulos.total)
  UPDATE v2.proyectos SET presupuesto_total = (SUM capitulos.total)
  ```
- **Resultado visible**:
  - Totales recalculados
  - Informe de validación (discrepancias)
  - Presupuesto total actualizado

---

### **FASE 4: Finalización** (Opcional)
- **Entrada**: Todo desde BD
- **Procesamiento**:
  - Completa descripciones si es necesario
  - Verificación final
- **Salida BD**:
  - Ninguna modificación adicional (ya está todo guardado)
- **Resultado visible**:
  - Confirmación de procesamiento completo
  - Estadísticas finales

---

## 🔄 Ventajas del Guardado Progresivo

### 1. **Visibilidad en Tiempo Real**
- El frontend puede consultar la BD después de cada fase
- El usuario ve el progreso inmediato
- No hay que esperar a que termine todo el procesamiento

### 2. **Debugging Más Fácil**
- Si Fase 2 falla, los datos de Fase 1 ya están guardados
- Se pueden reintentar fases individuales
- Archivos JSON intermedios + BD para comparar

### 3. **Re-ejecución Selectiva**
- Si cambias el parser de Fase 2, puedes reejecutar solo esa fase
- Los datos de Fase 1 se mantienen

### 4. **Interrupción y Continuación**
- Si el proceso se interrumpe en Fase 3, Fases 1 y 2 ya están guardadas
- Se puede continuar desde donde se quedó

---

## 🛠️ Implementación Técnica

### Nuevos Métodos en `DatabaseManagerV2`

```python
# FASE 1: Guardar estructura jerárquica
db.actualizar_fase1(proyecto_id, estructura, metadata)
  → Crea/actualiza capítulos y subcapítulos con totales
  → Actualiza layout_detectado y presupuesto_total

# FASE 2: Guardar partidas
db.actualizar_fase2(proyecto_id, estructura_completa)
  → Agrega partidas a los subcapítulos existentes
  → Mapea por código de subcapítulo

# FASE 3: Recalcular totales
db.actualizar_fase3(proyecto_id, validacion)
  → Recalcula todos los totales desde partidas
  → Actualiza presupuesto_total del proyecto
```

### Endpoints API Actualizados

```python
POST /api/proyectos/{id}/fase1
  → Ejecuta parser.ejecutar_fase1()
  → db.actualizar_fase1(...)
  → Retorna estructura con totales

POST /api/proyectos/{id}/fase2
  → Ejecuta parser.ejecutar_fase1() + ejecutar_fase2()
  → db.actualizar_fase2(...)
  → Retorna estructura con partidas

POST /api/proyectos/{id}/fase3
  → Ejecuta todas las fases
  → db.actualizar_fase3(...)
  → Retorna validación

POST /api/proyectos/{id}/fase4
  → Verificación final
  → Retorna estadísticas finales
```

---

## 📝 Archivos Modificados

### Backend
- ✅ `src/models_v2/db_manager_v2.py` - Nuevos métodos `actualizar_fase1/2/3()`
- ✅ `src/models_v2/db_models_v2.py` - Agregado campo `orden` a `Partida`
- ✅ `src/api_v2/main.py` - Endpoints actualizados para guardar en BD
- ✅ `migrations/add_orden_to_partidas.sql` - Migración SQL

### Testing
- ✅ `test_fases_progresivas.py` - Script para verificar guardado progresivo

---

## 🚀 Flujo de Usuario

1. **Upload PDF** → Proyecto vacío creado en BD
2. **Ir a página de edición** → `/proyectos/{id}/editar`
3. **Ejecutar Fase 1** → Estructura guardada, visible en BD
4. **Ejecutar Fase 2** → Partidas guardadas, consultables
5. **Ejecutar Fase 3** → Totales recalculados
6. **Ejecutar Fase 4** → Confirmación final
7. **Ver proyecto** → `/proyectos/{id}` muestra todos los datos

---

## ✅ Testing

```bash
# 1. Subir PDF
# 2. Ejecutar solo Fase 1 desde el frontend
# 3. Verificar datos en BD:
python test_fases_progresivas.py

# 4. Ejecutar Fase 2
# 5. Verificar datos en BD nuevamente
python test_fases_progresivas.py

# 6. Continuar con Fases 3 y 4
```

---

## 🎉 Resultado Final

Después de cada fase, el proyecto en `/proyectos/{id}` muestra:

- **Después de Fase 1**: Total general, capítulos, layout detectado
- **Después de Fase 2**: + Partidas, descripciones, precios
- **Después de Fase 3**: Totales validados y recalculados
- **Después de Fase 4**: Procesamiento completo confirmado

**¡Ya no es necesario esperar a Fase 4 para ver datos!**
