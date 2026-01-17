# 🔧 PROPUESTA: MEJORA DE FASE 2 (PARSER LOCAL POR SUBCAPÍTULOS)

**Fecha**: 2026-01-13
**Estado**: ✅ Contador implementado | 🔄 Mejora Fase 2 pendiente

---

## 📋 CONTEXTO

Actualmente la **Fase 2** procesa todo el PDF de una vez con el parser local (`PartidaParser`). Esto funciona, pero tiene limitaciones:

### ❌ **Problemas Actuales**:
1. Si falla en un subcapítulo, no sabemos cuál
2. No hay logs detallados por subcapítulo
3. Difícil depurar errores específicos
4. No aprovechamos el contador `num_partidas_ia` para validar en tiempo real

---

## ✅ **MEJORA PROPUESTA: PROCESAMIENTO POR SUBCAPÍTULOS**

### **Idea Central**:
En lugar de procesar todo el PDF → **Procesar subcapítulo por subcapítulo** usando la información de Fase 1.

### **Flujo Mejorado**:

```python
# FASE 1: IA extrae estructura
estructura = {
    "01.05.02": {
        "nombre": "MURO TIPO 2",
        "total_ia": 15000.50,
        "num_partidas_ia": 25  # 👈 Sabemos que debe haber 25 partidas
    }
}

# FASE 2: Parser local procesa por subcapítulos
for subcapitulo in estructura:
    # 1. Extraer solo las líneas de este subcapítulo
    texto_subcap = extraer_seccion(pdf, subcapitulo.codigo)

    # 2. Parsear partidas de esta sección
    partidas = parser.parsear_seccion(texto_subcap)

    # 3. VALIDACIÓN INMEDIATA
    if len(partidas) == subcapitulo.num_partidas_ia:
        ✅ "Subcapítulo 01.05.02: 25/25 partidas extraídas"
    else:
        ⚠️ "Subcapítulo 01.05.02: 18/25 partidas (faltan 7)"
        # → Marcar para re-extracción con IA

    # 4. Guardar en BD
    guardar_partidas(subcapitulo, partidas)
```

---

## 🎯 **VENTAJAS**

### 1️⃣ **Validación en Tiempo Real**
```
[FASE 2] Procesando subcapítulo 01.05.01...
  ✓ 12/12 partidas extraídas (100%)
[FASE 2] Procesando subcapítulo 01.05.02...
  ⚠️ 18/25 partidas extraídas (72%) - FALTA REVISAR
[FASE 2] Procesando subcapítulo 01.05.03...
  ✓ 8/8 partidas extraídas (100%)
```

### 2️⃣ **Re-Procesamiento Selectivo**
Si un subcapítulo falla:
```python
# Solo re-procesar los que fallaron
subcapitulos_fallidos = ["01.05.02", "01.10.05"]
for codigo in subcapitulos_fallidos:
    # Re-intentar con estrategia diferente
    # O marcar para extracción con IA
```

### 3️⃣ **Logs Detallados**
```
[01.05.01] ✓ 12 partidas | €8,250.50
[01.05.02] ⚠️ 18/25 partidas | €13,750.25 (esperado: €15,000.50)
[01.05.03] ✓ 8 partidas | €5,120.00
```

### 4️⃣ **Mejor Depuración**
Sabemos exactamente qué subcapítulo tiene problemas y cuántas partidas faltan.

---

## 🛠️ **IMPLEMENTACIÓN PROPUESTA**

### **Opción A: Modificar `PartidaParser` Existente** (Conservadora)

**Pros**:
- Mantiene el parser actual funcionando
- Cambios incrementales
- Bajo riesgo

**Contras**:
- El código actual no está optimizado para procesamiento por secciones
- Más difícil de adaptar

### **Opción B: Crear `HybridPartidaParser` Nuevo** (Recomendada ⭐)

**Crear**: `src/parser/hybrid_partida_parser.py`

```python
class HybridPartidaParser:
    """
    Parser local optimizado para el sistema híbrido.
    Procesa subcapítulos individualmente usando la estructura de Fase 1.
    """

    def __init__(self, pdf_path: str, estructura_ia: Dict):
        self.pdf_path = pdf_path
        self.estructura_ia = estructura_ia
        self.extractor = PDFExtractor(pdf_path)

    def parsear_subcapitulo(self, codigo_subcapitulo: str) -> Dict:
        """
        Parsea un subcapítulo específico

        Args:
            codigo_subcapitulo: "01.05.02"

        Returns:
            {
                "codigo": "01.05.02",
                "partidas": [...],
                "num_extraidas": 18,
                "num_esperadas": 25,
                "completitud": 0.72,
                "necesita_revision": True
            }
        """
        # 1. Obtener info de Fase 1
        subcap_ia = self._buscar_en_estructura(codigo_subcapitulo)
        num_esperadas = subcap_ia.get('num_partidas', 0)

        # 2. Extraer solo las líneas de este subcapítulo
        lineas = self._extraer_lineas_subcapitulo(codigo_subcapitulo)

        # 3. Clasificar y parsear
        clasificaciones = LineClassifier.clasificar_bloque(lineas)
        partidas = self._extraer_partidas(clasificaciones)

        # 4. Validar conteo
        num_extraidas = len(partidas)
        completitud = num_extraidas / num_esperadas if num_esperadas > 0 else 0
        necesita_revision = completitud < 0.9  # Si falta más del 10%

        return {
            "codigo": codigo_subcapitulo,
            "partidas": partidas,
            "num_extraidas": num_extraidas,
            "num_esperadas": num_esperadas,
            "completitud": completitud,
            "necesita_revision": necesita_revision
        }

    def parsear_proyecto_completo(self) -> Dict:
        """Parsea todos los subcapítulos del proyecto"""
        resultados = []

        # Obtener lista de subcapítulos HOJA (los que tienen partidas)
        subcapitulos_hoja = self._obtener_subcapitulos_hoja()

        for subcap_codigo in subcapitulos_hoja:
            logger.info(f"[FASE 2] Procesando {subcap_codigo}...")

            resultado = self.parsear_subcapitulo(subcap_codigo)
            resultados.append(resultado)

            # Log del resultado
            if resultado['necesita_revision']:
                logger.warning(
                    f"  ⚠️ {subcap_codigo}: {resultado['num_extraidas']}/{resultado['num_esperadas']} "
                    f"partidas ({resultado['completitud']*100:.1f}%)"
                )
            else:
                logger.info(
                    f"  ✓ {subcap_codigo}: {resultado['num_extraidas']}/{resultado['num_esperadas']} "
                    f"partidas ({resultado['completitud']*100:.1f}%)"
                )

        return {
            "subcapitulos_procesados": len(resultados),
            "subcapitulos_ok": sum(1 for r in resultados if not r['necesita_revision']),
            "subcapitulos_revisar": sum(1 for r in resultados if r['necesita_revision']),
            "resultados": resultados
        }
```

**Pros**:
- Código limpio y específico para híbrido
- Fácil de mantener y extender
- No afecta el parser original

**Contras**:
- Requiere crear nuevo archivo
- Más código inicial

---

## 📊 **COMPARACIÓN DE ENFOQUES**

| Característica | Sistema Actual | Sistema Mejorado |
|----------------|----------------|------------------|
| **Granularidad** | Todo el PDF | Por subcapítulo |
| **Validación** | Al final (Fase 3) | En tiempo real (Fase 2) |
| **Logs** | Genéricos | Detallados por subcapítulo |
| **Depuración** | Difícil | Fácil (sabemos qué subcap falla) |
| **Re-procesamiento** | Todo el proyecto | Solo subcapítulos fallidos |
| **Uso de IA** | No aprovecha | Usa `num_partidas_ia` |

---

## 🚀 **ROADMAP DE IMPLEMENTACIÓN**

### **Fase 2.1: Parser por Subcapítulos** (AHORA)
1. ✅ Contador de partidas implementado
2. 🔄 Crear `HybridPartidaParser`
3. 🔄 Integrar en `HybridOrchestrator`
4. 🔄 Validación en tiempo real

**Tiempo estimado**: 2-3 horas
**Impacto**: Alto (mejor depuración y logs)

### **Fase 2.2: Re-Procesamiento Inteligente** (SIGUIENTE)
1. Detectar subcapítulos con baja completitud
2. Re-intentar con estrategias diferentes:
   - Parser más agresivo
   - Ajustar patrones de regex
   - Diferentes layouts de columnas
3. Si aún falla → Marcar para IA

**Tiempo estimado**: 2-3 horas
**Impacto**: Medio (reduce llamadas a IA)

### **Fase 2.3: Re-Extracción con IA** (FUTURO)
1. Para subcapítulos que fallan con parser local
2. Usar `PartidaExtractionAgent` solo en subcaps problemáticos
3. Comparar resultados IA vs Local
4. Actualizar BD con mejor resultado

**Tiempo estimado**: 3-4 horas
**Impacto**: Alto (máxima precisión)

---

## 💡 **DECISIÓN RECOMENDADA**

### **Implementar Fase 2.1 AHORA** ⭐

**Por qué**:
1. ✅ Ya tenemos el contador implementado
2. ✅ Mejora inmediata en logs y depuración
3. ✅ Base sólida para futuras mejoras
4. ✅ Bajo riesgo (no rompe nada existente)

**Cómo**:
1. Crear `src/parser/hybrid_partida_parser.py`
2. Reutilizar lógica de `local_partida_parser.py` (más reciente)
3. Adaptar para procesar por subcapítulos
4. Integrar en `HybridOrchestrator.procesar_proyecto_completo()`

**Resultado esperado**:
```
[FASE 2] Procesando 20 subcapítulos...
  ✓ 01.05.01: 12/12 partidas (100%)
  ✓ 01.05.02: 25/25 partidas (100%)
  ⚠️ 01.05.03: 18/22 partidas (82%) - REVISAR
  ✓ 01.10.01: 8/8 partidas (100%)
  ...
[FASE 2] Completada: 18/20 OK, 2 necesitan revisión
```

---

## ❓ **SIGUIENTE PASO**

¿Quieres que implemente ahora la **Fase 2.1** (Parser por Subcapítulos)?

Si dices que sí, voy a:
1. ✅ Crear `hybrid_partida_parser.py`
2. ✅ Adaptar la extracción por subcapítulos
3. ✅ Integrar en el orquestador
4. ✅ Agregar validación en tiempo real

Esto mejorará inmediatamente la visibilidad y depuración del sistema híbrido.
