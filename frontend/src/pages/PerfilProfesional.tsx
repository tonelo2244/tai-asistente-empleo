import { useEffect, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { obtenerPerfilProfesional, actualizarPerfilProfesional } from '../services/api'

function PerfilProfesional() {
  const { token } = useAuth()
  const navigate = useNavigate()

  const [form, setForm] = useState({
    nombre_completo: '',
    telefono: '',
    ciudad: '',
    estudios: '',
    experiencia: '',
    habilidades: ''
  })

  const [cargando, setCargando] = useState(true)
  const [guardando, setGuardando] = useState(false)
  const [mensaje, setMensaje] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    if (!token) {
      navigate('/login')
      return
    }

    obtenerPerfilProfesional(token)
      .then(datos => setForm(datos))
      .catch(err => setError(err.message))
      .finally(() => setCargando(false))
  }, [token, navigate])

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) {
    const { name, value } = e.target
    setForm(prev => ({ ...prev, [name]: value }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!token) return

    setGuardando(true)
    setError('')
    setMensaje('')

    try {
      await actualizarPerfilProfesional(token, form)
      setMensaje('✓ Perfil guardado correctamente')
      setTimeout(() => setMensaje(''), 3000)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setGuardando(false)
    }
  }

  if (cargando) {
    return (
      <div className="profile-page">
        <div className="profile-container">
          <p className="text-center text-muted">Cargando tu perfil...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="profile-page">
      <div className="profile-container">
        <Link to="/dashboard" className="back-link">
          ← Volver al dashboard
        </Link>

        <div className="profile-header">
          <h1>Mi perfil profesional</h1>
          <p className="text-muted">
            Completa tu información profesional para recibir análisis más precisos
          </p>
        </div>

        <form onSubmit={handleSubmit} className="profile-form">
          <div className="form-field">
            <label htmlFor="nombre_completo">Nombre completo</label>
            <input
              id="nombre_completo"
              type="text"
              name="nombre_completo"
              placeholder="Ej: Juan Pérez García"
              value={form.nombre_completo}
              onChange={handleChange}
              disabled={guardando}
            />
          </div>

          <div className="form-field">
            <label htmlFor="telefono">Teléfono de contacto</label>
            <input
              id="telefono"
              type="tel"
              name="telefono"
              placeholder="Ej: +34 912345678"
              value={form.telefono}
              onChange={handleChange}
              disabled={guardando}
            />
          </div>

          <div className="form-field">
            <label htmlFor="ciudad">Ciudad</label>
            <input
              id="ciudad"
              type="text"
              name="ciudad"
              placeholder="Ej: Madrid"
              value={form.ciudad}
              onChange={handleChange}
              disabled={guardando}
            />
          </div>

          <div className="form-field">
            <label htmlFor="estudios">Formación académica</label>
            <textarea
              id="estudios"
              name="estudios"
              placeholder="Ej: Grado en Ingeniería Informática, Universidad Complutense de Madrid, 2020"
              value={form.estudios}
              onChange={handleChange}
              disabled={guardando}
            />
          </div>

          <div className="form-field">
            <label htmlFor="experiencia">Experiencia profesional</label>
            <textarea
              id="experiencia"
              name="experiencia"
              placeholder="Ej: Desarrollador Full Stack en TechCorp (2020-2023). Lideré un equipo de 3 personas en proyectos con Django y React..."
              value={form.experiencia}
              onChange={handleChange}
              disabled={guardando}
            />
          </div>

          <div className="form-field">
            <label htmlFor="habilidades">Habilidades técnicas y profesionales</label>
            <textarea
              id="habilidades"
              name="habilidades"
              placeholder="Ej: Python, Django, React, TypeScript, PostgreSQL, Docker, AWS, Git, Metodología Agile..."
              value={form.habilidades}
              onChange={handleChange}
              disabled={guardando}
            />
          </div>

          {error && <div className="form-error">{error}</div>}
          {mensaje && <div className="form-success">{mensaje}</div>}

          <div className="profile-actions">
            <button
              type="submit"
              disabled={guardando}
              className="btn-primary"
            >
              {guardando ? 'Guardando...' : '💾 Guardar cambios'}
            </button>
            <Link to="/dashboard" className="btn-secondary" style={{ textAlign: 'center' }}>
              Cancelar
            </Link>
          </div>
        </form>
      </div>
    </div>
  )
}

export default PerfilProfesional
