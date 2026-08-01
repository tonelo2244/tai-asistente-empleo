import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import {
  generarAnalisisPerfil,
  obtenerUltimoAnalisis,
  obtenerHistorialAnalisis,
} from '../services/api'
import type { ResultadoAnalisis } from '../services/api'

function AnalisisPerfilPage() {
  const { token } = useAuth()
  const navigate = useNavigate()

  const [analisis, setAnalisis] = useState<ResultadoAnalisis | null>(null)
  const [historial, setHistorial] = useState<ResultadoAnalisis[]>([])
  const [cargando, setCargando] = useState(true)
  const [generando, setGenerando] = useState(false)
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

    try {
      const lista = await obtenerHistorialAnalisis(token)
      setHistorial(lista)
      setMostrarHistorial(true)
    } catch (err: any) {
      setError(err.message)
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
          <p className="text-center text-muted">Cargando tu análisis...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="analysis-page">
      <div className="analysis-container">
        <Link to="/dashboard" className="back-link">
          ← Volver al dashboard
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
            {generando ? '⏳ Analizando...' : '📊 Generar nuevo análisis'}
          </button>

          <button onClick={handleVerHistorial} className="btn-secondary">
            📈 Ver historial
          </button>
        </div>

        {error && (
          <div className="analysis-result" style={{ borderTopColor: '#ef4444' }}>
            <p style={{ color: '#dc2626' }}>⚠️ {error}</p>
          </div>
        )}

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
                <strong>📝 Resumen:</strong> {analisis.resumen}
              </p>
            </div>

            {analisis.fortalezas.length > 0 && (
              <div className="analysis-section strengths">
                <h3>💪 Fortalezas</h3>
                <ul>
                  {analisis.fortalezas.map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              </div>
            )}

            {analisis.aspectos_mejora.length > 0 && (
              <div className="analysis-section improvements">
                <h3>🎯 Aspectos a mejorar</h3>
                <ul>
                  {analisis.aspectos_mejora.map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              </div>
            )}

            {analisis.recomendaciones.length > 0 && (
              <div className="analysis-section recommendations">
                <h3>💡 Recomendaciones</h3>
                <ul>
                  {analisis.recomendaciones.map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              </div>
            )}

            {analisis.aspectos_mejora.length === 0 && (
              <div className="no-content">
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
            <h3>📋 Historial de análisis</h3>

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
              <div style={{ fontSize: '48px', marginBottom: '16px' }}>📊</div>

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
                {generando ? '⏳ Analizando...' : 'Generar primer análisis'}
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
          <Link to="/perfil" style={{ marginRight: '16px' }}>
            📋 Editar mi perfil
          </Link>

          <Link to="/dashboard">🏠 Volver al dashboard</Link>
        </div>
      </div>
    </div>
  )
}

export default AnalisisPerfilPage

