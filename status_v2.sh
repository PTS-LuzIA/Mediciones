#!/bin/bash

# ============================================
# Script para ver estado Sistema Mediciones V2
# ============================================

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}Estado Sistema Mediciones V2${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# ============================================
# PostgreSQL
# ============================================
echo -e "${YELLOW}PostgreSQL:${NC}"
if pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
    echo -e "  ${GREEN}✅ Corriendo${NC}"
    if psql -U imac -lqt 2>/dev/null | cut -d \| -f 1 | grep -qw mediciones_db; then
        echo -e "  ${GREEN}✅ Base de datos 'mediciones_db' existe${NC}"
    else
        echo -e "  ${RED}❌ Base de datos 'mediciones_db' NO existe${NC}"
    fi
else
    echo -e "  ${RED}❌ NO está corriendo${NC}"
fi
echo ""

# ============================================
# Backend API
# ============================================
echo -e "${YELLOW}Backend API (puerto 8000):${NC}"
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    PID=$(lsof -t -i:8000)
    echo -e "  ${GREEN}✅ Corriendo (PID: $PID)${NC}"
    echo -e "  ${CYAN}   http://localhost:8000${NC}"
    echo -e "  ${CYAN}   http://localhost:8000/docs${NC}"
    
    # Verificar health endpoint
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "  ${GREEN}✅ Health check OK${NC}"
    else
        echo -e "  ${YELLOW}⚠️  Health check FAIL${NC}"
    fi
else
    echo -e "  ${RED}❌ NO está corriendo${NC}"
fi
echo ""

# ============================================
# Frontend
# ============================================
echo -e "${YELLOW}Frontend (puerto 3015):${NC}"
if lsof -Pi :3015 -sTCP:LISTEN -t >/dev/null 2>&1; then
    PID=$(lsof -t -i:3015)
    echo -e "  ${GREEN}✅ Corriendo (PID: $PID)${NC}"
    echo -e "  ${CYAN}   http://localhost:3015${NC}"
    
    # Verificar si responde
    if curl -s http://localhost:3015 > /dev/null 2>&1; then
        echo -e "  ${GREEN}✅ Respondiendo OK${NC}"
    else
        echo -e "  ${YELLOW}⚠️  No responde${NC}"
    fi
else
    echo -e "  ${RED}❌ NO está corriendo${NC}"
fi
echo ""

# ============================================
# Logs
# ============================================
echo -e "${YELLOW}Logs disponibles:${NC}"
if [ -f logs/backend_v2.log ]; then
    SIZE=$(wc -c < logs/backend_v2.log | xargs)
    echo -e "  ${GREEN}✅${NC} logs/backend_v2.log (${SIZE} bytes)"
else
    echo -e "  ${RED}❌${NC} logs/backend_v2.log (no existe)"
fi

if [ -f logs/frontend_v2.log ]; then
    SIZE=$(wc -c < logs/frontend_v2.log | xargs)
    echo -e "  ${GREEN}✅${NC} logs/frontend_v2.log (${SIZE} bytes)"
else
    echo -e "  ${RED}❌${NC} logs/frontend_v2.log (no existe)"
fi
echo ""

# ============================================
# Comandos útiles
# ============================================
echo -e "${CYAN}Comandos útiles:${NC}"
echo -e "  Iniciar:  ${GREEN}./start_v2.sh${NC}"
echo -e "  Detener:  ${RED}./stop_v2.sh${NC}"
echo -e "  Ver logs: ${YELLOW}tail -f logs/backend_v2.log logs/frontend_v2.log${NC}"
echo ""
