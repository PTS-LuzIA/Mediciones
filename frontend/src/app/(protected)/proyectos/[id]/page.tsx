// Detalle completo de proyecto
'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getProyecto, getProyectoStats, validarProyecto } from '@/lib/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import { formatEuros, formatDateTime, formatNumber } from '@/lib/utils'
import {
  ArrowLeft,
  FileText,
  CheckCircle,
  AlertCircle,
  ChevronDown,
  ChevronRight,
  TrendingUp,
  Layers,
  BarChart3
} from 'lucide-react'
import Link from 'next/link'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']

export default function ProyectoDetallePage({ params }: { params: { id: string } }) {
  const proyectoId = parseInt(params.id)
  const [expandedCapitulos, setExpandedCapitulos] = useState<Set<number>>(new Set())
  const [expandedSubcapitulos, setExpandedSubcapitulos] = useState<Set<number>>(new Set())
  const [showValidacion, setShowValidacion] = useState(false)

  // Cargar proyecto
  const { data: proyecto, isLoading } = useQuery({
    queryKey: ['proyecto', proyectoId],
    queryFn: () => getProyecto(proyectoId),
  })

  // Cargar stats
  const { data: stats } = useQuery({
    queryKey: ['proyecto-stats', proyectoId],
    queryFn: () => getProyectoStats(proyectoId),
  })

  // Cargar validación (solo si tiene mediciones)
  const { data: validacion, refetch: refetchValidacion } = useQuery({
    queryKey: ['proyecto-validacion', proyectoId],
    queryFn: () => validarProyecto(proyectoId),
    enabled: showValidacion && proyecto?.tiene_mediciones_auxiliares === true,
  })

  const toggleCapitulo = (id: number) => {
    const newSet = new Set(expandedCapitulos)
    if (newSet.has(id)) {
      newSet.delete(id)
    } else {
      newSet.add(id)
    }
    setExpandedCapitulos(newSet)
  }

  const toggleSubcapitulo = (id: number) => {
    const newSet = new Set(expandedSubcapitulos)
    if (newSet.has(id)) {
      newSet.delete(id)
    } else {
      newSet.add(id)
    }
    setExpandedSubcapitulos(newSet)
  }

  // Reconstruir jerarquía de subcapítulos desde lista plana
  const buildSubcapituloTree = (subcapitulos: any[]) => {
    if (!subcapitulos || subcapitulos.length === 0) return []

    // Crear mapa por código
    const map: { [key: string]: any } = {}
    const roots: any[] = []

    // Primero, crear una copia de cada subcapítulo con array de hijos
    subcapitulos.forEach(sub => {
      map[sub.codigo] = { ...sub, children: [] }
    })

    // Construir árbol
    subcapitulos.forEach(sub => {
      const node = map[sub.codigo]

      // Determinar si es raíz o tiene padre
      const parts = sub.codigo.split('.')

      if (parts.length === 2) {
        // Nivel 1: es raíz (ej: 01.01)
        roots.push(node)
      } else {
        // Nivel 2+: buscar padre (ej: 01.01.01 -> padre: 01.01)
        const parentCode = parts.slice(0, -1).join('.')
        const parent = map[parentCode]

        if (parent) {
          parent.children.push(node)
        } else {
          // Si no encuentra padre, agregar como raíz (fallback)
          roots.push(node)
        }
      }
    })

    return roots
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Cargando proyecto...</p>
        </div>
      </div>
    )
  }

  if (!proyecto) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
        <h2 className="text-xl font-semibold text-gray-900">Proyecto no encontrado</h2>
      </div>
    )
  }

  // Preparar datos para gráficos
  const chartData = proyecto.capitulos.slice(0, 6).map(cap => ({
    nombre: cap.codigo,
    total: Number(cap.total)
  }))

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center space-x-4">
          <Link href="/proyectos">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Volver
            </Button>
          </Link>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">{proyecto.nombre}</h1>
            <p className="text-gray-600 mt-1">
              Procesado el {formatDateTime(proyecto.fecha_creacion)}
            </p>
          </div>
        </div>

        <div className="flex gap-2">
          <Link href={`/proyectos/${proyectoId}/editar`}>
            <Button variant="outline">
              <FileText className="h-4 w-4 mr-2" />
              Procesar por Fases
            </Button>
          </Link>

          {proyecto.tiene_mediciones_auxiliares && (
            <Button
              onClick={() => {
                setShowValidacion(true)
              refetchValidacion()
            }}
            variant="secondary"
          >
            <CheckCircle className="h-4 w-4 mr-2" />
            Validar Mediciones
          </Button>
          )}
        </div>
      </div>

      {/* Info Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Presupuesto Total</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">
                  {formatEuros(Number(proyecto.presupuesto_total))}
                </p>
              </div>
              <TrendingUp className="h-8 w-8 text-green-600" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Capítulos</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">
                  {stats?.total_capitulos || 0}
                </p>
              </div>
              <Layers className="h-8 w-8 text-blue-600" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Partidas</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">
                  {stats?.total_partidas || 0}
                </p>
              </div>
              <FileText className="h-8 w-8 text-purple-600" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Layout</p>
                <p className="text-lg font-semibold text-gray-900 mt-1">
                  {proyecto.layout_detectado === 'double_column' ? '2 Columnas' : '1 Columna'}
                </p>
              </div>
              <BarChart3 className="h-8 w-8 text-orange-600" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Validación Results */}
      {showValidacion && validacion && (
        <Card className={validacion.partidas_invalidas > 0 ? 'border-red-300' : 'border-green-300'}>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              {validacion.partidas_invalidas > 0 ? (
                <AlertCircle className="h-5 w-5 text-red-600" />
              ) : (
                <CheckCircle className="h-5 w-5 text-green-600" />
              )}
              <span>Resultado de Validación</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
              <div>
                <p className="text-sm text-gray-600">Total Partidas</p>
                <p className="text-xl font-bold">{validacion.total_partidas}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Con Mediciones</p>
                <p className="text-xl font-bold">{validacion.partidas_con_mediciones}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Válidas</p>
                <p className="text-xl font-bold text-green-600">{validacion.partidas_validas}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Inválidas</p>
                <p className="text-xl font-bold text-red-600">{validacion.partidas_invalidas}</p>
              </div>
            </div>

            {validacion.detalles_invalidas.length > 0 && (
              <div className="mt-4">
                <h4 className="font-medium text-gray-900 mb-2">Partidas con errores:</h4>
                <div className="space-y-2">
                  {validacion.detalles_invalidas.map((detalle, idx) => (
                    <div key={idx} className="bg-red-50 border border-red-200 rounded-lg p-3">
                      <p className="font-medium text-red-900">{detalle.codigo}</p>
                      <p className="text-sm text-red-700">
                        Total: {formatNumber(detalle.cantidad_total)} |
                        Suma parciales: {formatNumber(detalle.suma_parciales)} |
                        Diferencia: {formatNumber(detalle.diferencia)}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Gráfico */}
      {chartData.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Distribución por Capítulos</CardTitle>
            <CardDescription>Presupuesto de los principales capítulos</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="nombre" />
                <YAxis />
                <Tooltip formatter={(value) => formatEuros(Number(value))} />
                <Bar dataKey="total" fill="#3b82f6" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* Jerarquía Completa */}
      <Card>
        <CardHeader>
          <CardTitle>Estructura del Proyecto</CardTitle>
          <CardDescription>Jerarquía completa de capítulos, subcapítulos y partidas</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {proyecto.capitulos.map((capitulo) => (
              <div key={capitulo.id} className="border border-gray-200 rounded-lg">
                {/* Capítulo */}
                <button
                  onClick={() => toggleCapitulo(capitulo.id)}
                  className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center space-x-3">
                    {expandedCapitulos.has(capitulo.id) ? (
                      <ChevronDown className="h-5 w-5 text-gray-500" />
                    ) : (
                      <ChevronRight className="h-5 w-5 text-gray-500" />
                    )}
                    <div className="text-left">
                      <p className="font-semibold text-gray-900">
                        {capitulo.codigo} - {capitulo.nombre}
                      </p>
                      <p className="text-sm text-gray-600">
                        {capitulo.subcapitulos.length} subcapítulos
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="font-semibold text-gray-900">
                      {formatEuros(Number(capitulo.total))}
                      {capitulo.total_calculado && Math.abs(Number(capitulo.total) - Number(capitulo.total_calculado)) > 0.01 && (
                        <span className="text-xs text-yellow-600 ml-1">
                          ({formatEuros(Number(capitulo.total_calculado))})
                        </span>
                      )}
                    </p>
                  </div>
                </button>

                {/* Subcapítulos */}
                {expandedCapitulos.has(capitulo.id) && (
                  <div className="border-t border-gray-200 bg-gray-50">
                    {buildSubcapituloTree(capitulo.subcapitulos).map((subcap) =>
                      renderSubcapituloNode(subcap, 1)
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )

  // Función recursiva para renderizar nodos de subcapítulos
  function renderSubcapituloNode(subcap: any, nivel: number): JSX.Element {
    const paddingLeft = 12 + ((nivel - 1) * 24)
    const hasChildren = subcap.children && subcap.children.length > 0
    const hasPartidas = subcap.partidas && subcap.partidas.length > 0

    return (
      <div key={subcap.id} className="border-b border-gray-200 last:border-b-0">
        <button
          onClick={() => toggleSubcapitulo(subcap.id)}
          className="w-full flex items-center justify-between p-4 hover:bg-gray-100 transition-colors"
          style={{ paddingLeft: `${paddingLeft}px` }}
        >
          <div className="flex items-center space-x-3">
            {(hasChildren || hasPartidas) && (
              expandedSubcapitulos.has(subcap.id) ? (
                <ChevronDown className="h-4 w-4 text-gray-500" />
              ) : (
                <ChevronRight className="h-4 w-4 text-gray-500" />
              )
            )}
            {!hasChildren && !hasPartidas && (
              <div className="h-4 w-4" /> // Espacio vacío para alineación
            )}
            <div className="text-left">
              <p className="font-medium text-gray-900">
                {subcap.codigo} - {subcap.nombre}
              </p>
              <p className="text-sm text-gray-600">
                Nivel {subcap.nivel} • {subcap.partidas.length} partidas
              </p>
            </div>
          </div>
          <div className="text-right">
            <p className="font-medium text-gray-900">
              {formatEuros(Number(subcap.total))}
              {subcap.total_calculado && Math.abs(Number(subcap.total) - Number(subcap.total_calculado)) > 0.01 && (
                <span className="text-xs text-yellow-600 ml-1">
                  ({formatEuros(Number(subcap.total_calculado))})
                </span>
              )}
            </p>
          </div>
        </button>

        {/* Hijos (subcapítulos anidados) */}
        {expandedSubcapitulos.has(subcap.id) && hasChildren && (
          <div>
            {subcap.children.map((child: any) => renderSubcapituloNode(child, nivel + 1))}
          </div>
        )}

        {/* Partidas */}
        {expandedSubcapitulos.has(subcap.id) && hasPartidas && (
                          <div className="bg-white">
                            <div className="overflow-x-auto">
                              <table className="w-full text-sm">
                                <thead>
                                  <tr className="border-b border-gray-200 bg-gray-50">
                                    <th className="text-left py-2 px-4 pl-16 font-medium text-gray-700">Código</th>
                                    <th className="text-left py-2 px-4 font-medium text-gray-700">Descripción</th>
                                    <th className="text-center py-2 px-4 font-medium text-gray-700">Ud</th>
                                    <th className="text-right py-2 px-4 font-medium text-gray-700">Cantidad</th>
                                    <th className="text-right py-2 px-4 font-medium text-gray-700">Precio</th>
                                    <th className="text-right py-2 px-4 font-medium text-gray-700">Importe</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {subcap.partidas.map((partida) => (
                                    <tr key={partida.id} className="border-b border-gray-100 hover:bg-gray-50">
                                      <td className="py-2 px-4 pl-16 font-mono text-xs">{partida.codigo}</td>
                                      <td className="py-2 px-4">
                                        <div className="font-semibold text-gray-900">{partida.resumen}</div>
                                        {partida.descripcion && (
                                          <div className="text-xs text-gray-500 mt-1">
                                            {partida.descripcion.substring(0, 100)}
                                            {partida.descripcion.length > 100 ? '...' : ''}
                                          </div>
                                        )}
                                      </td>
                                      <td className="py-2 px-4 text-center text-gray-600">{partida.unidad}</td>
                                      <td className="py-2 px-4 text-right">{formatNumber(Number(partida.cantidad_total))}</td>
                                      <td className="py-2 px-4 text-right">{formatNumber(Number(partida.precio))}</td>
                                      <td className="py-2 px-4 text-right font-medium">{formatEuros(Number(partida.importe))}</td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          </div>
                        )}
      </div>
    )
  }
}
