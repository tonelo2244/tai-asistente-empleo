import type { ReactNode } from 'react'
import { CheckCircle2, AlertTriangle } from 'lucide-react'

interface AlertProps {
  type: 'success' | 'error'
  children: ReactNode
}

// Mensaje de éxito/error con estilo único para toda la aplicación.
function Alert({ type, children }: AlertProps) {
  const Icon = type === 'success' ? CheckCircle2 : AlertTriangle

  return (
    <div className={`alert alert-${type}`} role={type === 'error' ? 'alert' : 'status'}>
      <Icon size={16} strokeWidth={2} />
      <span>{children}</span>
    </div>
  )
}

export default Alert
