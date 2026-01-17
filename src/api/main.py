"""
API REST con FastAPI para el sistema de mediciones.
Puerto: 3013
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import logging
import os
import shutil
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Importaciones locales
import sys
# Agregar el directorio src al path
src_path = str(Path(__file__).parent.parent)
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from parser.partida_parser import PartidaParser
from models.db_models import DatabaseManager
from models.ai_db_manager import AIDatabaseManager
from models.ai_models import AIProyecto
from llm.openrouter_client import OpenRouterClient
from llm.structure_extraction_agent import StructureExtractionAgent
from llm.partida_extraction_agent import PartidaExtractionAgent
from exporters.csv_exporter import CSVExporter
from exporters.excel_exporter import ExcelExporter
from exporters.xml_exporter import XMLExporter
from exporters.bc3_exporter import BC3Exporter

# Configuración
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="API Mediciones MVP",
    description="API para extraer y exportar mediciones desde PDFs de construcción",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directorios
UPLOAD_DIR = Path("data/uploads")
EXPORT_DIR = Path("data/exports")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

# Base de datos
db = DatabaseManager()
ai_db = AIDatabaseManager()  # Base de datos para proyectos con IA


# Modelos Pydantic
class ProyectoResponse(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str]
    fecha_creacion: str
    presupuesto_total: float
    num_capitulos: int
    num_partidas: int


class PartidaResponse(BaseModel):
    codigo: str
    unidad: str
    resumen: str
    descripcion: Optional[str]
    cantidad: float
    precio: float
    importe: float
    capitulo: Optional[str]
    subcapitulo: Optional[str]
    apartado: Optional[str]


class EstadisticasResponse(BaseModel):
    lineas_totales: int
    capitulos: int
    subcapitulos: int
    apartados: int
    partidas: int
    partidas_validas: int
    errores: List[dict]


# Endpoints

@app.get("/")
async def root():
    """Endpoint raíz"""
    return {
        "mensaje": "API Mediciones MVP",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "upload": "/upload",
            "proyectos": "/proyectos",
            "exportar": "/exportar/{proyecto_id}/{formato}"
        }
    }


@app.get("/health")
async def health_check():
    """Check de salud de la API"""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "database": "connected" if db.session else "disconnected"
    }


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """
    Sube y procesa un PDF de mediciones

    Returns:
        Estructura completa extraída + estadísticas
    """
    try:
        # Validar extensión
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Solo se permiten archivos PDF")

        # Guardar archivo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{file.filename}"
        file_path = UPLOAD_DIR / filename

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        logger.info(f"Archivo guardado: {file_path}")

        # Parsear PDF
        parser = PartidaParser(str(file_path))
        resultado = parser.parsear()

        # Guardar en base de datos
        proyecto = db.guardar_estructura(resultado['estructura'])
        db.calcular_totales(proyecto.id)

        logger.info(f"Proyecto creado con ID: {proyecto.id}")

        return {
            "success": True,
            "mensaje": "PDF procesado correctamente",
            "proyecto_id": proyecto.id,
            "archivo": filename,
            "estadisticas": resultado['estadisticas'],
            "estructura": resultado['estructura']
        }

    except Exception as e:
        logger.error(f"Error procesando PDF: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/proyectos")
async def listar_proyectos():
    """Lista todos los proyectos"""
    try:
        proyectos = db.listar_proyectos()

        return [
            {
                "id": p.id,
                "nombre": p.nombre,
                "descripcion": p.descripcion,
                "fecha_creacion": p.fecha_creacion.isoformat() if p.fecha_creacion else None,
                "presupuesto_total": p.presupuesto_total,
                "num_capitulos": len(p.capitulos),
                "num_partidas": sum(len(s.partidas) for c in p.capitulos for s in c.subcapitulos) +
                               sum(len(apt.partidas) for c in p.capitulos for s in c.subcapitulos for apt in s.apartados)
            }
            for p in proyectos
        ]

    except Exception as e:
        logger.error(f"Error listando proyectos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/proyectos/{proyecto_id}")
async def obtener_proyecto(proyecto_id: int):
    """Obtiene un proyecto por ID con estructura completa"""
    try:
        proyecto = db.obtener_proyecto(proyecto_id)

        if not proyecto:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        # Función recursiva para construir subcapítulos con toda su jerarquía
        def construir_subcapitulos_recursivo(subcapitulos):
            """Construye subcapítulos recursivamente incluyendo partidas y apartados"""
            resultado = []
            for subcapitulo in subcapitulos:
                # Partidas del subcapítulo
                partidas_sub = [
                    {
                        "codigo": p.codigo,
                        "unidad": p.unidad,
                        "resumen": p.resumen,
                        "descripcion": p.descripcion,
                        "cantidad": p.cantidad,
                        "precio": p.precio,
                        "importe": p.importe
                    }
                    for p in subcapitulo.partidas
                ]

                # Apartados del subcapítulo
                apartados = []
                for apt in subcapitulo.apartados:
                    partidas_apt = [
                        {
                            "codigo": p.codigo,
                            "unidad": p.unidad,
                            "resumen": p.resumen,
                            "descripcion": p.descripcion,
                            "cantidad": p.cantidad,
                            "precio": p.precio,
                            "importe": p.importe
                        }
                        for p in apt.partidas
                    ]
                    apartados.append({
                        "codigo": apt.codigo,
                        "nombre": apt.nombre,
                        "total": apt.total,
                        "partidas": partidas_apt
                    })

                sub_dict = {
                    "id": subcapitulo.id,
                    "codigo": subcapitulo.codigo,
                    "nombre": subcapitulo.nombre,
                    "total": subcapitulo.total,
                    "parent_id": subcapitulo.parent_id,
                    "partidas": partidas_sub,
                    "apartados": apartados,
                    # ✓ Recursión: incluir subcapítulos hijos
                    "subcapitulos_hijos": construir_subcapitulos_recursivo(subcapitulo.subcapitulos_hijos) if subcapitulo.subcapitulos_hijos else []
                }

                resultado.append(sub_dict)
            return resultado

        # Construir jerarquía completa
        capitulos_completos = []
        for cap in proyecto.capitulos:
            # ✓ Filtrar solo subcapítulos de nivel 1 (sin parent_id)
            subcapitulos_nivel1 = [s for s in cap.subcapitulos if s.parent_id is None]

            cap_dict = {
                "id": cap.id,
                "codigo": cap.codigo,
                "nombre": cap.nombre,
                "total": cap.total,
                # ✓ Construir árbol recursivo desde nivel 1
                "subcapitulos": construir_subcapitulos_recursivo(subcapitulos_nivel1)
            }

            capitulos_completos.append(cap_dict)

        return {
            "id": proyecto.id,
            "nombre": proyecto.nombre,
            "descripcion": proyecto.descripcion,
            "archivo_origen": proyecto.archivo_origen,
            "fecha_creacion": proyecto.fecha_creacion.isoformat() if proyecto.fecha_creacion else None,
            "presupuesto_total": proyecto.presupuesto_total,
            "capitulos": capitulos_completos,
            "estadisticas": {
                "capitulos": len(proyecto.capitulos),
                "subcapitulos": sum(len(c.subcapitulos) for c in proyecto.capitulos),
                "apartados": sum(len(s.apartados) for c in proyecto.capitulos for s in c.subcapitulos),
                "partidas": sum(len(s.partidas) for c in proyecto.capitulos for s in c.subcapitulos) +
                           sum(len(apt.partidas) for c in proyecto.capitulos for s in c.subcapitulos for apt in s.apartados)
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo proyecto: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/exportar/{proyecto_id}/{formato}")
async def exportar_proyecto(proyecto_id: int, formato: str):
    """
    Exporta un proyecto en el formato especificado

    Formatos: csv, excel, xml, bc3
    """
    try:
        # Obtener proyecto
        proyecto = db.obtener_proyecto(proyecto_id)
        if not proyecto:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        # Construir estructura para exportadores
        estructura = {
            'nombre': proyecto.nombre,
            'descripcion': proyecto.descripcion,
            'archivo_origen': proyecto.archivo_origen,
            'capitulos': []
        }

        for capitulo in proyecto.capitulos:
            cap_dict = {
                'codigo': capitulo.codigo,
                'nombre': capitulo.nombre,
                'subcapitulos': []
            }

            for subcapitulo in capitulo.subcapitulos:
                sub_dict = {
                    'codigo': subcapitulo.codigo,
                    'nombre': subcapitulo.nombre,
                    'apartados': [],
                    'partidas': []
                }

                # Partidas directas
                for partida in subcapitulo.partidas:
                    sub_dict['partidas'].append({
                        'codigo': partida.codigo,
                        'unidad': partida.unidad,
                        'resumen': partida.resumen,
                        'descripcion': partida.descripcion,
                        'cantidad': partida.cantidad,
                        'precio': partida.precio,
                        'importe': partida.importe
                    })

                # Apartados
                for apartado in subcapitulo.apartados:
                    apt_dict = {
                        'codigo': apartado.codigo,
                        'nombre': apartado.nombre,
                        'partidas': []
                    }

                    for partida in apartado.partidas:
                        apt_dict['partidas'].append({
                            'codigo': partida.codigo,
                            'unidad': partida.unidad,
                            'resumen': partida.resumen,
                            'descripcion': partida.descripcion,
                            'cantidad': partida.cantidad,
                            'precio': partida.precio,
                            'importe': partida.importe
                        })

                    sub_dict['apartados'].append(apt_dict)

                cap_dict['subcapitulos'].append(sub_dict)

            estructura['capitulos'].append(cap_dict)

        # Obtener todas las partidas planas (para CSV y Excel)
        partidas = []
        for cap in estructura['capitulos']:
            for sub in cap['subcapitulos']:
                for partida in sub['partidas']:
                    partidas.append({
                        **partida,
                        'capitulo': cap['codigo'],
                        'subcapitulo': sub['codigo'],
                        'apartado': None
                    })
                for apt in sub['apartados']:
                    for partida in apt['partidas']:
                        partidas.append({
                            **partida,
                            'capitulo': cap['codigo'],
                            'subcapitulo': sub['codigo'],
                            'apartado': apt['codigo']
                        })

        # Exportar según formato
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"proyecto_{proyecto_id}_{timestamp}"

        if formato.lower() == 'csv':
            output_path = EXPORT_DIR / f"{filename}.csv"
            CSVExporter.exportar(partidas, str(output_path))

        elif formato.lower() == 'excel':
            output_path = EXPORT_DIR / f"{filename}.xlsx"
            ExcelExporter.exportar(partidas, str(output_path))

        elif formato.lower() == 'xml':
            output_path = EXPORT_DIR / f"{filename}.xml"
            XMLExporter.exportar(estructura, str(output_path))

        elif formato.lower() == 'bc3':
            output_path = EXPORT_DIR / f"{filename}.bc3"
            BC3Exporter.exportar(estructura, str(output_path))

        else:
            raise HTTPException(status_code=400, detail=f"Formato no soportado: {formato}")

        logger.info(f"Exportado: {output_path}")

        # Retornar archivo
        return FileResponse(
            path=str(output_path),
            filename=output_path.name,
            media_type='application/octet-stream'
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exportando: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/proyectos/{proyecto_id}")
async def eliminar_proyecto(proyecto_id: int):
    """Elimina un proyecto"""
    try:
        proyecto = db.obtener_proyecto(proyecto_id)
        if not proyecto:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        db.session.delete(proyecto)
        db.session.commit()

        return {"success": True, "mensaje": f"Proyecto {proyecto_id} eliminado"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error eliminando proyecto: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINTS LOCALES - SISTEMA DE RESPALDO (Prefijo /local-)
# ============================================================================
# Estos endpoints preservan la funcionalidad del sistema local original
# antes de la implementación del sistema híbrido

@app.post("/local-upload")
async def local_upload_pdf(file: UploadFile = File(...)):
    """
    [BACKUP LOCAL] Sube y procesa un PDF de mediciones usando el sistema local

    Returns:
        Estructura completa extraída + estadísticas
    """
    try:
        # Validar extensión
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Solo se permiten archivos PDF")

        # Guardar archivo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"local_{timestamp}_{file.filename}"
        file_path = UPLOAD_DIR / filename

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        logger.info(f"[LOCAL] Archivo guardado: {file_path}")

        # Parsear PDF
        parser = PartidaParser(str(file_path))
        resultado = parser.parsear()

        # Guardar en base de datos
        proyecto = db.guardar_estructura(resultado['estructura'])
        db.calcular_totales(proyecto.id)

        logger.info(f"[LOCAL] Proyecto creado con ID: {proyecto.id}")

        return {
            "success": True,
            "mensaje": "PDF procesado correctamente (sistema local)",
            "proyecto_id": proyecto.id,
            "archivo": filename,
            "estadisticas": resultado['estadisticas'],
            "estructura": resultado['estructura']
        }

    except Exception as e:
        logger.error(f"[LOCAL] Error procesando PDF: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/local-proyectos")
async def listar_proyectos_locales():
    """[BACKUP LOCAL] Lista todos los proyectos locales"""
    try:
        proyectos = db.listar_proyectos()

        return [
            {
                "id": p.id,
                "nombre": p.nombre,
                "descripcion": p.descripcion,
                "fecha_creacion": p.fecha_creacion.isoformat() if p.fecha_creacion else None,
                "presupuesto_total": p.presupuesto_total,
                "num_capitulos": len(p.capitulos),
                "num_partidas": sum(len(s.partidas) for c in p.capitulos for s in c.subcapitulos) +
                               sum(len(apt.partidas) for c in p.capitulos for s in c.subcapitulos for apt in s.apartados)
            }
            for p in proyectos
        ]

    except Exception as e:
        logger.error(f"[LOCAL] Error listando proyectos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/local-proyectos/{proyecto_id}")
async def obtener_proyecto_local(proyecto_id: int):
    """[BACKUP LOCAL] Obtiene un proyecto local por ID con estructura completa"""
    try:
        proyecto = db.obtener_proyecto(proyecto_id)

        if not proyecto:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        # Función recursiva para construir subcapítulos con toda su jerarquía
        def construir_subcapitulos_recursivo(subcapitulos):
            """Construye subcapítulos recursivamente incluyendo partidas y apartados"""
            resultado = []
            for subcapitulo in subcapitulos:
                # Partidas del subcapítulo
                partidas_sub = [
                    {
                        "codigo": p.codigo,
                        "unidad": p.unidad,
                        "resumen": p.resumen,
                        "descripcion": p.descripcion,
                        "cantidad": p.cantidad,
                        "precio": p.precio,
                        "importe": p.importe
                    }
                    for p in subcapitulo.partidas
                ]

                # Apartados del subcapítulo
                apartados = []
                for apt in subcapitulo.apartados:
                    partidas_apt = [
                        {
                            "codigo": p.codigo,
                            "unidad": p.unidad,
                            "resumen": p.resumen,
                            "descripcion": p.descripcion,
                            "cantidad": p.cantidad,
                            "precio": p.precio,
                            "importe": p.importe
                        }
                        for p in apt.partidas
                    ]
                    apartados.append({
                        "codigo": apt.codigo,
                        "nombre": apt.nombre,
                        "total": apt.total,
                        "partidas": partidas_apt
                    })

                sub_dict = {
                    "id": subcapitulo.id,
                    "codigo": subcapitulo.codigo,
                    "nombre": subcapitulo.nombre,
                    "total": subcapitulo.total,
                    "parent_id": subcapitulo.parent_id,
                    "partidas": partidas_sub,
                    "apartados": apartados,
                    "subcapitulos_hijos": construir_subcapitulos_recursivo(subcapitulo.subcapitulos_hijos) if subcapitulo.subcapitulos_hijos else []
                }

                resultado.append(sub_dict)
            return resultado

        # Construir jerarquía completa
        capitulos_completos = []
        for cap in proyecto.capitulos:
            subcapitulos_nivel1 = [s for s in cap.subcapitulos if s.parent_id is None]

            cap_dict = {
                "id": cap.id,
                "codigo": cap.codigo,
                "nombre": cap.nombre,
                "total": cap.total,
                "subcapitulos": construir_subcapitulos_recursivo(subcapitulos_nivel1)
            }

            capitulos_completos.append(cap_dict)

        return {
            "id": proyecto.id,
            "nombre": proyecto.nombre,
            "descripcion": proyecto.descripcion,
            "archivo_origen": proyecto.archivo_origen,
            "fecha_creacion": proyecto.fecha_creacion.isoformat() if proyecto.fecha_creacion else None,
            "presupuesto_total": proyecto.presupuesto_total,
            "capitulos": capitulos_completos,
            "estadisticas": {
                "capitulos": len(proyecto.capitulos),
                "subcapitulos": sum(len(c.subcapitulos) for c in proyecto.capitulos),
                "apartados": sum(len(s.apartados) for c in proyecto.capitulos for s in c.subcapitulos),
                "partidas": sum(len(s.partidas) for c in proyecto.capitulos for s in c.subcapitulos) +
                           sum(len(apt.partidas) for c in proyecto.capitulos for s in c.subcapitulos for apt in s.apartados)
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[LOCAL] Error obteniendo proyecto: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/local-proyectos/{proyecto_id}")
async def eliminar_proyecto_local(proyecto_id: int):
    """[BACKUP LOCAL] Elimina un proyecto local"""
    try:
        proyecto = db.obtener_proyecto(proyecto_id)
        if not proyecto:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        db.session.delete(proyecto)
        db.session.commit()

        return {"success": True, "mensaje": f"Proyecto local {proyecto_id} eliminado"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[LOCAL] Error eliminando proyecto: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/local-exportar/{proyecto_id}/{formato}")
async def exportar_proyecto_local(proyecto_id: int, formato: str):
    """
    [BACKUP LOCAL] Exporta un proyecto local en el formato especificado

    Formatos: csv, excel, xml, bc3
    """
    try:
        # Reutilizar la lógica del endpoint normal de exportar
        return await exportar_proyecto(proyecto_id, formato)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[LOCAL] Error exportando: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINTS PARA AI PROJECTS (Procesamiento con LLM)
# ============================================================================

@app.post("/ai-upload-simple")
async def ai_upload_pdf_simple(file: UploadFile = File(...)):
    """
    Sube un PDF y crea un proyecto AI SIN procesarlo.
    El usuario luego ejecutará las Fases 1 y 2 manualmente.

    Returns:
        ID del proyecto creado
    """
    try:
        # Validar extensión
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Solo se permiten archivos PDF")

        # Guardar archivo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ai_{timestamp}_{file.filename}"
        file_path = UPLOAD_DIR / filename

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        logger.info(f"Archivo guardado (sin procesar): {file_path}")

        # Crear proyecto vacío (sin capítulos ni partidas)
        proyecto = AIProyecto(
            nombre=file.filename.replace('.pdf', ''),
            descripcion=f"Proyecto subido el {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            archivo_origen=str(file_path),
            modelo_usado='google/gemini-2.5-flash-lite'
        )
        ai_db.session.add(proyecto)
        ai_db.session.commit()

        logger.info(f"✓ Proyecto AI creado con ID: {proyecto.id} (pendiente de procesamiento)")

        return {
            "success": True,
            "proyecto_id": proyecto.id,
            "nombre": proyecto.nombre,
            "archivo": filename,
            "mensaje": "Proyecto creado. Ahora puedes extraer la estructura desde la página de detalle."
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error subiendo PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Error subiendo PDF: {str(e)}")


@app.post("/ai-upload")
async def ai_upload_pdf(file: UploadFile = File(...)):
    """
    Sube y procesa un PDF usando IA (Gemini 2.5 Flash Lite vía OpenRouter)
    MÉTODO ANTIGUO: Procesa todo de una vez (hasta 20 peticiones)

    Returns:
        Estructura completa extraída + estadísticas + confianzas
    """
    try:
        # Validar extensión
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Solo se permiten archivos PDF")

        # Guardar archivo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ai_{timestamp}_{file.filename}"
        file_path = UPLOAD_DIR / filename

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        logger.info(f"Archivo guardado para procesamiento IA: {file_path}")

        # Procesar con IA (con procesamiento incremental automático - hasta 20 intentos)
        client = OpenRouterClient()
        estructura_ia = await client.procesar_pdf_completo(str(file_path), max_intentos=20)

        # Guardar en base de datos
        proyecto = ai_db.guardar_estructura_ia(estructura_ia)

        logger.info(f"Proyecto IA creado con ID: {proyecto.id}")

        # Preparar respuesta
        return {
            "success": True,
            "proyecto_id": proyecto.id,
            "nombre": proyecto.nombre,
            "presupuesto_total": proyecto.presupuesto_total,
            "confianza_general": proyecto.confianza_general,
            "notas_ia": proyecto.notas_ia,
            "tiempo_procesamiento": proyecto.tiempo_procesamiento,
            "modelo_usado": proyecto.modelo_usado,
            "estadisticas": {
                "capitulos": len(estructura_ia.get('capitulos', [])),
                "total_partidas": sum(
                    len(sub.get('partidas', []))
                    for cap in estructura_ia.get('capitulos', [])
                    for sub in cap.get('subcapitulos', [])
                )
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error procesando PDF con IA: {e}")
        raise HTTPException(status_code=500, detail=f"Error procesando PDF: {str(e)}")


@app.get("/ai-proyectos")
async def listar_ai_proyectos():
    """Lista todos los proyectos procesados con IA"""
    try:
        proyectos = ai_db.listar_proyectos()

        lista = []
        for p in proyectos:
            # Contar partidas totales
            num_partidas = 0
            for cap in p.capitulos:
                for sub in cap.subcapitulos:
                    num_partidas += len(sub.partidas)
                    for apt in sub.apartados:
                        num_partidas += len(apt.partidas)

            lista.append({
                "id": p.id,
                "nombre": p.nombre,
                "descripcion": p.descripcion,
                "fecha_creacion": p.fecha_creacion.isoformat() if p.fecha_creacion else None,
                "presupuesto_total": p.presupuesto_total,
                "confianza_general": p.confianza_general,
                "modelo_usado": p.modelo_usado,
                "tiempo_procesamiento": p.tiempo_procesamiento,
                "num_capitulos": len(p.capitulos),
                "num_partidas": num_partidas
            })

        return lista

    except Exception as e:
        logger.error(f"Error listando proyectos IA: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/ai-proyectos/{proyecto_id}")
async def obtener_ai_proyecto(proyecto_id: int):
    """Obtiene un proyecto IA completo con toda su estructura"""
    try:
        proyecto = ai_db.obtener_proyecto(proyecto_id)

        if not proyecto:
            raise HTTPException(status_code=404, detail=f"Proyecto {proyecto_id} no encontrado")

        # Construir respuesta completa
        resultado = {
            "id": proyecto.id,
            "nombre": proyecto.nombre,
            "descripcion": proyecto.descripcion,
            "fecha_creacion": proyecto.fecha_creacion.isoformat() if proyecto.fecha_creacion else None,
            "presupuesto_total": proyecto.presupuesto_total,
            "confianza_general": proyecto.confianza_general,
            "notas_ia": proyecto.notas_ia,
            "modelo_usado": proyecto.modelo_usado,
            "tiempo_procesamiento": proyecto.tiempo_procesamiento,
            "capitulos": []
        }

        # Función recursiva para construir subcapítulos con toda su jerarquía
        def construir_subcapitulos_con_datos(subcapitulos):
            """Construye subcapítulos recursivamente incluyendo partidas y apartados"""
            resultado = []
            for subcapitulo in subcapitulos:
                sub_dict = {
                    "id": subcapitulo.id,
                    "codigo": subcapitulo.codigo,
                    "nombre": subcapitulo.nombre,
                    "total": subcapitulo.total,
                    "confianza": subcapitulo.confianza,
                    "notas": subcapitulo.notas,
                    "partidas": [
                        {
                            "id": p.id,
                            "codigo": p.codigo,
                            "unidad": p.unidad,
                            "resumen": p.resumen,
                            "descripcion": p.descripcion,
                            "cantidad": p.cantidad,
                            "precio": p.precio,
                            "importe": p.importe,
                            "confianza": p.confianza,
                            "notas": p.notas
                        }
                        for p in subcapitulo.partidas
                    ],
                    "apartados": [],
                    # ✓ Recursión: incluir subcapítulos hijos
                    "subcapitulos": construir_subcapitulos_con_datos(subcapitulo.subcapitulos) if subcapitulo.subcapitulos else []
                }

                # Agregar apartados
                for apartado in subcapitulo.apartados:
                    apt_dict = {
                        "id": apartado.id,
                        "codigo": apartado.codigo,
                        "nombre": apartado.nombre,
                        "total": apartado.total,
                        "confianza": apartado.confianza,
                        "notas": apartado.notas,
                        "partidas": [
                            {
                                "id": p.id,
                                "codigo": p.codigo,
                                "unidad": p.unidad,
                                "resumen": p.resumen,
                                "descripcion": p.descripcion,
                                "cantidad": p.cantidad,
                                "precio": p.precio,
                                "importe": p.importe,
                                "confianza": p.confianza,
                                "notas": p.notas
                            }
                            for p in apartado.partidas
                        ]
                    }
                    sub_dict["apartados"].append(apt_dict)

                resultado.append(sub_dict)
            return resultado

        # Construir jerarquía completa
        for capitulo in proyecto.capitulos:
            # ✓ Filtrar solo subcapítulos de nivel 1 (sin parent_id)
            subcapitulos_nivel1 = [s for s in capitulo.subcapitulos if s.parent_id is None]

            cap_dict = {
                "id": capitulo.id,
                "codigo": capitulo.codigo,
                "nombre": capitulo.nombre,
                "total": capitulo.total,
                "confianza": capitulo.confianza,
                "notas": capitulo.notas,
                # ✓ Construir árbol recursivo desde nivel 1
                "subcapitulos": construir_subcapitulos_con_datos(subcapitulos_nivel1)
            }

            resultado["capitulos"].append(cap_dict)

        return resultado

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo proyecto IA {proyecto_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/ai-proyectos/{proyecto_id}")
async def eliminar_ai_proyecto(proyecto_id: int):
    """Elimina un proyecto IA y todos sus datos relacionados"""
    try:
        success = ai_db.eliminar_proyecto(proyecto_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"Proyecto {proyecto_id} no encontrado")

        return {"success": True, "mensaje": f"Proyecto AI {proyecto_id} eliminado"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error eliminando proyecto IA: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# FASE 1: EXTRACCIÓN DE ESTRUCTURA (Capítulos y Subcapítulos)
# ============================================================================

@app.post("/api/extract-structure/{proyecto_id}")
async def extract_structure(proyecto_id: int):
    """
    FASE 1: Extrae la estructura jerárquica (capítulos/subcapítulos) de un proyecto

    Args:
        proyecto_id: ID del proyecto AI

    Returns:
        Estructura jerárquica con totales + validación
    """
    try:
        # Obtener proyecto
        proyecto = ai_db.obtener_proyecto(proyecto_id)
        if not proyecto:
            raise HTTPException(status_code=404, detail=f"Proyecto {proyecto_id} no encontrado")

        # Verificar que tenga archivo origen
        if not proyecto.archivo_origen:
            raise HTTPException(status_code=400, detail="Proyecto no tiene archivo PDF asociado")

        archivo_path = proyecto.archivo_origen
        if not os.path.exists(archivo_path):
            raise HTTPException(status_code=404, detail=f"Archivo PDF no encontrado: {archivo_path}")

        logger.info(f"Extrayendo estructura del proyecto {proyecto_id}")

        # Extraer estructura con el agente especializado
        agent = StructureExtractionAgent()
        estructura = await agent.extraer_estructura(archivo_path)

        # Guardar estructura en base de datos
        ai_db.guardar_solo_estructura(proyecto_id, estructura)

        # Validar totales
        validacion = agent.validar_totales(estructura)

        logger.info(f"✓ Estructura extraída: {len(estructura.get('capitulos', []))} capítulos")

        return {
            "success": True,
            "proyecto_id": proyecto_id,
            "estructura": estructura,
            "validacion": validacion,
            "tiempo_procesamiento": estructura.get('tiempo_procesamiento', 0)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extrayendo estructura: {e}")
        raise HTTPException(status_code=500, detail=f"Error extrayendo estructura: {str(e)}")


# ============================================================================
# FASE 2: EXTRACCIÓN DE PARTIDAS (Por Capítulos)
# ============================================================================

@app.post("/api/extract-partidas/{proyecto_id}")
async def extract_partidas_por_capitulos(proyecto_id: int):
    """
    FASE 2: Extrae partidas por capítulos con validación y re-intentos automáticos

    Procesa cada capítulo de forma independiente para:
    - Mejor manejo de errores (un capítulo fallido no bloquea los demás)
    - Validación de totales por capítulo
    - Re-intentos selectivos de capítulos con error
    - Progreso granular

    Args:
        proyecto_id: ID del proyecto AI

    Returns:
        Estado completo del proceso con detalle por capítulo
    """
    try:
        # Obtener proyecto con su estructura
        proyecto = ai_db.obtener_proyecto(proyecto_id)
        if not proyecto:
            raise HTTPException(status_code=404, detail=f"Proyecto {proyecto_id} no encontrado")

        # Verificar que tenga estructura
        if not proyecto.capitulos:
            raise HTTPException(
                status_code=400,
                detail="El proyecto no tiene estructura. Ejecuta primero la Fase 1 (Extracción de Estructura)"
            )

        # Verificar archivo PDF
        archivo_path = proyecto.archivo_origen
        if not archivo_path or not os.path.exists(archivo_path):
            raise HTTPException(status_code=404, detail=f"Archivo PDF no encontrado: {archivo_path}")

        logger.info(f"Iniciando extracción de partidas para proyecto {proyecto_id}")

        # 🧪 MODO PRUEBA: Limitar a solo el primer capítulo
        capitulos_a_procesar = proyecto.capitulos[:1]
        logger.info(f"🧪 MODO PRUEBA: Procesando solo el primer capítulo de {len(proyecto.capitulos)} totales")
        logger.info(f"Capítulos a procesar: {len(capitulos_a_procesar)}")

        # Estado de progreso
        estado = {
            "proyecto_id": proyecto_id,
            "estado": "processing",
            "timestamp": datetime.now().isoformat(),
            "capitulos": []
        }

        # Crear agente de extracción
        agent = PartidaExtractionAgent()

        # Procesar cada capítulo
        for idx, capitulo in enumerate(capitulos_a_procesar):
            logger.info(f"Procesando capítulo {idx+1}/{len(capitulos_a_procesar)}: {capitulo.codigo} - {capitulo.nombre}")

            # Preparar datos del capítulo para el agente
            capitulo_data = {
                "codigo": capitulo.codigo,
                "nombre": capitulo.nombre,
                "total": capitulo.total,
                "subcapitulos": construir_subcapitulos_dict(capitulo.subcapitulos)
            }

            # 🔢 Obtener subcapítulos hoja y procesar de 1 en 1
            subcapitulos_hoja = obtener_subcapitulos_hoja_planos(capitulo.subcapitulos)

            # 🧪 MODO PRUEBA: Limitar a solo 10 subcapítulos para testing
            MODO_PRUEBA = True  # Cambiar a False para procesar todos
            LIMITE_PRUEBA = 10
            if MODO_PRUEBA and len(subcapitulos_hoja) > LIMITE_PRUEBA:
                logger.warning(f"🧪 MODO PRUEBA: Limitando de {len(subcapitulos_hoja)} a {LIMITE_PRUEBA} subcapítulos")
                subcapitulos_hoja = subcapitulos_hoja[:LIMITE_PRUEBA]

            total_subcapitulos = len(subcapitulos_hoja)
            LOTE_SIZE = 1  # OBLIGATORIO: El modelo se comporta impredeciblemente con múltiples subcaps (repite 30x, extrae otros subcaps)

            logger.info(f"📊 Capítulo {capitulo.codigo} tiene {total_subcapitulos} subcapítulos hoja")
            total_lotes = (total_subcapitulos + LOTE_SIZE - 1) // LOTE_SIZE
            logger.info(f"🔢 Se procesarán de {LOTE_SIZE} en {LOTE_SIZE} (total: {total_lotes} peticiones)")

            # Acumular todas las partidas del capítulo
            todas_partidas = []
            total_extraido_cap = 0
            lotes_exitosos = 0
            lotes_error = []

            # Procesar en lotes
            for lote_idx in range(0, total_subcapitulos, LOTE_SIZE):
                lote_subcaps = subcapitulos_hoja[lote_idx:lote_idx + LOTE_SIZE]
                lote_num = (lote_idx // LOTE_SIZE) + 1

                if len(lote_subcaps) == 1:
                    logger.info(f"  📄 Lote {lote_num}/{total_lotes}: Subcapítulo {lote_subcaps[0]}")
                else:
                    logger.info(f"  📦 Lote {lote_num}/{total_lotes}: Subcapítulos {', '.join(lote_subcaps)}")

                # Extraer partidas del lote
                resultado = await agent.extraer_partidas_capitulo(archivo_path, capitulo_data, lote_subcaps)

                if resultado["success"]:
                    todas_partidas.extend(resultado["partidas"])
                    total_extraido_cap += resultado.get("total_extraido", 0)
                    lotes_exitosos += 1
                    logger.info(f"    ✓ {resultado.get('num_partidas', 0)} partidas extraídas ({resultado.get('total_extraido', 0):.2f} €)")
                else:
                    lotes_error.append({
                        "lote": lote_num,
                        "subcapitulos": lote_subcaps,
                        "error": resultado.get("error")
                    })
                    logger.error(f"    ❌ Error: {resultado.get('error')}")

            # Estado del capítulo completo
            estado_capitulo = {
                "codigo": capitulo.codigo,
                "nombre": capitulo.nombre,
                "estado": "completed" if not lotes_error else ("partial" if lotes_exitosos > 0 else "error"),
                "partidas_extraidas": len(todas_partidas),
                "total_esperado": capitulo.total,
                "total_extraido": total_extraido_cap,
                "tiempo_procesamiento": 0,  # Suma de todos los lotes
                "intentos": 1,
                "lotes_procesados": f"{lotes_exitosos}/{total_lotes}",
                "lotes_error": lotes_error if lotes_error else None,
                "error": None if not lotes_error else f"{len(lotes_error)} lotes con error"
            }

            # Guardar todas las partidas del capítulo
            if todas_partidas:
                # Validar totales
                validacion = agent.validar_totales(capitulo.total, total_extraido_cap)
                estado_capitulo["validacion"] = validacion

                # Guardar partidas en BD
                resultado_guardado = ai_db.guardar_partidas_capitulo(
                    proyecto_id,
                    capitulo.codigo,
                    todas_partidas
                )

                if not resultado_guardado["success"]:
                    estado_capitulo["estado"] = "error"
                    estado_capitulo["error"] = resultado_guardado.get("error", "Error guardando partidas")
                else:
                    logger.info(f"✓ Capítulo {capitulo.codigo}: {len(todas_partidas)} partidas guardadas ({lotes_exitosos}/{total_lotes} lotes)")

            estado["capitulos"].append(estado_capitulo)

        # TODO: Re-intentos por lote (implementar si es necesario)
        # Con el nuevo sistema de lotes, los reintentos se manejarían a nivel de lote individual
        # Por ahora, si un lote falla, queda registrado en lotes_error

        # Determinar estado final
        todos_ok = all(c["estado"] == "completed" for c in estado["capitulos"])
        parcial = any(c["estado"] == "completed" for c in estado["capitulos"])

        if todos_ok:
            estado["estado"] = "completed"
            # Recalcular totales finales
            ai_db.calcular_totales(proyecto_id)
            logger.info(f"✓ Extracción de partidas COMPLETADA para proyecto {proyecto_id}")
        elif parcial:
            estado["estado"] = "partial"
            logger.warning(f"⚠️ Extracción PARCIAL para proyecto {proyecto_id}")
        else:
            estado["estado"] = "error"
            logger.error(f"❌ Extracción FALLIDA para proyecto {proyecto_id}")

        # Estadísticas finales
        total_partidas = sum(c.get("partidas_extraidas", 0) for c in estado["capitulos"])
        capitulos_ok = sum(1 for c in estado["capitulos"] if c["estado"] == "completed")

        estado["resumen"] = {
            "total_partidas": total_partidas,
            "capitulos_procesados": capitulos_ok,
            "capitulos_totales": len(proyecto.capitulos),
            "capitulos_error": len([c for c in estado["capitulos"] if c["estado"] == "error"])
        }

        return estado

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extrayendo partidas: {e}")
        raise HTTPException(status_code=500, detail=f"Error extrayendo partidas: {str(e)}")


def obtener_subcapitulos_hoja_planos(subcapitulos):
    """
    Obtiene una lista plana de códigos de subcapítulos hoja (sin hijos)

    Args:
        subcapitulos: Lista de subcapítulos (ORM objects)

    Returns:
        Lista de códigos de subcapítulos hoja
    """
    hojas = []

    def recorrer(subs):
        for sub in subs:
            if sub.subcapitulos:
                # Tiene hijos, seguir buscando
                recorrer(sub.subcapitulos)
            else:
                # Es hoja
                hojas.append(sub.codigo)

    recorrer(subcapitulos)
    return hojas


def construir_subcapitulos_dict(subcapitulos):
    """Helper para construir dict de subcapítulos recursivamente"""
    resultado = []
    for sub in subcapitulos:
        if not sub.parent_id:  # Solo nivel 1
            sub_dict = {
                "codigo": sub.codigo,
                "nombre": sub.nombre,
                "total": sub.total,
                "subcapitulos": construir_subcapitulos_hijos(sub)
            }
            resultado.append(sub_dict)
    return resultado


def construir_subcapitulos_hijos(subcapitulo):
    """Helper recursivo para construir hijos"""
    if not subcapitulo.subcapitulos:
        return []

    resultado = []
    for hijo in subcapitulo.subcapitulos:
        hijo_dict = {
            "codigo": hijo.codigo,
            "nombre": hijo.nombre,
            "total": hijo.total,
            "subcapitulos": construir_subcapitulos_hijos(hijo)
        }
        resultado.append(hijo_dict)
    return resultado


@app.get("/api/structure/{proyecto_id}")
async def get_structure(proyecto_id: int):
    """
    Obtiene la estructura jerárquica guardada de un proyecto

    Args:
        proyecto_id: ID del proyecto AI

    Returns:
        Estructura jerárquica del proyecto
    """
    try:
        proyecto = ai_db.obtener_proyecto(proyecto_id)
        if not proyecto:
            raise HTTPException(status_code=404, detail=f"Proyecto {proyecto_id} no encontrado")

        # Construir estructura desde la base de datos
        estructura = {
            "nombre": proyecto.nombre,
            "descripcion": proyecto.descripcion,
            "capitulos": []
        }

        def construir_subcapitulos_recursivo(subcapitulos):
            """
            Construye subcapítulos recursivamente respetando la jerarquía.

            Args:
                subcapitulos: Lista de subcapítulos (ORM objects)

            Returns:
                Lista de diccionarios con subcapítulos y sus hijos anidados
            """
            resultado = []
            for sub in subcapitulos:
                sub_dict = {
                    "id": sub.id,
                    "codigo": sub.codigo,
                    "nombre": sub.nombre,
                    "total": sub.total,
                    "confianza": sub.confianza,
                    "notas": sub.notas,
                    "orden": sub.orden,
                    # ✓ Recursión: procesar subcapítulos hijos si existen
                    "subcapitulos": construir_subcapitulos_recursivo(sub.subcapitulos) if sub.subcapitulos else []
                }
                resultado.append(sub_dict)
            return resultado

        for capitulo in sorted(proyecto.capitulos, key=lambda c: c.orden):
            # ✓ Filtrar solo subcapítulos de nivel 1 (sin parent_id)
            subcapitulos_nivel1 = [s for s in capitulo.subcapitulos if s.parent_id is None]

            cap_dict = {
                "id": capitulo.id,
                "codigo": capitulo.codigo,
                "nombre": capitulo.nombre,
                "total": capitulo.total,
                "confianza": capitulo.confianza,
                "notas": capitulo.notas,
                "orden": capitulo.orden,
                # ✓ Solo pasar subcapítulos de nivel 1, la recursión se encarga del resto
                "subcapitulos": construir_subcapitulos_recursivo(
                    sorted(subcapitulos_nivel1, key=lambda s: s.orden)
                )
            }
            estructura["capitulos"].append(cap_dict)

        return {
            "success": True,
            "estructura": estructura,
            "tiene_estructura": len(estructura["capitulos"]) > 0
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo estructura: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINTS HÍBRIDOS (IA + Local + Validación)
# ============================================================================

from models.hybrid_db_manager import HybridDatabaseManager
from models.hybrid_models import HybridCapitulo, HybridSubcapitulo, HybridPartida
from llm.hybrid_orchestrator import HybridOrchestrator

# Inicializar gestor híbrido
hybrid_db = HybridDatabaseManager()
hybrid_orchestrator = HybridOrchestrator(hybrid_db)


@app.post("/hybrid-upload")
async def hybrid_upload_pdf(file: UploadFile = File(...)):
    """
    [HÍBRIDO] Sube un PDF y crea un proyecto híbrido vacío (sin procesar)

    El usuario podrá elegir qué fases procesar desde la página del proyecto.

    Returns:
        proyecto_id para redirigir a la página de procesamiento
    """
    try:
        # Validar extensión
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Solo se permiten archivos PDF")

        # Guardar archivo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"hybrid_{timestamp}_{file.filename}"
        file_path = UPLOAD_DIR / filename

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        logger.info(f"[HÍBRIDO] Archivo guardado: {file_path}")

        # Crear proyecto vacío (sin procesar)
        nombre_proyecto = file.filename.replace('.pdf', '')
        proyecto = hybrid_db.crear_proyecto(
            nombre=nombre_proyecto,
            descripcion=f"Proyecto híbrido - {filename}",
            archivo_origen=str(file_path)
        )

        logger.info(f"[HÍBRIDO] ✓ Proyecto {proyecto.id} creado (sin procesar)")

        return {
            "success": True,
            "mensaje": "PDF subido correctamente. Ahora puedes elegir qué fases procesar.",
            "proyecto_id": proyecto.id,
            "archivo": filename,
            "fase_actual": proyecto.fase_actual.value
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[HÍBRIDO] Error subiendo PDF: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/hybrid-proyectos")
async def listar_proyectos_hibridos():
    """[HÍBRIDO] Lista todos los proyectos híbridos"""
    try:
        proyectos = hybrid_db.listar_proyectos()

        lista = []
        for p in proyectos:
            # Contar partidas y subcapítulos
            num_partidas = 0
            num_subcapitulos = 0
            num_validados = 0
            num_discrepancias = 0

            for cap in p.capitulos:
                for sub in cap.subcapitulos:
                    num_subcapitulos += 1
                    num_partidas += len(sub.partidas)
                    for apt in sub.apartados:
                        num_partidas += len(apt.partidas)

                    # Contar estados de validación
                    from models.hybrid_models import EstadoValidacion
                    if sub.estado_validacion == EstadoValidacion.VALIDADO:
                        num_validados += 1
                    elif sub.estado_validacion == EstadoValidacion.DISCREPANCIA:
                        num_discrepancias += 1

            lista.append({
                "id": p.id,
                "nombre": p.nombre,
                "descripcion": p.descripcion,
                "fecha_creacion": p.fecha_creacion.isoformat() if p.fecha_creacion else None,
                "fase_actual": p.fase_actual.value,
                "presupuesto_total": p.total_estructura_ia,
                "total_estructura_ia": p.total_estructura_ia,
                "total_partidas_local": p.total_partidas_local,
                "porcentaje_coincidencia": p.porcentaje_coincidencia,
                "num_capitulos": len(p.capitulos),
                "num_subcapitulos": num_subcapitulos,
                "num_partidas": num_partidas,
                "num_validados": num_validados,
                "num_discrepancias": num_discrepancias
            })

        return lista

    except Exception as e:
        logger.error(f"[HÍBRIDO] Error listando proyectos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/hybrid-proyectos/{proyecto_id}")
async def obtener_proyecto_hibrido(proyecto_id: int):
    """[HÍBRIDO] Obtiene un proyecto híbrido completo con validación"""
    try:
        proyecto = hybrid_db.obtener_proyecto(proyecto_id)

        if not proyecto:
            raise HTTPException(status_code=404, detail=f"Proyecto híbrido {proyecto_id} no encontrado")

        from models.hybrid_models import EstadoValidacion

        # Función recursiva para construir subcapítulos con datos de validación
        def construir_subcapitulos_con_validacion(subcapitulos):
            """Construye subcapítulos recursivamente incluyendo validación"""
            resultado = []
            for subcapitulo in subcapitulos:
                sub_dict = {
                    "id": subcapitulo.id,
                    "codigo": subcapitulo.codigo,
                    "nombre": subcapitulo.nombre,
                    "total_ia": subcapitulo.total_ia,
                    "total_local": subcapitulo.total_local,
                    "total_final": subcapitulo.total_final,
                    "estado_validacion": subcapitulo.estado_validacion.value,
                    "diferencia_euros": subcapitulo.diferencia_euros,
                    "diferencia_porcentaje": subcapitulo.diferencia_porcentaje,
                    "necesita_revision_ia": bool(subcapitulo.necesita_revision_ia),
                    "confianza_ia": subcapitulo.confianza_ia,
                    "partidas": [
                        {
                            "id": p.id,
                            "codigo": p.codigo,
                            "unidad": p.unidad,
                            "resumen": p.resumen,
                            "descripcion": p.descripcion,
                            "cantidad": p.cantidad,
                            "precio": p.precio,
                            "importe": p.importe,
                            "origen": p.extraido_por
                        }
                        for p in subcapitulo.partidas
                    ],
                    "apartados": [
                        {
                            "id": apt.id,
                            "codigo": apt.codigo,
                            "nombre": apt.nombre,
                            "total": apt.total,
                            "partidas": [
                                {
                                    "id": p.id,
                                    "codigo": p.codigo,
                                    "unidad": p.unidad,
                                    "resumen": p.resumen,
                                    "descripcion": p.descripcion,
                                    "cantidad": p.cantidad,
                                    "precio": p.precio,
                                    "importe": p.importe,
                                    "origen": p.extraido_por
                                }
                                for p in apt.partidas
                            ]
                        }
                        for apt in subcapitulo.apartados
                    ],
                    "subcapitulos_hijos": construir_subcapitulos_con_validacion(subcapitulo.subcapitulos_hijos) if subcapitulo.subcapitulos_hijos else []
                }

                resultado.append(sub_dict)
            return resultado

        # Construir respuesta completa
        capitulos_completos = []
        for cap in proyecto.capitulos:
            subcapitulos_nivel1 = [s for s in cap.subcapitulos if s.parent_id is None]

            cap_dict = {
                "id": cap.id,
                "codigo": cap.codigo,
                "nombre": cap.nombre,
                "total_ia": cap.total_ia,
                "total_local": cap.total_local,
                "total_final": cap.total_final,
                "estado_validacion": cap.estado_validacion.value,
                "diferencia_euros": cap.diferencia_euros,
                "diferencia_porcentaje": cap.diferencia_porcentaje,
                "necesita_revision_ia": bool(cap.necesita_revision_ia) if hasattr(cap, 'necesita_revision_ia') else False,
                "partidas": [
                    {
                        "id": p.id,
                        "codigo": p.codigo,
                        "unidad": p.unidad,
                        "resumen": p.resumen,
                        "descripcion": p.descripcion,
                        "cantidad": p.cantidad,
                        "precio": p.precio,
                        "importe": p.importe,
                        "origen": p.extraido_por
                    }
                    for p in cap.partidas
                ] if cap.partidas else [],
                "subcapitulos": construir_subcapitulos_con_validacion(subcapitulos_nivel1)
            }

            capitulos_completos.append(cap_dict)

        # Calcular totales y diferencias
        total_ia = proyecto.total_estructura_ia or 0.0
        total_local = proyecto.total_partidas_local or 0.0
        diferencia_euros = total_ia - total_local
        diferencia_porcentaje = (diferencia_euros / total_ia * 100) if total_ia > 0 else 0.0

        return {
            "id": proyecto.id,
            "nombre": proyecto.nombre,
            "descripcion": proyecto.descripcion,
            "archivo_origen": proyecto.archivo_origen,
            "fecha_creacion": proyecto.fecha_creacion.isoformat() if proyecto.fecha_creacion else None,
            "fase_actual": proyecto.fase_actual.value,
            "fase": proyecto.fase_actual.value,  # Alias para compatibilidad con templates
            "total_estructura_ia": total_ia,
            "total_partidas_local": total_local,
            "total_ia": total_ia,  # Alias para template
            "total_local": total_local,  # Alias para template
            "total_final": total_local if total_local > 0 else total_ia,  # Preferir local si existe
            "diferencia_euros": diferencia_euros,
            "diferencia_porcentaje": diferencia_porcentaje,
            "porcentaje_coincidencia": proyecto.porcentaje_coincidencia,
            "modelo_usado": proyecto.modelo_usado,
            "tiempo_fase1": proyecto.tiempo_fase1,
            "tiempo_fase2": proyecto.tiempo_fase2,
            "tiempo_fase3": proyecto.tiempo_fase3,
            "tiempo_total": (proyecto.tiempo_fase1 or 0) + (proyecto.tiempo_fase2 or 0) + (proyecto.tiempo_fase3 or 0),
            "tiempos": {
                "fase1": proyecto.tiempo_fase1,
                "fase2": proyecto.tiempo_fase2,
                "fase3": proyecto.tiempo_fase3
            },
            "estadisticas": {
                "validados": proyecto.subcapitulos_validados or 0,
                "discrepancias": proyecto.subcapitulos_con_discrepancia or 0,
                "errores": 0,  # Podrías agregar un campo en el modelo
                "porcentaje_coincidencia": proyecto.porcentaje_coincidencia or 0.0
            },
            "estadisticas_validacion": {
                "subcapitulos_validados": proyecto.subcapitulos_validados,
                "subcapitulos_con_discrepancia": proyecto.subcapitulos_con_discrepancia,
                "subcapitulos_revisados_ia": proyecto.subcapitulos_revisados_ia
            },
            "capitulos": capitulos_completos
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[HÍBRIDO] Error obteniendo proyecto {proyecto_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINTS PARA EJECUTAR FASES INDIVIDUALES
# ============================================================================

@app.post("/hybrid-fase1a/{proyecto_id}")
async def ejecutar_fase1a_solo_estructura(proyecto_id: int):
    """
    [HÍBRIDO] Ejecuta solo la Fase 1A: Extracción de estructura (sin conteo)

    Extrae capítulos, subcapítulos y totales usando StructureExtractionAgent.
    NO ejecuta el conteo de partidas (eso es Fase 1B).
    """
    import time
    try:
        # Obtener proyecto
        proyecto = hybrid_db.obtener_proyecto(proyecto_id)
        if not proyecto:
            raise HTTPException(status_code=404, detail=f"Proyecto {proyecto_id} no encontrado")

        # Eliminar estructura anterior si existe
        if proyecto.capitulos:
            logger.info(f"[FASE 1A] Eliminando estructura anterior de proyecto {proyecto_id}")
            for capitulo in list(proyecto.capitulos):
                hybrid_db.session.delete(capitulo)
            hybrid_db.session.commit()

        # Ejecutar Fase 1A - Solo estructura
        logger.info(f"[FASE 1A] Extrayendo estructura con IA para proyecto {proyecto_id}")
        inicio = time.time()

        from llm.structure_extraction_agent import StructureExtractionAgent
        agent = StructureExtractionAgent()
        estructura_ia = await agent.extraer_estructura(proyecto.archivo_origen)

        tiempo = time.time() - inicio

        if not estructura_ia.get('capitulos'):
            raise Exception("No se pudo extraer estructura con IA")

        # Inicializar num_partidas a 0 (se llenará en Fase 1B)
        def init_num_partidas(items):
            for item in items:
                if 'num_partidas' not in item:
                    item['num_partidas'] = 0
                if item.get('subcapitulos'):
                    init_num_partidas(item['subcapitulos'])

        init_num_partidas(estructura_ia['capitulos'])

        # Guardar en BD
        success = hybrid_db.guardar_estructura_fase1(proyecto_id, estructura_ia, tiempo)

        if not success:
            raise Exception("Error guardando estructura en BD")

        logger.info(f"[FASE 1A] ✓ Completada - {len(estructura_ia['capitulos'])} capítulos")

        return {
            "success": True,
            "mensaje": "Fase 1A completada: Estructura extraída (sin conteo)",
            "capitulos_extraidos": len(estructura_ia['capitulos']),
            "tiempo": tiempo
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[FASE 1A] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/hybrid-fase1aa/{proyecto_id}")
async def ejecutar_fase1aa_estructura_local(proyecto_id: int):
    """
    [HÍBRIDO] Ejecuta Fase 1AA: Extracción de estructura con PARSER LOCAL (sin IA)

    Extrae capítulos, subcapítulos y totales usando LocalStructureExtractor.
    Es más rápido, determinista y no requiere costos de IA.
    """
    import time
    try:
        # Obtener proyecto
        proyecto = hybrid_db.obtener_proyecto(proyecto_id)
        if not proyecto:
            raise HTTPException(status_code=404, detail=f"Proyecto {proyecto_id} no encontrado")

        # Eliminar estructura anterior si existe
        if proyecto.capitulos:
            logger.info(f"[FASE 1AA] Eliminando estructura anterior de proyecto {proyecto_id}")
            for capitulo in list(proyecto.capitulos):
                hybrid_db.session.delete(capitulo)
            hybrid_db.session.commit()

        # Ejecutar Fase 1AA - Estructura LOCAL
        logger.info(f"[FASE 1AA] Extrayendo estructura con PARSER LOCAL para proyecto {proyecto_id}")
        inicio = time.time()

        from parser.local_structure_extractor import LocalStructureExtractor
        extractor = LocalStructureExtractor(proyecto.archivo_origen)
        estructura_local = extractor.extraer_estructura()

        tiempo = time.time() - inicio

        if not estructura_local.get('capitulos'):
            raise Exception("No se pudo extraer estructura con parser local")

        # Guardar estructura en BD
        success = hybrid_db.guardar_estructura_fase1(
            proyecto.id,
            estructura_local,
            tiempo
        )

        if not success:
            raise Exception("Error guardando estructura en BD")

        # Contar subcapítulos
        def contar_subcaps_recursivo(cap_dict):
            count = len(cap_dict.get('subcapitulos', []))
            for sub in cap_dict.get('subcapitulos', []):
                count += contar_subcaps_recursivo(sub)
            return count

        total_subcaps = sum(contar_subcaps_recursivo(cap) for cap in estructura_local['capitulos'])

        logger.info(f"[FASE 1AA] ✓ Completada - {len(estructura_local['capitulos'])} capítulos, {total_subcaps} subcapítulos")

        return {
            "success": True,
            "mensaje": "Fase 1AA completada: Estructura extraída con parser local (sin IA)",
            "capitulos_extraidos": len(estructura_local['capitulos']),
            "subcapitulos_extraidos": total_subcaps,
            "metodo": "LOCAL (determinista, sin IA)",
            "tiempo": tiempo
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[FASE 1AA] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/hybrid-fase1b/{proyecto_id}")
async def ejecutar_fase1b_solo_conteo(proyecto_id: int):
    """
    [HÍBRIDO] Ejecuta solo la Fase 1B: Conteo de partidas

    Cuenta el número de partidas usando PartidaCountAgent.
    Requiere que la Fase 1A esté completada.
    """
    import time
    try:
        # Obtener proyecto
        proyecto = hybrid_db.obtener_proyecto(proyecto_id)
        if not proyecto:
            raise HTTPException(status_code=404, detail=f"Proyecto {proyecto_id} no encontrado")

        # Verificar que existe estructura
        if not proyecto.capitulos:
            raise HTTPException(
                status_code=400,
                detail="No hay estructura. Ejecuta primero Fase 1A."
            )

        # Reconstruir estructura JSON desde BD
        def construir_estructura(caps):
            resultado = []
            for cap in caps:
                cap_dict = {
                    "codigo": cap.codigo,
                    "nombre": cap.nombre,
                    "total": cap.total_ia or 0.0,
                    "subcapitulos": []
                }

                def agregar_subcaps(subcaps_bd):
                    res = []
                    for sub in subcaps_bd:
                        sub_dict = {
                            "codigo": sub.codigo,
                            "nombre": sub.nombre,
                            "total": sub.total_ia or 0.0,
                            "subcapitulos": agregar_subcaps(sub.subcapitulos_hijos) if sub.subcapitulos_hijos else []
                        }
                        res.append(sub_dict)
                    return res

                cap_dict["subcapitulos"] = agregar_subcaps([s for s in cap.subcapitulos if not s.parent_id])
                resultado.append(cap_dict)
            return resultado

        estructura_bd = {
            "nombre": proyecto.nombre,
            "capitulos": construir_estructura(proyecto.capitulos)
        }

        # Ejecutar conteo
        logger.info(f"[FASE 1B] Contando partidas para proyecto {proyecto_id}")
        inicio = time.time()

        from llm.partida_count_agent import PartidaCountAgent
        count_agent = PartidaCountAgent()
        conteo = await count_agent.contar_partidas(proyecto.archivo_origen, estructura_bd)
        estructura_con_conteo = count_agent.fusionar_conteo_con_estructura(estructura_bd, conteo)

        tiempo = time.time() - inicio

        # Actualizar num_partidas_ia en BD
        def actualizar_conteos(caps_bd, caps_json):
            for cap_bd in caps_bd:
                cap_json = next((c for c in caps_json if c['codigo'] == cap_bd.codigo), None)
                if cap_json:
                    cap_bd.num_partidas_ia = cap_json.get('num_partidas', 0)

                    def actualizar_subcaps(subcaps_bd, subcaps_json):
                        for sub_bd in subcaps_bd:
                            sub_json = next((s for s in subcaps_json if s['codigo'] == sub_bd.codigo), None)
                            if sub_json:
                                sub_bd.num_partidas_ia = sub_json.get('num_partidas', 0)
                                if sub_bd.subcapitulos_hijos and sub_json.get('subcapitulos'):
                                    actualizar_subcaps(sub_bd.subcapitulos_hijos, sub_json['subcapitulos'])

                    if cap_bd.subcapitulos and cap_json.get('subcapitulos'):
                        actualizar_subcaps([s for s in cap_bd.subcapitulos if not s.parent_id], cap_json['subcapitulos'])

        actualizar_conteos(proyecto.capitulos, estructura_con_conteo['capitulos'])
        hybrid_db.session.commit()

        total_partidas = count_agent._contar_partidas_total(estructura_con_conteo.get('capitulos', []))
        logger.info(f"[FASE 1B] ✓ Completada - {total_partidas} partidas contadas")

        return {
            "success": True,
            "mensaje": "Fase 1B completada: Partidas contadas",
            "total_partidas_contadas": total_partidas,
            "tiempo": tiempo
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[FASE 1B] Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/hybrid-fase1/{proyecto_id}")
async def ejecutar_fase1_estructura(
    proyecto_id: int,
    metodo: str = Query(default="local", description="Método de extracción: 'local' o 'ia'")
):
    """
    [HÍBRIDO] Ejecuta Fase 1: Extracción de Estructura

    Args:
        proyecto_id: ID del proyecto
        metodo: 'local' (parser determinista, default) o 'ia' (LLM con conteo)
    """
    import time
    try:
        # Obtener proyecto
        proyecto = hybrid_db.obtener_proyecto(proyecto_id)
        if not proyecto:
            raise HTTPException(status_code=404, detail=f"Proyecto {proyecto_id} no encontrado")

        # Eliminar estructura anterior si existe
        if proyecto.capitulos:
            logger.info(f"[FASE 1] Eliminando estructura anterior de proyecto {proyecto_id}")
            for capitulo in list(proyecto.capitulos):
                hybrid_db.session.delete(capitulo)
            hybrid_db.session.commit()

        # Ejecutar Fase 1 según método elegido
        inicio = time.time()

        if metodo.lower() == "local":
            # ✅ MÉTODO LOCAL (Nuevo - Recomendado)
            logger.info(f"🔧 [FASE 1] Extrayendo estructura con PARSER LOCAL para proyecto {proyecto_id}")

            from parser.local_structure_extractor import LocalStructureExtractor
            extractor = LocalStructureExtractor(proyecto.archivo_origen)
            estructura_ia = extractor.extraer_estructura()

            if not estructura_ia.get('capitulos'):
                raise Exception("No se pudo extraer estructura con parser local")

            # Validación automática
            validacion = estructura_ia.get('validacion_local', {})
            if not validacion.get('valido', True):
                logger.warning(f"  ⚠️ Detectadas {len(validacion.get('inconsistencias', []))} inconsistencias en totales")
            else:
                logger.info(f"  ✓ Validación: Todos los totales cuadran")

        else:
            # 🤖 MÉTODO IA (Original)
            logger.info(f"📊 [FASE 1] Extrayendo estructura con IA para proyecto {proyecto_id}")

            # Paso 1.1: Extraer estructura (capítulos, subcapítulos, totales)
            logger.info(f"  [FASE 1.1] Extrayendo jerarquía de capítulos y subcapítulos...")
            from llm.structure_extraction_agent import StructureExtractionAgent
            agent = StructureExtractionAgent()
            estructura_ia = await agent.extraer_estructura(proyecto.archivo_origen)

            if not estructura_ia.get('capitulos'):
                raise Exception("No se pudo extraer estructura con IA")

            # Paso 1.2: Contar partidas de cada capítulo/subcapítulo
            logger.info(f"  [FASE 1.2] Contando número de partidas por sección...")
            conteo_inicio = time.time()

            from llm.partida_count_agent import PartidaCountAgent
            count_agent = PartidaCountAgent()
            conteo = await count_agent.contar_partidas(proyecto.archivo_origen, estructura_ia)
            estructura_ia = count_agent.fusionar_conteo_con_estructura(estructura_ia, conteo)

            conteo_tiempo = time.time() - conteo_inicio
            logger.info(f"  ✓ Conteo completado en {conteo_tiempo:.2f}s")

        tiempo = time.time() - inicio

        # Guardar en BD
        success = hybrid_db.guardar_estructura_fase1(proyecto_id, estructura_ia, tiempo)

        if not success:
            raise Exception("Error guardando estructura en BD")

        logger.info(f"[FASE 1] ✓ Completada con método '{metodo}' - {len(estructura_ia['capitulos'])} capítulos")

        return {
            "success": True,
            "mensaje": f"Fase 1 completada: Estructura extraída con {metodo.upper()}",
            "metodo": metodo,
            "capitulos_extraidos": len(estructura_ia['capitulos']),
            "tiempo": tiempo,
            "validacion": estructura_ia.get('validacion_local') if metodo == "local" else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[FASE 1] Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/hybrid-fase2/{proyecto_id}")
async def ejecutar_fase2_partidas(proyecto_id: int):
    """
    [HÍBRIDO] Ejecuta solo la Fase 2: Extracción de partidas con parser local

    Extrae partidas individuales usando PartidaParser (sin IA).
    Requiere que la Fase 1 esté completada.
    Si ya existen partidas, las elimina y las vuelve a procesar.
    """
    import time
    try:
        # Obtener proyecto
        proyecto = hybrid_db.obtener_proyecto(proyecto_id)
        if not proyecto:
            raise HTTPException(status_code=404, detail=f"Proyecto {proyecto_id} no encontrado")

        # Verificar que existe estructura (Fase 1 completada)
        if not proyecto.capitulos:
            raise HTTPException(
                status_code=400,
                detail="Debe completar la Fase 1 (extracción de estructura) antes de ejecutar la Fase 2"
            )

        # Eliminar partidas anteriores si existen para evitar duplicados
        # Al reprocesar, se limpia la BD y se regeneran todas las partidas desde cero
        total_partidas_eliminadas = 0
        for capitulo in proyecto.capitulos:
            for subcapitulo in capitulo.subcapitulos:
                total_partidas_eliminadas += len(subcapitulo.partidas)
                for partida in list(subcapitulo.partidas):
                    hybrid_db.session.delete(partida)
                for apartado in subcapitulo.apartados:
                    total_partidas_eliminadas += len(apartado.partidas)
                    for partida in list(apartado.partidas):
                        hybrid_db.session.delete(partida)

        if total_partidas_eliminadas > 0:
            logger.info(f"[FASE 2] Eliminadas {total_partidas_eliminadas} partidas anteriores para reprocesamiento limpio")
            hybrid_db.session.commit()

        # Ejecutar Fase 2 con extractor dirigido
        logger.info(f"[FASE 2] Extrayendo partidas con extractor dirigido para proyecto {proyecto_id}")
        inicio = time.time()

        from parser.guided_partida_extractor import GuidedPartidaExtractor

        extractor = GuidedPartidaExtractor(proyecto.archivo_origen)
        extractor.extraer_texto()  # Extraer y clasificar todo el texto una sola vez

        # Recorrer estructura de Fase 1 y extraer partidas de cada subcapítulo
        partidas_por_subcapitulo = {}
        total_partidas = 0

        def procesar_subcapitulo(subcapitulo, nivel=0):
            """Procesa un subcapítulo y sus hijos recursivamente"""
            nonlocal total_partidas

            codigo = subcapitulo.codigo
            logger.info(f"{'  ' * nivel}[FASE 2] Extrayendo partidas de {codigo}")

            partidas = extractor.extraer_partidas_subcapitulo(codigo)
            partidas_por_subcapitulo[codigo] = partidas
            total_partidas += len(partidas)

            # Procesar subcapítulos hijos recursivamente
            for hijo in subcapitulo.subcapitulos_hijos:
                procesar_subcapitulo(hijo, nivel + 1)

        # Procesar todos los capítulos
        for capitulo in proyecto.capitulos:
            logger.info(f"[FASE 2] Procesando capítulo {capitulo.codigo}")
            for subcapitulo in capitulo.subcapitulos:
                procesar_subcapitulo(subcapitulo)

        tiempo = time.time() - inicio

        if total_partidas == 0:
            logger.warning(f"[FASE 2] No se extrajeron partidas")
            return {
                "success": False,
                "error": "El extractor no pudo extraer partidas del PDF",
                "tiempo": tiempo
            }

        logger.info(f"[FASE 2] ✓ Total de partidas extraídas: {total_partidas}")

        # Guardar en BD - convertir a formato esperado
        resultado = hybrid_db.guardar_partidas_fase2_dirigido(proyecto_id, partidas_por_subcapitulo, tiempo)

        if not resultado['success']:
            raise Exception(f"Error guardando partidas: {resultado.get('error')}")

        logger.info(f"[FASE 2] ✓ Completada - {resultado['partidas_guardadas']} partidas")

        return {
            "success": True,
            "mensaje": "Fase 2 completada: Partidas extraídas con parser local",
            "partidas_extraidas": resultado['partidas_guardadas'],
            "tiempo": tiempo
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[FASE 2] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/hybrid-fase3/{proyecto_id}")
async def ejecutar_fase3_validacion(proyecto_id: int, tolerancia: float = 0.0):
    """
    [HÍBRIDO] Ejecuta solo la Fase 3: Validación cruzada IA vs Local

    Compara SOLO totales en euros de IA (Fase 1) vs Local (Fase 2).
    Validación: IGUALDAD EXACTA (diff < 0.01€). NO valida conteo de partidas.
    Requiere que las Fases 1 y 2 estén completadas.
    """
    import time
    try:
        # Obtener proyecto
        proyecto = hybrid_db.obtener_proyecto(proyecto_id)
        if not proyecto:
            raise HTTPException(status_code=404, detail=f"Proyecto {proyecto_id} no encontrado")

        # Verificar que existen capítulos (Fase 1)
        if not proyecto.capitulos:
            raise HTTPException(
                status_code=400,
                detail="Debe completar la Fase 1 (extracción de estructura) antes de validar"
            )

        # Verificar que existen partidas (Fase 2)
        tiene_partidas = False
        for capitulo in proyecto.capitulos:
            for subcapitulo in capitulo.subcapitulos:
                if subcapitulo.partidas or subcapitulo.apartados:
                    tiene_partidas = True
                    break
            if tiene_partidas:
                break

        if not tiene_partidas:
            raise HTTPException(
                status_code=400,
                detail="Debe completar la Fase 2 (extracción de partidas) antes de validar"
            )

        # IMPORTANTE: Recalcular totales locales ANTES de validar
        # Esto asegura que los totales de los padres estén actualizados después de
        # modificar partidas de los hijos
        logger.info(f"[FASE 3] Recalculando totales locales antes de validar...")
        hybrid_db._calcular_totales_locales(proyecto_id)

        # Ejecutar Fase 3
        logger.info(f"[FASE 3] Validando proyecto {proyecto_id} con tolerancia {tolerancia}%")
        inicio = time.time()

        resultado = hybrid_db.validar_fase3(proyecto_id, tolerancia)
        tiempo = time.time() - inicio

        if not resultado['success']:
            raise Exception(f"Error en validación: {resultado.get('error')}")

        elementos_a_revisar = resultado.get('elementos_a_revisar', [])

        if elementos_a_revisar:
            logger.warning(f"[FASE 3] ⚠️ {len(elementos_a_revisar)} elementos con discrepancia necesitan revisión")
            for elem in elementos_a_revisar:
                logger.warning(f"  • {elem['tipo'].upper()} {elem['codigo']} - {elem['nombre']}: "
                             f"IA={elem['total_ia']:.2f}€ vs Local={elem['total_local']:.2f}€ "
                             f"(Δ {elem['diferencia_porcentaje']:.1f}%)")
        else:
            logger.info(f"[FASE 3] ✓ Completada - {resultado['porcentaje_coincidencia']:.1f}% coincidencia")

        return {
            "success": True,
            "mensaje": f"Fase 3 completada: {resultado['validados']} validados, {resultado['discrepancias']} discrepancias",
            "validados": resultado['validados'],
            "discrepancias": resultado['discrepancias'],
            "errores": 0,  # No hay errores, solo validados o discrepancias
            "elementos_a_revisar": elementos_a_revisar,
            "subcapitulos_a_revisar": elementos_a_revisar,  # Alias por compatibilidad
            "porcentaje_coincidencia": resultado['porcentaje_coincidencia'],
            "tiempo": tiempo
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[FASE 3] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/hybrid-fase4/{proyecto_id}")
async def ejecutar_fase4_descripciones(proyecto_id: int):
    """
    [HÍBRIDO] Ejecuta Fase 4: Completar descripciones con parser local (sin LLM)

    Busca en el texto ya clasificado las descripciones de partidas que están vacías.
    Utiliza el parser local (LineClassifier) para identificar líneas PARTIDA_DESCRIPCION.

    Coste: $0 (procesamiento 100% local)
    Velocidad: ~1,000 partidas/segundo
    """
    import time
    try:
        # Obtener proyecto
        proyecto = hybrid_db.obtener_proyecto(proyecto_id)
        if not proyecto:
            raise HTTPException(status_code=404, detail=f"Proyecto {proyecto_id} no encontrado")

        # Verificar que tiene archivo origen
        if not proyecto.archivo_origen or not os.path.exists(proyecto.archivo_origen):
            raise HTTPException(
                status_code=400,
                detail="No se encontró el archivo PDF original del proyecto"
            )

        logger.info(f"[FASE 4] Completando descripciones del proyecto {proyecto_id}")
        inicio = time.time()

        # Importar y ejecutar LocalDescriptionExtractor
        from parser.local_description_extractor import LocalDescriptionExtractor

        extractor = LocalDescriptionExtractor(proyecto.archivo_origen)
        resultado = extractor.completar_descripciones_proyecto(proyecto_id)

        tiempo = time.time() - inicio

        if not resultado['success']:
            raise Exception(f"Error completando descripciones: {resultado.get('error')}")

        logger.info(f"[FASE 4] ✓ Completada en {tiempo:.2f}s")
        logger.info(f"  • Partidas procesadas: {resultado['partidas_procesadas']}")
        logger.info(f"  • Descripciones encontradas: {resultado['descripciones_encontradas']} ({resultado['porcentaje_completado']:.1f}%)")
        logger.info(f"  • Sin descripción: {resultado['sin_descripcion']}")

        return {
            "success": True,
            "mensaje": f"Fase 4 completada: {resultado['descripciones_encontradas']}/{resultado['partidas_procesadas']} descripciones encontradas ({resultado['porcentaje_completado']:.1f}%)",
            "partidas_procesadas": resultado['partidas_procesadas'],
            "descripciones_encontradas": resultado['descripciones_encontradas'],
            "sin_descripcion": resultado['sin_descripcion'],
            "porcentaje_completado": resultado['porcentaje_completado'],
            "tiempo": tiempo
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[FASE 4] Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/hybrid-revisar-elemento/{proyecto_id}")
async def revisar_elemento_con_ia(
    proyecto_id: int,
    elemento_tipo: str = Query(..., description="Tipo de elemento: 'capitulo' o 'subcapitulo'"),
    elemento_id: int = Query(..., description="ID del elemento a revisar")
):
    """
    [HÍBRIDO] Revisa un elemento (capítulo o subcapítulo) con discrepancia usando IA

    Extrae las partidas del elemento usando el LLM y compara con las partidas locales.
    Actualiza, añade o elimina partidas según sea necesario.
    """
    try:
        # Obtener proyecto
        proyecto = hybrid_db.obtener_proyecto(proyecto_id)
        if not proyecto:
            raise HTTPException(status_code=404, detail=f"Proyecto {proyecto_id} no encontrado")

        # Verificar que existe el archivo PDF
        if not proyecto.archivo_origen or not os.path.exists(proyecto.archivo_origen):
            raise HTTPException(
                status_code=400,
                detail="No se encontró el archivo PDF del proyecto"
            )

        logger.info(f"[IA-REVISION] Iniciando revisión de {elemento_tipo} {elemento_id} en proyecto {proyecto_id}")

        # Importar el agente de extracción
        from llm.partida_extraction_agent import PartidaExtractionAgent

        agent = PartidaExtractionAgent(use_openrouter=True)

        # Obtener el elemento a revisar
        if elemento_tipo == "capitulo":
            elemento = hybrid_db.session.query(HybridCapitulo).filter_by(id=elemento_id).first()
            if not elemento:
                raise HTTPException(status_code=404, detail=f"Capítulo {elemento_id} no encontrado")

            # Preparar datos del capítulo para el agente
            capitulo_data = {
                "codigo": elemento.codigo,
                "nombre": elemento.nombre,
                "total": elemento.total_ia
            }

            # Extraer partidas del capítulo usando IA
            resultado_ia = await agent.extraer_partidas_capitulo(
                pdf_path=proyecto.archivo_origen,
                capitulo=capitulo_data,
                subcapitulos_filtrados=None  # Extraer todo el capítulo
            )

        elif elemento_tipo == "subcapitulo":
            elemento = hybrid_db.session.query(HybridSubcapitulo).filter_by(id=elemento_id).first()
            if not elemento:
                raise HTTPException(status_code=404, detail=f"Subcapítulo {elemento_id} no encontrado")

            # Obtener el capítulo padre
            capitulo_padre = elemento.capitulo

            # Preparar datos para el agente
            capitulo_data = {
                "codigo": capitulo_padre.codigo,
                "nombre": capitulo_padre.nombre,
                "total": capitulo_padre.total_ia
            }

            # Extraer solo este subcapítulo
            resultado_ia = await agent.extraer_partidas_capitulo(
                pdf_path=proyecto.archivo_origen,
                capitulo=capitulo_data,
                subcapitulos_filtrados=[elemento.codigo]
            )
        else:
            raise HTTPException(status_code=400, detail="elemento_tipo debe ser 'capitulo' o 'subcapitulo'")

        if not resultado_ia.get('success'):
            raise Exception(f"Error en extracción IA: {resultado_ia.get('error')}")

        # Procesar resultado y actualizar base de datos
        partidas_ia = resultado_ia.get('partidas', [])

        logger.info(f"[IA-REVISION] IA extrajo {len(partidas_ia)} partidas del {elemento_tipo}")

        # Comparar con partidas existentes y actualizar
        resultado_actualizacion = await hybrid_db.actualizar_partidas_elemento(
            elemento_tipo=elemento_tipo,
            elemento_id=elemento_id,
            partidas_ia=partidas_ia
        )

        return {
            "success": True,
            "mensaje": f"Revisión IA completada para {elemento_tipo} {elemento.codigo}",
            "elemento": {
                "tipo": elemento_tipo,
                "codigo": elemento.codigo,
                "nombre": elemento.nombre
            },
            "partidas_ia_extraidas": len(partidas_ia),
            "actualizacion": resultado_actualizacion,
            "tiempo": resultado_ia.get('tiempo_procesamiento', 0)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[IA-REVISION] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/hybrid-revisar-todos/{proyecto_id}")
async def revisar_todos_elementos_con_ia(proyecto_id: int):
    """
    [HÍBRIDO] Revisa TODOS los elementos con discrepancia de forma inteligente

    Estrategia:
    1. Identifica solo subcapítulos "hoja" (sin hijos) con discrepancia
    2. Los procesa uno por uno (cada elemento se procesa máximo 1 vez)
    3. Después de cada procesamiento, re-ejecuta Fase 3 para recalcular
    4. Repite hasta procesar todos los elementos o alcanzar límite (100 iteraciones)

    Esto evita revisar padres cuya discrepancia viene de sus hijos y evita bucles infinitos.
    """
    try:
        MAX_ITERACIONES = 100  # Límite temporal de seguridad (se quitará una vez verificado)
        iteracion = 0
        total_procesados = 0
        total_errores = 0
        elementos_ya_procesados = set()  # Set para trackear elementos ya procesados (por ID)

        logger.info(f"[IA-REVISION-MASIVA] Iniciando revisión masiva para proyecto {proyecto_id}")

        # Guardar texto completo del PDF al inicio (solo primera vez)
        proyecto = hybrid_db.obtener_proyecto(proyecto_id)
        if proyecto and proyecto.archivo_origen:
            try:
                from parser.pdf_extractor import PDFExtractor
                nombre_pdf = os.path.basename(proyecto.archivo_origen).replace('.pdf', '')
                texto_completo_path = f"logs/extracted_full_text_{proyecto_id}_{nombre_pdf}.txt"

                # Solo guardar si no existe
                if not os.path.exists(texto_completo_path):
                    os.makedirs('logs', exist_ok=True)
                    extractor = PDFExtractor(proyecto.archivo_origen)
                    extractor.guardar_texto(texto_completo_path)
                    logger.info(f"💾 Texto completo guardado en: {texto_completo_path}")
                else:
                    logger.info(f"✓ Texto completo ya existe: {texto_completo_path}")
            except Exception as e:
                logger.warning(f"⚠️ No se pudo guardar texto completo: {e}")

        while iteracion < MAX_ITERACIONES:
            iteracion += 1
            logger.info(f"[IA-REVISION-MASIVA] Iteración {iteracion}/{MAX_ITERACIONES}")

            # 1. Obtener proyecto actualizado
            proyecto = hybrid_db.obtener_proyecto(proyecto_id)
            if not proyecto:
                raise HTTPException(status_code=404, detail=f"Proyecto {proyecto_id} no encontrado")

            # 2. Identificar subcapítulos HOJA con discrepancia
            elementos_a_revisar = []

            for capitulo in proyecto.capitulos:
                # Función recursiva para encontrar hojas
                def encontrar_hojas_con_discrepancia(subcapitulos, capitulo_id):
                    hojas = []
                    for sub in subcapitulos:
                        # Si tiene hijos, explorar recursivamente
                        if hasattr(sub, 'subcapitulos_hijos') and sub.subcapitulos_hijos and len(sub.subcapitulos_hijos) > 0:
                            hojas.extend(encontrar_hojas_con_discrepancia(sub.subcapitulos_hijos, capitulo_id))
                        else:
                            # Es hoja: verificar si tiene discrepancia Y no ha sido procesado aún
                            if (hasattr(sub, 'estado_validacion') and
                                sub.estado_validacion and
                                sub.estado_validacion.value.lower() == 'discrepancia' and
                                hasattr(sub, 'necesita_revision_ia') and
                                sub.necesita_revision_ia and
                                sub.id not in elementos_ya_procesados):  # ← NUEVO: saltar ya procesados
                                hojas.append({
                                    'tipo': 'subcapitulo',
                                    'id': sub.id,
                                    'codigo': sub.codigo,
                                    'nombre': sub.nombre,
                                    'capitulo_id': capitulo_id
                                })
                    return hojas

                # Buscar en subcapítulos del capítulo
                if hasattr(capitulo, 'subcapitulos') and capitulo.subcapitulos:
                    elementos_a_revisar.extend(
                        encontrar_hojas_con_discrepancia(capitulo.subcapitulos, capitulo.id)
                    )

            # 3. Si no hay elementos pendientes (todos fueron procesados o validados), terminar
            if not elementos_a_revisar:
                logger.info(f"[IA-REVISION-MASIVA] ✓ No hay más elementos hoja pendientes de procesar")
                logger.info(f"[IA-REVISION-MASIVA] Total procesados en esta ejecución: {len(elementos_ya_procesados)}")
                break

            logger.info(f"[IA-REVISION-MASIVA] Encontrados {len(elementos_a_revisar)} elementos hoja con discrepancia (pendientes de procesar)")

            # 4. Procesar el PRIMERO de la lista
            elemento = elementos_a_revisar[0]
            logger.info(f"[IA-REVISION-MASIVA] Procesando {elemento['codigo']} - {elemento['nombre']}")

            # Marcar como procesado ANTES de intentar procesarlo (para evitar bucles infinitos)
            elementos_ya_procesados.add(elemento['id'])

            try:
                # Importar el agente de extracción
                from llm.partida_extraction_agent import PartidaExtractionAgent
                agent = PartidaExtractionAgent(use_openrouter=True)

                # Obtener subcapítulo y capítulo padre
                subcapitulo = hybrid_db.session.query(HybridSubcapitulo).filter_by(id=elemento['id']).first()
                if not subcapitulo:
                    logger.error(f"[IA-REVISION-MASIVA] Subcapítulo {elemento['id']} no encontrado")
                    total_errores += 1
                    continue

                capitulo_padre = subcapitulo.capitulo

                # Preparar datos para el agente
                capitulo_data = {
                    "codigo": capitulo_padre.codigo,
                    "nombre": capitulo_padre.nombre,
                    "total": capitulo_padre.total_ia
                }

                # Extraer partidas del subcapítulo usando IA
                resultado_ia = await agent.extraer_partidas_capitulo(
                    pdf_path=proyecto.archivo_origen,
                    capitulo=capitulo_data,
                    subcapitulos_filtrados=[subcapitulo.codigo]
                )

                if resultado_ia.get('success'):
                    partidas_ia = resultado_ia.get('partidas', [])

                    # Actualizar partidas
                    resultado_actualizacion = await hybrid_db.actualizar_partidas_elemento(
                        elemento_tipo='subcapitulo',
                        elemento_id=elemento['id'],
                        partidas_ia=partidas_ia
                    )

                    if resultado_actualizacion.get('success'):
                        total_procesados += 1
                        logger.info(f"[IA-REVISION-MASIVA] ✓ {elemento['codigo']}: {resultado_actualizacion['actualizadas']} act, {resultado_actualizacion['agregadas']} agr, {resultado_actualizacion['eliminadas']} elim")
                    else:
                        logger.error(f"[IA-REVISION-MASIVA] ✗ Error actualizando {elemento['codigo']}: {resultado_actualizacion.get('error')}")
                        total_errores += 1
                else:
                    logger.error(f"[IA-REVISION-MASIVA] ✗ Error extrayendo {elemento['codigo']}: {resultado_ia.get('error')}")
                    total_errores += 1

            except Exception as e:
                logger.error(f"[IA-REVISION-MASIVA] ✗ Error procesando {elemento['codigo']}: {e}")
                total_errores += 1

            # 5. Recalcular totales locales de todo el proyecto
            # IMPORTANTE: Después de actualizar un subcapítulo hijo, los totales de los padres
            # pueden haber cambiado, así que recalculamos ANTES de validar
            logger.info(f"[IA-REVISION-MASIVA] Recalculando totales locales del proyecto...")
            try:
                hybrid_db._calcular_totales_locales(proyecto_id)
                logger.info(f"[IA-REVISION-MASIVA] ✓ Totales recalculados")
            except Exception as e:
                logger.error(f"[IA-REVISION-MASIVA] Error recalculando totales: {e}")

            # 6. Re-ejecutar Fase 3 para validar con los totales actualizados
            logger.info(f"[IA-REVISION-MASIVA] Validando con Fase 3...")
            try:
                # Llamar al endpoint de Fase 3 internamente con tolerancia 0.0 (igualdad exacta)
                import httpx
                async with httpx.AsyncClient() as client:
                    response = await client.post(f"http://localhost:3013/hybrid-fase3/{proyecto_id}?tolerancia=0.0")
                    if response.status_code != 200:
                        logger.warning(f"[IA-REVISION-MASIVA] Advertencia en Fase 3: {response.text}")
            except Exception as e:
                logger.error(f"[IA-REVISION-MASIVA] Error en Fase 3: {e}")

        # Resultado final - contar elementos que quedaron sin validar
        proyecto_final = hybrid_db.obtener_proyecto(proyecto_id)
        elementos_pendientes = 0
        for capitulo in proyecto_final.capitulos:
            def contar_hojas_pendientes(subcapitulos):
                count = 0
                for sub in subcapitulos:
                    if hasattr(sub, 'subcapitulos_hijos') and sub.subcapitulos_hijos and len(sub.subcapitulos_hijos) > 0:
                        count += contar_hojas_pendientes(sub.subcapitulos_hijos)
                    else:
                        if (hasattr(sub, 'estado_validacion') and sub.estado_validacion and
                            sub.estado_validacion.value.lower() == 'discrepancia'):
                            count += 1
                return count

            if hasattr(capitulo, 'subcapitulos') and capitulo.subcapitulos:
                elementos_pendientes += contar_hojas_pendientes(capitulo.subcapitulos)

        if iteracion >= MAX_ITERACIONES:
            logger.warning(f"[IA-REVISION-MASIVA] ⚠️ Alcanzado límite de {MAX_ITERACIONES} iteraciones")

        logger.info(f"[IA-REVISION-MASIVA] ✓ Completado: {len(elementos_ya_procesados)} procesados, {elementos_pendientes} aún con discrepancia")

        return {
            "success": True,
            "mensaje": f"Revisión masiva completada: {len(elementos_ya_procesados)} procesados, {elementos_pendientes} aún con discrepancia",
            "iteraciones": iteracion,
            "elementos_procesados": len(elementos_ya_procesados),
            "elementos_pendientes": elementos_pendientes,
            "errores": total_errores,
            "limite_alcanzado": iteracion >= MAX_ITERACIONES
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[IA-REVISION-MASIVA] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/hybrid-proyectos/{proyecto_id}")
async def eliminar_proyecto_hibrido(proyecto_id: int):
    """[HÍBRIDO] Elimina un proyecto híbrido"""
    try:
        success = hybrid_db.eliminar_proyecto(proyecto_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"Proyecto híbrido {proyecto_id} no encontrado")

        return {"success": True, "mensaje": f"Proyecto híbrido {proyecto_id} eliminado"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[HÍBRIDO] Error eliminando proyecto: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/hybrid-exportar/{proyecto_id}/{formato}")
async def exportar_proyecto_hibrido(proyecto_id: int, formato: str):
    """
    [HÍBRIDO] Exporta un proyecto híbrido en el formato especificado

    Usa los totales validados finales
    Formatos: csv, excel, xml, bc3
    """
    try:
        proyecto = hybrid_db.obtener_proyecto(proyecto_id)
        if not proyecto:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        # Construir estructura para exportadores (igual que sistema normal)
        estructura = {
            'nombre': proyecto.nombre,
            'descripcion': proyecto.descripcion,
            'archivo_origen': proyecto.archivo_origen,
            'capitulos': []
        }

        for capitulo in proyecto.capitulos:
            cap_dict = {
                'codigo': capitulo.codigo,
                'nombre': capitulo.nombre,
                'subcapitulos': []
            }

            for subcapitulo in capitulo.subcapitulos:
                sub_dict = {
                    'codigo': subcapitulo.codigo,
                    'nombre': subcapitulo.nombre,
                    'apartados': [],
                    'partidas': []
                }

                # Partidas directas
                for partida in subcapitulo.partidas:
                    sub_dict['partidas'].append({
                        'codigo': partida.codigo,
                        'unidad': partida.unidad,
                        'resumen': partida.resumen,
                        'descripcion': partida.descripcion,
                        'cantidad': partida.cantidad,
                        'precio': partida.precio,
                        'importe': partida.importe
                    })

                # Apartados
                for apartado in subcapitulo.apartados:
                    apt_dict = {
                        'codigo': apartado.codigo,
                        'nombre': apartado.nombre,
                        'partidas': []
                    }

                    for partida in apartado.partidas:
                        apt_dict['partidas'].append({
                            'codigo': partida.codigo,
                            'unidad': partida.unidad,
                            'resumen': partida.resumen,
                            'descripcion': partida.descripcion,
                            'cantidad': partida.cantidad,
                            'precio': partida.precio,
                            'importe': partida.importe
                        })

                    sub_dict['apartados'].append(apt_dict)

                cap_dict['subcapitulos'].append(sub_dict)

            estructura['capitulos'].append(cap_dict)

        # Obtener todas las partidas planas (para CSV y Excel)
        partidas = []
        for cap in estructura['capitulos']:
            for sub in cap['subcapitulos']:
                for partida in sub['partidas']:
                    partidas.append({
                        **partida,
                        'capitulo': cap['codigo'],
                        'subcapitulo': sub['codigo'],
                        'apartado': None
                    })
                for apt in sub['apartados']:
                    for partida in apt['partidas']:
                        partidas.append({
                            **partida,
                            'capitulo': cap['codigo'],
                            'subcapitulo': sub['codigo'],
                            'apartado': apt['codigo']
                        })

        # Exportar según formato
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"hybrid_{proyecto_id}_{timestamp}"

        if formato.lower() == 'csv':
            output_path = EXPORT_DIR / f"{filename}.csv"
            CSVExporter.exportar(partidas, str(output_path))

        elif formato.lower() == 'excel':
            output_path = EXPORT_DIR / f"{filename}.xlsx"
            ExcelExporter.exportar(partidas, str(output_path))

        elif formato.lower() == 'xml':
            output_path = EXPORT_DIR / f"{filename}.xml"
            XMLExporter.exportar(estructura, str(output_path))

        elif formato.lower() == 'bc3':
            output_path = EXPORT_DIR / f"{filename}.bc3"
            BC3Exporter.exportar(estructura, str(output_path))

        else:
            raise HTTPException(status_code=400, detail=f"Formato no soportado: {formato}")

        logger.info(f"[HÍBRIDO] Exportado: {output_path}")

        # Retornar archivo
        return FileResponse(
            path=str(output_path),
            filename=output_path.name,
            media_type='application/octet-stream'
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[HÍBRIDO] Error exportando: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3013)
