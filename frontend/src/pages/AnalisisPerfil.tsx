import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import {
  ArrowLeft,
  BarChart3,
  History,
  ThumbsUp,
  Target,
  Lightbulb,
  FileText,
  CheckCircle2,
  UserCog,
  Home,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import {
  generarAnalisisPerfil,
  obtenerUltimoAnalisis,
  obtenerHistorialAnalisis,
} from '../services/api'
import type { ResultadoAnalisis } from '../services/api'
import Spinner from '../components/Spinner'
import Alert from '../components/Alert'

function AnalisisPerfilPage() {
  const { token } = useAuth()
  const navigate = useNavigate()

  const [analisis, setAnalisis] = useState<ResultadoAnalisis | null>(null)
  const [historial, setHistorial] = useState<ResultadoAnalisis[]>([])
  const [cargando, setCargando] = useState(true)
  const [generando, setGenerando] = useState(false)
  const [cargandoHistorial, setCargandoHistorial] = useState(false)
  const [mostrarHistorial, setMostrarHistorial] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!token) {
      navigate('/login')
      return
    }

    obtenerUltimoAnalisis(token)
      .then(datos => setAnalisis(datos))
      .catch(() => setAnalisis(null))
      .finally(() => setCargando(false))
  }, [token, navigate])

  async function handleGenerar() {
    if (!token) return

    setGenerando(true)
    setError('')

    try {
      const nuevo = await generarAnalisisPerfil(token)
      setAnalisis(nuevo)
      setMostrarHistorial(false)

      const lista = await obtenerHistorialAnalisis(token)
      setHistorial(lista)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setGenerando(false)
    }
  }

  async function handleVerHistorial() {
    if (!token) return

    setError('')
    setCargandoHistorial(true)

    try {
      const lista = await obtenerHistorialAnalisis(token)
      setHistorial(lista)
      setMostrarHistorial(true)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setCargandoHistorial(false)
    }
  }

  function getScoreBadgeClass(score: number): string {
    if (score >= 80) return 'high'
    if (score >= 50) return 'medium'
    return 'low'
  }

  if (cargando) {
    return (
      <div className="analysis-page">
        <div className="analysis-container">
          <div className="loading-state">
            <Spinner size={28} variant="dark" />
            <p>Cargando tu análisis...</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="analysis-page">
      <div className="analysis-container">
        <Link to="/dashboard" className="back-link">
          <ArrowLeft size={16} /> Volver al dashboard
        </Link>

        <div className="analysis-header">
          <h1>Análisis de tu perfil profesional</h1>
          <p className="text-muted">
            Obtén recomendaciones personalizadas para mejorar tu empleabilidad
          </p>
        </div>

        <div className="analysis-actions">
          <button
            onClick={handleGenerar}
            disabled={generando}
            className="btn-primary"
          >
            {generando ? <Spinner size={14} variant="light" /> : <BarChart3 size={16} />}
            {generando ? 'Analizando...' : 'Generar nuevo análisis'}
          </button>

          <button
            onClick={handleVerHistorial}
            disabled={cargandoHistorial}
            className="btn-secondary"
          >
            {cargandoHistorial ? <Spinner size={14} variant="dark" /> : <History size={16} />}
            {cargandoHistorial ? 'Cargando...' : 'Ver historial'}
          </button>
        </div>

        {error && <Alert type="error">{error}</Alert>}

        {analisis && !mostrarHistorial && (
          <div className="analysis-result">
            <div className="analysis-score-section">
              <div className="analysis-score">
                <h2>Puntuación del perfil</h2>

                <div className="score-progress">
                  <div
                    className={`score-progress-fill ${getScoreBadgeClass(
                      analisis.puntuacion_completitud
                    )}`}
                    style={{
                      width: `${analisis.puntuacion_completitud}%`,
                    }}
                  />
                </div>

                <p>
                  Tu perfil alcanza una completitud del{' '}
                  <strong>{analisis.puntuacion_completitud}%</strong>.
                </p>
              </div>

              <div
                className={`score-badge ${getScoreBadgeClass(
                  analisis.puntuacion_completitud
                )}`}
              >
                {analisis.puntuacion_completitud}%
              </div>
            </div>

            <div className="analysis-summary">
              <p>
                <FileText size={16} style={{ verticalAlign: '-3px', marginRight: '6px' }} />
                <strong>Resumen:</strong> {analisis.resumen}
              </p>
            </div>

            <div className="analysis-section strengths">
              <h3>
                <ThumbsUp size={18} /> Fortalezas
              </h3>
              {analisis.fortalezas.length > 0 ? (
                <ul>
                  {analisis.fortalezas.map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              ) : (
                <p className="text-muted" style={{ margin: 0 }}>
                  Aún no se han detectado fortalezas. Completa más campos de tu
                  perfil para que aparezcan aquí.
                </p>
              )}
            </div>

            {analisis.aspectos_mejora.length > 0 && (
              <div className="analysis-section improvements">
                <h3>
                  <Target size={18} /> Aspectos a mejorar
                </h3>
                <ul>
                  {analisis.aspectos_mejora.map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              </div>
            )}

            {analisis.recomendaciones.length > 0 && (
              <div className="analysis-section recommendations">
                <h3>
                  <Lightbulb size={18} /> Recomendaciones
                </h3>
                <ul>
                  {analisis.recomendaciones.map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              </div>
            )}

            {analisis.aspectos_mejora.length === 0 && (
              <div className="no-content">
                <CheckCircle2
                  size={18}
                  style={{ verticalAlign: '-4px', marginRight: '8px', color: 'var(--success)' }}
                />
                ¡Excelente! Tu perfil está completo y bien estructurado. Sigue
                mejorando tu experiencia y habilidades.
              </div>
            )}

            <div
              style={{
                marginTop: '24px',
                paddingTop: '24px',
                borderTop: '1px solid #e5e7eb',
              }}
            >
              <p className="text-muted" style={{ fontSize: '12px', margin: 0 }}>
                Análisis generado el {analisis.fecha_creacion}
              </p>
            </div>
          </div>
        )}

        {mostrarHistorial && historial.length > 0 && (
          <div className="history-section">
            <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <History size={18} /> Historial de análisis
            </h3>

            <div className="history-list">
              {historial.map(item => (
                <div key={item.id} className="history-item">
                  <div className="history-item-header">
                    <div>
                      <div className="history-item-id">Análisis #{item.id}</div>
                      <div className="history-item-date">
                        {item.fecha_creacion}
                      </div>
                    </div>

                    <div className="history-item-score">
                      {item.puntuacion_completitud}%
                    </div>
                  </div>

                  <div className="score-progress history-progress">
                    <div
                      className={`score-progress-fill ${getScoreBadgeClass(
                        item.puntuacion_completitud
                      )}`}
                      style={{
                        width: `${item.puntuacion_completitud}%`,
                      }}
                    />
                  </div>

                  <p className="history-item-summary">{item.resumen}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {!analisis && !mostrarHistorial && (
          <div className="analysis-result">
            <div style={{ textAlign: 'center', padding: '48px 24px' }}>
              <div className="card-icon" style={{ margin: '0 auto 16px' }}>
                <BarChart3 size={26} />
              </div>

              <h3 style={{ margin: '0 0 8px 0' }}>Aún no tienes análisis</h3>

              <p className="text-muted" style={{ margin: '0 0 24px 0' }}>
                Completa tu perfil profesional y genera el primer análisis para
                recibir recomendaciones personalizadas.
              </p>

              <button
                onClick={handleGenerar}
                disabled={generando}
                className="btn-primary"
              >
                {generando ? <Spinner size={14} variant="light" /> : <BarChart3 size={16} />}
                {generando ? 'Analizando...' : 'Generar primer análisis'}
              </button>
            </div>
          </div>
        )}

        <div
          style={{
            textAlign: 'center',
            marginTop: '32px',
            paddingTop: '24px',
            borderTop: '1px solid #e5e7eb',
          }}
        >
          <Link
            to="/perfil"
            style={{ marginRight: '16px', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
          >
            <UserCog size={15} /> Editar mi perfil
          </Link>

          <Link to="/dashboard" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
            <Home size={15} /> Volver al dashboard
          </Link>
        </div>
      </div>
    </div>
  )
}

export default AnalisisPerfilPage

