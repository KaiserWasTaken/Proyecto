import type { Dispositivo, ResultadoEjecucion, ResultadoValidacion } from './types'

const apiUrl = (import.meta.env.VITE_API_URL || 'http://localhost:8001').replace(/\/+$/, '')

async function solicitar<T>(ruta: string, opciones?: RequestInit): Promise<T> {
  let respuesta: Response
  try {
    respuesta = await fetch(`${apiUrl}${ruta}`, opciones)
  } catch {
    throw new Error('No se pudo conectar con el servidor')
  }
  if (!respuesta.ok) {
    throw new Error(`El servidor respondió con error HTTP ${respuesta.status}`)
  }
  return respuesta.json() as Promise<T>
}

export function getDevices(): Promise<Dispositivo[]> {
  return solicitar<Dispositivo[]>('/api/devices')
}

export function validateCommand(source: string): Promise<ResultadoValidacion> {
  return solicitar<ResultadoValidacion>('/api/commands/validate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ source }),
  })
}

export function executeCommand(source: string): Promise<ResultadoEjecucion> {
  return solicitar<ResultadoEjecucion>('/api/commands/execute', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ source }),
  })
}
