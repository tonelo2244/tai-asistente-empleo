import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import {
  ArrowLeft,
  Briefcase,
  History,
  ThumbsUp,
  Target,
  Tags,
  Lightbulb,
  CheckCircle2,
  XCircle,
  Home,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import {
  crearOferta,
  obtenerHistorialOfertas,
} from '../services/api'
import type { DatosOferta, Oferta } from '../services/api'
import Spinner from '../components/Spinner'
import Alert from '../components/Alert'

const FORM_INICIAL: DatosOferta = {
  titulo_puesto: '',
  empresa: '',
  ubicacion: '',
  descripcion: '',
  requisitos: '',
  habilidades: '',
  estudios_requeridos: '',
  experiencia_requerida: '',
}

function CompararOfertaPage() {
  const { token } = useAuth()
  const navigate = useNavigate()

  const [form, setForm] = useState<DatosOferta>(FORM_INICIAL)
  const [resultado, setResultado] = useState<Oferta | null>(null)
  const [historial, setHistorial] = useState<Oferta[]>([])
  const [comparando, setComparando] = useState(false)
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

    setComparando(true)
    setError('')

    try {
      const nueva = await crearOferta(token, form)
      setResultado(nueva)
      setMostrarHistorial(false)
      setForm(FORM_INICIAL)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setComparando(false)
    }
  }

  async function handleVerHistorial() {
    if (!token) return

    setError('')
    setCargandoHistorial(true)

    try {
      const lista = await obtenerHistorialOfertas(token)
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
          <h1>Comparar con una oferta de empleo</h1>
          <p className="text-muted">
            Introduce una oferta y compárala con tu perfil profesional y tu último CV analizado
          </p>
        </div>

        <form onSubmit={handleSubmit} className="profile-form" style={{ marginBottom: '32px' }}>
          <div className="form-field">
            <label htmlFor="titulo_puesto">Título del puesto</label>
            <input
              id="titulo_puesto"
              type="text"
              name="titulo_puesto"
              placeholder="Ej: Desarrollador Backend"
              value={form.titulo_puesto}
              onChange={handleChange}
              disabled={comparando}
              required
            />
          </div>

          <div className="form-field">
            <label htmlFor="empresa">Empresa</label>
            <input
              id="empresa"
              type="text"
              name="empresa"
              placeholder="Ej: TechCorp"
              value={form.empresa}
              onChange={handleChange}
              disabled={comparando}
              required
            />
          </div>

          <div className="form-field">
            <label htmlFor="ubicacion">Ubicación</label>
            <input
              id="ubicacion"
              type="text"
              name="ubicacion"
              placeholder="Ej: Madrid (híbrido)"
              value={form.ubicacion}
              onChange={handleChange}
              disabled={comparando}
            />
          </div>

          <div className="form-field">
            <label htmlFor="descripcion">Descripción de la oferta</label>
            <textarea
              id="descripcion"
              name="descripcion"
              placeholder="Pega aquí la descripción completa del puesto..."
              value={form.descripcion}
              onChange={handleChange}
              disabled={comparando}
              required
            />
          </div>

          <div className="form-field">
            <label htmlFor="requisitos">Requisitos</label>
            <textarea
              id="requisitos"
              name="requisitos"
              placeholder="Ej: Experiencia con bases de datos relacionales, metodologías ágiles..."
              value={form.requisitos}
              onChange={handleChange}
              disabled={comparando}
            />
          </div>

          <div className="form-field">
            <label htmlFor="habilidades">Habilidades requeridas</label>
            <textarea
              id="habilidades"
              name="habilidades"
              placeholder="Ej: Python, Django, React, Docker, Git..."
              value={form.habilidades}
              onChange={handleChange}
              disabled={comparando}
            />
          </div>

          <div className="form-field">
            <label htmlFor="estudios_requeridos">Estudios requeridos</label>
            <input
              id="estudios_requeridos"
              type="text"
              name="estudios_requeridos"
              placeholder="Ej: Grado en Ingeniería Informática"
              value={form.estudios_requeridos}
              onChange={handleChange}
              disabled={comparando}
            />
          </div>

          <div className="form-field">
            <label htmlFor="experiencia_requerida">Experiencia requerida</label>
            <input
              id="experiencia_requerida"
              type="text"
              name="experiencia_requerida"
              placeholder="Ej: 2 años de experiencia"
              value={form.experiencia_requerida}
              onChange={handleChange}
              disabled={comparando}
            />
          </div>

          {error && <Alert type="error">{error}</Alert>}

          <div className="profile-actions">
            <button
              type="submit"
              disabled={comparando}
              className="btn-primary"
            >
              {comparando ? <Spinner size={14} variant="light" /> : <Briefcase size={16} />}
              {comparando ? 'Comparando...' : 'Comparar con mi perfil'}
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
                <h2>Compatibilidad con la oferta</h2>

                <div className="score-progress">
                  <div
                    className={`score-progress-fill ${getScoreBadgeClass(resultado.clasificacion)}`}
                    style={{ width: `${resultado.porcentaje_match}%` }}
                  />
                </div>

                <p>
                  <strong>{resultado.titulo_puesto}</strong> en{' '}
                  <strong>{resultado.empresa}</strong>: compatibilidad{' '}
                  <strong>{resultado.clasificacion}</strong>.
                </p>
              </div>

              <div className={`score-badge ${getScoreBadgeClass(resultado.clasificacion)}`}>
                {resultado.porcentaje_match}%
              </div>
            </div>

            <div className="user-info" style={{ margin: '24px 0' }}>
              <div className="user-info-item">
                <div className="stat-icon">
                  {resultado.experiencia_compatible ? (
                    <CheckCircle2 size={20} />
                  ) : (
                    <XCircle size={20} />
                  )}
                </div>
                <div className="user-info-item-text">
                  <span className="info-label">Experiencia</span>
                  <strong>{resultado.experiencia_compatible ? 'Compatible' : 'No compatible'}</strong>
                </div>
              </div>

              <div className="user-info-item">
                <div className="stat-icon">
                  {resultado.estudios_compatibles ? (
                    <CheckCircle2 size={20} />
                  ) : (
                    <XCircle size={20} />
                  )}
                </div>
                <div className="user-info-item-text">
                  <span className="info-label">Estudios</span>
                  <strong>{resultado.estudios_compatibles ? 'Compatibles' : 'No compatibles'}</strong>
                </div>
              </div>
            </div>

            <div className="analysis-section strengths">
              <h3>
                <ThumbsUp size={18} /> Habilidades coincidentes
              </h3>
              {resultado.habilidades_coincidentes.length > 0 ? (
                <ul>
                  {resultado.habilidades_coincidentes.map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              ) : (
                <p className="text-muted" style={{ margin: 0 }}>
                  No se han detectado habilidades coincidentes con esta oferta.
                </p>
              )}
            </div>

            {resultado.habilidades_faltantes.length > 0 && (
              <div className="analysis-section improvements">
                <h3>
                  <Target size={18} /> Habilidades faltantes
                </h3>
                <ul>
                  {resultado.habilidades_faltantes.map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              </div>
            )}

            {resultado.palabras_clave_coincidentes.length > 0 && (
              <div className="analysis-section">
                <h3>
                  <Tags size={18} /> Palabras clave coincidentes
                </h3>
                <ul>
                  {resultado.palabras_clave_coincidentes.map((item, i) => (
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

            {resultado.habilidades_faltantes.length === 0 &&
              resultado.experiencia_compatible &&
              resultado.estudios_compatibles && (
                <div className="no-content">
                  <CheckCircle2
                    size={18}
                    style={{ verticalAlign: '-4px', marginRight: '8px', color: 'var(--success)' }}
                  />
                  ¡Excelente compatibilidad! Cumples los requisitos detectados en esta oferta.
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
                Comparación generada el {resultado.fecha_creacion}
              </p>
            </div>
          </div>
        )}

        {mostrarHistorial && historial.length > 0 && (
          <div className="history-section">
            <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <History size={18} /> Historial de ofertas comparadas
            </h3>

            <div className="history-list">
              {historial.map(item => (
                <div key={item.id} className="history-item">
                  <div className="history-item-header">
                    <div>
                      <div className="history-item-id">
                        {item.titulo_puesto} — {item.empresa}
                      </div>
                      <div className="history-item-date">{item.fecha_creacion}</div>
                    </div>

                    <div className="history-item-score">{item.porcentaje_match}%</div>
                  </div>

                  <div className="score-progress history-progress">
                    <div
                      className={`score-progress-fill ${getScoreBadgeClass(item.clasificacion)}`}
                      style={{ width: `${item.porcentaje_match}%` }}
                    />
                  </div>

                  <p className="history-item-summary">
                    Compatibilidad: {item.clasificacion}
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
                <Briefcase size={26} />
              </div>
              <h3 style={{ margin: '0 0 8px 0' }}>Aún no has comparado ninguna oferta</h3>
              <p className="text-muted" style={{ margin: 0 }}>
                Rellena el formulario para comparar tu primera oferta de empleo.
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

export default CompararOfertaPage
