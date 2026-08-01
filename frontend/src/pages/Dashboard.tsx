import { useEffect, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { ping } from '../services/api'

function Dashboard() {
  const { token, username, rol, logout } = useAuth()
  const navigate = useNavigate()
  const [mensajePing, setMensajePing] = useState('Comprobando...')

  useEffect(() => {
    if (!token) {
      navigate('/login')
      return
    }

    ping()
      .then((data) => setMensajePing(data.message))
      .catch(() => setMensajePing('No se pudo conectar con el backend'))
  }, [token, navigate])

  function handleLogout() {
    logout()
    navigate('/login')
  }

  function obtenerTextoRol() {
    if (rol === 'usuario') return 'Buscador de empleo'
    if (rol === 'orientador') return 'Asesor profesional'
    return 'Administrador'
  }

  return (
    <div className="dashboard-page">
      <div className="dashboard-container">
        <header className="dashboard-header">
          <div>
            <h1>Bienvenido, {username} 👋</h1>
            <p className="welcome-text">
              Aquí puedes gestionar tu perfil profesional y analizar tu empleabilidad.
            </p>
          </div>

          <div className="user-info">
            <div className="user-info-item">
              <span className="info-label">Tipo de cuenta</span>
              <strong>{obtenerTextoRol()}</strong>
            </div>

            <div className="user-info-item">
              <span className="info-label">Estado del sistema</span>
              <strong>{mensajePing}</strong>
            </div>
          </div>
        </header>

        <section className="dashboard-intro">
          <p>
            <strong>¿Qué es TAI?</strong> TAI es tu asistente inteligente para el desarrollo
            profesional. Analiza tu perfil, identifica fortalezas, detecta áreas de mejora y
            genera recomendaciones personalizadas para optimizar tu empleabilidad.
          </p>
        </section>

        <section className="dashboard-cards">
          <Link to="/perfil" className="card">
            <div className="card-icon">📋</div>
            <div className="card-content">
              <h3>Mi perfil profesional</h3>
              <p>
                Crea y edita tu perfil con tu experiencia, formación académica y habilidades.
              </p>
            </div>
            <span className="card-link">Editar perfil →</span>
          </Link>

          <Link to="/analisis" className="card">
            <div className="card-icon">📊</div>
            <div className="card-content">
              <h3>Analizar mi perfil</h3>
              <p>
                Recibe un análisis detallado con puntuación, fortalezas, aspectos de mejora y
                recomendaciones.
              </p>
            </div>
            <span className="card-link">Iniciar análisis →</span>
          </Link>

          <Link to="/analisis" className="card">
            <div className="card-icon">📈</div>
            <div className="card-content">
              <h3>Historial de análisis</h3>
              <p>
                Consulta tus análisis anteriores y realiza un seguimiento de tu evolución.
              </p>
            </div>
            <span className="card-link">Ver historial →</span>
          </Link>
        </section>

        <div className="dashboard-actions">
          <button onClick={handleLogout} className="btn-secondary">
            Cerrar sesión
          </button>
        </div>
      </div>
    </div>
  )
}

export default Dashboard