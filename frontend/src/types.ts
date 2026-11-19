export interface Dispositivo {
  identificador: string
  tipo: string
  estado: string
  operaciones: string[]
}

export interface ErrorAnalisis {
  fase: 'lexico' | 'sintactico' | 'semantico'
  codigo: string
  mensaje: string
  linea: number
  columna: number
}

type InstruccionSimple =
  | { tipo: 'CONTROL_DISPOSITIVO'; operacion: string; dispositivo: string }
  | { tipo: 'CONSULTA'; dispositivo: string }
  | { tipo: 'LISTADO' }
  | { tipo: 'NOTIFICACION'; mensaje: string }
  | { tipo: 'CORREO'; destinatario: string; mensaje: string }

export type Instruccion =
  | InstruccionSimple
  | { tipo: 'CONDICIONAL'; dispositivo: string; estado: string; accion: InstruccionSimple }
  | { tipo: 'REPETIR'; veces: number; accion: InstruccionSimple }

export interface ResultadoValidacion {
  valido: boolean
  errores: ErrorAnalisis[]
  instrucciones: Instruccion[]
}

export interface EventoEjecucion {
  tipo: string
  texto: string
  dispositivo?: string
  estado?: string
}

export interface ResultadoEjecucion {
  valido: boolean
  exito: boolean
  errores: ErrorAnalisis[]
  eventos: EventoEjecucion[]
}
