#!/bin/bash
# Script para limpiar archivos temporales de análisis

echo "🗑️  Limpiando archivos temporales..."

# Eliminar directorio temporal
if [ -d "logs/TEMP_BORRAR" ]; then
    rm -rf logs/TEMP_BORRAR
    echo "✓ Directorio logs/TEMP_BORRAR eliminado"
else
    echo "⚠️  Directorio logs/TEMP_BORRAR no existe"
fi

# Eliminar archivos antiguos con _BORRAR en el nombre
find logs -name "*_BORRAR*" -type f -delete 2>/dev/null
echo "✓ Archivos con sufijo _BORRAR eliminados"

echo "✅ Limpieza completada"
