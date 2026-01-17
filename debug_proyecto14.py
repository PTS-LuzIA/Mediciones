"""
Script de debug para analizar el Proyecto 14 (PE_PRE_R2_RAMPA_PORTAL.pdf)
Verificar problemas pendientes:
- Nombre del proyecto
- Partida 01.06
- Partidas 01.17 y 01.18
- Capítulos 02 y 03
"""

import sys
from pathlib import Path

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.parser.partida_parser import PartidaParser
from src.models.db_models import Proyecto, Capitulo, Partida, DatabaseManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analizar_proyecto14():
    """Analizar el proyecto 14 para identificar problemas"""

    db_manager = DatabaseManager('data/mediciones.db')
    db = db_manager.session

    # Buscar el proyecto 14 directamente
    proyecto = db.query(Proyecto).filter(
        Proyecto.id == 14
    ).first()

    if not proyecto:
        print("❌ No se encontró el proyecto #14")
        return

    print(f"📄 PROYECTO #{proyecto.id}")
    print(f"   Nombre: {proyecto.nombre}")
    print(f"   Archivo: {proyecto.archivo_origen}")
    print(f"   Fecha: {proyecto.fecha_creacion}")
    print()

    # Verificar capítulos
    capitulos = db.query(Capitulo).filter(
        Capitulo.proyecto_id == proyecto.id
    ).order_by(Capitulo.codigo).all()

    print(f"📊 CAPÍTULOS ENCONTRADOS: {len(capitulos)}")
    print("-" * 80)

    for cap in capitulos:
        print(f"\n{'='*80}")
        print(f"CAPÍTULO {cap.codigo}: {cap.nombre}")
        print(f"{'='*80}")

        # Partidas del capítulo
        partidas = db.query(Partida).filter(
            Partida.capitulo_id == cap.id
        ).order_by(Partida.codigo).all()

        print(f"\n  Partidas encontradas: {len(partidas)}")

        if partidas:
            for p in partidas:
                print(f"\n  ✓ {p.codigo} | {p.unidad} | {p.resumen[:60]}")
                print(f"    Cantidad: {p.cantidad} | Precio: {p.precio} | Importe: {p.importe}")
        else:
            print("  ⚠️  No se encontraron partidas")

    print("\n" + "="*80)
    print("VERIFICACIONES ESPECÍFICAS")
    print("="*80)

    # 1. Verificar nombre del proyecto
    print("\n1️⃣  NOMBRE DEL PROYECTO:")
    if "APEO" in proyecto.nombre or "01.01" in proyecto.nombre:
        print(f"   ❌ INCORRECTO: {proyecto.nombre}")
        print("   ✓ Debería ser: PROYECTO PARA REFORMA DE PORTAL DE ENTRADA...")
    else:
        print(f"   ✓ Correcto: {proyecto.nombre}")

    # 2. Verificar partida 01.06
    print("\n2️⃣  PARTIDA 01.06:")
    partida_0106 = db.query(Partida).join(Capitulo).filter(
        Capitulo.proyecto_id == proyecto.id,
        Partida.codigo == "01.06"
    ).first()

    if partida_0106:
        print(f"   ✓ ENCONTRADA: {partida_0106.codigo}")
        print(f"     Unidad: {partida_0106.unidad}")
        print(f"     Resumen: {partida_0106.resumen}")
        print(f"     Cantidad: {partida_0106.cantidad}")
        print(f"     Precio: {partida_0106.precio}")
        print(f"     Importe: {partida_0106.importe}")

        # Verificar que no tiene valores de 01.05
        partida_0105 = db.query(Partida).join(Capitulo).filter(
            Capitulo.proyecto_id == proyecto.id,
            Partida.codigo == "01.05"
        ).first()

        if partida_0105:
            if (partida_0106.cantidad == partida_0105.cantidad and
                partida_0106.precio == partida_0105.precio):
                print("   ⚠️  ADVERTENCIA: Tiene los mismos valores que 01.05")
            else:
                print("   ✓ Tiene valores propios (diferentes de 01.05)")
    else:
        print("   ❌ NO ENCONTRADA")

    # 3. Verificar partidas 01.17 y 01.18
    print("\n3️⃣  PARTIDAS 01.17 Y 01.18:")
    for codigo in ["01.17", "01.18"]:
        partida = db.query(Partida).join(Capitulo).filter(
            Capitulo.proyecto_id == proyecto.id,
            Partida.codigo == codigo
        ).first()

        if partida:
            print(f"   ✓ {codigo} ENCONTRADA")
        else:
            print(f"   ❌ {codigo} NO ENCONTRADA")

    # 4. Verificar capítulos 02 y 03
    print("\n4️⃣  CAPÍTULOS 02 Y 03:")
    for codigo_cap in ["02", "03"]:
        cap = db.query(Capitulo).filter(
            Capitulo.proyecto_id == proyecto.id,
            Capitulo.codigo == codigo_cap
        ).first()

        if cap:
            print(f"\n   CAPÍTULO {codigo_cap}: {cap.nombre}")

            # Partidas
            partidas = db.query(Partida).filter(
                Partida.capitulo_id == cap.id
            ).all()

            print(f"   Partidas: {len(partidas)}")
            for p in partidas:
                print(f"     • {p.codigo} | {p.unidad} | {p.resumen[:50]}")
        else:
            print(f"   ❌ CAPÍTULO {codigo_cap} NO ENCONTRADO")

    db.close()

if __name__ == "__main__":
    analizar_proyecto14()
