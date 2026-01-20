// Types para toda la aplicación
// Coinciden con los schemas de la API

export interface User {
  username: string
  user_id: number
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user: User
}

export interface Proyecto {
  id: number
  nombre: string
  fecha_creacion: string
  presupuesto_total: number
  layout_detectado?: string
  tiene_mediciones_auxiliares: boolean
  num_capitulos?: number
}

export interface ProyectoStats {
  total_capitulos: number
  total_subcapitulos: number
  total_partidas: number
  partidas_con_mediciones: number
  presupuesto_total: number
}

export interface MedicionParcial {
  id: number
  orden: number
  descripcion?: string
  uds: number
  longitud: number
  anchura: number
  altura: number
  parciales: number
  subtotal: number
}

export interface Partida {
  id: number
  codigo: string
  unidad?: string
  descripcion?: string
  cantidad_total: number
  precio: number
  importe: number
  tiene_mediciones: boolean
  mediciones_validadas: boolean
  mediciones: MedicionParcial[]
}

export interface Subcapitulo {
  id: number
  codigo: string
  nombre?: string
  total: number
  nivel?: number
  partidas: Partida[]
}

export interface Capitulo {
  id: number
  codigo: string
  nombre?: string
  total: number
  subcapitulos: Subcapitulo[]
}

export interface ProyectoDetalle extends Proyecto {
  capitulos: Capitulo[]
}

export interface UploadResponse {
  success: boolean
  message: string
  proyecto_id?: number
  filename: string
  size_bytes: number
  procesamiento: {
    total_capitulos: number
    total_subcapitulos: number
    total_partidas: number
    presupuesto_total: number
  }
}

export interface ValidacionPartida {
  codigo: string
  cantidad_total: number
  suma_parciales: number
  diferencia: number
  valido: boolean
}

export interface ValidacionProyecto {
  proyecto_id: number
  total_partidas: number
  partidas_con_mediciones: number
  partidas_validas: number
  partidas_invalidas: number
  detalles_invalidas: ValidacionPartida[]
}
