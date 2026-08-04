import { useEffect, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import {
  FileText,
  BarChart3,
  History,
  ArrowRight,
  UserCircle2,
  CheckCircle2,
  XCircle,
  LogOut,
  Sparkles,
  FileUp,
  Briefcase,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { ping } from '../services/api'

function Dashboard() {
  const { token, username, rol, logout } = useAuth()
  const navigate = useNavigate()
  const [mensajePing, setMensajePing] = useState('Comprobando...')
  const [backendActivo, setBackendActivo] = useState<boolean | null>(null)

  useEffect(() => {
    if (!token) {
      navigate('/login')
      return
    }

    ping()
      .then((data) => {
        setMensajePing(data.message)
        setBackendActivo(true)
      })
      .catch(() => {
        setMensajePing('No se pudo conectar con el backend')
        setBackendActivo(false)
      })
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
            <h1>Bienvenido, {username}</h1>
            <p className="welcome-text">
              Aquí puedes gestionar tu perfil profesional y analizar tu empleabilidad.
            </p>
          </div>

          <div className="user-info">
            <div className="user-info-item">
              <div className="stat-icon">
                <UserCircle2 size={20} />
              </div>
              <div className="user-info-item-text">
                <span className="info-label">Tipo de cuenta</span>
                <strong>{obtenerTextoRol()}</strong>
              </div>
            </div>

            <div className="user-info-item">
              <div className="stat-icon">
                {backendActivo === false ? (
                  <XCircle size={20} />
                ) : (
                  <CheckCircle2 size={20} />
                )}
              </div>
              <div className="user-info-item-text">
                <span className="info-label">Estado del sistema</span>
                <strong>{mensajePing}</strong>
              </div>
            </div>
          </div>
        </header>

        <section className="dashboard-intro">
          <Sparkles size={20} />
          <p>
            <strong>¿Qué es TAI?</strong> TAI es tu asistente inteligente para el desarrollo
            profesional. Analiza tu perfil, identifica fortalezas, detecta áreas de mejora y
            genera recomendaciones personalizadas para optimizar tu empleabilidad.
          </p>
        </section>

        <section className="dashboard-cards">
          <Link to="/perfil" className="card">
            <div className="card-icon">
              <FileText size={22} />
            </div>
            <div className="card-content">
              <h3>Mi perfil profesional</h3>
              <p>
                Crea y edita tu perfil con tu experiencia, formación académica y habilidades.
              </p>
            </div>
            <span className="card-link">
              Editar perfil <ArrowRight size={14} />
            </span>
          </Link>

          <Link to="/analisis" className="card">
            <div className="card-icon">
              <BarChart3 size={22} />
            </div>
            <div className="card-content">
              <h3>Analizar mi perfil</h3>
              <p>
                Recibe un análisis detallado con puntuación, fortalezas, aspectos de mejora y
                recomendaciones.
              </p>
            </div>
            <span className="card-link">
              Iniciar análisis <ArrowRight size={14} />
            </span>
          </Link>

          <Link to="/analisis" className="card">
            <div className="card-icon">
              <History size={22} />
            </div>
            <div className="card-content">
              <h3>Historial de análisis</h3>
              <p>
                Consulta tus análisis anteriores y realiza un seguimiento de tu evolución.
              </p>
            </div>
            <span className="card-link">
              Ver historial <ArrowRight size={14} />
            </span>
          </Link>

          <Link to="/cv" className="card">
            <div className="card-icon">
              <FileUp size={22} />
            </div>
            <div className="card-content">
              <h3>Analizar mi CV</h3>
              <p>
                Sube tu currículum en PDF y recibe puntuación, fortalezas y recomendaciones.
              </p>
            </div>
            <span className="card-link">
              Subir CV <ArrowRight size={14} />
            </span>
          </Link>

          <Link to="/ofertas" className="card">
            <div className="card-icon">
              <Briefcase size={22} />
            </div>
            <div className="card-content">
              <h3>Comparar con ofertas</h3>
              <p>
                Introduce una oferta de empleo y descubre tu porcentaje de compatibilidad.
              </p>
            </div>
            <span className="card-link">
              Comparar oferta <ArrowRight size={14} />
            </span>
          </Link>
        </section>

        <div className="dashboard-actions">
          <button onClick={handleLogout} className="btn-secondary">
            <LogOut size={16} />
            Cerrar sesión
          </button>
        </div>
      </div>
    </div>
  )
}

export default Dashboard