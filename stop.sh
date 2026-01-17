#!/bin/bash

###############################################################################
# Script para detener MVP Mediciones
# Detiene API (3013) y Aplicación Web (3012)
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

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║            Deteniendo MVP Mediciones                   ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

stopped_count=0

# Función para detener un servicio
stop_service() {
    local service_name=$1
    local port=$2
    local pid_file=$3

    echo -e "${YELLOW}Deteniendo $service_name...${NC}"

    local stopped=false

    # Intentar detener por PID file primero
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 $pid 2>/dev/null; then
            if kill $pid 2>/dev/null; then
                echo -e "  ${GREEN}✓ Proceso detenido (PID: $pid)${NC}"
                stopped=true
                ((stopped_count++))
                sleep 1
            fi
        else
            echo -e "  ${YELLOW}⚠ PID $pid no está corriendo${NC}"
        fi
        rm -f "$pid_file"
    fi

    # Verificar si el puerto sigue ocupado
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        local port_pid=$(lsof -t -i:$port 2>/dev/null)
        echo -e "  ${YELLOW}⚠ Puerto $port aún está en uso (PID: $port_pid)${NC}"
        echo -n "  ${YELLOW}Forzando cierre...${NC}"

        if kill -9 $port_pid 2>/dev/null; then
            sleep 1
            if ! lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
                echo -e " ${GREEN}✓${NC}"
                stopped=true
                ((stopped_count++))
            else
                echo -e " ${RED}✗ No se pudo liberar el puerto${NC}"
            fi
        else
            echo -e " ${RED}✗ Error al forzar cierre${NC}"
        fi
    elif [ "$stopped" = false ]; then
        echo -e "  ${CYAN}• El servicio no estaba corriendo${NC}"
    fi
}

# Detener API
stop_service "API Backend" $API_PORT "logs/api.pid"
echo ""

# Detener App
stop_service "Aplicación Web" $APP_PORT "logs/app.pid"
echo ""

# Resumen
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
if [ $stopped_count -eq 0 ]; then
    echo -e "${CYAN}No había servicios corriendo${NC}"
else
    echo -e "${GREEN}✓ Sistema detenido correctamente${NC}"
    echo -e "${GREEN}  $stopped_count servicio(s) detenido(s)${NC}"
fi
echo ""
