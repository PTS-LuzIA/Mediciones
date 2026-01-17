# Sistema de Conteo de Partidas con LLM

## 📋 Descripción

Se ha implementado una **nueva petición al LLM** en la Fase 1 del sistema híbrido para contar el número de partidas de cada capítulo y subcapítulo.

## 🔄 Flujo de Procesamiento

### Fase 1 - Extracción de Estructura (Ahora con 2 pasos)

#### **Paso 1.1**: Extracción de Jerarquía
- **Agente**: `StructureExtractionAgent`
- **Petición**: Primera petición al LLM
- **Extrae**:
  - Capítulos y subcapítulos (jerarquía completa)
  - Nombres y códigos
  - Totales en euros de cada sección
  - Nivel de confianza

#### **Paso 1.2**: Conteo de Partidas (NUEVO ✨)
- **Agente**: `PartidaCountAgent`
- **Petición**: Segunda petición al LLM (independiente)
- **Extrae**:
  - Número de partidas de cada capítulo
  - Número de partidas de cada subcapítulo
  - Conteo exacto sin detalles de las partidas

### ¿Por qué 2 peticiones separadas?

1. **Simplicidad del prompt**: Cada petición tiene un objetivo claro
2. **Respuesta más compacta**: El conteo devuelve solo códigos y números
3. **Mejor precisión**: El LLM se enfoca solo en contar, no en extraer toda la información
4. **Reutilización**: La estructura extraída se pasa al agente de conteo

## 📁 Archivos Creados/Modificados

### Nuevos Archivos
- ✅ `src/llm/partida_count_agent.py` - Agente especializado en contar partidas

### Archivos Modificados
- ✅ `src/llm/hybrid_orchestrator.py` - Integra el conteo en Fase 1
- ✅ `src/api/main.py` - Endpoint `/hybrid-fase1/{proyecto_id}` ejecuta el conteo
- ✅ `src/app/templates/hybrid_proyecto_detalle.html` - UI muestra conteo IA vs Local

### Sin Cambios (Ya Preparados)
- ℹ️ `src/models/hybrid_db_manager.py` - Ya guardaba `num_partidas_ia`
- ℹ️ `src/models/hybrid_models.py` - Ya tenía los campos en BD

## 🎯 Uso

### Desde la UI

1. Sube un PDF en el sistema híbrido
2. Ejecuta "Fase 1 - Extraer Estructura"
3. Verás en los logs:
   ```
   [FASE 1.1] Extrayendo jerarquía de capítulos y subcapítulos...
   [FASE 1.2] Contando número de partidas por sección...
   ✓ Conteo completado en X.XXs
   ```
4. En la página del proyecto verás:
   - Columna "Partidas IA" con el conteo del LLM
   - Columna "Partidas Local" con el conteo del parser
   - Resaltado en **rojo** si los conteos no coinciden

### Desde Código Python

```python
from llm.structure_extraction_agent import StructureExtractionAgent
from llm.partida_count_agent import PartidaCountAgent

# Paso 1: Extraer estructura
structure_agent = StructureExtractionAgent()
estructura = await structure_agent.extraer_estructura("ruta/al/presupuesto.pdf")

# Paso 2: Contar partidas
count_agent = PartidaCountAgent()
conteo = await count_agent.contar_partidas("ruta/al/presupuesto.pdf", estructura)

# Paso 3: Fusionar
estructura_completa = count_agent.fusionar_conteo_con_estructura(estructura, conteo)

# Ahora estructura_completa tiene el campo 'num_partidas' en cada nivel
print(estructura_completa['capitulos'][0]['num_partidas'])
```

### Script de Prueba

Ejecuta el script de prueba incluido:

```bash
cd /Volumes/DATOS_IA/G_Drive_LuzIA/IA/Proyectos/MVP/Mediciones
python test_conteo_partidas.py
```

**Nota**: Ajusta la ruta del PDF en el script según tu sistema.

## 📊 Formato JSON del Conteo

El agente devuelve una estructura JSON compacta:

```json
{
  "capitulos": [
    {
      "codigo": "01",
      "num_partidas": 5,
      "subcapitulos": [
        {
          "codigo": "01.05",
          "num_partidas": 12,
          "subcapitulos": [
            {
              "codigo": "01.05.01",
              "num_partidas": 8,
              "subcapitulos": []
            }
          ]
        }
      ]
    }
  ]
}
```

Solo contiene:
- `codigo`: Código del capítulo/subcapítulo
- `num_partidas`: Número de partidas directas
- `subcapitulos`: Subcapítulos hijos (recursivo)

## 🔍 Validación

### En Fase 3

El sistema ahora valida **dos criterios**:

1. **Total en €**: IA vs Local (tolerancia: ±0.01€)
2. **Número de partidas**: IA vs Local (debe ser exacto)

Si cualquiera de los dos no coincide:
- Estado: `DISCREPANCIA` ⚠️
- Necesita revisión: `necesita_revision_ia = 1`

### Visualización en UI

En la tabla de resumen:
- Columna "Partidas IA": Muestra el conteo del LLM
- Columna "Partidas Local": Muestra partidas extraídas por parser
- **Color rojo**: Si los conteos no coinciden
- **Color azul/verde**: Si coinciden

En la estructura detallada:
```
IA: 1.234,56 € (15 partidas) | Local: 1.234,56 € (15 partidas)
```

En la sección de validación:
```
Número de partidas: IA: 15 | Local: 14  ← En rojo si no coinciden
Diferencia en total: 0,00 € (0.00%)
```

## ⚙️ Configuración

### Variables de Entorno

Asegúrate de tener configurado:

```bash
OPENROUTER_API_KEY=tu_api_key_aqui
```

### Modelo Usado

Por defecto: `google/gemini-2.5-flash-lite`

Puedes cambiarlo en `src/llm/partida_count_agent.py`:

```python
self.model = "google/gemini-2.5-flash-lite"
```

## 🐛 Troubleshooting

### Error: "PartidaCountAgent no encontrado"

Verifica que el archivo existe:
```bash
ls src/llm/partida_count_agent.py
```

### No se ejecuta el conteo

Verifica los logs en la API:
```bash
# Deberías ver:
[FASE 1.1] Extrayendo jerarquía...
[FASE 1.2] Contando número de partidas...
✓ Conteo completado en X.XXs
```

Si no ves el paso 1.2, reinicia la API.

### Conteo incorrecto

El LLM puede contar mal si:
- El PDF tiene un formato muy irregular
- Los códigos de partidas no son consistentes
- Hay partidas sin código claro

Revisa manualmente y compara con el conteo local.

## 📈 Beneficios

1. **Detección temprana de errores**: Sabes cuántas partidas debe tener cada sección antes del parseo local
2. **Validación robusta**: Compara tanto totales como conteo de partidas
3. **Debugging más fácil**: Si el conteo no coincide, sabes dónde buscar problemas
4. **No invasivo**: No modifica la petición original de estructura

## 🔮 Futuras Mejoras

- Permitir ajustar tolerancia en el conteo (ej: ±1 partida)
- Incluir conteo de partidas en el prompt de estructura (prompt único)
- Cache de conteos para re-procesamiento rápido
- Comparación visual partida por partida

## 📞 Soporte

Para problemas o mejoras, consulta los archivos:
- `src/llm/partida_count_agent.py` - Lógica del conteo
- `src/llm/hybrid_orchestrator.py` - Integración en Fase 1
- `src/api/main.py` - Endpoint de API
