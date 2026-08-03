interface SpinnerProps {
  size?: number
  variant?: 'light' | 'dark'
}

// Indicador de carga reutilizable. 'light' para botones sobre fondos de color,
// 'dark' para estados de carga de página completa sobre fondo claro.
function Spinner({ size = 16, variant = 'dark' }: SpinnerProps) {
  return (
    <span
      className={`spinner ${variant === 'light' ? 'spinner-light' : 'spinner-dark'}`}
      style={{ width: size, height: size }}
      aria-hidden="true"
    />
  )
}

export default Spinner
