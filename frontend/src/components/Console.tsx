import { useState } from 'react'
import type { FormEvent, KeyboardEvent } from 'react'
import { validateCommand } from '../api'
import type { ResultadoValidacion } from '../types'

interface ConsoleProps {
  refrescarDispositivos: () => Promise<void>
}

export function Console(_props: ConsoleProps) {
  const [fuente, setFuente] = useState('')
  const [resultado, setResultado] = useState<ResultadoValidacion | null>(null)
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function validar() {
    if (cargando) return
    setCargando(true)
    setError(null)
    setResultado(null)
    try {
      setResultado(await validateCommand(fuente))
    } catch (causa) {
      setError(causa instanceof Error ? causa.message : 'Error inesperado al validar')
    } finally {
      setCargando(false)
    }
  }

  function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault()
    void validar()
  }

  function atajo(evento: KeyboardEvent<HTMLTextAreaElement>) {
    if (evento.ctrlKey && evento.key === 'Enter') {
      evento.preventDefault()
      void validar()
    }
  }

  return (
    <section className="panel" aria-labelledby="console-title">
      <p className="eyebrow">LENGUAJE DE COMANDOS</p>
      <h2 id="console-title">Consola</h2>
      <p className="section-description">Escribe una instrucción por línea para validarla.</p>
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
            {cargando ? 'Validando...' : 'Ejecutar'}
          </button>
          <span>Ctrl + Enter</span>
        </div>
      </form>
      <p className="validation-note">En esta fase solo se validan comandos; los estados no cambian.</p>
      {cargando && <p role="status">Validando instrucciones...</p>}
      {error && <p className="error-message" role="alert">{error}</p>}
      {resultado && (
        <div className="result" aria-live="polite">
          <h3 className={resultado.valido ? 'success-text' : 'error-text'}>
            {resultado.valido ? 'Instrucciones válidas' : 'Se encontraron errores'}
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
          {resultado.instrucciones.length > 0 && (
            <>
              <h4>Instrucciones reconocidas</h4>
              <pre>{JSON.stringify(resultado.instrucciones, null, 2)}</pre>
            </>
          )}
        </div>
      )}
    </section>
  )
}
