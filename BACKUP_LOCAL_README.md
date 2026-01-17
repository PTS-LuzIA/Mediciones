# BACKUP DEL SISTEMA LOCAL - MVP Mediciones

**Fecha de creación**: 2026-01-12
**Propósito**: Preservar la funcionalidad completa del sistema LOCAL antes de implementar proyectos híbridos

## Archivos de respaldo creados

### 1. Modelos de Base de Datos
- **`src/models/local_db_models.py`**
  - Copia completa de `db_models.py`
  - Modelos SQLAlchemy para proyectos locales
  - DatabaseManager original

### 2. Parser de PDFs
- **`src/parser/local_partida_parser.py`**
  - Copia completa de `partida_parser.py`
  - PartidaParser con toda la lógica de extracción local

### 3. Templates HTML
- **`src/app/templates/local_proyectos.html`**
  - Copia de `proyectos.html`
  - Lista de proyectos procesados localmente

- **`src/app/templates/local_proyecto_detalle.html`** (pendiente)
  - Copia de `proyecto_detalle.html`
  - Vista detallada de proyecto local

- **`src/app/templates/local_index.html`** (pendiente)
  - Copia de `index.html`
  - Página de upload local

## Endpoints API pendientes de crear

Los siguientes endpoints deben ser añadidos a `src/api/main.py` con prefijo `/local-`:

- `POST /local-upload` - Subir y procesar PDF localmente
- `GET /local-proyectos` - Listar proyectos locales
- `GET /local-proyectos/{id}` - Obtener proyecto local
- `DELETE /local-proyectos/{id}` - Eliminar proyecto local
- `GET /local-exportar/{id}/{formato}` - Exportar proyecto local

## Rutas App pendientes de crear

Las siguientes rutas deben ser añadidas a `src/app/main.py`:

- `GET /local-upload` - Página de upload local
- `POST /local-upload` - Procesar upload local
- `GET /local-proyectos` - Lista de proyectos locales
- `GET /local-proyecto/{id}` - Detalle de proyecto local

## Base de datos

El sistema local usa:
- **Base de datos**: `data/mediciones.db` (SQLite)
- **Tablas**: `proyectos`, `capitulos`, `subcapitulos`, `apartados`, `partidas`

## Cómo restaurar el sistema local

Si necesitas volver al sistema local completo:

1. Restaurar modelos:
   ```bash
   cp src/models/local_db_models.py src/models/db_models.py
   ```

2. Restaurar parser:
   ```bash
   cp src/parser/local_partida_parser.py src/parser/partida_parser.py
   ```

3. Restaurar templates:
   ```bash
   cp src/app/templates/local_proyectos.html src/app/templates/proyectos.html
   cp src/app/templates/local_proyecto_detalle.html src/app/templates/proyecto_detalle.html
   cp src/app/templates/local_index.html src/app/templates/index.html
   ```

## Estado del Backup: ✅ COMPLETADO

**Fecha de finalización**: 2026-01-12 23:55

### Resumen
- ✅ 3 archivos Python de respaldo creados
- ✅ 3 templates HTML de respaldo creados
- ✅ 5 endpoints API `/local-*` implementados
- ✅ 4 rutas web `/local-*` implementadas
- ✅ Sistema local completamente funcional y preservado

### Acceso al sistema local de respaldo

**URLs de acceso:**
- Upload local: `http://localhost:3012/local-upload`
- Lista proyectos locales: `http://localhost:3012/local-proyectos`
- Detalle proyecto: `http://localhost:3012/local-proyecto/{id}`

**Endpoints API:**
- Base URL: `http://localhost:3013`
- Todos los endpoints con prefijo `/local-*` están operativos

## Próximos pasos

**Sistema híbrido** - Ahora puedes implementar el sistema híbrido en los archivos originales:
1. Modificar `src/models/db_models.py` para soportar proyectos híbridos
2. Modificar `src/parser/partida_parser.py` para procesamiento híbrido
3. Actualizar templates originales para mostrar proyectos híbridos
4. Mantener endpoints originales para compatibilidad

---

**IMPORTANTE**:
- ✅ El sistema local está completamente preservado y funcional
- ✅ Puedes acceder al sistema local mediante las rutas `/local-*`
- ⚠️ No elimines estos archivos de respaldo hasta que el sistema híbrido esté completamente probado
- 📝 Los archivos originales (`db_models.py`, `partida_parser.py`, etc.) pueden ser modificados libremente
