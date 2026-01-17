#!/bin/bash

echo "======================================"
echo "  MONITOR DE EXTRACCIÓN DE PARTIDAS"
echo "======================================"
echo ""
echo "Monitoreando logs/api.log..."
echo "Presiona Ctrl+C para detener"
echo ""

tail -f logs/api.log | grep -E "(Iniciando|Procesando|Extrayendo|ERROR|✓|📊|📁|Tamaño)"
