# 🔄 CAMBIOS EN EL FLUJO DE UPLOAD HÍBRIDO

**Fecha**: 2026-01-13
**Objetivo**: Permitir elegir qué fases procesar desde la página del proyecto

---

## 📋 CAMBIOS REALIZADOS

### ✅ **1. API: Endpoint `/hybrid-upload` Modificado**

**Archivo**: `src/api/main.py` (línea 1364)

**ANTES**:
```python
# Procesaba las 3 fases automáticamente
resultado = await hybrid_orchestrator.procesar_proyecto_completo(...)
```

**AHORA**:
```python
# Solo crea el proyecto vacío
proyecto = hybrid_db.crear_proyecto(
    nombre=nombre_proyecto,
    descripcion=f"Proyecto híbrido - {filename}",
    archivo_origen=str(file_path)
)
```

**Resultado**:
- El upload es **instantáneo** (solo guarda el archivo)
- El proyecto queda en estado `CREADO`
- El usuario puede elegir qué fases ejecutar

---

### ✅ **2. APP: Endpoint `/hybrid-upload` Actualizado**

**Archivo**: `src/app/main.py` (línea 268)

**Cambios**:
- **Timeout reducido**: `660s → 60s` (ya no procesa, solo sube)
- **Mensaje actualizado**: "Subir PDF (solo guarda el archivo, no procesa)"
- **Redirección**: Igual, va a `/hybrid-proyecto/{id}`

---

### ✅ **3. Template: Upload Actualizado**

**Archivo**: `src/app/templates/hybrid_upload.html`

**Cambios**:

#### **Alerta informativa**:
```html
<div class="alert alert-info">
    <strong>📤 Paso 1: Subir Archivo</strong>
    <p>Sube tu PDF. El archivo se guardará y podrás elegir qué fases procesar.</p>
</div>
```

#### **Botón actualizado**:
```html
<!-- ANTES -->
<button>⚡ Procesar con Sistema Híbrido</button>

<!-- AHORA -->
<button>📤 Subir PDF (Elegir Fases Después)</button>
```

#### **Loading message**:
```html
<!-- ANTES -->
<p>Procesando con Sistema Híbrido (3 Fases)...</p>
<p>Fase 1: Extracción de estructura con IA...</p>
...

<!-- AHORA -->
<p>Subiendo archivo PDF...</p>
<p>Guardando el archivo en el servidor...</p>
<p>✨ Una vez subido, podrás elegir qué fases procesar</p>
```

---

### ✅ **4. Template: Detalle de Proyecto (Ya Existía)**

**Archivo**: `src/app/templates/hybrid_proyecto_detalle.html`

**Ya tenía** los botones para ejecutar cada fase:
- 📊 **FASE 1**: Botón para extraer estructura con IA
- ⚙️ **FASE 2**: Botón para extraer partidas con parser local
- ✓ **FASE 3**: Botón para validar coincidencias

**No se modificó** porque ya estaba perfecto.

---

## 🎯 FLUJO NUEVO

### **ANTES** (Automático):
```
1. Usuario sube PDF
2. ⏳ Espera 1-3 minutos
3. Sistema procesa automáticamente las 3 fases
4. Muestra resultados
```

### **AHORA** (Manual):
```
1. Usuario sube PDF
   ↓ (instantáneo)
2. Proyecto creado en estado "CREADO"
   ↓
3. Usuario ve página del proyecto con 3 botones
   ↓
4. Usuario elige:
   - 📊 Ejecutar Fase 1 (IA estructura)
   - ⚙️ Ejecutar Fase 2 (Parser local)
   - ✓ Ejecutar Fase 3 (Validación)

5. Puede ejecutar las fases:
   - Una por una
   - En cualquier orden (respetando dependencias)
   - Re-ejecutar si es necesario
```

---

## 💡 VENTAJAS DEL NUEVO FLUJO

### 1️⃣ **Control Granular**
- Ejecuta solo la fase que necesitas
- Re-procesa fases sin perder las demás
- Prueba diferentes configuraciones

### 2️⃣ **Feedback Inmediato**
- El upload es instantáneo
- No hay que esperar 3 minutos para ver algo
- Mejor experiencia de usuario

### 3️⃣ **Depuración Más Fácil**
- Si falla la Fase 1, no pierdes tiempo en Fase 2
- Puedes re-ejecutar solo la fase problemática
- Logs más claros por fase

### 4️⃣ **Flexibilidad**
- Procesa solo Fase 1 para ver estructura rápido
- Compara diferentes enfoques de Fase 2
- Ajusta tolerancia de Fase 3 sin re-procesar todo

---

## 📊 ENDPOINTS API DISPONIBLES

Ya existían los endpoints para procesar cada fase:

### **POST `/hybrid-upload`** - Subir archivo (MODIFICADO)
```json
{
  "success": true,
  "mensaje": "PDF subido correctamente. Ahora puedes elegir qué fases procesar.",
  "proyecto_id": 3,
  "fase_actual": "creado"
}
```

### **POST `/hybrid-fase1/{proyecto_id}`** - Ejecutar Fase 1
```json
{
  "success": true,
  "mensaje": "Fase 1 completada: Estructura extraída con IA",
  "capitulos_extraidos": 4,
  "tiempo": 35.2
}
```

### **POST `/hybrid-fase2/{proyecto_id}`** - Ejecutar Fase 2
```json
{
  "success": true,
  "mensaje": "Fase 2 completada: Partidas extraídas con parser local",
  "partidas_extraidas": 245,
  "tiempo": 8.5
}
```

### **POST `/hybrid-fase3/{proyecto_id}?tolerancia=5.0`** - Ejecutar Fase 3
```json
{
  "success": true,
  "mensaje": "Fase 3 completada: Validación cruzada",
  "validados": 18,
  "discrepancias": 2,
  "porcentaje_coincidencia": 95.5
}
```

---

## ✅ ARCHIVOS MODIFICADOS

1. ✅ `src/api/main.py` - Endpoint upload solo guarda archivo
2. ✅ `src/app/main.py` - Timeout reducido y mensaje actualizado
3. ✅ `src/app/templates/hybrid_upload.html` - Textos y botón actualizados

**Archivos NO modificados** (ya estaban bien):
- `src/app/templates/hybrid_proyecto_detalle.html` - Ya tenía los botones
- `src/api/main.py` - Endpoints de fases individuales ya existían

---

## 🎉 RESULTADO

El sistema híbrido ahora permite:

✅ **Upload instantáneo** del PDF
✅ **Elegir qué fases ejecutar** desde la página del proyecto
✅ **Re-ejecutar fases** individualmente si es necesario
✅ **Mejor depuración** con logs por fase
✅ **Control total** sobre el procesamiento

**Todo listo para usar!** 🚀
