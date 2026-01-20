#!/usr/bin/env python3
"""
Script para ejecutar la API REST V2
====================================

Uso:
    python run_api.py              # Desarrollo (reload automático)
    python run_api.py --production # Producción (sin reload)

"""

import sys
import argparse
import uvicorn
from pathlib import Path

# Agregar src al path
sys.path.append(str(Path(__file__).parent / 'src'))

from api_v2.config import settings


def main():
    parser = argparse.ArgumentParser(description='Ejecutar API REST V2')
    parser.add_argument(
        '--production',
        action='store_true',
        help='Ejecutar en modo producción (sin reload)'
    )
    parser.add_argument(
        '--host',
        default='0.0.0.0',
        help='Host (default: 0.0.0.0)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8000,
        help='Puerto (default: 8000)'
    )

    args = parser.parse_args()

    print(f"\n{'='*80}")
    print(f"INICIANDO API REST V2")
    print(f"{'='*80}")
    print(f"\nModo: {'PRODUCCIÓN' if args.production else 'DESARROLLO'}")
    print(f"Host: {args.host}")
    print(f"Puerto: {args.port}")
    print(f"\nDocumentación:")
    print(f"  Swagger UI: http://localhost:{args.port}/api/docs")
    print(f"  ReDoc: http://localhost:{args.port}/api/redoc")
    print(f"\n{'='*80}\n")

    uvicorn.run(
        "api_v2.main:app",
        host=args.host,
        port=args.port,
        reload=not args.production,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True
    )


if __name__ == "__main__":
    main()
