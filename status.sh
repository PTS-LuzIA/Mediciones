#!/bin/bash

###############################################################################
# Script para verificar el estado de MVP Mediciones
###############################################################################

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuración
API_PORT=3013
APP_PORT=3012
LLM_PORT=8080

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║            Estado de MVP Mediciones                    ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

check_service() {
    local name=$1
    local port=$2
    local health_url=$3

    echo -n "  $name (puerto $port): "

    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        local pid=$(lsof -t -i:$port 2>/dev/null)

        # Verificar health endpoint si está disponible
        if [ -n "$health_url" ] && curl -s "$health_url" >/dev/null 2>&1; then
            echo -e "${GREEN}✓ Corriendo${NC} (PID: $pid, health: OK)"
        else
            echo -e "${YELLOW}⚠ Corriendo${NC} (PID: $pid)"
        fi
        return 0
    else
        echo -e "${RED}✗ Detenido${NC}"
        return 1
    fi
}

services_running=0

# Verificar API
if check_service "API Backend" $API_PORT "http://localhost:$API_PORT/health"; then
    ((services_running++))
    echo -e "    ${CYAN}→ Documentación: http://localhost:$API_PORT/docs${NC}"
fi

# Verificar App
if check_service "Aplicación Web" $APP_PORT "http://localhost:$APP_PORT/health"; then
    ((services_running++))
    echo -e "    ${CYAN}→ Interfaz: http://localhost:$APP_PORT${NC}"
fi

# Verificar LLM Server (opcional)
echo ""
echo -e "${YELLOW}Servicios LLM (opcionales):${NC}"
if check_service "LiteLLM Gateway" $LLM_PORT; then
    echo -e "    ${CYAN}→ API: http://localhost:$LLM_PORT${NC}"
fi
check_service "Llama Server (Qwen)" 8081
check_service "BGE-M3 Embeddings" 8082
check_service "Ollama" 11434

# Resumen
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [ $services_running -eq 2 ]; then
    echo -e "${GREEN}Sistema completo corriendo ($services_running/2 servicios)${NC}"
elif [ $services_running -gt 0 ]; then
    echo -e "${YELLOW}Sistema parcialmente activo ($services_running/2 servicios)${NC}"
    echo -e "${YELLOW}Ejecuta ./start.sh para iniciar los servicios faltantes${NC}"
else
    echo -e "${RED}Sistema detenido${NC}"
    echo -e "${CYAN}Ejecuta ./start.sh para iniciar el sistema${NC}"
fi
echo ""
