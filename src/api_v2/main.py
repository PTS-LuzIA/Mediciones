"""
FastAPI Main Application - API REST V2
======================================

API REST production-ready con:
- Autenticación JWT
- Rate limiting
- CORS
- Validación Pydantic
- Upload seguro
- Logging
- Documentación automática (Swagger)

"""

import os
import logging
from pathlib import Path
from datetime import timedelta
from typing import List

from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    BackgroundTasks,
    Request
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .config import settings
from .security import (
    authenticate_user,
    create_access_token,
    get_current_user,
    Token
)
from .schemas import (
    LoginRequest,
    TokenResponse,
    ProyectoListItem,
    ProyectoResponse,
    ProyectoStats,
    UploadResponse,
    ValidacionProyectoResponse,
    MessageResponse,
    ErrorResponse
)

# Configurar logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(settings.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Crear aplicación FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API REST para procesamiento de presupuestos de construcción",
    docs_url="/api/docs" if settings.DEBUG else None,  # Desactivar docs en producción
    redoc_url="/api/redoc" if settings.DEBUG else None
)

# Configurar rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configurar CORS - IMPORTANTE: Debe estar antes de otros middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],  # Permitir todos los métodos
    allow_headers=["*"],  # Permitir todos los headers
    expose_headers=["*"]  # Exponer todos los headers
)

# Exception handler global que mantiene CORS
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Maneja excepciones globales manteniendo headers CORS"""
    logger.error(f"Error no manejado: {exc}", exc_info=True)

    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": "true",
        }
    )

# Crear directorio de uploads si no existe
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)


# ============================================
# Endpoints Públicos
# ============================================

@app.get("/", tags=["Health"])
@limiter.limit("10/minute")
async def root(request: Request):
    """Health check"""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "healthy"
    }


@app.post("/api/auth/login", response_model=TokenResponse, tags=["Auth"])
@limiter.limit("5/minute")
async def login(request: Request, credentials: LoginRequest):
    """
    Autenticación de usuario

    Returns:
        Token JWT y datos del usuario
    """
    logger.info(f"Intento de login: {credentials.username}")

    user = authenticate_user(credentials.username, credentials.password)

    if not user:
        logger.warning(f"Login fallido: {credentials.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Crear token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"], "user_id": user["user_id"]},
        expires_delta=access_token_expires
    )

    logger.info(f"Login exitoso: {credentials.username}")

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user={
            "username": user["username"],
            "user_id": user["user_id"]
        }
    )


# ============================================
# Endpoints Protegidos (requieren autenticación)
# ============================================

@app.get("/api/proyectos", response_model=List[ProyectoListItem], tags=["Proyectos"])
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def listar_proyectos(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Lista todos los proyectos (sin detalles completos)

    Requiere autenticación.
    """
    from models_v2.db_manager_v2 import DatabaseManagerV2

    logger.info(f"Usuario {current_user['username']} solicitó lista de proyectos")

    try:
        with DatabaseManagerV2() as db:
            proyectos = db.listar_proyectos()

            # Convertir a schema
            result = [
                ProyectoListItem(
                    id=p.id,
                    nombre=p.nombre,
                    fecha_creacion=p.fecha_creacion,
                    presupuesto_total=p.presupuesto_total,
                    layout_detectado=p.layout_detectado,
                    tiene_mediciones_auxiliares=p.tiene_mediciones_auxiliares or False,
                    num_capitulos=len(p.capitulos)
                )
                for p in proyectos
            ]

            return result

    except Exception as e:
        logger.error(f"Error listando proyectos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al listar proyectos"
        )


@app.get("/api/proyectos/{proyecto_id}", response_model=ProyectoResponse, tags=["Proyectos"])
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def obtener_proyecto(
    request: Request,
    proyecto_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Obtiene un proyecto completo con toda su jerarquía

    Requiere autenticación.
    """
    from models_v2.db_manager_v2 import DatabaseManagerV2

    logger.info(f"Usuario {current_user['username']} solicitó proyecto {proyecto_id}")

    try:
        with DatabaseManagerV2() as db:
            proyecto = db.obtener_proyecto(proyecto_id)

            if not proyecto:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Proyecto {proyecto_id} no encontrado"
                )

            return proyecto

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo proyecto {proyecto_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener proyecto"
        )


@app.get("/api/proyectos/{proyecto_id}/stats", response_model=ProyectoStats, tags=["Proyectos"])
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def obtener_estadisticas(
    request: Request,
    proyecto_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Obtiene estadísticas de un proyecto

    Requiere autenticación.
    """
    from models_v2.db_manager_v2 import DatabaseManagerV2

    try:
        with DatabaseManagerV2() as db:
            proyecto = db.obtener_proyecto(proyecto_id)

            if not proyecto:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Proyecto {proyecto_id} no encontrado"
                )

            # Calcular estadísticas
            total_subcaps = sum(len(cap.subcapitulos) for cap in proyecto.capitulos)
            total_partidas = sum(
                len(sub.partidas)
                for cap in proyecto.capitulos
                for sub in cap.subcapitulos
            )
            partidas_con_med = sum(
                1 for cap in proyecto.capitulos
                for sub in cap.subcapitulos
                for part in sub.partidas
                if part.tiene_mediciones
            )

            return ProyectoStats(
                total_capitulos=len(proyecto.capitulos),
                total_subcapitulos=total_subcaps,
                total_partidas=total_partidas,
                partidas_con_mediciones=partidas_con_med,
                presupuesto_total=proyecto.presupuesto_total
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo stats proyecto {proyecto_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener estadísticas"
        )


@app.post("/api/proyectos/upload", response_model=UploadResponse, tags=["Proyectos"])
@limiter.limit("10/minute")  # Límite más restrictivo para uploads
async def upload_pdf(
    request: Request,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Upload de PDF (SOLO guarda, NO procesa)

    Validaciones:
    - Tipo de archivo (.pdf)
    - Tamaño máximo (50MB)

    Requiere autenticación.
    """
    from models_v2.db_manager_v2 import DatabaseManagerV2
    from parser_v2.pdf_extractor import PDFExtractor

    logger.info(f"Usuario {current_user['username']} subió PDF: {file.filename}")

    # Validar extensión
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de archivo no permitido. Solo: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )

    # Leer archivo
    contents = await file.read()
    file_size = len(contents)

    # Validar tamaño
    if file_size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Archivo demasiado grande. Máximo: {settings.MAX_UPLOAD_SIZE / 1024 / 1024:.0f}MB"
        )

    # Guardar archivo
    upload_path = Path(settings.UPLOAD_DIR) / f"{current_user['user_id']}_{file.filename}"

    try:
        with open(upload_path, "wb") as f:
            f.write(contents)

        # Extraer SOLO el nombre del proyecto del PDF (primera línea o título)
        try:
            pdf_extractor = PDFExtractor(str(upload_path))
            datos_pdf = pdf_extractor.extraer_todo()
            lineas = datos_pdf['all_lines']

            # Buscar nombre en primeras 10 líneas
            nombre_proyecto = file.filename.replace('.pdf', '')
            for linea in lineas[:10]:
                linea_limpia = linea.strip()
                # Si es una línea larga con palabras (no solo números/códigos)
                if len(linea_limpia) > 20 and not linea_limpia.startswith('CAPÍTULO'):
                    nombre_proyecto = linea_limpia[:100]  # Máximo 100 caracteres
                    break
        except:
            nombre_proyecto = file.filename.replace('.pdf', '')

        # Crear proyecto en BD (sin estructura, solo metadata)
        with DatabaseManagerV2() as db:
            proyecto = db.crear_proyecto_vacio(
                nombre=nombre_proyecto,
                pdf_path=str(upload_path),
                filename=file.filename
            )

        logger.info(f"PDF guardado. Proyecto ID: {proyecto.id} - Listo para procesar por fases")

        return UploadResponse(
            success=True,
            message="PDF guardado correctamente. Procesa por fases en la página de edición.",
            proyecto_id=proyecto.id,
            filename=file.filename,
            size_bytes=file_size,
            procesamiento={
                'total_capitulos': 0,
                'total_subcapitulos': 0,
                'total_partidas': 0,
                'presupuesto_total': 0.0,
                'estado': 'pendiente_procesamiento'
            }
        )

    except Exception as e:
        logger.error(f"Error guardando PDF: {e}")

        # Limpiar archivo si hubo error
        if upload_path.exists():
            os.remove(upload_path)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error guardando PDF: {str(e)}"
        )


@app.get("/api/proyectos/{proyecto_id}/validar", response_model=ValidacionProyectoResponse, tags=["Validación"])
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def validar_mediciones(
    request: Request,
    proyecto_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Valida las mediciones parciales de un proyecto

    Requiere autenticación.
    """
    from models_v2.db_manager_v2 import DatabaseManagerV2

    logger.info(f"Usuario {current_user['username']} validó proyecto {proyecto_id}")

    try:
        with DatabaseManagerV2() as db:
            resultado = db.validar_mediciones_proyecto(proyecto_id)

            if 'error' in resultado:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=resultado['error']
                )

            return ValidacionProyectoResponse(**resultado)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validando proyecto {proyecto_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al validar mediciones"
        )


# ============================================
# Endpoints de Procesamiento por Fases
# ============================================

@app.post("/api/proyectos/{proyecto_id}/fase1", tags=["Procesamiento"])
@limiter.limit("10/minute")
async def ejecutar_fase1(
    request: Request,
    proyecto_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    FASE 1: Extrae estructura jerárquica (capítulos/subcapítulos) y GUARDA EN BD
    """
    from models_v2.db_manager_v2 import DatabaseManagerV2
    from parser_v2.partida_parser_v2_4fases import PartidaParserV2_4Fases

    logger.info(f"Usuario {current_user['username']} ejecuta FASE 1 en proyecto {proyecto_id}")

    try:
        with DatabaseManagerV2() as db:
            proyecto = db.obtener_proyecto(proyecto_id)
            if not proyecto:
                raise HTTPException(404, "Proyecto no encontrado")

            pdf_path = proyecto.pdf_path
            if not pdf_path or not Path(pdf_path).exists():
                raise HTTPException(400, "PDF no encontrado")

            # Ejecutar SOLO Fase 1
            parser = PartidaParserV2_4Fases(pdf_path, current_user['user_id'], proyecto_id)
            parser.ejecutar_fase1()

            # GUARDAR EN BD - Fase 1
            estructura = parser.fase1_resultado.get('estructura', {})
            metadata = {
                'layout_detectado': parser.fase1_resultado.get('layout_info', {}).get('total_columnas', 1),
                'pdf_nombre': Path(pdf_path).name
            }

            # Formatear layout_detectado como string descriptivo
            num_cols = metadata['layout_detectado']
            metadata['layout_detectado'] = f"{num_cols} Columna{'s' if num_cols > 1 else ''}"

            db.actualizar_fase1(proyecto_id, estructura, metadata)

            logger.info(f"✓ Fase 1 guardada en BD para proyecto {proyecto_id}")

            return {
                "success": True,
                "fase": 1,
                "resultado": parser.fase1_resultado,
                "mensaje": "Fase 1 completada y guardada en BD: Estructura extraída"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en Fase 1: {e}", exc_info=True)
        raise HTTPException(500, f"Error en Fase 1: {str(e)}")


@app.post("/api/proyectos/{proyecto_id}/fase2", tags=["Procesamiento"])
@limiter.limit("10/minute")
async def ejecutar_fase2(
    request: Request,
    proyecto_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    FASE 2: Clasifica líneas y extrae partidas y GUARDA EN BD
    """
    from models_v2.db_manager_v2 import DatabaseManagerV2
    from parser_v2.partida_parser_v2_4fases import PartidaParserV2_4Fases

    logger.info(f"Usuario {current_user['username']} ejecuta FASE 2 en proyecto {proyecto_id}")

    try:
        with DatabaseManagerV2() as db:
            proyecto = db.obtener_proyecto(proyecto_id)
            if not proyecto:
                raise HTTPException(404, "Proyecto no encontrado")

            pdf_path = proyecto.pdf_path
            if not pdf_path or not Path(pdf_path).exists():
                raise HTTPException(400, "PDF no encontrado")

            # Ejecutar Fase 1 + 2
            parser = PartidaParserV2_4Fases(pdf_path, current_user['user_id'], proyecto_id)
            parser.ejecutar_fase1()
            parser.ejecutar_fase2()

            # GUARDAR EN BD - Fase 2 (partidas)
            estructura_completa = parser.fase2_resultado.get('estructura_completa', {})
            db.actualizar_fase2(proyecto_id, estructura_completa)

            logger.info(f"✓ Fase 2 guardada en BD para proyecto {proyecto_id}")

            return {
                "success": True,
                "fase": 2,
                "resultado": parser.fase2_resultado,
                "mensaje": f"Fase 2 completada y guardada en BD: {parser.fase2_resultado['num_partidas']} partidas extraídas"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en Fase 2: {e}", exc_info=True)
        raise HTTPException(500, f"Error en Fase 2: {str(e)}")


@app.post("/api/proyectos/{proyecto_id}/fase3", tags=["Procesamiento"])
@limiter.limit("10/minute")
async def ejecutar_fase3(
    request: Request,
    proyecto_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    FASE 3: Merge totales, validación y RECALCULA EN BD
    """
    from models_v2.db_manager_v2 import DatabaseManagerV2
    from parser_v2.partida_parser_v2_4fases import PartidaParserV2_4Fases

    logger.info(f"Usuario {current_user['username']} ejecuta FASE 3 en proyecto {proyecto_id}")

    try:
        with DatabaseManagerV2() as db:
            proyecto = db.obtener_proyecto(proyecto_id)
            if not proyecto:
                raise HTTPException(404, "Proyecto no encontrado")

            pdf_path = proyecto.pdf_path
            if not pdf_path or not Path(pdf_path).exists():
                raise HTTPException(400, "PDF no encontrado")

            # Ejecutar Fase 1 + 2 + 3
            parser = PartidaParserV2_4Fases(pdf_path, current_user['user_id'], proyecto_id)
            parser.ejecutar_fase1()
            parser.ejecutar_fase2()
            parser.ejecutar_fase3()

            # GUARDAR EN BD - Fase 3 (calcular totales y detectar discrepancias)
            validacion = parser.fase3_resultado
            resultado_fase3 = db.actualizar_fase3(proyecto_id, validacion)

            discrepancias = resultado_fase3.get('discrepancias', [])
            logger.info(f"✓ Fase 3 guardada en BD para proyecto {proyecto_id}")
            logger.info(f"  {len(discrepancias)} discrepancias detectadas")

            return {
                "success": True,
                "fase": 3,
                "resultado": parser.fase3_resultado,
                "discrepancias": discrepancias,
                "total_original": resultado_fase3.get('total_original', 0),
                "total_calculado": resultado_fase3.get('total_calculado', 0),
                "num_discrepancias": len(discrepancias),
                "mensaje": f"Fase 3 completada: {len(discrepancias)} discrepancias detectadas"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en Fase 3: {e}", exc_info=True)
        raise HTTPException(500, f"Error en Fase 3: {str(e)}")


@app.post("/api/proyectos/{proyecto_id}/fase4", tags=["Procesamiento"])
@limiter.limit("10/minute")
async def ejecutar_fase4(
    request: Request,
    proyecto_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    FASE 4: Completa descripciones (si es necesario) y verifica BD

    Nota: Las fases 1-3 ya guardaron todo en BD, esta fase solo verifica
    y completa descripciones si hace falta.
    """
    from models_v2.db_manager_v2 import DatabaseManagerV2
    from parser_v2.partida_parser_v2_4fases import PartidaParserV2_4Fases

    logger.info(f"Usuario {current_user['username']} ejecuta FASE 4 en proyecto {proyecto_id}")

    try:
        with DatabaseManagerV2() as db:
            proyecto = db.obtener_proyecto(proyecto_id)
            if not proyecto:
                raise HTTPException(404, "Proyecto no encontrado")

            pdf_path = proyecto.pdf_path
            if not pdf_path or not Path(pdf_path).exists():
                raise HTTPException(400, "PDF no encontrado")

            # Ejecutar TODAS las fases
            parser = PartidaParserV2_4Fases(pdf_path, current_user['user_id'], proyecto_id)
            resultado = parser.parsear()  # Ejecuta las 4 fases

            # Fase 4: Completar descripciones si es necesario
            # (Ya tenemos los datos en BD de fases 1-3, aquí solo completamos)

            logger.info(f"✓ Fase 4 completada para proyecto {proyecto_id}")

            # Obtener proyecto actualizado para retornar stats
            proyecto_actualizado = db.obtener_proyecto(proyecto_id)

            return {
                "success": True,
                "fase": 4,
                "resultado": {
                    'total_capitulos': len(proyecto_actualizado.capitulos),
                    'total_subcapitulos': sum(len(cap.subcapitulos) for cap in proyecto_actualizado.capitulos),
                    'total_partidas': sum(
                        len(sub.partidas)
                        for cap in proyecto_actualizado.capitulos
                        for sub in cap.subcapitulos
                    ),
                    'presupuesto_total': float(proyecto_actualizado.presupuesto_total)
                },
                "mensaje": "Fase 4 completada: Procesamiento finalizado"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en Fase 4: {e}", exc_info=True)
        raise HTTPException(500, f"Error en Fase 4: {str(e)}")


@app.post("/api/proyectos/{proyecto_id}/resolver-discrepancia", tags=["Procesamiento"])
@limiter.limit("10/minute")  # Reducido porque usa IA
async def resolver_discrepancia_individual(
    request: Request,
    proyecto_id: int,
    tipo: str,
    elemento_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Resuelve una discrepancia individual usando IA

    La IA analiza el PDF y encuentra partidas faltantes que explican la diferencia.
    IMPORTANTE: El total del PDF (Fase 1) es SIEMPRE correcto.

    Args:
        tipo: "capitulo" o "subcapitulo"
        elemento_id: ID del elemento con discrepancia
    """
    from models_v2.db_manager_v2 import DatabaseManagerV2

    logger.info(f"Usuario {current_user['username']} resuelve discrepancia {tipo} {elemento_id} con IA")

    try:
        with DatabaseManagerV2() as db:
            # Obtener proyecto y PDF
            proyecto = db.obtener_proyecto(proyecto_id)
            if not proyecto:
                raise HTTPException(404, "Proyecto no encontrado")

            pdf_path = proyecto.pdf_path
            if not pdf_path or not Path(pdf_path).exists():
                raise HTTPException(400, "PDF no encontrado")

            # Resolver discrepancia con IA
            resultado = await db.resolver_discrepancia_con_ia(
                proyecto_id, tipo, elemento_id, pdf_path
            )

            if not resultado['success']:
                raise HTTPException(500, resultado.get('error', 'Error al resolver discrepancia'))

            return {
                "success": True,
                "mensaje": f"✓ {resultado['partidas_agregadas']} partidas agregadas por IA",
                "partidas_agregadas": resultado['partidas_agregadas'],
                "total_agregado": resultado['total_agregado'],
                "partidas": resultado['partidas']
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al resolver discrepancia: {e}", exc_info=True)
        raise HTTPException(500, f"Error al resolver discrepancia: {str(e)}")


@app.post("/api/proyectos/{proyecto_id}/resolver-discrepancias-bulk", tags=["Procesamiento"])
@limiter.limit("5/minute")  # Muy limitado porque es intensivo en IA
async def resolver_discrepancias_bulk(
    request: Request,
    proyecto_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Resuelve TODAS las discrepancias de un proyecto usando IA

    Itera sobre todas las discrepancias y usa IA para encontrar partidas faltantes.
    IMPORTANTE: El total del PDF (Fase 1) es SIEMPRE correcto.
    Este proceso puede tardar varios minutos dependiendo del número de discrepancias.
    """
    from models_v2.db_manager_v2 import DatabaseManagerV2

    logger.info(f"Usuario {current_user['username']} resuelve TODAS las discrepancias con IA (proyecto {proyecto_id})")

    try:
        with DatabaseManagerV2() as db:
            # Obtener proyecto y PDF
            proyecto = db.obtener_proyecto(proyecto_id)
            if not proyecto:
                raise HTTPException(404, "Proyecto no encontrado")

            pdf_path = proyecto.pdf_path
            if not pdf_path or not Path(pdf_path).exists():
                raise HTTPException(400, "PDF no encontrado")

            # Resolver todas las discrepancias con IA
            resultado = await db.resolver_discrepancias_bulk_con_ia(proyecto_id, pdf_path)

            if not resultado['success']:
                raise HTTPException(500, resultado.get('error', 'Error al resolver discrepancias'))

            # Construir mensaje informativo
            mensaje = f"✓ {resultado['resueltas_exitosas']} discrepancias resueltas ({resultado['total_partidas_agregadas']} partidas agregadas)"
            if resultado.get('omitidas_sin_partidas', 0) > 0:
                mensaje += f", {resultado['omitidas_sin_partidas']} omitidas (sin partidas directas)"

            return {
                "success": True,
                "mensaje": mensaje,
                "resueltas_exitosas": resultado['resueltas_exitosas'],
                "resueltas_fallidas": resultado['resueltas_fallidas'],
                "omitidas_sin_partidas": resultado.get('omitidas_sin_partidas', 0),
                "total_partidas_agregadas": resultado['total_partidas_agregadas'],
                "errores": resultado['errores']
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al resolver discrepancias bulk: {e}", exc_info=True)
        raise HTTPException(500, f"Error al resolver discrepancias: {str(e)}")


@app.delete("/api/proyectos/{proyecto_id}", response_model=MessageResponse, tags=["Proyectos"])
@limiter.limit("30/minute")
async def eliminar_proyecto(
    request: Request,
    proyecto_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Elimina un proyecto

    Requiere autenticación.
    """
    from models_v2.db_manager_v2 import DatabaseManagerV2

    logger.warning(f"Usuario {current_user['username']} eliminó proyecto {proyecto_id}")

    try:
        with DatabaseManagerV2() as db:
            proyecto = db.obtener_proyecto(proyecto_id)

            if not proyecto:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Proyecto {proyecto_id} no encontrado"
                )

            # Eliminar (cascade eliminará todo)
            db.session.delete(proyecto)
            db.session.commit()

            return MessageResponse(
                success=True,
                message=f"Proyecto {proyecto_id} eliminado correctamente"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error eliminando proyecto {proyecto_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar proyecto"
        )


# ============================================
# Error Handlers
# ============================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Manejador global de excepciones HTTP"""
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "code": str(exc.status_code)
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
