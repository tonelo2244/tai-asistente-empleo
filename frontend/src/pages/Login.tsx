import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { loginUsuario } from '../services/api'

function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [cargando, setCargando] = useState(false)

  const { login } = useAuth()
  const navigate = useNavigate()

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setCargando(true)

    try {
      const datos = await loginUsuario(username, password)
      login(datos.token, datos.rol, datos.username)
      navigate('/dashboard')
    } catch (err: any) {
      setError(err.message)
    } finally {
      setCargando(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-container">
        <div className="auth-header">
          <h1>TAI</h1>
          <p className="auth-subtitle">
            Tu asistente inteligente para el desarrollo profesional y la optimización de tu empleabilidad
          </p>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="form-group">
            <label htmlFor="username">Usuario o email</label>
            <input
              id="username"
              type="text"
              placeholder="Ingresa tu usuario"
              value={username}
              onChange={e => setUsername(e.target.value)}
              required
              disabled={cargando}
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Contraseña</label>
            <input
              id="password"
              type="password"
              placeholder="Ingresa tu contraseña"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              disabled={cargando}
            />
          </div>

          {error && <div className="form-error">{error}</div>}

          <button
            type="submit"
            disabled={cargando}
            className="auth-button"
          >
            {cargando ? 'Conectando...' : 'Iniciar sesión'}
          </button>
        </form>

        <div className="auth-footer">
          ¿No tienes cuenta?{' '}
          <Link to="/registro">Crea una aquí</Link>
        </div>
      </div>
    </div>
  )
}

export default Login
