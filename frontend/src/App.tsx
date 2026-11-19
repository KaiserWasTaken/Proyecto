import { useCallback, useEffect, useState } from 'react'
import { getDevices } from './api'
import { Console } from './components/Console'
import { DevicePanel } from './components/DevicePanel'
import type { Dispositivo } from './types'

function App() {
  const [dispositivos, setDispositivos] = useState<Dispositivo[]>([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refrescarDispositivos = useCallback(async () => {
    setCargando(true)
    setError(null)
    try {
      setDispositivos(await getDevices())
    } catch (causa) {
      setError(causa instanceof Error ? causa.message : 'Error inesperado al cargar dispositivos')
    } finally {
      setCargando(false)
    }
  }, [])

  useEffect(() => {
    void refrescarDispositivos()
  }, [refrescarDispositivos])

  return (
    <main className="app">
      <header className="app-header">
        <p className="eyebrow">LENGUAJES Y AUTÓMATAS II</p>
        <h1>CommandFlow</h1>
        <p>Ejecuta instrucciones para dispositivos simulados.</p>
        <a href="http://localhost:8025" target="_blank" rel="noopener noreferrer">Abrir Mailpit</a>
      </header>
      <div className="workspace">
        <Console refrescarDispositivos={refrescarDispositivos} />
        <DevicePanel dispositivos={dispositivos} cargando={cargando} error={error} />
      </div>
    </main>
  )
}

export default App
