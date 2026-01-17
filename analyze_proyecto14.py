"""
Análisis detallado del Proyecto 14 (PE_PRE_R2_RAMPA_PORTAL)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.models.db_models import Proyecto, Capitulo, Subcapitulo, Partida, DatabaseManager

db_manager = DatabaseManager('data/mediciones.db')
db = db_manager.session

# Cargar proyecto 14
proyecto = db.query(Proyecto).filter(Proyecto.id == 14).first()

if not proyecto:
    print("❌ No se encontró el proyecto #14")
    exit(1)

print(f"\n{'='*80}")
print(f"PROYECTO #{proyecto.id}")
print(f"{'='*80}")
print(f"Nombre: {proyecto.nombre}")
print(f"Archivo: {proyecto.archivo_origen}")
print(f"Fecha: {proyecto.fecha_creacion}\n")

# 1. Verificar nombre del proyecto
print("="*80)
print("1️⃣  VERIFICACIÓN: NOMBRE DEL PROYECTO")
print("="*80)
if "APEO" in proyecto.nombre or "01.01" in proyecto.nombre:
    print(f"❌ INCORRECTO: '{proyecto.nombre}'")
    print("✓ DEBERÍA SER: 'PROYECTO PARA REFORMA DE PORTAL DE ENTRADA EN CALLE OBISPO...'")
else:
    print(f"✓ Correcto: {proyecto.nombre}")

# Listar estructura completa
capitulos = db.query(Capitulo).filter(
    Capitulo.proyecto_id == proyecto.id
).order_by(Capitulo.codigo).all()

print(f"\n{'='*80}")
print(f"ESTRUCTURA DEL PROYECTO: {len(capitulos)} capítulos")
print(f"{'='*80}\n")

total_partidas = 0

for cap in capitulos:
    print(f"\n📁 CAPÍTULO {cap.codigo}: {cap.nombre}")

    # Subcapítulos del capítulo
    subcapitulos = db.query(Subcapitulo).filter(
        Subcapitulo.capitulo_id == cap.id
    ).order_by(Subcapitulo.codigo).all()

    if subcapitulos:
        for sub in subcapitulos:
            print(f"   📂 SUBCAPÍTULO {sub.codigo}: {sub.nombre}")

            # Partidas del subcapítulo
            partidas = db.query(Partida).filter(
                Partida.subcapitulo_id == sub.id
            ).order_by(Partida.codigo).all()

            if partidas:
                for p in partidas:
                    print(f"      • {p.codigo} | {p.unidad:3s} | {p.resumen[:50]}")
                    total_partidas += 1
    else:
        # Partidas directas del capítulo (sin subcapítulo)
        partidas = db.query(Partida).filter(
            Partida.subcapitulo_id.in_(
                db.query(Subcapitulo.id).filter(Subcapitulo.capitulo_id == cap.id)
            )
        ).order_by(Partida.codigo).all()

        if not partidas:
            print(f"   ⚠️  Sin subcapítulos ni partidas")

print(f"\n{'='*80}")
print(f"Total de partidas encontradas: {total_partidas}")
print(f"{'='*80}\n")

# 2. Verificar partida 01.06
print("="*80)
print("2️⃣  VERIFICACIÓN: PARTIDA 01.06")
print("="*80)

# Buscar en todos los subcapítulos del capítulo 01
cap_01 = next((c for c in capitulos if c.codigo == "01"), None)
if cap_01:
    subcaps_01 = db.query(Subcapitulo).filter(
        Subcapitulo.capitulo_id == cap_01.id
    ).all()

    partida_0106 = None
    for sub in subcaps_01:
        p = db.query(Partida).filter(
            Partida.subcapitulo_id == sub.id,
            Partida.codigo == "01.06"
        ).first()
        if p:
            partida_0106 = p
            break

    if partida_0106:
        print(f"✓ ENCONTRADA: {partida_0106.codigo}")
        print(f"  Unidad: {partida_0106.unidad}")
        print(f"  Resumen: {partida_0106.resumen}")
        print(f"  Cantidad: {partida_0106.cantidad}")
        print(f"  Precio: {partida_0106.precio}")
        print(f"  Importe: {partida_0106.importe}")

        # Verificar vs 01.05
        partida_0105 = None
        for sub in subcaps_01:
            p = db.query(Partida).filter(
                Partida.subcapitulo_id == sub.id,
                Partida.codigo == "01.05"
            ).first()
            if p:
                partida_0105 = p
                break

        if partida_0105:
            print(f"\n  Comparación con 01.05:")
            print(f"  01.05: Cant={partida_0105.cantidad}, Precio={partida_0105.precio}")
            print(f"  01.06: Cant={partida_0106.cantidad}, Precio={partida_0106.precio}")
            if (partida_0106.cantidad == partida_0105.cantidad and
                partida_0106.precio == partida_0105.precio):
                print("  ⚠️  ADVERTENCIA: Valores idénticos a 01.05")
            else:
                print("  ✓ Valores propios (diferentes de 01.05)")
    else:
        print("❌ NO ENCONTRADA")
else:
    print("❌ No se encontró el capítulo 01")

# 3. Verificar partidas 01.17 y 01.18
print(f"\n{'='*80}")
print("3️⃣  VERIFICACIÓN: PARTIDAS 01.17 Y 01.18")
print("="*80)

if cap_01:
    for codigo in ["01.17", "01.18"]:
        found = False
        for sub in subcaps_01:
            p = db.query(Partida).filter(
                Partida.subcapitulo_id == sub.id,
                Partida.codigo == codigo
            ).first()
            if p:
                print(f"✓ {codigo} ENCONTRADA: {p.resumen[:60]}")
                found = True
                break
        if not found:
            print(f"❌ {codigo} NO ENCONTRADA")
else:
    print("❌ No se encontró el capítulo 01")

# 4. Verificar capítulos 02 y 03
print(f"\n{'='*80}")
print("4️⃣  VERIFICACIÓN: CAPÍTULOS 02 Y 03")
print("="*80)

for codigo_cap in ["02", "03"]:
    cap = next((c for c in capitulos if c.codigo == codigo_cap), None)
    if cap:
        print(f"\n✓ CAPÍTULO {codigo_cap}: {cap.nombre}")

        # Subcapítulos
        subcaps = db.query(Subcapitulo).filter(
            Subcapitulo.capitulo_id == cap.id
        ).all()

        print(f"  Subcapítulos: {len(subcaps)}")
        if subcaps:
            for sub in subcaps:
                print(f"    • {sub.codigo}: {sub.nombre}")
        else:
            print(f"  ⚠️  NO tiene subcapítulos")

        # Buscar partidas
        total_partidas_cap = 0
        for sub in subcaps:
            partidas = db.query(Partida).filter(
                Partida.subcapitulo_id == sub.id
            ).all()
            total_partidas_cap += len(partidas)
            for p in partidas:
                print(f"      • {p.codigo} | {p.unidad} | {p.resumen[:50]}")

        print(f"  Total partidas: {total_partidas_cap}")
        if total_partidas_cap == 0:
            print(f"  ⚠️  NO tiene partidas")
    else:
        print(f"❌ CAPÍTULO {codigo_cap} NO ENCONTRADO")

print("\n" + "="*80)
db_manager.cerrar()
