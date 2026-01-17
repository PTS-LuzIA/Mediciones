# 🤖 Integración con LLM Server

## Resumen

El MVP Mediciones puede integrarse opcionalmente con un servidor LLM local para funciones avanzadas de procesamiento de texto y corrección de errores.

---

## 📍 Ubicación del LLM Server

```
/Volumes/DATOS_IA/G_Drive_LuzIA/IA/Proyectos/LLM-Server
```

---

## 🔌 Arquitectura del LLM Server

El LLM Server es una arquitectura multi-servicio que ejecuta:

### Servicios y Puertos

| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| **LiteLLM Gateway** | 8080 | API unificada compatible con OpenAI |
| **Llama Server** | 8081 | Qwen 2.5 7B (128K context) - Chat |
| **BGE-M3** | 8082 | Embeddings para RAG |
| **Ollama** | 11434 | Modelos de visión (llava, llama3.2-vision) |
| **Redis** | 6379 | Cache para LiteLLM |

### Modelos Disponibles

1. **Qwen 2.5 7B Instruct** (Puerto 8081)
   - Contexto: 128K tokens
   - GPU: Metal (Apple Silicon)
   - Uso: Chat optimizado para producción
   - Ubicación: `/Volumes/DATOS_IA/G_Drive_LuzIA/IA/AI-MODELS/llm/GGUF/qwen/`

2. **BGE-M3** (Puerto 8082)
   - Dimensiones: 1024
   - Uso: Embeddings para RAG
   - Ubicación: `/Volumes/DATOS_IA/G_Drive_LuzIA/IA/AI-MODELS/llm/GGUF/bge-m3/`

3. **Modelos Ollama** (Puerto 11434)
   - llava
   - llama3.2-vision
   - Uso: Análisis de imágenes

---

## 🚀 Iniciar el LLM Server

### Opción 1: Inicio Manual

```bash
cd /Volumes/DATOS_IA/G_Drive_LuzIA/IA/Proyectos/LLM-Server
./start-native.sh
```

El script iniciará automáticamente:
1. Redis (caché)
2. Ollama (modelos de visión)
3. Llama Server (Qwen 2.5 7B)
4. BGE-M3 Server (embeddings)
5. LiteLLM Gateway (API unificada)

**Tiempo de inicio:** 1-2 minutos (depende del hardware)

### Opción 2: Inicio Automático desde MVP Mediciones

Al ejecutar `./start.sh` del MVP Mediciones:

1. El script detecta si LLM Server está corriendo (puerto 8080)
2. Si no está activo, pregunta si deseas iniciarlo
3. Si aceptas, ejecuta automáticamente `start-native.sh`

---

## 🔍 Verificar Estado del LLM Server

### Método 1: Verificar puertos

```bash
# Verificar todos los servicios
lsof -i :8080  # LiteLLM Gateway
lsof -i :8081  # Llama Server
lsof -i :8082  # BGE-M3
lsof -i :11434 # Ollama
```

### Método 2: Health checks

```bash
# LiteLLM Gateway
curl http://localhost:8080/health

# Llama Server
curl http://localhost:8081/health

# BGE-M3
curl http://localhost:8082/health

# Ollama
curl http://localhost:11434/api/tags
```

### Método 3: Listar modelos disponibles

```bash
curl http://localhost:8080/v1/models
```

---

## 🛠️ Detener el LLM Server

```bash
cd /Volumes/DATOS_IA/G_Drive_LuzIA/IA/Proyectos/LLM-Server
./stop-native.sh
```

---

## 💡 Uso desde MVP Mediciones

### Estado Actual

El MVP Mediciones **no requiere** el LLM Server para funcionar. Todas las funcionalidades de parsing, exportación y API funcionan independientemente.

### Integración Futura (Planificada)

El LLM Server se usará para:

1. **Corrección de OCR**: Mejorar texto extraído de PDFs escaneados
2. **Normalización inteligente**: Corregir errores de parsing
3. **Clasificación avanzada**: Mejorar detección de tipos de línea
4. **Validación semántica**: Verificar coherencia de descripciones
5. **Sugerencias**: Proponer correcciones automáticas

### Ejemplo de Integración Futura

```python
import requests

# Llamada al LLM para corregir texto
def corregir_descripcion(texto_parcial):
    response = requests.post('http://localhost:8080/v1/chat/completions', json={
        'model': 'qwen2.5-7b',
        'messages': [
            {'role': 'system', 'content': 'Eres un experto en presupuestos de construcción.'},
            {'role': 'user', 'content': f'Completa esta descripción: {texto_parcial}'}
        ],
        'max_tokens': 100
    })
    return response.json()['choices'][0]['message']['content']

# Ejemplo
texto_roto = "Demolición y levantado de bordillo de cualquier tipo en tramos ais..."
texto_corregido = corregir_descripcion(texto_roto)
```

---

## 📊 Recursos del Sistema

### Requisitos Mínimos

- **RAM**: 8 GB (16 GB recomendado)
- **CPU**: Apple Silicon (M1/M2/M3)
- **Disco**: 20 GB para modelos

### Consumo de Recursos

| Servicio | RAM | CPU | GPU |
|----------|-----|-----|-----|
| Qwen 2.5 7B | ~5 GB | 10-20% | Metal (33 layers) |
| BGE-M3 | ~2 GB | 5-10% | CPU |
| Ollama | ~4 GB | Variable | Metal |
| LiteLLM | ~500 MB | 1-5% | - |
| Redis | ~50 MB | <1% | - |

**Total aproximado:** 12-15 GB RAM en uso

---

## 🔧 Configuración

La configuración del LLM Server está en:

```
/Volumes/DATOS_IA/G_Drive_LuzIA/IA/Proyectos/LLM-Server/.env
```

Variables principales:

```bash
# Puertos
LITELLM_PORT=8080
LLAMA_SERVER_PORT=8081
BGE_M3_PORT=8082
OLLAMA_PORT=11434

# Configuración Llama Server
CONTEXT_SIZE=131072  # 128K tokens
PARALLEL_REQUESTS=6
THREADS=8
GPU_LAYERS=33  # Metal GPU
```

---

## 🐛 Troubleshooting

### Error: "Port 8080 already in use"

```bash
# Verificar qué proceso usa el puerto
lsof -i :8080

# Detener LLM Server correctamente
cd /Volumes/DATOS_IA/G_Drive_LuzIA/IA/Proyectos/LLM-Server
./stop-native.sh
```

### Error: "Model not found"

Verifica que los modelos existan:

```bash
ls -lh /Volumes/DATOS_IA/G_Drive_LuzIA/IA/AI-MODELS/llm/GGUF/qwen/
ls -lh /Volumes/DATOS_IA/G_Drive_LuzIA/IA/AI-MODELS/llm/GGUF/bge-m3/
```

### Error: Timeout al iniciar

El primer inicio puede tardar más porque carga los modelos. Espera 2-3 minutos.

Ver logs:

```bash
tail -f /Volumes/DATOS_IA/G_Drive_LuzIA/IA/Proyectos/LLM-Server/logs/llama-server.log
tail -f /Volumes/DATOS_IA/G_Drive_LuzIA/IA/Proyectos/LLM-Server/logs/litellm.log
```

---

## 📚 Documentación Adicional

- [LLM-Server README](file:///Volumes/DATOS_IA/G_Drive_LuzIA/IA/Proyectos/LLM-Server/README.md)
- [LiteLLM Docs](https://docs.litellm.ai)
- [llama.cpp](https://github.com/ggerganov/llama.cpp)
- [Ollama](https://ollama.ai)

---

**Nota:** El LLM Server es completamente **opcional**. El MVP Mediciones funciona al 100% sin él. La integración con LLM está planificada para versiones futuras que incluirán OCR y corrección automática.
