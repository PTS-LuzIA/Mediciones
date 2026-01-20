// Cliente API - Axios configurado para FastAPI backend
import axios, { AxiosError } from 'axios'
import type {
  LoginResponse,
  Proyecto,
  ProyectoDetalle,
  ProyectoStats,
  UploadResponse,
  ValidacionProyecto
} from '@/types'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// Instancia de Axios
export const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Interceptor para añadir token JWT automáticamente
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Interceptor para manejar errores 401 (token expirado)
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Token expirado - limpiar y redirigir a login
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// ============================================
// Auth
// ============================================

export const login = async (username: string, password: string): Promise<LoginResponse> => {
  const { data } = await api.post<LoginResponse>('/api/auth/login', {
    username,
    password,
  })
  return data
}

// ============================================
// Proyectos
// ============================================

export const getProyectos = async (): Promise<Proyecto[]> => {
  const { data } = await api.get<Proyecto[]>('/api/proyectos')
  return data
}

export const getProyecto = async (id: number): Promise<ProyectoDetalle> => {
  const { data } = await api.get<ProyectoDetalle>(`/api/proyectos/${id}`)
  return data
}

export const getProyectoStats = async (id: number): Promise<ProyectoStats> => {
  const { data} = await api.get<ProyectoStats>(`/api/proyectos/${id}/stats`)
  return data
}

export const uploadPDF = async (file: File): Promise<UploadResponse> => {
  const formData = new FormData()
  formData.append('file', file)

  const { data } = await api.post<UploadResponse>('/api/proyectos/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })

  return data
}

export const deleteProyecto = async (id: number): Promise<void> => {
  await api.delete(`/api/proyectos/${id}`)
}

export const validarProyecto = async (id: number): Promise<ValidacionProyecto> => {
  const { data } = await api.get<ValidacionProyecto>(`/api/proyectos/${id}/validar`)
  return data
}

// ============================================
// Health Check
// ============================================

export const healthCheck = async (): Promise<{ status: string }> => {
  const { data } = await api.get('/')
  return data
}
