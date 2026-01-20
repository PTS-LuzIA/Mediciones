// Store global de autenticación con Zustand
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User } from '@/types'

interface AuthState {
  token: string | null
  user: User | null
  isAuthenticated: boolean

  // Actions
  setAuth: (token: string, user: User) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      isAuthenticated: false,

      setAuth: (token, user) => {
        // Guardar también en localStorage para el interceptor de Axios
        localStorage.setItem('token', token)
        localStorage.setItem('user', JSON.stringify(user))

        set({
          token,
          user,
          isAuthenticated: true,
        })
      },

      logout: () => {
        localStorage.removeItem('token')
        localStorage.removeItem('user')

        set({
          token: null,
          user: null,
          isAuthenticated: false,
        })
      },
    }),
    {
      name: 'auth-storage', // nombre en localStorage
    }
  )
)
