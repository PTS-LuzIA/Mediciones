# API REST V2 - Documentación
## Sistema de Mediciones - Production Ready

---

## 🚀 Quick Start

### 1. Instalar Dependencias

```bash
pip install -r requirements_api.txt
```

### 2. Configurar Variables (.env)

Asegúrate de tener en `.env`:

```bash
# API Security
SECRET_KEY=your_secret_key_here  # Generar con: openssl rand -hex 32
DEBUG=True  # False en producción

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=mediciones_db
POSTGRES_USER=imac
POSTGRES_PASSWORD=
```

### 3. Ejecutar API

```bash
# Desarrollo (con auto-reload)
python run_api.py

# Producción
python run_api.py --production
```

La API estará disponible en: `http://localhost:8000`

---

## 📚 Documentación Interactiva

Una vez ejecutando, accede a:

- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

---

## 🔐 Autenticación

### Login

**Endpoint**: `POST /api/auth/login`

**Request**:
```json
{
  "username": "admin",
  "password": "admin123"
}
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "username": "admin",
    "user_id": 1
  }
}
```

### Usar Token

Incluir en headers de todas las peticiones autenticadas:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## 📋 Endpoints

### Health Check

```http
GET /
```

**Response**:
```json
{
  "app": "Mediciones API V2",
  "version": "2.0.0",
  "status": "healthy"
}
```

---

### Autenticación

#### Login

```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "admin123"
}
```

---

### Proyectos

#### Listar Proyectos

```http
GET /api/proyectos
Authorization: Bearer {token}
```

**Response**:
```json
[
  {
    "id": 1,
    "nombre": "Proyecto Tolosa",
    "fecha_creacion": "2026-01-17T21:30:00",
    "presupuesto_total": 500125.75,
    "layout_detectado": "double_column",
    "tiene_mediciones_auxiliares": false,
    "num_capitulos": 15
  }
]
```

---

#### Obtener Proyecto Completo

```http
GET /api/proyectos/{proyecto_id}
Authorization: Bearer {token}
```

**Response**: Proyecto con toda la jerarquía (capítulos, subcapítulos, partidas, mediciones)

---

#### Upload PDF

```http
POST /api/proyectos/upload
Authorization: Bearer {token}
Content-Type: multipart/form-data

file: <archivo.pdf>
```

**Response**:
```json
{
  "success": true,
  "message": "PDF procesado exitosamente",
  "proyecto_id": 2,
  "filename": "proyecto.pdf",
  "size_bytes": 1048576,
  "procesamiento": {
    "total_capitulos": 10,
    "total_subcapitulos": 35,
    "total_partidas": 156,
    "presupuesto_total": 1234567.89
  }
}
```

---

#### Estadísticas de Proyecto

```http
GET /api/proyectos/{proyecto_id}/stats
Authorization: Bearer {token}
```

**Response**:
```json
{
  "total_capitulos": 10,
  "total_subcapitulos": 35,
  "total_partidas": 156,
  "partidas_con_mediciones": 98,
  "presupuesto_total": 1234567.89
}
```

---

#### Eliminar Proyecto

```http
DELETE /api/proyectos/{proyecto_id}
Authorization: Bearer {token}
```

**Response**:
```json
{
  "success": true,
  "message": "Proyecto 2 eliminado correctamente"
}
```

---

### Validación

#### Validar Mediciones

```http
GET /api/proyectos/{proyecto_id}/validar
Authorization: Bearer {token}
```

**Response**:
```json
{
  "proyecto_id": 2,
  "total_partidas": 156,
  "partidas_con_mediciones": 98,
  "partidas_validas": 95,
  "partidas_invalidas": 3,
  "detalles_invalidas": [
    {
      "codigo": "E31OA30A",
      "cantidad_total": 3.00,
      "suma_parciales": 3.50,
      "diferencia": 0.50,
      "valido": false
    }
  ]
}
```

---

## 🔒 Seguridad

### Capas de Seguridad Implementadas

1. **Autenticación JWT**
   - Tokens firmados con HS256
   - Expiración configurable (default: 30 min)
   - Refresh automático (TODO)

2. **Rate Limiting**
   - Login: 5 req/min
   - Upload: 10 req/min
   - General: 60 req/min

3. **CORS**
   - Dominios permitidos configurables
   - Solo métodos HTTP necesarios

4. **Validación**
   - Pydantic schemas en todos los inputs
   - Validación de tipos de archivo
   - Límite de tamaño (50MB)

5. **SQL Injection**
   - Protección automática de SQLAlchemy
   - Prepared statements

6. **File Upload**
   - Solo archivos PDF
   - Validación de extensión
   - Validación de tamaño
   - Sanitización de nombres

7. **Logging**
   - Todos los accesos registrados
   - Logs de errores completos
   - Auditoría de operaciones

---

## ⚙️ Configuración

### Variables de Entorno

```bash
# Aplicación
APP_NAME=Mediciones API V2
APP_VERSION=2.0.0
DEBUG=True  # False en producción

# Seguridad
SECRET_KEY=your_secret_key_here
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60

# Upload
MAX_UPLOAD_SIZE=52428800  # 50 MB en bytes

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=mediciones_db
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password

# Logging
LOG_LEVEL=INFO
```

---

## 📊 Rate Limits

| Endpoint | Límite |
|----------|--------|
| `POST /api/auth/login` | 5/min |
| `POST /api/proyectos/upload` | 10/min |
| `GET /` | 10/min |
| Otros endpoints | 60/min |

---

## 🚨 Códigos de Error

| Código | Descripción |
|--------|-------------|
| 400 | Bad Request - Validación fallida |
| 401 | Unauthorized - Token inválido/expirado |
| 403 | Forbidden - Sin permisos |
| 404 | Not Found - Recurso no encontrado |
| 413 | Request Entity Too Large - Archivo muy grande |
| 429 | Too Many Requests - Rate limit excedido |
| 500 | Internal Server Error - Error del servidor |

---

## 🧪 Testing

### Con cURL

```bash
# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# Listar proyectos
curl -X GET http://localhost:8000/api/proyectos \
  -H "Authorization: Bearer YOUR_TOKEN"

# Upload PDF
curl -X POST http://localhost:8000/api/proyectos/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@/path/to/proyecto.pdf"
```

### Con Python

```python
import requests

# Login
response = requests.post(
    "http://localhost:8000/api/auth/login",
    json={"username": "admin", "password": "admin123"}
)
token = response.json()["access_token"]

# Listar proyectos
response = requests.get(
    "http://localhost:8000/api/proyectos",
    headers={"Authorization": f"Bearer {token}"}
)
proyectos = response.json()
```

---

## 🐳 Docker (Producción)

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copiar requirements
COPY requirements_api.txt .
RUN pip install --no-cache-dir -r requirements_api.txt

# Copiar código
COPY . .

# Exponer puerto
EXPOSE 8000

# Ejecutar API
CMD ["python", "run_api.py", "--production", "--host", "0.0.0.0"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DEBUG=False
      - POSTGRES_HOST=postgres
      - SECRET_KEY=${SECRET_KEY}
    depends_on:
      - postgres

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: mediciones_db
      POSTGRES_USER: mediciones_user
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

---

## 📝 Notas de Producción

### Antes de Desplegar

1. **Generar SECRET_KEY**:
   ```bash
   openssl rand -hex 32
   ```

2. **Desactivar DEBUG**:
   ```bash
   DEBUG=False
   ```

3. **Configurar HTTPS** (Nginx + Certbot)

4. **Configurar CORS** (dominios de producción)

5. **Revisar Rate Limits** (según carga esperada)

6. **Configurar Logging** (archivo + servicio externo)

7. **Backup de PostgreSQL** (automático)

---

## 🔧 Troubleshooting

### Error: SECRET_KEY en producción

```
⚠️  CRITICAL: SECRET_KEY must be changed in production!
```

**Solución**: Generar y configurar SECRET_KEY en `.env`

### Error: CORS

```
Access to fetch at 'http://api...' from origin 'http://frontend...' has been blocked by CORS policy
```

**Solución**: Añadir el dominio del frontend en `settings.CORS_ORIGINS`

### Error: Rate limit excedido

```
429 Too Many Requests
```

**Solución**: Esperar o ajustar `RATE_LIMIT_PER_MINUTE` en config

---

## 📞 Soporte

- **Logs**: `logs/api_v2.log`
- **Swagger**: `/api/docs`
- **ReDoc**: `/api/redoc`

---

**Versión**: 2.0.0
**Fecha**: Enero 2026
