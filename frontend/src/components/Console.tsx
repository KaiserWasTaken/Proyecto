import { useState } from 'react'
import type { FormEvent, KeyboardEvent } from 'react'
import { executeCommand } from '../api'
import type { ResultadoEjecucion } from '../types'

interface ConsoleProps {
  refrescarDispositivos: () => Promise<void>
}

export function Console({ refrescarDispositivos }: ConsoleProps) {
  const [fuente, setFuente] = useState('')
  const [resultado, setResultado] = useState<ResultadoEjecucion | null>(null)
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function ejecutar() {
    if (cargando) return
    setCargando(true)
    setError(null)
    setResultado(null)
    try {
      setResultado(await executeCommand(fuente))
    } catch (causa) {
      setError(causa instanceof Error ? causa.message : 'Error inesperado al ejecutar')
    } finally {
      try {
        await refrescarDispositivos()
      } finally {
        setCargando(false)
      }
    }
  }

  function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault()
    void ejecutar()
  }

  function atajo(evento: KeyboardEvent<HTMLTextAreaElement>) {
    if (evento.ctrlKey && evento.key === 'Enter') {
      evento.preventDefault()
      void ejecutar()
    }
  }

  return (
    <section className="panel" aria-labelledby="console-title">
      <p className="eyebrow">LENGUAJE DE COMANDOS</p>
      <h2 id="console-title">Consola</h2>
      <p className="section-description">Escribe una instrucción por línea para ejecutarla.</p>
      <form onSubmit={enviar}>
        <label htmlFor="source">Instrucciones</label>
        <textarea
          id="source"
          value={fuente}
          onChange={(evento) => {
            setFuente(evento.target.value)
            setResultado(null)
            setError(null)
          }}
          onKeyDown={atajo}
          placeholder={'ENCENDER led1\nCONSULTAR led1'}
          spellCheck={false}
          disabled={cargando}
        />
        <div className="form-actions">
          <button type="submit" disabled={cargando}>
            {cargando ? 'Ejecutando...' : 'Ejecutar'}
          </button>
          <span>Ctrl + Enter</span>
        </div>
      </form>
      {cargando && <p role="status">Ejecutando instrucciones...</p>}
      {error && <p className="error-message" role="alert">{error}</p>}
      {resultado && (
        <div className="result" aria-live="polite">
          <h3 className={resultado.valido && resultado.exito ? 'success-text' : 'error-text'}>
            {!resultado.valido
              ? 'Se encontraron errores'
              : resultado.exito ? 'Ejecución completada' : 'Se ejecutó con errores'}
          </h3>
          {resultado.errores.length > 0 && (
            <ul className="error-list">
              {resultado.errores.map((error, indice) => (
                <li key={`${error.fase}-${error.linea}-${error.columna}-${indice}`}>
                  <strong>{error.fase} · {error.codigo}</strong>
                  <span>{error.mensaje}</span>
                  <span>Línea {error.linea}, columna {error.columna}</span>
                </li>
              ))}
            </ul>
          )}
          {resultado.valido && resultado.eventos.length > 0 && (
            <ol className="event-list">
              {resultado.eventos.map((evento, indice) => (
                <li key={indice} className={evento.tipo.startsWith('ERROR') ? 'error-text' : undefined}>
                  {evento.texto}
                </li>
              ))}
            </ol>
          )}
        </div>
      )}
    </section>
  )
}
