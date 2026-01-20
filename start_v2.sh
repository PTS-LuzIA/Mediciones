#!/bin/bash

# ============================================
# Script para iniciar Sistema Mediciones V2
# Backend (FastAPI) + Frontend (Next.js)
# ============================================

# Colores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}Sistema Mediciones V2${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# Obtener el directorio del script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Crear directorio logs si no existe
mkdir -p logs

# ============================================
# 1. Verificar PostgreSQL
# ============================================
echo -e "${YELLOW}[1/4] Verificando PostgreSQL...${NC}"
if ! pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
    echo -e "${RED}❌ PostgreSQL no está corriendo${NC}"
    echo -e "${YELLOW}Iniciando PostgreSQL...${NC}"
    # Intentar iniciar PostgreSQL (comando varía según instalación)
    if command -v brew &> /dev/null; then
        brew services start postgresql@13 2>/dev/null || brew services start postgresql 2>/dev/null
    fi
    sleep 2
    if ! pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
        echo -e "${RED}❌ No se pudo iniciar PostgreSQL${NC}"
        echo -e "${YELLOW}Por favor, inicia PostgreSQL manualmente:${NC}"
        echo -e "${CYAN}  brew services start postgresql${NC}"
        exit 1
    fi
fi
echo -e "${GREEN}✅ PostgreSQL está corriendo${NC}"
echo ""

# ============================================
# 2. Crear base de datos si no existe
# ============================================
echo -e "${YELLOW}[2/4] Verificando base de datos...${NC}"
if ! psql -U imac -lqt 2>/dev/null | cut -d \| -f 1 | grep -qw mediciones_db; then
    echo -e "${YELLOW}Creando base de datos mediciones_db...${NC}"
    createdb -O imac mediciones_db 2>/dev/null
    echo -e "${GREEN}✅ Base de datos creada${NC}"
else
    echo -e "${GREEN}✅ Base de datos existe${NC}"
fi
echo ""

# ============================================
# 3. Iniciar Backend (FastAPI)
# ============================================
echo -e "${YELLOW}[3/4] Iniciando Backend API...${NC}"

# Verificar si el puerto 8000 está libre
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Puerto 8000 ocupado. Deteniendo proceso anterior...${NC}"
    lsof -ti:8000 | xargs kill -9 2>/dev/null
    sleep 1
fi

# Iniciar backend en background
python run_api.py > logs/backend_v2.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > .backend_v2.pid

# Esperar a que el backend esté listo
echo -e "${CYAN}Esperando a que el backend esté listo...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Backend API corriendo en http://localhost:8000${NC}"
        echo -e "${GREEN}   📚 Docs disponibles en http://localhost:8000/docs${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ Backend no respondió a tiempo${NC}"
        echo -e "${YELLOW}Ver logs en: logs/backend_v2.log${NC}"
        echo -e "${YELLOW}Últimas líneas:${NC}"
        tail -20 logs/backend_v2.log
        exit 1
    fi
    sleep 1
done
echo ""

# ============================================
# 4. Iniciar Frontend (Next.js)
# ============================================
echo -e "${YELLOW}[4/4] Iniciando Frontend...${NC}"

# Verificar si el puerto 3015 está libre
if lsof -Pi :3015 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Puerto 3015 ocupado. Deteniendo proceso anterior...${NC}"
    lsof -ti:3015 | xargs kill -9 2>/dev/null
    sleep 1
fi

# Navegar al directorio frontend
cd frontend

# Verificar si node_modules existe
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}📦 Instalando dependencias del frontend...${NC}"
    npm install
fi

# Iniciar frontend en background
npm run dev > ../logs/frontend_v2.log 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > ../.frontend_v2.pid

# Esperar a que el frontend esté listo
echo -e "${CYAN}Esperando a que el frontend esté listo...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:3015 > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Frontend corriendo en http://localhost:3015${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ Frontend no respondió a tiempo${NC}"
        echo -e "${YELLOW}Ver logs en: logs/frontend_v2.log${NC}"
        echo -e "${YELLOW}Últimas líneas:${NC}"
        tail -20 ../logs/frontend_v2.log
        exit 1
    fi
    sleep 1
done

cd ..
echo ""

# ============================================
# Resumen Final
# ============================================
echo -e "${BLUE}================================${NC}"
echo -e "${GREEN}✅ Sistema V2 iniciado correctamente${NC}"
echo -e "${BLUE}================================${NC}"
echo ""
echo -e "${GREEN}🌐 Frontend:${NC}  http://localhost:3015"
echo -e "${GREEN}🔌 Backend:${NC}   http://localhost:8000"
echo -e "${GREEN}📚 API Docs:${NC}  http://localhost:8000/docs"
echo ""
echo -e "${YELLOW}👤 Credenciales:${NC}"
echo -e "   Usuario:    ${CYAN}admin${NC}"
echo -e "   Contraseña: ${CYAN}admin123${NC}"
echo ""
echo -e "${YELLOW}📋 Procesos:${NC}"
echo -e "   Backend PID:  ${CYAN}$BACKEND_PID${NC}"
echo -e "   Frontend PID: ${CYAN}$FRONTEND_PID${NC}"
echo ""
echo -e "${YELLOW}📁 Logs:${NC}"
echo -e "   Backend:  ${CYAN}logs/backend_v2.log${NC}"
echo -e "   Frontend: ${CYAN}logs/frontend_v2.log${NC}"
echo ""
echo -e "${RED}⚠️  Para detener el sistema:${NC}"
echo -e "   ${CYAN}./stop_v2.sh${NC}"
echo -e "   ${BLUE}o manualmente:${NC}"
echo -e "   ${CYAN}kill $BACKEND_PID $FRONTEND_PID${NC}"
echo ""
echo -e "${BLUE}================================${NC}"
echo -e "${GREEN}🚀 Abre http://localhost:3015 para comenzar${NC}"
echo -e "${BLUE}================================${NC}"
