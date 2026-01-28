// Página de Edición - Procesar Proyecto por Fases
'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Play, CheckCircle, Clock, AlertCircle } from 'lucide-react'
import Link from 'next/link'
import Button from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

type FaseEstado = 'pendiente' | 'procesando' | 'completada' | 'error'

interface FaseInfo {
  numero: number
  nombre: string
  descripcion: string
  estado: FaseEstado
  resultado?: any
  error?: string
}

export default function EditarProyectoPage({ params }: { params: { id: string } }) {
  const router = useRouter()
  const queryClient = useQueryClient()
  const proyectoId = params.id
  const [proyectoLoaded, setProyectoLoaded] = useState(false)

  const [fases, setFases] = useState<FaseInfo[]>([
    {
      numero: 1,
      nombre: 'Extracción de Estructura',
      descripcion: 'Extrae capítulos y subcapítulos con totales',
      estado: 'pendiente'
    },
    {
      numero: 2,
      nombre: 'Extracción de Partidas',
      descripcion: 'Clasifica líneas y extrae partidas individuales',
      estado: 'pendiente'
    },
    {
      numero: 3,
      nombre: 'Validación de Totales',
      descripcion: 'Merge totales y valida coherencia',
      estado: 'pendiente'
    },
    {
      numero: 4,
      nombre: 'Guardar en BD',
      descripcion: 'Completa descripciones y guarda todo',
      estado: 'pendiente'
    }
  ])

  // Función para cargar estado del proyecto (extraída para reutilizar)
  const cargarEstadoProyecto = async () => {
    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`${API_URL}/api/proyectos/${proyectoId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (!response.ok) return

      const proyecto = await response.json()

      // Marcar fases completadas basándose en el estado del proyecto
      setFases(prev => prev.map(f => {
        // Preservar estado 'procesando' si existe
        if (f.estado === 'procesando') return f

        // Fase 1: Si hay capítulos
        if (f.numero === 1 && proyecto.capitulos && proyecto.capitulos.length > 0) {
          return { ...f, estado: 'completada' as FaseEstado }
        }
        // Fase 2: Si hay partidas en algún subcapítulo
        if (f.numero === 2) {
          const tienePartidas = proyecto.capitulos?.some((cap: any) =>
            cap.subcapitulos?.some((sub: any) => sub.partidas && sub.partidas.length > 0)
          )
          if (tienePartidas) {
            return { ...f, estado: 'completada' as FaseEstado }
          }
        }
        // Fase 3: Si tiene presupuesto_total Y tiene partidas (indicador de Fase 2 ejecutada)
        // No marcar como completada solo con presupuesto_total porque puede ser inicial del PDF
        if (f.numero === 3) {
          const tienePartidas = proyecto.capitulos?.some((cap: any) =>
            cap.subcapitulos?.some((sub: any) => sub.partidas && sub.partidas.length > 0)
          )
          // Solo si tiene partidas Y tiene presupuesto > 0
          if (tienePartidas && proyecto.presupuesto_total && proyecto.presupuesto_total > 0) {
            return { ...f, estado: 'completada' as FaseEstado }
          }
        }
        return f
      }))

      setProyectoLoaded(true)
    } catch (error) {
      console.error('Error cargando estado del proyecto:', error)
    }
  }

  // Cargar estado del proyecto al montar componente
  useEffect(() => {
    cargarEstadoProyecto()
  }, [proyectoId])

  const ejecutarFase = async (numeroFase: number) => {
    // Actualizar estado a "procesando"
    setFases(prev => prev.map(f =>
      f.numero === numeroFase ? { ...f, estado: 'procesando' as FaseEstado, error: undefined } : f
    ))

    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`${API_URL}/api/proyectos/${proyectoId}/fase${numeroFase}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (!response.ok) {
        throw new Error(`Error ${response.status}: ${response.statusText}`)
      }

      const data = await response.json()

      // Actualizar estado a "completada"
      setFases(prev => prev.map(f =>
        f.numero === numeroFase ? { ...f, estado: 'completada' as FaseEstado, resultado: data } : f
      ))

      // IMPORTANTE: Invalidar cache de React Query para forzar recarga de datos
      // Esto asegura que cuando el usuario vuelva a la página de detalle, vea los datos actualizados
      queryClient.invalidateQueries({ queryKey: ['proyecto', parseInt(proyectoId)] })
      queryClient.invalidateQueries({ queryKey: ['proyecto-stats', parseInt(proyectoId)] })

      // Recargar estado local del componente
      await cargarEstadoProyecto()

      // Si es fase 4, redirigir al detalle del proyecto
      if (numeroFase === 4) {
        setTimeout(() => {
          router.push(`/proyectos/${proyectoId}`)
        }, 2000)
      }

    } catch (error: any) {
      console.error(`Error en fase ${numeroFase}:`, error)
      setFases(prev => prev.map(f =>
        f.numero === numeroFase
          ? { ...f, estado: 'error' as FaseEstado, error: error.message }
          : f
      ))
    }
  }

  const ejecutarTodasLasFases = async () => {
    for (let i = 1; i <= 4; i++) {
      await ejecutarFase(i)
      // Pequeña pausa entre fases
      await new Promise(resolve => setTimeout(resolve, 500))
    }
  }

  // Estados para resolución de discrepancias
  const [resolviendoIndividual, setResolviendoIndividual] = useState<string | null>(null)
  const [resolviendoBulk, setResolviendoBulk] = useState(false)

  // Función para resolver una discrepancia individual
  const resolverDiscrepanciaIndividual = async (tipo: string, id: number, codigo: string) => {
    const clave = `${tipo}_${id}`
    setResolviendoIndividual(clave)

    try {
      const token = localStorage.getItem('token')
      const response = await fetch(
        `${API_URL}/api/proyectos/${proyectoId}/resolver-discrepancia?tipo=${tipo}&elemento_id=${id}`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      )

      if (!response.ok) {
        throw new Error(`Error ${response.status}: ${response.statusText}`)
      }

      const data = await response.json()
      console.log('Discrepancia resuelta:', data)
      alert(`✓ ${codigo}: ${data.partidas_agregadas} partidas agregadas por IA (${data.total_agregado.toFixed(2)} €)`)

      // Recargar estado del proyecto y re-ejecutar Fase 3 para actualizar discrepancias
      await ejecutarFase(3)

    } catch (error: any) {
      console.error('Error al resolver discrepancia:', error)
      alert(`❌ Error al resolver discrepancia: ${error.message}`)
    } finally {
      setResolviendoIndividual(null)
    }
  }

  // Función para resolver todas las discrepancias
  const resolverTodasLasDiscrepancias = async () => {
    if (!confirm('⚠️ Esto puede tardar varios minutos. La IA buscará partidas faltantes para cada discrepancia.\n\n¿Continuar?')) {
      return
    }

    setResolviendoBulk(true)

    try {
      const token = localStorage.getItem('token')
      const response = await fetch(
        `${API_URL}/api/proyectos/${proyectoId}/resolver-discrepancias-bulk`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      )

      if (!response.ok) {
        throw new Error(`Error ${response.status}: ${response.statusText}`)
      }

      const data = await response.json()
      console.log('Discrepancias resueltas:', data)

      // Mostrar resultado detallado
      let mensaje = `✓ Resolución completada:\n\n`
      mensaje += `• Exitosas: ${data.resueltas_exitosas}\n`
      mensaje += `• Fallidas: ${data.resueltas_fallidas}\n`
      mensaje += `• Total partidas agregadas: ${data.total_partidas_agregadas}\n`

      if (data.errores && data.errores.length > 0) {
        mensaje += `\n⚠️ Errores:\n${data.errores.slice(0, 3).join('\n')}`
        if (data.errores.length > 3) {
          mensaje += `\n... y ${data.errores.length - 3} más`
        }
      }

      alert(mensaje)

      // Re-ejecutar Fase 3 para actualizar la visualización
      await ejecutarFase(3)

    } catch (error: any) {
      console.error('Error al resolver discrepancias:', error)
      alert(`❌ Error al resolver discrepancias: ${error.message}`)
    } finally {
      setResolviendoBulk(false)
    }
  }

  const getEstadoIcon = (estado: FaseEstado) => {
    switch (estado) {
      case 'completada':
        return <CheckCircle className="h-6 w-6 text-green-600" />
      case 'procesando':
        return <Clock className="h-6 w-6 text-blue-600 animate-spin" />
      case 'error':
        return <AlertCircle className="h-6 w-6 text-red-600" />
      default:
        return <div className="h-6 w-6 rounded-full border-2 border-gray-300" />
    }
  }

  const getEstadoColor = (estado: FaseEstado) => {
    switch (estado) {
      case 'completada':
        return 'bg-green-50 border-green-200'
      case 'procesando':
        return 'bg-blue-50 border-blue-200'
      case 'error':
        return 'bg-red-50 border-red-200'
      default:
        return 'bg-white border-gray-200'
    }
  }

  const renderEstructura = (resultado: any) => {
    if (!resultado?.resultado) return null

    // Fase 1: Estructura
    if (resultado.fase === 1 && resultado.resultado.estructura) {
      const caps = resultado.resultado.estructura.capitulos || []
      const totalGeneral = caps.reduce((sum: number, cap: any) => sum + (cap.total || 0), 0)

      return (
        <div className="mt-4 space-y-2">
          <div className="bg-green-50 border border-green-200 rounded-lg p-3 mb-3">
            <p className="text-sm font-bold text-green-900">
              💰 TOTAL GENERAL: {totalGeneral.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} €
            </p>
            <p className="text-xs text-green-700 mt-1">
              {caps.length} capítulos detectados
            </p>
          </div>

          <p className="text-sm font-semibold text-gray-700">Estructura extraída:</p>
          {caps.map((cap: any, i: number) => (
            <div key={i} className="ml-4">
              <div className="text-sm font-medium text-gray-900">
                📁 CAP {cap.codigo}: {cap.nombre} - {(cap.total || 0).toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} €
              </div>
              {cap.subcapitulos && cap.subcapitulos.length > 0 && renderSubcapitulos(cap.subcapitulos, 1)}
            </div>
          ))}
        </div>
      )
    }

    // Fase 2: Estructura con partidas
    if (resultado.fase === 2 && resultado.resultado.estructura_completa) {
      const caps = resultado.resultado.estructura_completa.capitulos || []
      return (
        <div className="mt-4 space-y-2">
          <p className="text-sm font-semibold text-gray-700">Estructura con partidas:</p>
          {caps.map((cap: any, i: number) => (
            <div key={i} className="ml-4">
              <div className="text-sm font-medium text-gray-900">
                📁 CAP {cap.codigo}: {cap.nombre} ({cap.partidas?.length || 0} partidas)
              </div>
              {cap.subcapitulos && cap.subcapitulos.length > 0 && renderSubcapitulosConPartidas(cap.subcapitulos, 1)}
            </div>
          ))}
        </div>
      )
    }

    return null
  }

  const renderSubcapitulos = (subs: any[], nivel: number) => {
    return subs.map((sub: any, i: number) => (
      <div key={i} style={{ marginLeft: `${nivel * 16}px` }}>
        <div className="text-xs text-gray-800">
          {'  '.repeat(nivel)}└─ SUB {sub.codigo}: {sub.nombre} - {sub.total?.toFixed(2) || '0.00'} €
        </div>
        {sub.subcapitulos && sub.subcapitulos.length > 0 && renderSubcapitulos(sub.subcapitulos, nivel + 1)}
      </div>
    ))
  }

  const renderSubcapitulosConPartidas = (subs: any[], nivel: number) => {
    return subs.map((sub: any, i: number) => (
      <div key={i} style={{ marginLeft: `${nivel * 16}px` }}>
        <div className="text-xs text-gray-800">
          {'  '.repeat(nivel)}└─ SUB {sub.codigo}: {sub.nombre} ({sub.partidas?.length || 0} partidas)
        </div>
        {sub.subcapitulos && sub.subcapitulos.length > 0 && renderSubcapitulosConPartidas(sub.subcapitulos, nivel + 1)}
      </div>
    ))
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      {/* Header */}
      <div className="mb-8">
        <Link href={`/proyectos/${proyectoId}`} className="inline-flex items-center text-primary-600 hover:text-primary-700 mb-4">
          <ArrowLeft className="h-4 w-4 mr-2" />
          Volver al proyecto
        </Link>
        <h1 className="text-3xl font-bold text-gray-900">Procesar Proyecto por Fases</h1>
        <p className="text-gray-600 mt-2">Ejecuta cada fase manualmente para debugging paso a paso</p>
      </div>

      {/* Botón para ejecutar todas las fases */}
      <div className="mb-6">
        <Button
          onClick={ejecutarTodasLasFases}
          className="w-full"
          disabled={fases.some(f => f.estado === 'procesando')}
        >
          <Play className="h-5 w-5 mr-2" />
          Ejecutar Todas las Fases
        </Button>
      </div>

      {/* Fases */}
      <div className="space-y-4">
        {fases.map((fase) => (
          <Card key={fase.numero} className={`border-2 ${getEstadoColor(fase.estado)}`}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  {getEstadoIcon(fase.estado)}
                  <div>
                    <CardTitle className="text-lg">
                      Fase {fase.numero}: {fase.nombre}
                    </CardTitle>
                    <p className="text-sm text-gray-600 mt-1">{fase.descripcion}</p>
                  </div>
                </div>
                <Button
                  onClick={() => ejecutarFase(fase.numero)}
                  disabled={fase.estado === 'procesando'}
                  size="sm"
                  variant={fase.estado === 'completada' ? 'outline' : 'primary'}
                >
                  {fase.estado === 'procesando' ? 'Procesando...' :
                   fase.estado === 'completada' ? 'Reejecutar' : 'Ejecutar'}
                </Button>
              </div>
            </CardHeader>

            {/* Resultado o error */}
            {fase.resultado && fase.estado === 'completada' && (
              <CardContent>
                <div className="bg-white rounded-lg p-4 border border-gray-200">
                  <p className="text-sm font-medium text-green-700 mb-2">✓ {fase.resultado.mensaje}</p>

                  {/* Mostrar estructura en árbol */}
                  {renderEstructura(fase.resultado)}

                  {/* FASE 3: Mostrar discrepancias */}
                  {fase.numero === 3 && fase.resultado.discrepancias && fase.resultado.discrepancias.length > 0 && (
                    <div className="mt-4">
                      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-4">
                        <h3 className="font-semibold text-yellow-900 mb-2">
                          ⚠️ Discrepancias Detectadas: {fase.resultado.discrepancias.length}
                        </h3>
                        <div className="text-sm text-yellow-800 mb-3">
                          <p>Total Original (PDF): <span className="font-bold">{fase.resultado.total_original?.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} €</span></p>
                          <p>Total Calculado (Partidas): <span className="font-bold">{fase.resultado.total_calculado?.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} €</span></p>
                          <p>Diferencia: <span className="font-bold">{((fase.resultado.total_original || 0) - (fase.resultado.total_calculado || 0)).toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} €</span></p>
                        </div>

                        {/* Tabla de discrepancias */}
                        <div className="bg-white rounded border border-yellow-300 overflow-hidden">
                          <div className="overflow-x-auto max-h-96">
                            <table className="min-w-full divide-y divide-gray-200">
                              <thead className="bg-yellow-100">
                                <tr>
                                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-700">Tipo</th>
                                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-700">Código</th>
                                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-700">Nombre</th>
                                  <th className="px-3 py-2 text-right text-xs font-medium text-gray-700">Original</th>
                                  <th className="px-3 py-2 text-right text-xs font-medium text-gray-700">Calculado</th>
                                  <th className="px-3 py-2 text-right text-xs font-medium text-gray-700">Diferencia</th>
                                  <th className="px-3 py-2 text-center text-xs font-medium text-gray-700">Acción</th>
                                </tr>
                              </thead>
                              <tbody className="bg-white divide-y divide-gray-200">
                                {fase.resultado.discrepancias.map((disc: any, idx: number) => (
                                  <tr key={idx} className="hover:bg-gray-50">
                                    <td className="px-3 py-2 text-xs text-gray-600">
                                      {disc.tipo === 'capitulo' ? '📁 Capítulo' : '📂 Subcapítulo'}
                                    </td>
                                    <td className="px-3 py-2 text-xs font-mono text-gray-900">{disc.codigo}</td>
                                    <td className="px-3 py-2 text-xs text-gray-700 max-w-xs truncate" title={disc.nombre}>
                                      {disc.nombre}
                                    </td>
                                    <td className="px-3 py-2 text-xs text-right font-medium text-gray-900">
                                      {disc.total_original?.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} €
                                    </td>
                                    <td className="px-3 py-2 text-xs text-right font-medium text-gray-900">
                                      {disc.total_calculado?.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} €
                                    </td>
                                    <td className={`px-3 py-2 text-xs text-right font-bold ${Math.abs(disc.diferencia) < 0.01 ? 'text-green-600' : 'text-red-600'}`}>
                                      {disc.diferencia?.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} €
                                    </td>
                                    <td className="px-3 py-2 text-center">
                                      <Button
                                        size="sm"
                                        variant="outline"
                                        className="text-xs py-1 px-2 h-auto"
                                        disabled={resolviendoIndividual === `${disc.tipo}_${disc.id}` || resolviendoBulk}
                                        onClick={() => resolverDiscrepanciaIndividual(disc.tipo, disc.id, disc.codigo)}
                                        title="🤖 Usar IA para encontrar partidas faltantes"
                                      >
                                        {resolviendoIndividual === `${disc.tipo}_${disc.id}` ? '⏳' : '🤖'} Resolver con IA
                                      </Button>
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>

                        {/* Botones de resolución masiva */}
                        <div className="mt-4 flex gap-2">
                          <Button
                            size="sm"
                            variant="primary"
                            className="bg-blue-600 hover:bg-blue-700"
                            disabled={resolviendoBulk || resolviendoIndividual !== null}
                            onClick={resolverTodasLasDiscrepancias}
                          >
                            {resolviendoBulk ? '⏳ Procesando con IA...' : '🤖 Resolver Todas con IA'}
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            className="text-gray-700 border-gray-400 hover:bg-gray-100"
                            onClick={() => router.push(`/proyectos/${proyectoId}`)}
                          >
                            📋 Ver en Detalle
                          </Button>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* FASE 3: Sin discrepancias */}
                  {fase.numero === 3 && fase.resultado.discrepancias && fase.resultado.discrepancias.length === 0 && (
                    <div className="mt-4 bg-green-50 border border-green-200 rounded-lg p-4">
                      <p className="text-sm font-medium text-green-700">
                        ✓ No se encontraron discrepancias. Todos los totales coinciden con las partidas.
                      </p>
                      <div className="text-xs text-green-600 mt-2">
                        <p>Total: {fase.resultado.total_calculado?.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} €</p>
                      </div>
                    </div>
                  )}

                  {/* Detalles JSON colapsable */}
                  {fase.resultado.resultado && (
                    <details className="text-xs text-gray-600 mt-4">
                      <summary className="cursor-pointer hover:text-gray-900 font-medium">Ver JSON completo</summary>
                      <pre className="mt-2 p-2 bg-gray-50 rounded overflow-x-auto max-h-96">
                        {JSON.stringify(fase.resultado.resultado, null, 2)}
                      </pre>
                    </details>
                  )}
                </div>
              </CardContent>
            )}

            {fase.error && fase.estado === 'error' && (
              <CardContent>
                <div className="bg-red-50 rounded-lg p-4 border border-red-200">
                  <p className="text-sm font-medium text-red-700">✗ Error: {fase.error}</p>
                </div>
              </CardContent>
            )}
          </Card>
        ))}
      </div>

      {/* Info sobre archivos intermedios */}
      <Card className="mt-8 bg-blue-50 border-blue-200">
        <CardHeader>
          <CardTitle className="text-sm text-blue-900">📁 Archivos Intermedios</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-blue-800">
            Los resultados de cada fase se guardan en:
            <code className="block mt-2 p-2 bg-blue-100 rounded text-xs">
              logs/parser_v2_fases/
            </code>
          </p>
          <p className="text-xs text-blue-700 mt-2">
            Puedes revisar estos archivos JSON para depurar cada paso del procesamiento.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
