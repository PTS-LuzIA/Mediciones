// Página de upload de PDF
'use client'

import { useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { useMutation } from '@tanstack/react-query'
import { uploadPDF } from '@/lib/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import { validatePDF, formatEuros } from '@/lib/utils'
import { Upload, FileText, CheckCircle, AlertCircle, ArrowLeft } from 'lucide-react'
import Link from 'next/link'

export default function UploadPage() {
  const router = useRouter()
  const [file, setFile] = useState<File | null>(null)
  const [dragActive, setDragActive] = useState(false)
  const [error, setError] = useState('')

  // Mutation de upload
  const uploadMutation = useMutation({
    mutationFn: uploadPDF,
    onSuccess: (data) => {
      // Redirigir a la página de edición para procesar por fases
      router.push(`/proyectos/${data.proyecto_id}/editar`)
    },
    onError: (error: any) => {
      setError(error.response?.data?.detail || 'Error al procesar PDF')
    },
  })

  // Manejar selección de archivo
  const handleFileChange = (selectedFile: File | null) => {
    setError('')

    if (!selectedFile) {
      setFile(null)
      return
    }

    const validation = validatePDF(selectedFile)
    if (!validation.valid) {
      setError(validation.error || '')
      setFile(null)
      return
    }

    setFile(selectedFile)
  }

  // Drag & Drop handlers
  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileChange(e.dataTransfer.files[0])
    }
  }, [])

  // Submit
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file) return

    uploadMutation.mutate(file)
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center space-x-4">
        <Link href="/proyectos">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Volver
          </Button>
        </Link>
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Subir Proyecto</h1>
          <p className="text-gray-600 mt-1">Procesa un PDF de presupuesto automáticamente</p>
        </div>
      </div>

      {/* Upload Card */}
      <Card>
        <CardHeader>
          <CardTitle>Seleccionar PDF</CardTitle>
          <CardDescription>
            El sistema detectará automáticamente el formato y procesará las mediciones
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Drag & Drop Area */}
            <div
              className={`relative border-2 border-dashed rounded-lg p-12 text-center transition-colors ${
                dragActive
                  ? 'border-primary-500 bg-primary-50'
                  : file
                  ? 'border-green-500 bg-green-50'
                  : 'border-gray-300 hover:border-gray-400'
              }`}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
            >
              <input
                type="file"
                accept=".pdf"
                onChange={(e) => handleFileChange(e.target.files?.[0] || null)}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                disabled={uploadMutation.isPending}
              />

              {file ? (
                <div className="space-y-4">
                  <div className="inline-flex items-center justify-center w-16 h-16 bg-green-100 rounded-full">
                    <CheckCircle className="h-8 w-8 text-green-600" />
                  </div>
                  <div>
                    <p className="text-lg font-medium text-gray-900">{file.name}</p>
                    <p className="text-sm text-gray-600 mt-1">
                      {(file.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={(e) => {
                      e.preventDefault()
                      setFile(null)
                    }}
                  >
                    Cambiar archivo
                  </Button>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="inline-flex items-center justify-center w-16 h-16 bg-gray-100 rounded-full">
                    <Upload className="h-8 w-8 text-gray-600" />
                  </div>
                  <div>
                    <p className="text-lg font-medium text-gray-900">
                      {dragActive ? 'Suelta el archivo aquí' : 'Arrastra un PDF aquí'}
                    </p>
                    <p className="text-sm text-gray-600 mt-1">
                      o haz clic para seleccionar
                    </p>
                  </div>
                  <p className="text-xs text-gray-500">
                    Máximo 50MB • Solo archivos PDF
                  </p>
                </div>
              )}
            </div>

            {/* Error */}
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start space-x-3">
                <AlertCircle className="h-5 w-5 text-red-600 mt-0.5 flex-shrink-0" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-red-800">Error</p>
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              </div>
            )}

            {/* Success (mientras procesa) */}
            {uploadMutation.isPending && (
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="flex items-center space-x-3">
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-blue-800">Procesando PDF...</p>
                    <p className="text-sm text-blue-700">
                      Detectando formato, extrayendo datos y guardando en base de datos
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Submit Button */}
            <div className="flex justify-end space-x-3">
              <Link href="/proyectos">
                <Button type="button" variant="ghost">
                  Cancelar
                </Button>
              </Link>
              <Button
                type="submit"
                disabled={!file || uploadMutation.isPending}
                isLoading={uploadMutation.isPending}
              >
                <Upload className="h-4 w-4 mr-2" />
                Procesar PDF
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* Info Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-start space-x-3">
              <div className="flex-shrink-0">
                <div className="h-8 w-8 bg-primary-100 rounded-full flex items-center justify-center">
                  <FileText className="h-5 w-5 text-primary-600" />
                </div>
              </div>
              <div>
                <h3 className="font-medium text-gray-900 mb-1">Detección Automática</h3>
                <p className="text-sm text-gray-600">
                  El sistema detecta automáticamente si el PDF tiene 1 o 2 columnas
                  y si incluye mediciones auxiliares.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-start space-x-3">
              <div className="flex-shrink-0">
                <div className="h-8 w-8 bg-green-100 rounded-full flex items-center justify-center">
                  <CheckCircle className="h-5 w-5 text-green-600" />
                </div>
              </div>
              <div>
                <h3 className="font-medium text-gray-900 mb-1">Validación Completa</h3>
                <p className="text-sm text-gray-600">
                  Las mediciones parciales se validan automáticamente comparando
                  la suma con el total de cada partida.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
