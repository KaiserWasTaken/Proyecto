import type { Dispositivo } from '../types'

interface DeviceCardProps {
  dispositivo: Dispositivo
}

export function DeviceCard({ dispositivo }: DeviceCardProps) {
  const activo = dispositivo.estado === 'ENCENDIDO' || dispositivo.estado === 'ACTIVADA'
  const claseIndicador = activo
    ? dispositivo.tipo === 'ALARMA' ? 'indicator indicator--alarm' : 'indicator indicator--active'
    : 'indicator'

  return (
    <article className="device-card">
      <span className={claseIndicador} aria-hidden="true" />
      <div>
        <h3>{dispositivo.identificador}</h3>
        <p>{dispositivo.tipo}</p>
        <p className="device-state">{dispositivo.estado}</p>
      </div>
    </article>
  )
}
