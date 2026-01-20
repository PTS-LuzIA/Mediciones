// Utilidades generales
import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

// Combinar clases de Tailwind sin conflictos
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// Formatear números como euros
export function formatEuros(amount: number): string {
  return new Intl.NumberFormat('es-ES', {
    style: 'currency',
    currency: 'EUR',
  }).format(amount)
}

// Formatear fechas
export function formatDate(date: string | Date): string {
  return new Intl.DateTimeFormat('es-ES', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  }).format(new Date(date))
}

// Formatear fecha y hora
export function formatDateTime(date: string | Date): string {
  return new Intl.DateTimeFormat('es-ES', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(date))
}

// Formatear números con separadores de miles
export function formatNumber(num: number, decimals: number = 2): string {
  return new Intl.NumberFormat('es-ES', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(num)
}

// Truncar texto
export function truncate(text: string, length: number): string {
  if (text.length <= length) return text
  return text.substring(0, length) + '...'
}

// Obtener iniciales de nombre
export function getInitials(name: string): string {
  return name
    .split(' ')
    .map(word => word[0])
    .join('')
    .substring(0, 2)
    .toUpperCase()
}

// Validar archivo PDF
export function validatePDF(file: File): { valid: boolean; error?: string } {
  const maxSize = 50 * 1024 * 1024 // 50 MB

  if (!file.type.includes('pdf')) {
    return { valid: false, error: 'El archivo debe ser un PDF' }
  }

  if (file.size > maxSize) {
    return { valid: false, error: 'El archivo no puede superar 50MB' }
  }

  return { valid: true }
}
