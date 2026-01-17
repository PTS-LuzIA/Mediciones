#!/bin/bash

###############################################################################
# Script de inicio para MVP Mediciones
# Verifica y arranca:
# - LLM Server (si no está corriendo)
# - API Mediciones en puerto 3013
# - Aplicación Web en puerto 3012
###############################################################################

set -e  # Salir si hay error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuración
API_PORT=3013
APP_PORT=3012
LLM_SERVER_DIR="/Volumes/DATOS_IA/G_Drive_LuzIA/IA/Proyectos/LLM-Server"
LLM_PORT=8080  # Puerto LiteLLM Gateway
LLM_SERVER_SCRIPT="$LLM_SERVER_DIR/start-native.sh"
VENV_DIR="venv"

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     MVP MEDICIONES - Sistema de Inicio Automático     ║${NC}"
echo -e "${BLUE}║          API (3013) + Aplicación Web (3012)            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

###############################################################################
# FUNCIONES
###############################################################################

check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Puerto en uso
    else
        return 1  # Puerto libre
    fi
}

check_llm_server() {
    echo -e "${YELLOW}[1/5] Verificando LLM Server...${NC}"

    # Verificar si LiteLLM Gateway está corriendo
    if check_port $LLM_PORT; then
        echo -e "${GREEN}✓ LLM Server está corriendo${NC}"
        echo -e "${GREEN}  • LiteLLM Gateway: http://localhost:$LLM_PORT${NC}"

        # Verificar otros servicios
        if check_port 8081; then
            echo -e "${GREEN}  • Llama Server (Qwen 2.5): http://localhost:8081${NC}"
        fi
        if check_port 8082; then
            echo -e "${GREEN}  • BGE-M3 Embeddings: http://localhost:8082${NC}"
        fi
        if check_port 11434; then
            echo -e "${GREEN}  • Ollama: http://localhost:11434${NC}"
        fi

        return 0
    else
        echo -e "${YELLOW}⚠ LLM Server NO está corriendo${NC}"
        echo -e "${YELLOW}  El MVP Mediciones funcionará con funcionalidad limitada${NC}"
        echo ""
        echo -e "${YELLOW}  Para iniciar el LLM Server manualmente:${NC}"
        echo -e "${CYAN}    $ cd $LLM_SERVER_DIR${NC}"
        echo -e "${CYAN}    $ ./start-native.sh${NC}"
        echo ""

        return 1
    fi
}

setup_venv() {
    echo -e "\n${YELLOW}[2/5] Configurando entorno virtual Python...${NC}"

    if [ ! -d "$VENV_DIR" ]; then
        echo -e "${YELLOW}  Creando entorno virtual...${NC}"
        python3 -m venv $VENV_DIR
        echo -e "${GREEN}✓ Entorno virtual creado${NC}"
    else
        echo -e "${GREEN}✓ Entorno virtual ya existe${NC}"
    fi

    # Activar entorno virtual
    source $VENV_DIR/bin/activate

    # Instalar/actualizar dependencias
    echo -e "${YELLOW}  Instalando dependencias...${NC}"
    pip install -q --upgrade pip
    pip install -q -r requirements.txt

    echo -e "${GREEN}✓ Dependencias instaladas${NC}"
}

check_ports() {
    echo -e "\n${YELLOW}[3/5] Verificando puertos...${NC}"

    local api_running=false
    local app_running=false

    # Verificar puerto API
    if check_port $API_PORT; then
        api_running=true
        local api_pid=$(lsof -t -i:$API_PORT 2>/dev/null)
        echo -e "${YELLOW}⚠ Puerto $API_PORT (API) ya está en uso (PID: $api_pid)${NC}"
    else
        echo -e "${GREEN}✓ Puerto $API_PORT (API) disponible${NC}"
    fi

    # Verificar puerto APP
    if check_port $APP_PORT; then
        app_running=true
        local app_pid=$(lsof -t -i:$APP_PORT 2>/dev/null)
        echo -e "${YELLOW}⚠ Puerto $APP_PORT (App) ya está en uso (PID: $app_pid)${NC}"
    else
        echo -e "${GREEN}✓ Puerto $APP_PORT (App) disponible${NC}"
    fi

    # Si hay servicios corriendo, reiniciar automáticamente
    if [ "$api_running" = true ] || [ "$app_running" = true ]; then
        echo ""
        echo -e "${YELLOW}⚠ Servicios detectados, reiniciando automáticamente...${NC}"

        if [ "$api_running" = true ]; then
            kill -9 $(lsof -t -i:$API_PORT) 2>/dev/null || true
            echo -e "${GREEN}✓ Puerto $API_PORT liberado${NC}"
        fi
        if [ "$app_running" = true ]; then
            kill -9 $(lsof -t -i:$APP_PORT) 2>/dev/null || true
            echo -e "${GREEN}✓ Puerto $APP_PORT liberado${NC}"
        fi
        sleep 2

        # No saltamos nada, forzamos reinicio
        SKIP_API=false
        SKIP_APP=false
    fi
}

start_api() {
    echo -e "\n${YELLOW}[4/5] Iniciando API Backend...${NC}"

    # Si ya está corriendo, verificar salud
    if [ "$SKIP_API" = true ]; then
        echo -e "${YELLOW}⚠ API ya está corriendo, verificando...${NC}"

        # Verificar health endpoint
        if curl -s http://localhost:$API_PORT/health >/dev/null 2>&1; then
            echo -e "${GREEN}✓ API está funcionando correctamente${NC}"
            echo -e "${GREEN}  • Endpoint: http://localhost:$API_PORT${NC}"
            echo -e "${GREEN}  • Documentación: http://localhost:$API_PORT/docs${NC}"
            return 0
        else
            echo -e "${RED}✗ API no responde correctamente${NC}"
            echo -e "${YELLOW}  Reiniciando API...${NC}"
            kill -9 $(lsof -t -i:$API_PORT) 2>/dev/null || true
            sleep 2
        fi
    fi

    # Asegurar que directorios existen
    mkdir -p data/uploads data/exports logs

    # Exportar PYTHONPATH
    export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

    # Iniciar API en background
    echo -e "${GREEN}➜ Iniciando API en puerto $API_PORT...${NC}"
    python3 -m uvicorn src.api.main:app --host 0.0.0.0 --port $API_PORT > logs/api.log 2>&1 &
    API_PID=$!
    echo $API_PID > logs/api.pid

    # Esperar a que la API esté lista (max 10 intentos)
    echo -n "  Esperando..."
    for i in {1..10}; do
        sleep 1
        if check_port $API_PORT; then
            echo ""
            echo -e "${GREEN}✓ API iniciada correctamente${NC}"
            echo -e "${GREEN}  • Endpoint: http://localhost:$API_PORT${NC}"
            echo -e "${GREEN}  • Documentación: http://localhost:$API_PORT/docs${NC}"
            return 0
        fi
        echo -n "."
    done

    # Si llegamos aquí, falló
    echo ""
    echo -e "${RED}✗ Error: API no inició correctamente${NC}"
    echo -e "${YELLOW}Últimas líneas del log:${NC}"
    tail -20 logs/api.log
    exit 1
}

start_app() {
    echo -e "\n${YELLOW}[5/5] Iniciando Aplicación Web...${NC}"

    # Si ya está corriendo, verificar salud
    if [ "$SKIP_APP" = true ]; then
        echo -e "${YELLOW}⚠ App ya está corriendo, verificando...${NC}"

        # Verificar health endpoint
        if curl -s http://localhost:$APP_PORT/health >/dev/null 2>&1; then
            echo -e "${GREEN}✓ App está funcionando correctamente${NC}"
            echo -e "${GREEN}  • Endpoint: http://localhost:$APP_PORT${NC}"
            return 0
        else
            echo -e "${RED}✗ App no responde correctamente${NC}"
            echo -e "${YELLOW}  Reiniciando App...${NC}"
            kill -9 $(lsof -t -i:$APP_PORT) 2>/dev/null || true
            sleep 2
        fi
    fi

    # Iniciar App
    echo -e "${GREEN}➜ Iniciando App en puerto $APP_PORT...${NC}"
    python3 -m uvicorn src.app.main:app --host 0.0.0.0 --port $APP_PORT > logs/app.log 2>&1 &
    APP_PID=$!
    echo $APP_PID > logs/app.pid

    # Esperar a que la app esté lista (max 10 intentos)
    echo -n "  Esperando..."
    for i in {1..10}; do
        sleep 1
        if check_port $APP_PORT; then
            echo ""
            echo -e "${GREEN}✓ App iniciada correctamente${NC}"
            echo -e "${GREEN}  • Endpoint: http://localhost:$APP_PORT${NC}"
            return 0
        fi
        echo -n "."
    done

    # Si llegamos aquí, falló
    echo ""
    echo -e "${RED}✗ Error: App no inició correctamente${NC}"
    echo -e "${YELLOW}Últimas líneas del log:${NC}"
    tail -20 logs/app.log

    # Limpiar API si fue iniciada por este script
    if [ -f logs/api.pid ] && [ -z "$SKIP_API" ]; then
        kill $(cat logs/api.pid) 2>/dev/null || true
    fi
    exit 1
}

show_summary() {
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║                 ✓ SISTEMA INICIADO                     ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${CYAN}Servicios activos:${NC}"
    echo ""
    echo -e "  ${GREEN}█${NC} Aplicación Web:"
    echo -e "    ${BLUE}➜  http://localhost:$APP_PORT${NC}"
    echo -e "    Interfaz principal para subir PDFs y ver proyectos"
    echo ""
    echo -e "  ${GREEN}█${NC} API Backend:"
    echo -e "    ${BLUE}➜  http://localhost:$API_PORT${NC}"
    echo -e "    ${BLUE}➜  http://localhost:$API_PORT/docs${NC} (Documentación)"
    echo ""
    if check_port $LLM_PORT; then
        echo -e "  ${GREEN}█${NC} LLM Server:"
        echo -e "    ${BLUE}➜  http://localhost:$LLM_PORT${NC}"
        echo ""
    fi
    echo -e "${YELLOW}Logs:${NC}"
    echo -e "  • API: logs/api.log"
    echo -e "  • App: logs/app.log"
    echo ""
    echo -e "${YELLOW}Para detener:${NC}"
    echo -e "  Presiona ${RED}Ctrl+C${NC} o ejecuta: ${CYAN}./stop.sh${NC}"
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

cleanup() {
    echo ""
    echo -e "${YELLOW}Deteniendo servicios de Mediciones...${NC}"

    if [ -f logs/api.pid ]; then
        API_PID=$(cat logs/api.pid)
        kill $API_PID 2>/dev/null || true
        rm logs/api.pid
        echo -e "${GREEN}✓ API detenida${NC}"
    fi

    if [ -f logs/app.pid ]; then
        APP_PID=$(cat logs/app.pid)
        kill $APP_PID 2>/dev/null || true
        rm logs/app.pid
        echo -e "${GREEN}✓ App detenida${NC}"
    fi

    echo ""
    echo -e "${BLUE}Servicios de Mediciones detenidos${NC}"
    echo -e "${YELLOW}Nota: LLM Server sigue corriendo (no gestionado por este script)${NC}"
    exit 0
}

# Trap Ctrl+C
trap cleanup INT TERM

###############################################################################
# MAIN
###############################################################################

# Verificar LLM Server (permitir continuar si no está corriendo)
check_llm_server || true

# Setup entorno virtual
setup_venv

# Verificar puertos
check_ports

# Iniciar API
start_api

# Iniciar App
start_app

# Mostrar resumen
show_summary

# Mantener script corriendo y mostrar logs
echo -e "${CYAN}Mostrando logs de la aplicación (Ctrl+C para detener):${NC}"
echo ""
tail -f logs/app.log logs/api.log
