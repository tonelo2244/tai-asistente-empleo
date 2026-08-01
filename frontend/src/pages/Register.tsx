import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { registrarUsuario, obtenerUsuarioAutenticado } from '../services/api'

function Register() {
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [rol, setRol] = useState('usuario')
  const [error, setError] = useState('')
  const [cargando, setCargando] = useState(false)

  const { login } = useAuth()
  const navigate = useNavigate()

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setCargando(true)

    try {
      const datos = await registrarUsuario(username, email, password, rol)
      const perfil = await obtenerUsuarioAutenticado(datos.token)
      login(datos.token, perfil.rol, perfil.username)
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
            Crea tu cuenta y comienza a optimizar tu perfil profesional
          </p>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="form-group">
            <label htmlFor="username">Usuario</label>
            <input
              id="username"
              type="text"
              placeholder="Elige un nombre de usuario"
              value={username}
              onChange={e => setUsername(e.target.value)}
              required
              disabled={cargando}
            />
          </div>

          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              placeholder="tu@email.com"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
              disabled={cargando}
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Contraseña</label>
            <input
              id="password"
              type="password"
              placeholder="Elige una contraseña segura"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              disabled={cargando}
            />
          </div>

          <div className="form-group">
            <label htmlFor="rol">Tipo de cuenta</label>
            <select
              id="rol"
              value={rol}
              onChange={e => setRol(e.target.value)}
              disabled={cargando}
            >
              <option value="usuario">Usuario (Buscador de empleo)</option>
              <option value="orientador">Orientador (Asesor profesional)</option>
              <option value="administrador">Administrador</option>
            </select>
          </div>

          {error && <div className="form-error">{error}</div>}

          <button
            type="submit"
            disabled={cargando}
            className="auth-button"
          >
            {cargando ? 'Creando cuenta...' : 'Crear cuenta'}
          </button>
        </form>

        <div className="auth-footer">
          ¿Ya tienes cuenta?{' '}
          <Link to="/login">Inicia sesión aquí</Link>
        </div>
      </div>
    </div>
  )
}

export default Register
