import type { Dispositivo } from '../types'
import { DeviceCard } from './DeviceCard'

interface DevicePanelProps {
  dispositivos: Dispositivo[]
  cargando: boolean
  error: string | null
}

export function DevicePanel({ dispositivos, cargando, error }: DevicePanelProps) {
  return (
    <section className="panel" aria-labelledby="devices-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">SIMULACIÓN</p>
          <h2 id="devices-title">Dispositivos</h2>
        </div>
      </div>
      <p className="section-description">Estado actual de los dispositivos simulados.</p>
      {cargando && <p role="status">Cargando dispositivos...</p>}
      {error && <p className="error-message" role="alert">{error}</p>}
      {!cargando && !error && (
        <div className="device-grid">
          {dispositivos.map((dispositivo) => (
            <DeviceCard key={dispositivo.identificador} dispositivo={dispositivo} />
          ))}
        </div>
      )}
    </section>
  )
}
