# Frontend Mediciones V2 - React + Next.js

## 🚀 Stack Tecnológico

- **React 18** - UI Library
- **Next.js 14** - Framework (App Router)
- **TypeScript** - Type Safety
- **TailwindCSS** - Styling
- **React Query** - Data Fetching & Caching
- **Zustand** - State Management
- **Axios** - HTTP Client
- **Lucide React** - Icons

---

## 📦 Instalación

```bash
cd frontend
npm install
```

---

## 🏃 Ejecutar

### Desarrollo

```bash
npm run dev
```

Abre: **http://localhost:3015**

### Producción

```bash
npm run build
npm start
```

---

## 🔑 Credenciales Demo

```
Usuario: admin
Contraseña: admin123
```

---

## 📁 Estructura

```
frontend/
├── src/
│   ├── app/                    # Pages (App Router)
│   │   ├── (protected)/       # Rutas protegidas
│   │   │   ├── dashboard/     # Dashboard ✅
│   │   │   └── proyectos/     # Proyectos ✅
│   │   │       ├── page.tsx   # Lista de proyectos
│   │   │       ├── upload/    # Upload PDF
│   │   │       └── [id]/      # Detalle proyecto
│   │   ├── login/             # Login ✅
│   │   └── page.tsx           # Home (redirect)
│   │
│   ├── components/            # Componentes React
│   │   ├── ui/               # Componentes base (Button, Card, Input)
│   │   ├── Navbar.tsx        # Navegación
│   │   └── ProtectedRoute.tsx # HOC protección
│   │
│   ├── lib/                   # Utilidades
│   │   ├── api.ts            # Cliente API (Axios)
│   │   └── utils.ts          # Helpers
│   │
│   ├── store/                 # State global (Zustand)
│   │   └── authStore.ts      # Auth state
│   │
│   └── types/                 # TypeScript types
│       └── index.ts          # Todos los types
│
├── public/                    # Assets estáticos
└── package.json
```

---

## ✅ Funcionalidades Implementadas

### 🔐 Autenticación
- [x] Login con JWT
- [x] Logout
- [x] Protección de rutas
- [x] Persistencia de sesión

### 📊 Dashboard
- [x] Estadísticas generales (4 cards)
- [x] Últimos 5 proyectos
- [x] Quick actions
- [x] Loading states y error handling

### 📋 Lista de Proyectos
- [x] Tabla completa con todos los proyectos
- [x] Tarjetas visuales responsivas
- [x] Información detallada (fecha, capítulos, presupuesto)
- [x] Links a detalle de proyecto

### 📤 Upload PDF
- [x] Drag & drop funcional
- [x] File input alternativo
- [x] Progress indicator con animación
- [x] Validación de archivo (PDF only, max 10MB)
- [x] Preview y redirección al proyecto creado

### 📄 Detalle Proyecto
- [x] Jerarquía completa expandible (caps → subcaps → partidas)
- [x] 4 tarjetas de estadísticas
- [x] Tabla completa de partidas con todos los campos
- [x] Validación de mediciones auxiliares
- [x] Listado de partidas inválidas con diferencias
- [x] Botón "Validar Mediciones" dinámico

### 📈 Gráficos
- [x] Bar chart con distribución por capítulos (top 6)
- [x] Tooltips formateados en euros
- [x] Responsive container
- [x] Recharts integration

### 🎨 UI/UX
- [x] Componentes reutilizables (Button, Card, Input)
- [x] Responsive design completo
- [x] Loading states en todas las páginas
- [x] Error handling con mensajes informativos
- [x] Iconos Lucide React
- [x] TailwindCSS styling consistente

---

## 🔗 Conexión con Backend

El frontend se conecta automáticamente a:

```
http://localhost:8000
```

Configurado en: `.env.local`

---

## 🛠️ Scripts Disponibles

```bash
# Desarrollo
npm run dev

# Build
npm run build

# Producción
npm start

# Lint
npm run lint
```

---

## 📝 Notas

- **Solo exposición**: El frontend NO tiene lógica de negocio
- **Toda la lógica** está en el backend (FastAPI)
- **TypeScript strict**: Type safety completo
- **React Query**: Caché automático de datos
- **Zustand**: State management mínimo (solo auth)

---

## 🐛 Troubleshooting

### Error: Cannot connect to API

**Solución**: Asegúrate de que el backend esté corriendo:

```bash
cd ..
python run_api.py
```

### Error: Module not found

**Solución**: Reinstala dependencias:

```bash
rm -rf node_modules package-lock.json
npm install
```

---

**Estado**: ✅ 100% Completado
**Incluye**: Login, Dashboard, Lista Proyectos, Upload PDF, Detalle con Validación y Gráficos
