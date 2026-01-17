# 🚀 Inicio Rápido - MVP Mediciones

## En 3 pasos

### 1️⃣ Iniciar el sistema

```bash
./start.sh
```

Espera a ver este mensaje:

```
╔════════════════════════════════════════════════════════╗
║                 ✓ SISTEMA INICIADO                     ║
╚════════════════════════════════════════════════════════╝

Servicios activos:

  █ Aplicación Web:
    ➜  http://localhost:3012
    Interfaz principal para subir PDFs y ver proyectos

  █ API Backend:
    ➜  http://localhost:3013
    ➜  http://localhost:3013/docs (Documentación)
```

### 2️⃣ Abrir tu navegador

```
http://localhost:3012
```

### 3️⃣ Subir un PDF

1. Arrastra un PDF de presupuesto
2. Click en "Procesar PDF"
3. ¡Listo! Verás el presupuesto procesado

## 📥 Exportar

En la página del proyecto, click en:
- 📄 **CSV** - Para importar en hojas de cálculo
- 📊 **Excel** - Con formato y dos hojas
- 📋 **XML** - Para intercambio de datos
- 🏗️ **BC3** - Formato estándar español

## 🛑 Detener

```bash
./stop.sh
```

O presiona `Ctrl+C` en la terminal

## 📍 URLs Importantes

| Servicio | URL | Uso |
|----------|-----|-----|
| **App Web** | http://localhost:3012 | Interfaz principal |
| **API Docs** | http://localhost:3013/docs | Documentación Swagger |
| **Health API** | http://localhost:3013/health | Estado del API |
| **Health App** | http://localhost:3012/health | Estado de la App |

## 🎯 Ejemplo con el PDF incluido

Si tienes el archivo de ejemplo:

```bash
# 1. Iniciar
./start.sh

# 2. Abrir navegador en http://localhost:3012

# 3. Arrastrar: ejemplo/PROYECTO CALYPOFADO_extract.pdf

# 4. ¡Listo!
```

Deberías ver:
- ✅ 2 Capítulos
- ✅ 8 Subcapítulos
- ✅ 2 Apartados
- ✅ 102 Partidas

## 🐛 Si algo falla

### Puerto ocupado
```bash
./stop.sh
./start.sh
```

### Ver logs
```bash
tail -f logs/api.log logs/app.log
```

### Reinstalar dependencias
```bash
source venv/bin/activate
pip install --upgrade -r requirements.txt
```

## 📚 Más información

- **Guía completa**: [README_APP.md](README_APP.md)
- **Arquitectura**: [SISTEMA_COMPLETO.md](SISTEMA_COMPLETO.md)
- **API Original**: [README.md](README.md)

---

**¡Disfruta procesando presupuestos! 🎉**
