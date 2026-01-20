// Dashboard principal
'use client'

import { useQuery } from '@tanstack/react-query'
import { getProyectos } from '@/lib/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
import { formatEuros, formatDate } from '@/lib/utils'
import { FileText, TrendingUp, CheckCircle, AlertCircle, Upload, FolderOpen } from 'lucide-react'
import Link from 'next/link'
import Button from '@/components/ui/Button'

export default function DashboardPage() {
  // Cargar proyectos
  const { data: proyectos, isLoading, error } = useQuery({
    queryKey: ['proyectos'],
    queryFn: getProyectos,
  })

  // Calcular estadísticas
  const stats = proyectos ? {
    totalProyectos: proyectos.length,
    presupuestoTotal: proyectos.reduce((sum, p) => sum + Number(p.presupuesto_total), 0),
    conMediciones: proyectos.filter(p => p.tiene_mediciones_auxiliares).length,
    ultimosProyectos: proyectos.slice(0, 5),
  } : null

  if (error) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
        <h2 className="text-xl font-semibold text-gray-900 mb-2">Error al cargar datos</h2>
        <p className="text-gray-600">No se pudieron cargar los proyectos</p>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-600 mt-1">Resumen general del sistema</p>
        </div>
        <Link href="/proyectos/upload">
          <Button className="flex items-center space-x-2">
            <Upload className="h-5 w-5" />
            <span>Nuevo Proyecto</span>
          </Button>
        </Link>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Total Proyectos */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Total Proyectos</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">
                  {isLoading ? '...' : stats?.totalProyectos || 0}
                </p>
              </div>
              <div className="h-12 w-12 bg-primary-100 rounded-full flex items-center justify-center">
                <FolderOpen className="h-6 w-6 text-primary-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Presupuesto Total */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Presupuesto Total</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">
                  {isLoading ? '...' : formatEuros(stats?.presupuestoTotal || 0).slice(0, -3) + 'K'}
                </p>
              </div>
              <div className="h-12 w-12 bg-green-100 rounded-full flex items-center justify-center">
                <TrendingUp className="h-6 w-6 text-green-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Con Mediciones */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Con Mediciones</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">
                  {isLoading ? '...' : stats?.conMediciones || 0}
                </p>
              </div>
              <div className="h-12 w-12 bg-blue-100 rounded-full flex items-center justify-center">
                <CheckCircle className="h-6 w-6 text-blue-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Sin Mediciones */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Sin Mediciones</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">
                  {isLoading ? '...' : (stats?.totalProyectos || 0) - (stats?.conMediciones || 0)}
                </p>
              </div>
              <div className="h-12 w-12 bg-yellow-100 rounded-full flex items-center justify-center">
                <FileText className="h-6 w-6 text-yellow-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Últimos Proyectos */}
      <Card>
        <CardHeader>
          <CardTitle>Últimos Proyectos</CardTitle>
          <CardDescription>Proyectos procesados recientemente</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto"></div>
            </div>
          ) : stats?.ultimosProyectos && stats.ultimosProyectos.length > 0 ? (
            <div className="space-y-4">
              {stats.ultimosProyectos.map((proyecto) => (
                <Link
                  key={proyecto.id}
                  href={`/proyectos/${proyecto.id}`}
                  className="block p-4 rounded-lg border border-gray-200 hover:border-primary-300 hover:bg-primary-50 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <h3 className="font-medium text-gray-900">{proyecto.nombre}</h3>
                      <p className="text-sm text-gray-600 mt-1">
                        {formatDate(proyecto.fecha_creacion)} • {proyecto.num_capitulos} capítulos
                      </p>
                    </div>
                    <div className="text-right ml-4">
                      <p className="font-semibold text-gray-900">
                        {formatEuros(Number(proyecto.presupuesto_total))}
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        {proyecto.tiene_mediciones_auxiliares ? 'Con mediciones' : 'Sin mediciones'}
                      </p>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <div className="text-center py-12">
              <FolderOpen className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No hay proyectos</h3>
              <p className="text-gray-600 mb-4">Comienza subiendo tu primer PDF</p>
              <Link href="/proyectos/upload">
                <Button>
                  <Upload className="h-4 w-4 mr-2" />
                  Subir Proyecto
                </Button>
              </Link>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card className="bg-gradient-to-br from-primary-50 to-primary-100 border-primary-200">
          <CardContent className="pt-6">
            <FileText className="h-10 w-10 text-primary-600 mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Nuevo Proyecto</h3>
            <p className="text-sm text-gray-600 mb-4">
              Sube un PDF de presupuesto para procesarlo automáticamente
            </p>
            <Link href="/proyectos/upload">
              <Button variant="primary">Subir PDF</Button>
            </Link>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200">
          <CardContent className="pt-6">
            <FolderOpen className="h-10 w-10 text-blue-600 mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Ver Proyectos</h3>
            <p className="text-sm text-gray-600 mb-4">
              Explora todos los proyectos procesados y sus detalles
            </p>
            <Link href="/proyectos">
              <Button variant="secondary">Ver Todos</Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
