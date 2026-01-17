# Logs Temporales de Análisis

## Directorio: `logs/TEMP_BORRAR/`

Este directorio contiene **todas las respuestas RAW** del LLM durante la extracción de partidas, tanto exitosas como con errores.

### Propósito

- **Análisis y debugging**: Ver exactamente qué está devolviendo el modelo
- **Validación**: Comprobar si el modelo está respetando las restricciones del prompt
- **Temporal**: Estos archivos se pueden eliminar sin afectar el funcionamiento

### Tipos de archivos

1. **`raw_response_*_BORRAR.json`**: Respuestas exitosas (JSON parseado correctamente)
2. **`error_response_*_BORRAR.json`**: Respuestas con errores de parsing

### Nomenclatura

```
raw_response_{CAPITULO}_{SUBCAPITULOS}_{TIMESTAMP}_BORRAR.json
error_response_{CAPITULO}_{SUBCAPITULOS}_{TIMESTAMP}_BORRAR.json
```

Ejemplo:
- `raw_response_01_01.01_1768240770_BORRAR.json`
- `error_response_01_01.02_01.03_1768240850_BORRAR.json`

### Limpieza

Para eliminar todos los archivos temporales:

```bash
./limpiar_logs_temp.sh
```

O manualmente:
```bash
rm -rf logs/TEMP_BORRAR
```

### Análisis

Para ver qué subcapítulos está extrayendo realmente el modelo:

```bash
# Ver todos los subcapítulos únicos en una respuesta
grep -o '"subcapitulo_codigo": "[^"]*"' logs/TEMP_BORRAR/raw_response_*.json | sort | uniq -c

# Contar cuántas partidas hay en total
grep -c '"codigo":' logs/TEMP_BORRAR/raw_response_*.json
```

## Cambios Realizados

### 1. Prompt más restrictivo

Se añadió una **RESTRICCIÓN CRÍTICA** al inicio del prompt cuando hay filtro de subcapítulos:

```
🚨 RESTRICCIÓN CRÍTICA - LEE ESTO PRIMERO:
Solo debes extraer partidas de estos subcapítulos específicos: {subcapitulos}
❌ IGNORA completamente cualquier partida de otros subcapítulos
```

### 2. Guardado automático de respuestas

**Todas** las respuestas del LLM se guardan automáticamente en `logs/TEMP_BORRAR/` para análisis posterior, independientemente de si el parsing fue exitoso o no.

### 3. Repetición de restricción

La restricción de subcapítulos se repite **3 veces** en diferentes partes del prompt para asegurar que el modelo la respete.
