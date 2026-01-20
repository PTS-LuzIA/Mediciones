# Sistema Mediciones V2

Sistema completo de procesamiento de PDFs de presupuestos con detección multi-formato.

## 🚀 Inicio Rápido

### 1. Iniciar el sistema completo

```bash
./start_v2.sh
```

Este script automáticamente:
- ✅ Verifica PostgreSQL
- ✅ Crea la base de datos si no existe
- ✅ Inicia el Backend API (puerto 8000)
- ✅ Inicia el Frontend (puerto 3015)

### 2. Acceder al sistema

Abre tu navegador en: **http://localhost:3015**

**Credenciales:**
- Usuario: `admin`
- Contraseña: `admin123`

### 3. Detener el sistema

```bash
./stop_v2.sh
```

### 4. Ver estado

```bash
./status_v2.sh
```

---

## 📚 URLs Importantes

- **Frontend**: http://localhost:3015
- **Backend API**: http://localhost:8000
- **API Docs (Swagger)**: http://localhost:8000/docs

---

## 🔧 Comandos Útiles

```bash
# Ver logs en tiempo real
tail -f logs/backend_v2.log logs/frontend_v2.log

# Reiniciar solo el backend
./stop_v2.sh && python run_api.py

# Reiniciar solo el frontend
cd frontend && npm run dev
```

---

## 📖 Documentación Completa

Ver [SISTEMA_V2_COMPLETADO.md](SISTEMA_V2_COMPLETADO.md) para documentación técnica detallada.

---

## 🎯 Características

- ✅ Detección automática de 4 formatos de PDF
- ✅ Procesamiento de mediciones auxiliares
- ✅ Validación de cantidades
- ✅ Frontend moderno con React + Next.js
- ✅ API REST con autenticación JWT
- ✅ PostgreSQL con schema aislado

---

## 🐛 Problemas Comunes

### Puerto ocupado

```bash
# Liberar puerto 8000
lsof -ti:8000 | xargs kill -9

# Liberar puerto 3015
lsof -ti:3015 | xargs kill -9
```

### PostgreSQL no inicia

```bash
# Con Homebrew
brew services start postgresql

# Verificar
pg_isready -h localhost -p 5432
```

### Frontend no encuentra dependencias

```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

---

**Estado**: ✅ 100% Completado y funcional

---

## 🔓 Auto-Login en Desarrollo

Por defecto, el sistema está configurado para **iniciar sesión automáticamente** en modo desarrollo para facilitar el testing.

### Activado por defecto

Cuando accedes a http://localhost:3015, automáticamente:
1. Hace login con `admin/admin123`
2. Redirige al dashboard
3. Muestra un mensaje "Iniciando sesión automáticamente..."

### Desactivar Auto-Login

Si prefieres ver la pantalla de login, hay dos opciones:

**Opción 1: Variable de entorno (Recomendado)**

Edita `frontend/.env.local`:
```bash
NEXT_PUBLIC_AUTO_LOGIN=false
```

Luego reinicia el frontend:
```bash
cd frontend && npm run dev
```

**Opción 2: Cambiar código**

Edita `frontend/src/app/login/page.tsx` línea 14:
```typescript
const AUTO_LOGIN = false  // Cambiar a false
```

### En Producción

El auto-login **solo funciona en desarrollo** (`NODE_ENV === 'development'`).

En producción automáticamente se desactiva y siempre mostrará la pantalla de login.

