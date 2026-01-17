"""
Aplicación Web para MVP Mediciones
Puerto: 3012
Interfaz de usuario para subir PDFs, procesar y exportar mediciones
"""

from fastapi import FastAPI, Request, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import httpx
import logging

# Configuración
API_BASE_URL = "http://localhost:3013"
APP_PORT = 3012

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crear app
app = FastAPI(title="MVP Mediciones - Web App", version="1.0.0")

# Templates
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# Añadir filtro personalizado para formato europeo de números
def european_number(value):
    """Convierte número a formato europeo (1.234,56)"""
    try:
        return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return str(value)

templates.env.filters['european'] = european_number

# Static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Página principal"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/proyectos", response_class=HTMLResponse)
async def lista_proyectos(request: Request):
    """Página de lista de proyectos"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE_URL}/proyectos")
            response.raise_for_status()
            proyectos = response.json()
    except Exception as e:
        logger.error(f"Error al obtener proyectos: {e}")
        proyectos = []

    return templates.TemplateResponse(
        "proyectos.html",
        {"request": request, "proyectos": proyectos}
    )


@app.get("/proyecto/{proyecto_id}", response_class=HTMLResponse)
async def ver_proyecto(request: Request, proyecto_id: int):
    """Página de detalle de proyecto"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE_URL}/proyectos/{proyecto_id}")
            response.raise_for_status()
            proyecto = response.json()
    except Exception as e:
        logger.error(f"Error al obtener proyecto {proyecto_id}: {e}")
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    return templates.TemplateResponse(
        "proyecto_detalle.html",
        {"request": request, "proyecto": proyecto}
    )


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """Subir PDF a la API"""
    try:
        # Leer archivo
        contents = await file.read()

        # Enviar a la API
        async with httpx.AsyncClient(timeout=300.0) as client:
            files = {"file": (file.filename, contents, file.content_type)}
            response = await client.post(f"{API_BASE_URL}/upload", files=files)
            response.raise_for_status()
            result = response.json()

        # Redirigir al proyecto creado
        proyecto_id = result.get("proyecto_id")
        return RedirectResponse(url=f"/proyecto/{proyecto_id}", status_code=303)

    except httpx.HTTPError as e:
        logger.error(f"Error HTTP al subir archivo: {e}")
        raise HTTPException(status_code=500, detail=f"Error al procesar PDF: {str(e)}")
    except Exception as e:
        logger.error(f"Error al subir archivo: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# ============================================================================
# RUTAS LOCALES - SISTEMA DE RESPALDO (Prefijo /local-)
# ============================================================================

@app.get("/local-upload", response_class=HTMLResponse)
async def local_upload_page(request: Request):
    """Página de upload para sistema local"""
    return templates.TemplateResponse("local_index.html", {"request": request})


@app.post("/local-upload")
async def local_upload_pdf(file: UploadFile = File(...)):
    """Subir PDF a la API para procesamiento local"""
    try:
        # Leer archivo
        contents = await file.read()

        # Enviar a la API local
        async with httpx.AsyncClient(timeout=300.0) as client:
            files = {"file": (file.filename, contents, file.content_type)}
            response = await client.post(f"{API_BASE_URL}/local-upload", files=files)
            response.raise_for_status()
            result = response.json()

        # Redirigir al proyecto creado
        proyecto_id = result.get("proyecto_id")
        return RedirectResponse(url=f"/local-proyecto/{proyecto_id}", status_code=303)

    except httpx.HTTPError as e:
        logger.error(f"[LOCAL] Error HTTP al subir archivo: {e}")
        raise HTTPException(status_code=500, detail=f"Error al procesar PDF (local): {str(e)}")
    except Exception as e:
        logger.error(f"[LOCAL] Error al subir archivo: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.get("/local-proyectos", response_class=HTMLResponse)
async def lista_proyectos_locales(request: Request):
    """Página de lista de proyectos locales"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE_URL}/local-proyectos")
            response.raise_for_status()
            proyectos = response.json()
    except Exception as e:
        logger.error(f"[LOCAL] Error al obtener proyectos: {e}")
        proyectos = []

    return templates.TemplateResponse(
        "local_proyectos.html",
        {"request": request, "proyectos": proyectos}
    )


@app.get("/local-proyecto/{proyecto_id}", response_class=HTMLResponse)
async def ver_proyecto_local(request: Request, proyecto_id: int):
    """Página de detalle de proyecto local"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE_URL}/local-proyectos/{proyecto_id}")
            response.raise_for_status()
            proyecto = response.json()
    except Exception as e:
        logger.error(f"[LOCAL] Error al obtener proyecto {proyecto_id}: {e}")
        raise HTTPException(status_code=404, detail="Proyecto local no encontrado")

    return templates.TemplateResponse(
        "local_proyecto_detalle.html",
        {"request": request, "proyecto": proyecto}
    )


# ============================================================================
# RUTAS AI
# ============================================================================

@app.get("/ai-proyectos", response_class=HTMLResponse)
async def lista_ai_proyectos(request: Request):
    """Página de lista de proyectos AI"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE_URL}/ai-proyectos")
            response.raise_for_status()
            proyectos = response.json()
    except Exception as e:
        logger.error(f"Error al obtener proyectos AI: {e}")
        proyectos = []

    return templates.TemplateResponse(
        "ai_proyectos.html",
        {"request": request, "proyectos": proyectos}
    )


@app.get("/ai-proyecto/{proyecto_id}", response_class=HTMLResponse)
async def ver_ai_proyecto(request: Request, proyecto_id: int):
    """Página de detalle de proyecto AI"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE_URL}/ai-proyectos/{proyecto_id}")
            response.raise_for_status()
            proyecto = response.json()
    except Exception as e:
        logger.error(f"Error al obtener proyecto AI {proyecto_id}: {e}")
        raise HTTPException(status_code=404, detail="Proyecto AI no encontrado")

    return templates.TemplateResponse(
        "ai_proyecto_detalle.html",
        {"request": request, "proyecto": proyecto}
    )


@app.get("/ai-upload", response_class=HTMLResponse)
async def ai_upload_page(request: Request):
    """Página de upload AI"""
    return templates.TemplateResponse("ai_upload.html", {"request": request})


@app.post("/ai-upload")
async def ai_upload_pdf(file: UploadFile = File(...)):
    """Subir PDF a la API para procesamiento AI"""
    try:
        # Leer archivo
        contents = await file.read()

        # Enviar a la API AI
        async with httpx.AsyncClient(timeout=660.0) as client:  # 11 minutos (más que la API)
            files = {"file": (file.filename, contents, file.content_type)}
            response = await client.post(f"{API_BASE_URL}/ai-upload", files=files)
            response.raise_for_status()
            result = response.json()

        # Redirigir al proyecto creado
        proyecto_id = result.get("proyecto_id")
        return RedirectResponse(url=f"/ai-proyecto/{proyecto_id}", status_code=303)

    except httpx.HTTPError as e:
        logger.error(f"Error HTTP al subir archivo AI: {e}")
        raise HTTPException(status_code=500, detail=f"Error al procesar PDF con IA: {str(e)}")
    except Exception as e:
        logger.error(f"Error al subir archivo AI: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# ============================================================================
# RUTAS HÍBRIDAS (IA + Local + Validación)
# ============================================================================

@app.get("/hybrid-upload", response_class=HTMLResponse)
async def hybrid_upload_page(request: Request):
    """Página de upload para sistema híbrido"""
    return templates.TemplateResponse("hybrid_upload.html", {"request": request})


@app.post("/hybrid-upload")
async def hybrid_upload_pdf(file: UploadFile = File(...)):
    """Subir PDF a la API (solo guarda el archivo, no procesa)"""
    try:
        # Leer archivo
        contents = await file.read()

        # Enviar a la API híbrida (solo upload, sin procesamiento)
        async with httpx.AsyncClient(timeout=60.0) as client:  # 1 minuto suficiente para upload
            files = {"file": (file.filename, contents, file.content_type)}
            response = await client.post(f"{API_BASE_URL}/hybrid-upload", files=files)
            response.raise_for_status()
            result = response.json()

        # Redirigir al proyecto creado
        proyecto_id = result.get("proyecto_id")
        return RedirectResponse(url=f"/hybrid-proyecto/{proyecto_id}", status_code=303)

    except httpx.HTTPError as e:
        logger.error(f"[HYBRID] Error HTTP al subir archivo: {e}")
        raise HTTPException(status_code=500, detail=f"Error al subir PDF: {str(e)}")
    except Exception as e:
        logger.error(f"[HYBRID] Error al subir archivo: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.get("/hybrid-proyectos", response_class=HTMLResponse)
async def lista_proyectos_hibridos(request: Request):
    """Página de lista de proyectos híbridos"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE_URL}/hybrid-proyectos")
            response.raise_for_status()
            proyectos = response.json()
    except Exception as e:
        logger.error(f"[HYBRID] Error al obtener proyectos: {e}")
        proyectos = []

    return templates.TemplateResponse(
        "hybrid_proyectos.html",
        {"request": request, "proyectos": proyectos}
    )


@app.get("/hybrid-proyecto/{proyecto_id}", response_class=HTMLResponse)
async def ver_proyecto_hibrido(request: Request, proyecto_id: int):
    """Página de detalle de proyecto híbrido"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE_URL}/hybrid-proyectos/{proyecto_id}")
            response.raise_for_status()
            proyecto = response.json()
    except Exception as e:
        logger.error(f"[HYBRID] Error al obtener proyecto {proyecto_id}: {e}")
        raise HTTPException(status_code=404, detail="Proyecto híbrido no encontrado")

    return templates.TemplateResponse(
        "hybrid_proyecto_detalle.html",
        {"request": request, "proyecto": proyecto}
    )


@app.get("/health")
async def health():
    """Health check de la app"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE_URL}/health")
            api_status = response.status_code == 200
    except:
        api_status = False

    return {
        "app": "ok",
        "api": "ok" if api_status else "error",
        "api_url": API_BASE_URL
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=APP_PORT)
