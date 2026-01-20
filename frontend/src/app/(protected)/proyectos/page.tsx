// Lista de todos los proyectos
'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getProyectos, deleteProyecto } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import { formatEuros, formatDateTime } from '@/lib/utils'
import { Upload, Search, Eye, Trash2, FileText, AlertCircle, CheckCircle } from 'lucide-react'
import Link from 'next/link'

export default function ProyectosPage() {
  const queryClient = useQueryClient()
  const [searchTerm, setSearchTerm] = useState('')

  // Cargar proyectos
  const { data: proyectos, isLoading } = useQuery({
    queryKey: ['proyectos'],
    queryFn: getProyectos,
  })

  // Mutation para eliminar
  const deleteMutation = useMutation({
    mutationFn: deleteProyecto,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['proyectos'] })
    },
  })

  // Filtrar proyectos
  const proyectosFiltrados = proyectos?.filter(p =>
    p.nombre.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const handleDelete = async (id: number, nombre: string) => {
    if (confirm(`¿Eliminar proyecto "${nombre}"?`)) {
      try {
        await deleteMutation.mutateAsync(id)
      } catch (error) {
        alert('Error al eliminar proyecto')
      }
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Proyectos</h1>
          <p className="text-gray-600 mt-1">
            {proyectos?.length || 0} proyectos en total
          </p>
        </div>
        <Link href="/proyectos/upload">
          <Button className="flex items-center space-x-2">
            <Upload className="h-5 w-5" />
            <span>Subir Proyecto</span>
          </Button>
        </Link>
      </div>

      {/* Búsqueda */}
      <Card>
        <CardContent className="pt-6">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
            <Input
              type="text"
              placeholder="Buscar proyectos..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>
        </CardContent>
      </Card>

      {/* Tabla de Proyectos */}
      <Card>
        <CardHeader>
          <CardTitle>Todos los Proyectos</CardTitle>
          <CardDescription>
            Lista completa de proyectos procesados
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
              <p className="text-gray-600 mt-4">Cargando proyectos...</p>
            </div>
          ) : proyectosFiltrados && proyectosFiltrados.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-3 px-4 font-semibold text-gray-700">Proyecto</th>
                    <th className="text-left py-3 px-4 font-semibold text-gray-700">Fecha</th>
                    <th className="text-left py-3 px-4 font-semibold text-gray-700">Layout</th>
                    <th className="text-left py-3 px-4 font-semibold text-gray-700">Mediciones</th>
                    <th className="text-right py-3 px-4 font-semibold text-gray-700">Presupuesto</th>
                    <th className="text-right py-3 px-4 font-semibold text-gray-700">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {proyectosFiltrados.map((proyecto) => (
                    <tr
                      key={proyecto.id}
                      className="border-b border-gray-100 hover:bg-gray-50 transition-colors"
                    >
                      <td className="py-4 px-4">
                        <div className="flex items-center space-x-3">
                          <div className="h-10 w-10 bg-primary-100 rounded-lg flex items-center justify-center">
                            <FileText className="h-5 w-5 text-primary-600" />
                          </div>
                          <div>
                            <p className="font-medium text-gray-900">{proyecto.nombre}</p>
                            <p className="text-sm text-gray-500">
                              {proyecto.num_capitulos} capítulos
                            </p>
                          </div>
                        </div>
                      </td>
                      <td className="py-4 px-4">
                        <p className="text-sm text-gray-900">
                          {formatDateTime(proyecto.fecha_creacion)}
                        </p>
                      </td>
                      <td className="py-4 px-4">
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                          {proyecto.layout_detectado === 'double_column' ? '2 columnas' : '1 columna'}
                        </span>
                      </td>
                      <td className="py-4 px-4">
                        {proyecto.tiene_mediciones_auxiliares ? (
                          <span className="inline-flex items-center text-sm text-green-700">
                            <CheckCircle className="h-4 w-4 mr-1" />
                            Con mediciones
                          </span>
                        ) : (
                          <span className="inline-flex items-center text-sm text-gray-500">
                            <AlertCircle className="h-4 w-4 mr-1" />
                            Sin mediciones
                          </span>
                        )}
                      </td>
                      <td className="py-4 px-4 text-right">
                        <p className="font-semibold text-gray-900">
                          {formatEuros(Number(proyecto.presupuesto_total))}
                        </p>
                      </td>
                      <td className="py-4 px-4">
                        <div className="flex items-center justify-end space-x-2">
                          <Link href={`/proyectos/${proyecto.id}`}>
                            <Button size="sm" variant="ghost">
                              <Eye className="h-4 w-4" />
                            </Button>
                          </Link>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleDelete(proyecto.id, proyecto.nombre)}
                            disabled={deleteMutation.isPending}
                          >
                            <Trash2 className="h-4 w-4 text-red-600" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-12">
              <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                {searchTerm ? 'No se encontraron proyectos' : 'No hay proyectos'}
              </h3>
              <p className="text-gray-600 mb-4">
                {searchTerm ? 'Intenta con otro término de búsqueda' : 'Comienza subiendo tu primer PDF'}
              </p>
              {!searchTerm && (
                <Link href="/proyectos/upload">
                  <Button>
                    <Upload className="h-4 w-4 mr-2" />
                    Subir Proyecto
                  </Button>
                </Link>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
