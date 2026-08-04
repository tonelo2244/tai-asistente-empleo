import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import {
  ArrowLeft,
  IdCard,
  History,
  Sparkles,
  ThumbsUp,
  Target,
  Lightbulb,
  Home,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import {
  crearOptimizacionLinkedIn,
  obtenerHistorialLinkedIn,
} from '../services/api'
import type { DatosLinkedIn, OptimizacionLinkedIn } from '../services/api'
import Spinner from '../components/Spinner'
import Alert from '../components/Alert'

const FORM_INICIAL: DatosLinkedIn = {
  titular_actual: '',
  extracto: '',
  experiencia: '',
  estudios: '',
  habilidades: '',
}

function OptimizarLinkedInPage() {
  const { token } = useAuth()
  const navigate = useNavigate()

  const [form, setForm] = useState<DatosLinkedIn>(FORM_INICIAL)
  const [resultado, setResultado] = useState<OptimizacionLinkedIn | null>(null)
  const [historial, setHistorial] = useState<OptimizacionLinkedIn[]>([])
  const [optimizando, setOptimizando] = useState(false)
  const [cargandoHistorial, setCargandoHistorial] = useState(false)
  const [mostrarHistorial, setMostrarHistorial] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!token) {
      navigate('/login')
    }
  }, [token, navigate])

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) {
    const { name, value } = e.target
    setForm(prev => ({ ...prev, [name]: value }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!token) return

    setOptimizando(true)
    setError('')

    try {
      const nueva = await crearOptimizacionLinkedIn(token, form)
      setResultado(nueva)
      setMostrarHistorial(false)
      setForm(FORM_INICIAL)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setOptimizando(false)
    }
  }

  async function handleVerHistorial() {
    if (!token) return

    setError('')
    setCargandoHistorial(true)

    try {
      const lista = await obtenerHistorialLinkedIn(token)
      setHistorial(lista)
      setMostrarHistorial(true)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setCargandoHistorial(false)
    }
  }

  function getScoreBadgeClass(clasificacion: string): string {
    if (clasificacion === 'Excelente' || clasificacion === 'Muy buena') return 'high'
    if (clasificacion === 'Buena' || clasificacion === 'Mejorable') return 'medium'
    return 'low'
  }

  return (
    <div className="analysis-page">
      <div className="analysis-container">
        <Link to="/dashboard" className="back-link">
          <ArrowLeft size={16} /> Volver al dashboard
        </Link>

        <div className="analysis-header">
          <h1>Optimizar tu perfil de LinkedIn</h1>
          <p className="text-muted">
            Introduce tu perfil actual de LinkedIn y recibe una puntuación, un titular
            optimizado y un plan de mejora
          </p>
        </div>

        <form onSubmit={handleSubmit} className="profile-form" style={{ marginBottom: '32px' }}>
          <div className="form-field">
            <label htmlFor="titular_actual">Titular profesional actual</label>
            <input
              id="titular_actual"
              type="text"
              name="titular_actual"
              placeholder="Ej: Desarrollador Full Stack"
              value={form.titular_actual}
              onChange={handleChange}
              disabled={optimizando}
            />
          </div>

          <div className="form-field">
            <label htmlFor="extracto">Extracto / Acerca de</label>
            <textarea
              id="extracto"
              name="extracto"
              placeholder="Pega aquí tu extracto (Acerca de) de LinkedIn..."
              value={form.extracto}
              onChange={handleChange}
              disabled={optimizando}
              required
            />
          </div>

          <div className="form-field">
            <label htmlFor="experiencia">Experiencia</label>
            <textarea
              id="experiencia"
              name="experiencia"
              placeholder="Ej: Desarrollador Full Stack en TechCorp (2020-2023)..."
              value={form.experiencia}
              onChange={handleChange}
              disabled={optimizando}
            />
          </div>

          <div className="form-field">
            <label htmlFor="estudios">Estudios</label>
            <textarea
              id="estudios"
              name="estudios"
              placeholder="Ej: Grado en Ingeniería Informática, Universidad Complutense de Madrid"
              value={form.estudios}
              onChange={handleChange}
              disabled={optimizando}
            />
          </div>

          <div className="form-field">
            <label htmlFor="habilidades">Habilidades</label>
            <textarea
              id="habilidades"
              name="habilidades"
              placeholder="Ej: Python, Django, React, TypeScript, Docker, Git..."
              value={form.habilidades}
              onChange={handleChange}
              disabled={optimizando}
            />
          </div>

          {error && <Alert type="error">{error}</Alert>}

          <div className="profile-actions">
            <button
              type="submit"
              disabled={optimizando}
              className="btn-primary"
            >
              {optimizando ? <Spinner size={14} variant="light" /> : <IdCard size={16} />}
              {optimizando ? 'Optimizando...' : 'Optimizar mi perfil'}
            </button>

            <button
              type="button"
              onClick={handleVerHistorial}
              disabled={cargandoHistorial}
              className="btn-secondary"
            >
              {cargandoHistorial ? <Spinner size={14} variant="dark" /> : <History size={16} />}
              {cargandoHistorial ? 'Cargando...' : 'Ver historial'}
            </button>
          </div>
        </form>

        {resultado && !mostrarHistorial && (
          <div className="analysis-result">
            <div className="analysis-score-section">
              <div className="analysis-score">
                <h2>Puntuación del perfil de LinkedIn</h2>

                <div className="score-progress">
                  <div
                    className={`score-progress-fill ${getScoreBadgeClass(resultado.clasificacion)}`}
                    style={{ width: `${resultado.puntuacion}%` }}
                  />
                </div>

                <p>
                  Tu perfil obtiene una puntuación de <strong>{resultado.puntuacion}%</strong>{' '}
                  (<strong>{resultado.clasificacion}</strong>).
                </p>
              </div>

              <div className={`score-badge ${getScoreBadgeClass(resultado.clasificacion)}`}>
                {resultado.puntuacion}%
              </div>
            </div>

            {resultado.titular_optimizado && (
              <div className="analysis-summary">
                <p>
                  <Sparkles size={16} style={{ verticalAlign: '-3px', marginRight: '6px' }} />
                  <strong>Titular optimizado:</strong> {resultado.titular_optimizado}
                </p>
              </div>
            )}

            <div className="analysis-section strengths">
              <h3>
                <ThumbsUp size={18} /> Fortalezas
              </h3>
              {resultado.fortalezas.length > 0 ? (
                <ul>
                  {resultado.fortalezas.map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              ) : (
                <p className="text-muted" style={{ margin: 0 }}>
                  Aún no se han detectado fortalezas en tu perfil de LinkedIn.
                </p>
              )}
            </div>

            {resultado.debilidades.length > 0 && (
              <div className="analysis-section improvements">
                <h3>
                  <Target size={18} /> Debilidades
                </h3>
                <ul>
                  {resultado.debilidades.map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              </div>
            )}

            {resultado.plan_mejora.length > 0 && (
              <div className="analysis-section recommendations">
                <h3>
                  <Lightbulb size={18} /> Plan de mejora
                </h3>
                <ul>
                  {resultado.plan_mejora.map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
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
                Análisis generado el {resultado.fecha_creacion}
              </p>
            </div>
          </div>
        )}

        {mostrarHistorial && historial.length > 0 && (
          <div className="history-section">
            <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <History size={18} /> Historial de optimizaciones
            </h3>

            <div className="history-list">
              {historial.map(item => (
                <div key={item.id} className="history-item">
                  <div className="history-item-header">
                    <div>
                      <div className="history-item-id">
                        {item.titular_optimizado || item.titular_actual || 'Perfil de LinkedIn'}
                      </div>
                      <div className="history-item-date">{item.fecha_creacion}</div>
                    </div>

                    <div className="history-item-score">{item.puntuacion}%</div>
                  </div>

                  <div className="score-progress history-progress">
                    <div
                      className={`score-progress-fill ${getScoreBadgeClass(item.clasificacion)}`}
                      style={{ width: `${item.puntuacion}%` }}
                    />
                  </div>

                  <p className="history-item-summary">
                    Clasificación: {item.clasificacion}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {mostrarHistorial && historial.length === 0 && (
          <div className="analysis-result">
            <div style={{ textAlign: 'center', padding: '48px 24px' }}>
              <div className="card-icon" style={{ margin: '0 auto 16px' }}>
                <IdCard size={26} />
              </div>
              <h3 style={{ margin: '0 0 8px 0' }}>Aún no has optimizado tu perfil</h3>
              <p className="text-muted" style={{ margin: 0 }}>
                Rellena el formulario para analizar tu primer perfil de LinkedIn.
              </p>
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
          <Link to="/dashboard" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
            <Home size={15} /> Volver al dashboard
          </Link>
        </div>
      </div>
    </div>
  )
}

export default OptimizarLinkedInPage
