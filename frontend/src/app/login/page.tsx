// Página de Login
'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/store/authStore'
import { login } from '@/lib/api'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
import { FileText, AlertCircle } from 'lucide-react'

// Auto-login en desarrollo
const DEV_MODE = process.env.NODE_ENV === 'development'
const AUTO_LOGIN_ENV = process.env.NEXT_PUBLIC_AUTO_LOGIN !== 'false' // Se puede desactivar con env var
const AUTO_LOGIN = DEV_MODE && AUTO_LOGIN_ENV

export default function LoginPage() {
  const router = useRouter()
  const setAuth = useAuthStore((state) => state.setAuth)

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(AUTO_LOGIN) // Start loading if auto-login

  // Auto-login en desarrollo
  useEffect(() => {
    if (AUTO_LOGIN) {
      const autoLogin = async () => {
        try {
          const response = await login('admin', 'admin123')
          setAuth(response.access_token, response.user)
          router.push('/dashboard')
        } catch (err: any) {
          // Si falla el auto-login, mostrar formulario
          setIsLoading(false)
          setError('Auto-login falló. Por favor, inicia sesión manualmente.')
        }
      }
      autoLogin()
    }
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)

    try {
      const response = await login(username, password)
      setAuth(response.access_token, response.user)
      router.push('/dashboard')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al iniciar sesión')
    } finally {
      setIsLoading(false)
    }
  }

  // Mostrar loading durante auto-login
  if (AUTO_LOGIN && isLoading && !error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-50 to-primary-100 px-4">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-primary-600 rounded-full mb-4">
            <FileText className="h-8 w-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-gray-900 mb-4">Mediciones V2</h1>
          <div className="flex items-center justify-center space-x-2">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600"></div>
            <p className="text-gray-600">Iniciando sesión automáticamente...</p>
          </div>
          <p className="text-xs text-gray-500 mt-4">Modo desarrollo - Auto-login activado</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-50 to-primary-100 px-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-primary-600 rounded-full mb-4">
            <FileText className="h-8 w-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-gray-900">Mediciones V2</h1>
          <p className="text-gray-600 mt-2">Sistema de Gestión de Presupuestos</p>
        </div>

        {/* Login Card */}
        <Card>
          <CardHeader>
            <CardTitle>Iniciar Sesión</CardTitle>
            <CardDescription>
              Ingresa tus credenciales para acceder al sistema
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Error Alert */}
              {error && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start space-x-3">
                  <AlertCircle className="h-5 w-5 text-red-600 mt-0.5" />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-red-800">Error</p>
                    <p className="text-sm text-red-700">{error}</p>
                  </div>
                </div>
              )}

              {/* Username */}
              <Input
                label="Usuario"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="admin"
                required
                autoFocus
              />

              {/* Password */}
              <Input
                label="Contraseña"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
              />

              {/* Submit Button */}
              <Button
                type="submit"
                className="w-full"
                isLoading={isLoading}
                disabled={!username || !password}
              >
                Iniciar Sesión
              </Button>
            </form>

            {/* Demo Credentials */}
            <div className="mt-6 p-4 bg-gray-50 rounded-lg">
              <p className="text-xs font-medium text-gray-700 mb-2">
                Credenciales de demostración:
              </p>
              <p className="text-xs text-gray-600">
                Usuario: <code className="bg-white px-1 py-0.5 rounded">admin</code>
              </p>
              <p className="text-xs text-gray-600">
                Contraseña: <code className="bg-white px-1 py-0.5 rounded">admin123</code>
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Footer */}
        <p className="text-center text-sm text-gray-600 mt-8">
          Sistema de Mediciones V2 - Enero 2026
        </p>
      </div>
    </div>
  )
}
