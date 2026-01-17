# Solución: Visualización Completa de Jerarquía de Subcapítulos

## Problema Identificado

El sistema solo mostraba el primer nivel de subcapítulos en el árbol de estructura, cuando en muchos casos existen múltiples niveles anidados (nivel 2, 3, 4, etc.).

### Análisis del Problema

1. **Extracción (structure_extraction_agent.py)**: ✅ **Funcionaba correctamente**
   - El LLM extraía correctamente toda la jerarquía multinivel
   - El formato JSON incluía `subcapitulos` anidados recursivamente

2. **Modelo de Base de Datos (ai_models.py)**: ❌ **NO soportaba jerarquía**
   - La clase `AISubcapitulo` NO tenía campo `parent_id`
   - NO tenía relación recursiva consigo misma
   - Era una estructura plana

3. **Guardado (ai_db_manager.py)**: ❌ **No usaba parent_id**
   - La función `guardar_subcapitulos_recursivo` recibía `parent_id` pero nunca lo usaba
   - Todos los subcapítulos se guardaban al mismo nivel (solo relacionados con `capitulo_id`)

4. **API (main.py)**: ❌ **No reconstruía jerarquía**
   - Las funciones que devolvían la estructura no procesaban subcapítulos anidados
   - Solo devolvía subcapítulos de primer nivel

5. **Frontend (ai_proyecto_detalle.html)**: ❌ **No renderizaba recursivamente**
   - Solo mostraba los primeros 3 subcapítulos de nivel 1
   - No había código para mostrar niveles inferiores

## Solución Implementada

### 1. Modelo de Base de Datos (`src/models/ai_models.py`)

**Cambios:**
- ✅ Agregado campo `parent_id` a `AISubcapitulo` (ForeignKey auto-referencial)
- ✅ Agregada relación `parent` (subcapítulo padre)
- ✅ Agregada relación `subcapitulos` (hijos)

```python
class AISubcapitulo(Base):
    # ...
    parent_id = Column(Integer, ForeignKey('ai_subcapitulos.id'), nullable=True)

    # Relación recursiva
    parent = relationship("AISubcapitulo", remote_side=[id], back_populates="subcapitulos")
    subcapitulos = relationship("AISubcapitulo", back_populates="parent", cascade="all, delete-orphan")
```

### 2. Guardado en Base de Datos (`src/models/ai_db_manager.py`)

**Cambios:**
- ✅ Actualizada función `guardar_subcapitulos_recursivo` para usar correctamente `parent_id`
- ✅ Los subcapítulos ahora se guardan con su jerarquía real

```python
def guardar_subcapitulos_recursivo(subcapitulos_data, capitulo_id, parent_id=None):
    # ...
    subcapitulo = AISubcapitulo(
        capitulo_id=capitulo_id,
        parent_id=parent_id,  # ✓ Ahora se usa correctamente
        # ...
    )
    # ...
    if sub_data.get('subcapitulos'):
        guardar_subcapitulos_recursivo(
            sub_data['subcapitulos'],
            capitulo_id,
            subcapitulo.id  # ✓ El ID actual se convierte en parent_id de sus hijos
        )
```

### 3. API (`src/api/main.py`)

**Cambios:**
- ✅ Actualizada función `construir_subcapitulos_recursivo` en endpoint `/api/structure/{proyecto_id}`
- ✅ Agregada función `construir_subcapitulos_con_datos` en endpoint `/ai-proyectos/{proyecto_id}`
- ✅ Ambas funciones ahora filtran subcapítulos de nivel 1 (`parent_id is None`) y construyen el árbol recursivamente

```python
def construir_subcapitulos_recursivo(subcapitulos):
    resultado = []
    for sub in subcapitulos:
        sub_dict = {
            # ...
            # ✓ Recursión: procesar subcapítulos hijos
            "subcapitulos": construir_subcapitulos_recursivo(sub.subcapitulos) if sub.subcapitulos else []
        }
        resultado.append(sub_dict)
    return resultado

# Al llamar, filtrar solo nivel 1:
subcapitulos_nivel1 = [s for s in capitulo.subcapitulos if s.parent_id is None]
construir_subcapitulos_recursivo(subcapitulos_nivel1)
```

### 4. Frontend (`src/app/templates/ai_proyecto_detalle.html`)

**Cambios:**

#### Vista de Resumen (Fase 1):
- ✅ Agregado macro recursivo `mostrar_subcapitulos` para mostrar el árbol con indentación
- ✅ Muestra hasta 3 subcapítulos de nivel 1, luego 2 por nivel inferior
- ✅ Usa margen izquierdo progresivo para indicar profundidad

```jinja2
{% macro mostrar_subcapitulos(subcaps, nivel=1, limite=3) %}
    {% for subcapitulo in subcaps[:limite] %}
    <div style="margin-left: {{ (nivel - 1) * 15 }}px;">
        └─ {{ subcapitulo.codigo }} - {{ subcapitulo.nombre }}
    </div>
    {# Recursión: mostrar subcapítulos hijos #}
    {% if subcapitulo.subcapitulos %}
        {{ mostrar_subcapitulos(subcapitulo.subcapitulos, nivel + 1, 2) }}
    {% endif %}
    {% endfor %}
{% endmacro %}
```

#### Vista de Estructura Completa:
- ✅ Agregado macro recursivo `renderizar_subcapitulos` para renderizar toda la jerarquía
- ✅ Cada subcapítulo muestra sus partidas, apartados, y subcapítulos hijos
- ✅ Los subcapítulos hijos aparecen en una sección separada con título "📂 Subcapítulos de nivel inferior"

```jinja2
{% macro renderizar_subcapitulos(subcapitulos, prefijo_id, margen_izq=0) %}
    {% for subcapitulo in subcapitulos %}
        {# Renderizar partidas y apartados #}

        {# RECURSIÓN: Renderizar subcapítulos hijos #}
        {% if subcapitulo.subcapitulos %}
        <div style="border-top: 2px dashed #dee2e6;">
            <h6>📂 Subcapítulos de nivel inferior:</h6>
            {{ renderizar_subcapitulos(subcapitulo.subcapitulos, prefijo_id ~ '_' ~ loop.index, 0) }}
        </div>
        {% endif %}
    {% endfor %}
{% endmacro %}
```

### 5. Migración de Base de Datos

**Script:** `migrate_add_parent_id.py`

- ✅ Agrega columna `parent_id` a tabla `ai_subcapitulos`
- ✅ Los subcapítulos existentes quedan con `parent_id = NULL` (nivel 1, correcto)
- ✅ Los nuevos proyectos procesados usarán la jerarquía completa

**Ejecución:**
```bash
python migrate_add_parent_id.py
```

**Resultado:**
```
✓ Migración completada exitosamente
  Columna parent_id agregada a ai_subcapitulos
  Total de subcapítulos en la BD: 199
```

## Resultados

### Antes (❌):
- Solo se mostraban subcapítulos de nivel 1
- Ejemplo: Solo mostraba `01.01`, `01.02`, etc.
- Los subcapítulos `01.01.01`, `01.01.02` NO aparecían

### Después (✅):
- Se muestra toda la jerarquía multinivel
- Ejemplo árbol:
  ```
  01 - CAPÍTULO PRINCIPAL
    └─ 01.01 - Subcapítulo Nivel 1
        └─ 01.01.01 - Subcapítulo Nivel 2
            └─ 01.01.01.01 - Subcapítulo Nivel 3
    └─ 01.02 - Otro Subcapítulo Nivel 1
        └─ 01.02.01 - Subcapítulo Nivel 2
  ```

### Vista de Detalle:
- Cada subcapítulo es colapsable/expandible
- Muestra partidas directas
- Muestra apartados
- Muestra subcapítulos hijos en sección separada
- Indicador de cantidad: "(X partidas, Y subcapítulos)"

## Archivos Modificados

1. ✅ `src/models/ai_models.py` - Modelo con relación recursiva
2. ✅ `src/models/ai_db_manager.py` - Guardado jerárquico correcto
3. ✅ `src/api/main.py` - Reconstrucción recursiva en API
4. ✅ `src/app/templates/ai_proyecto_detalle.html` - Renderizado recursivo completo
5. ✅ `migrate_add_parent_id.py` - Script de migración (nuevo)

## Próximos Pasos

Para probar la solución:

1. **Si tienes proyectos existentes:** Ya están migrados, pero solo tienen nivel 1. Para ver la jerarquía completa:
   - Procesa un nuevo PDF usando "Extraer Estructura" (Fase 1)

2. **Procesar un nuevo PDF:**
   ```bash
   # Iniciar el servidor
   ./start.sh

   # Ir a http://localhost:3014/ai-upload
   # Subir un PDF con subcapítulos multinivel
   # Hacer clic en "Extraer Estructura"
   ```

3. **Verificar el resultado:**
   - En la vista de proyecto, ver el árbol en "FASE 1: Estructura del Presupuesto"
   - Hacer clic en "Ver estructura completa" para ver todos los niveles
   - Expandir subcapítulos para ver sus hijos anidados

## Notas Técnicas

### Jerarquía en Base de Datos:
- **Nivel 1:** `parent_id = NULL`, asociado a `capitulo_id`
- **Nivel 2+:** `parent_id = ID_del_padre`, también asociado a `capitulo_id`

### Recursión:
- SQLAlchemy soporta relaciones auto-referenciales con `remote_side=[id]`
- Jinja2 soporta macros recursivos (se llaman a sí mismos)
- La API reconstruye el árbol navegando por `subcapitulo.subcapitulos`

### Performance:
- La relación recursiva usa `lazy='select'` por defecto
- Para proyectos grandes, considerar eager loading: `.options(selectinload(AISubcapitulo.subcapitulos))`
