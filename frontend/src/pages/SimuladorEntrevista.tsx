import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import {
  ArrowLeft,
  MessageSquare,
  History,
  ThumbsUp,
  Target,
  Lightbulb,
  Home,
  ArrowRight,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import {
  iniciarEntrevista,
  finalizarEntrevista,
  obtenerHistorialEntrevistas,
} from '../services/api'
import type {
  PreguntaEntrevista,
  RespuestaEntrevista,
  SimulacionEntrevista,
} from '../services/api'
import Spinner from '../components/Spinner'
import Alert from '../components/Alert'

type Vista = 'inicio' | 'preguntas' | 'resultado' | 'historial'

function SimuladorEntrevistaPage() {
  const { token } = useAuth()
  const navigate = useNavigate()

  const [vista, setVista] = useState<Vista>('inicio')
  const [preguntas, setPreguntas] = useState<PreguntaEntrevista[]>([])
  const [indiceActual, setIndiceActual] = useState(0)
  const [respuestaActual, setRespuestaActual] = useState('')
  const [respuestas, setRespuestas] = useState<RespuestaEntrevista[]>([])
  const [resultado, setResultado] = useState<SimulacionEntrevista | null>(null)
  const [historial, setHistorial] = useState<SimulacionEntrevista[]>([])
  const [cargando, setCargando] = useState(false)
  const [cargandoHistorial, setCargandoHistorial] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!token) {
      navigate('/login')
    }
  }, [token, navigate])

  async function handleIniciar() {
    if (!token) return

    setCargando(true)
    setError('')

    try {
      const datos = await iniciarEntrevista(token)
      setPreguntas(datos.preguntas)
      setRespuestas([])
      setIndiceActual(0)
      setRespuestaActual('')
      setVista('preguntas')
    } catch (err: any) {
      setError(err.message)
    } finally {
      setCargando(false)
    }
  }

  async function handleSiguiente(e: React.FormEvent) {
    e.preventDefault()
    if (!token || cargando) return

    const preguntaActual = preguntas[indiceActual]
    const nuevasRespuestas = [
      ...respuestas,
      { ...preguntaActual, respuesta: respuestaActual },
    ]

    const esUltimaPregunta = indiceActual + 1 >= preguntas.length

    if (!esUltimaPregunta) {
      setRespuestas(nuevasRespuestas)
      setRespuestaActual('')
      setIndiceActual(indiceActual + 1)
      return
    }

    setCargando(true)
    setError('')

    try {
      const nuevoResultado = await finalizarEntrevista(token, nuevasRespuestas)
      setResultado(nuevoResultado)
      setVista('resultado')
    } catch (err: any) {
      setError(err.message)
    } finally {
      setCargando(false)
    }
  }

  async function handleVerHistorial() {
    if (!token) return

    setError('')
    setCargandoHistorial(true)

    try {
      const lista = await obtenerHistorialEntrevistas(token)
      setHistorial(lista)
      setVista('historial')
    } catch (err: any) {
      setError(err.message)
    } finally {
      setCargandoHistorial(false)
    }
  }

  function volverAlInicio() {
    setVista('inicio')
    setResultado(null)
    setError('')
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
          <h1>Simulador de entrevistas</h1>
          <p className="text-muted">
            Responde a preguntas generadas a partir de tu perfil, tu CV, tus ofertas comparadas
            y tu LinkedIn, y recibe feedback sobre tus respuestas
          </p>
        </div>

        {error && <Alert type="error">{error}</Alert>}

        {vista === 'inicio' && (
          <div className="analysis-result">
            <div style={{ textAlign: 'center', padding: '48px 24px' }}>
              <div className="card-icon" style={{ margin: '0 auto 16px' }}>
                <MessageSquare size={26} />
              </div>
              <h3 style={{ margin: '0 0 8px 0' }}>Practica antes de tu próxima entrevista</h3>
              <p className="text-muted" style={{ margin: '0 0 24px 0' }}>
                Se generarán 10 preguntas adaptadas a tu información disponible en TAI.
              </p>

              <div className="analysis-actions" style={{ marginBottom: 0 }}>
                <button onClick={handleIniciar} disabled={cargando} className="btn-primary">
                  {cargando ? <Spinner size={14} variant="light" /> : <MessageSquare size={16} />}
                  {cargando ? 'Preparando...' : 'Iniciar simulación'}
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
            </div>
          </div>
        )}

        {vista === 'preguntas' && preguntas[indiceActual] && (
          <div className="analysis-result">
            <p className="text-muted" style={{ fontSize: '13px', margin: '0 0 8px 0' }}>
              Pregunta {indiceActual + 1} de {preguntas.length}
            </p>

            <div className="score-progress" style={{ marginBottom: '24px' }}>
              <div
                className="score-progress-fill"
                style={{
                  width: `${((indiceActual + 1) / preguntas.length) * 100}%`,
                  backgroundColor: 'var(--primary)',
                }}
              />
            </div>

            <div className="analysis-summary">
              <p>{preguntas[indiceActual].pregunta}</p>
            </div>

            <form onSubmit={handleSiguiente} className="profile-form" style={{ marginTop: '24px' }}>
              <div className="form-field">
                <label htmlFor="respuesta">Tu respuesta</label>
                <textarea
                  id="respuesta"
                  value={respuestaActual}
                  onChange={e => setRespuestaActual(e.target.value)}
                  placeholder="Escribe tu respuesta..."
                  disabled={cargando}
                  style={{ minHeight: '160px' }}
                />
              </div>

              <div className="profile-actions">
                <button type="submit" disabled={cargando} className="btn-primary">
                  {cargando ? (
                    <Spinner size={14} variant="light" />
                  ) : indiceActual + 1 >= preguntas.length ? (
                    <MessageSquare size={16} />
                  ) : (
                    <ArrowRight size={16} />
                  )}
                  {cargando
                    ? 'Evaluando...'
                    : indiceActual + 1 >= preguntas.length
                      ? 'Finalizar entrevista'
                      : 'Siguiente pregunta'}
                </button>
              </div>
            </form>
          </div>
        )}

        {vista === 'resultado' && resultado && (
          <div className="analysis-result">
            <div className="analysis-score-section">
              <div className="analysis-score">
                <h2>Resultado de la simulación</h2>

                <div className="score-progress">
                  <div
                    className={`score-progress-fill ${getScoreBadgeClass(resultado.clasificacion)}`}
                    style={{ width: `${resultado.puntuacion}%` }}
                  />
                </div>

                <p>
                  Has obtenido una puntuación de <strong>{resultado.puntuacion}%</strong>{' '}
                  (<strong>{resultado.clasificacion}</strong>).
                </p>
              </div>

              <div className={`score-badge ${getScoreBadgeClass(resultado.clasificacion)}`}>
                {resultado.puntuacion}%
              </div>
            </div>

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
                  Aún no se han detectado fortalezas en esta simulación.
                </p>
              )}
            </div>

            {resultado.aspectos_mejora.length > 0 && (
              <div className="analysis-section improvements">
                <h3>
                  <Target size={18} /> Aspectos a mejorar
                </h3>
                <ul>
                  {resultado.aspectos_mejora.map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              </div>
            )}

            {resultado.recomendaciones.length > 0 && (
              <div className="analysis-section recommendations">
                <h3>
                  <Lightbulb size={18} /> Recomendaciones
                </h3>
                <ul>
                  {resultado.recomendaciones.map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              </div>
            )}

            <details style={{ marginTop: '24px' }}>
              <summary style={{ cursor: 'pointer', fontWeight: 600, fontSize: '14px' }}>
                Ver preguntas y respuestas
              </summary>
              <div className="history-list" style={{ marginTop: '16px' }}>
                {resultado.preguntas.map(item => (
                  <div key={item.orden} className="history-item">
                    <p className="history-item-id" style={{ marginBottom: '8px' }}>
                      {item.orden}. {item.pregunta}
                    </p>
                    <p className="history-item-summary">
                      {item.respuesta || 'Sin respuesta.'}
                    </p>
                  </div>
                ))}
              </div>
            </details>

            <div
              style={{
                marginTop: '24px',
                paddingTop: '24px',
                borderTop: '1px solid #e5e7eb',
                display: 'flex',
                gap: '12px',
                flexWrap: 'wrap',
              }}
            >
              <button onClick={handleIniciar} disabled={cargando} className="btn-primary">
                {cargando ? <Spinner size={14} variant="light" /> : <MessageSquare size={16} />}
                Nueva simulación
              </button>
              <button onClick={volverAlInicio} className="btn-secondary">
                Volver al inicio
              </button>
            </div>
          </div>
        )}

        {vista === 'historial' && historial.length > 0 && (
          <div className="history-section">
            <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <History size={18} /> Historial de simulaciones
            </h3>

            <div className="history-list">
              {historial.map(item => (
                <div key={item.id} className="history-item">
                  <div className="history-item-header">
                    <div>
                      <div className="history-item-id">Simulación #{item.id}</div>
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

                  {item.fortalezas.length > 0 && (
                    <p className="history-item-summary">
                      <strong>Fortalezas:</strong> {item.fortalezas.join(' ')}
                    </p>
                  )}

                  {item.recomendaciones.length > 0 && (
                    <p className="history-item-summary">
                      <strong>Recomendaciones:</strong> {item.recomendaciones.join(' ')}
                    </p>
                  )}

                  <details style={{ marginTop: '8px' }}>
                    <summary style={{ cursor: 'pointer', fontSize: '13px' }}>
                      Ver preguntas y respuestas
                    </summary>
                    <div style={{ marginTop: '8px' }}>
                      {item.preguntas.map(pregunta => (
                        <div key={pregunta.orden} style={{ marginBottom: '8px' }}>
                          <p className="history-item-summary">
                            <strong>{pregunta.orden}. {pregunta.pregunta}</strong>
                          </p>
                          <p className="history-item-summary">
                            {pregunta.respuesta || 'Sin respuesta.'}
                          </p>
                        </div>
                      ))}
                    </div>
                  </details>
                </div>
              ))}
            </div>
          </div>
        )}

        {vista === 'historial' && historial.length === 0 && (
          <div className="analysis-result">
            <div style={{ textAlign: 'center', padding: '48px 24px' }}>
              <div className="card-icon" style={{ margin: '0 auto 16px' }}>
                <History size={26} />
              </div>
              <h3 style={{ margin: '0 0 8px 0' }}>Aún no has realizado ninguna simulación</h3>
              <p className="text-muted" style={{ margin: 0 }}>
                Inicia tu primera simulación de entrevista desde el inicio de esta página.
              </p>
            </div>
          </div>
        )}

        {(vista === 'historial' || vista === 'resultado') && (
          <div
            style={{
              textAlign: 'center',
              marginTop: '32px',
              paddingTop: '24px',
              borderTop: '1px solid #e5e7eb',
            }}
          >
            {vista === 'historial' && (
              <button
                onClick={volverAlInicio}
                className="btn-secondary"
                style={{ marginRight: '16px' }}
              >
                Volver al inicio
              </button>
            )}
            <Link to="/dashboard" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
              <Home size={15} /> Volver al dashboard
            </Link>
          </div>
        )}
      </div>
    </div>
  )
}

export default SimuladorEntrevistaPage
