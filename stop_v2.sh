#!/bin/bash

# ============================================
# Script para detener Sistema Mediciones V2
# ============================================

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}Deteniendo Sistema V2${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# Obtener directorio del script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

STOPPED=0

# ============================================
# Detener Backend
# ============================================
if [ -f .backend_v2.pid ]; then
    BACKEND_PID=$(cat .backend_v2.pid)
    if ps -p $BACKEND_PID > /dev/null 2>&1; then
        echo -e "${YELLOW}Deteniendo Backend (PID: $BACKEND_PID)...${NC}"
        kill $BACKEND_PID 2>/dev/null
        sleep 1
        # Si no se detuvo, forzar
        if ps -p $BACKEND_PID > /dev/null 2>&1; then
            kill -9 $BACKEND_PID 2>/dev/null
        fi
        echo -e "${GREEN}✅ Backend detenido${NC}"
        STOPPED=1
    fi
    rm .backend_v2.pid
fi

# Detener por puerto si no hay PID file
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${YELLOW}Deteniendo proceso en puerto 8000...${NC}"
    lsof -ti:8000 | xargs kill -9 2>/dev/null
    echo -e "${GREEN}✅ Puerto 8000 liberado${NC}"
    STOPPED=1
fi

# ============================================
# Detener Frontend
# ============================================
if [ -f .frontend_v2.pid ]; then
    FRONTEND_PID=$(cat .frontend_v2.pid)
    if ps -p $FRONTEND_PID > /dev/null 2>&1; then
        echo -e "${YELLOW}Deteniendo Frontend (PID: $FRONTEND_PID)...${NC}"
        kill $FRONTEND_PID 2>/dev/null
        sleep 1
        # Si no se detuvo, forzar
        if ps -p $FRONTEND_PID > /dev/null 2>&1; then
            kill -9 $FRONTEND_PID 2>/dev/null
        fi
        echo -e "${GREEN}✅ Frontend detenido${NC}"
        STOPPED=1
    fi
    rm .frontend_v2.pid
fi

# Detener por puerto si no hay PID file
if lsof -Pi :3015 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${YELLOW}Deteniendo proceso en puerto 3015...${NC}"
    lsof -ti:3015 | xargs kill -9 2>/dev/null
    echo -e "${GREEN}✅ Puerto 3015 liberado${NC}"
    STOPPED=1
fi

# ============================================
# Resumen
# ============================================
echo ""
if [ $STOPPED -eq 1 ]; then
    echo -e "${GREEN}✅ Sistema V2 detenido correctamente${NC}"
else
    echo -e "${YELLOW}⚠️  No se encontraron procesos corriendo${NC}"
fi
echo ""
