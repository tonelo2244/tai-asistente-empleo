import { useState, useEffect, useRef } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import {
  ArrowLeft,
  Upload,
  FileText,
  History,
  ThumbsUp,
  Target,
  Lightbulb,
  CheckCircle2,
  Home,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import {
  subirCV,
  obtenerUltimoCV,
  obtenerHistorialCV,
} from '../services/api'
import type { Curriculum } from '../services/api'
import Spinner from '../components/Spinner'
import Alert from '../components/Alert'

const TIPO_PDF = 'application/pdf'
const TAMANO_MAXIMO_MB = 5
const TAMANO_MAXIMO_BYTES = TAMANO_MAXIMO_MB * 1024 * 1024

function AnalisisCVPage() {
  const { token } = useAuth()
  const navigate = useNavigate()
  const inputArchivoRef = useRef<HTMLInputElement>(null)

  const [cv, setCv] = useState<Curriculum | null>(null)
  const [historial, setHistorial] = useState<Curriculum[]>([])
  const [archivoSeleccionado, setArchivoSeleccionado] = useState<File | null>(null)
  const [cargando, setCargando] = useState(true)
  const [subiendo, setSubiendo] = useState(false)
  const [cargandoHistorial, setCargandoHistorial] = useState(false)
  const [mostrarHistorial, setMostrarHistorial] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!token) {
      navigate('/login')
      return
    }

    obtenerUltimoCV(token)
      .then(datos => setCv(datos))
      .catch(() => setCv(null))
      .finally(() => setCargando(false))
  }, [token, navigate])

  function handleSeleccionarArchivo(e: React.ChangeEvent<HTMLInputElement>) {
    const archivo = e.target.files?.[0] ?? null
    setError('')

    if (!archivo) {
      setArchivoSeleccionado(null)
      return
    }

    if (archivo.type !== TIPO_PDF && !archivo.name.toLowerCase().endsWith('.pdf')) {
      setError('Solo se admiten archivos PDF.')
      setArchivoSeleccionado(null)
      e.target.value = ''
      return
    }

    if (archivo.size > TAMANO_MAXIMO_BYTES) {
      setError(`El archivo supera el tamaño máximo permitido (${TAMANO_MAXIMO_MB} MB).`)
      setArchivoSeleccionado(null)
      e.target.value = ''
      return
    }

    setArchivoSeleccionado(archivo)
  }

  async function handleSubir() {
    if (!token || !archivoSeleccionado) return

    setSubiendo(true)
    setError('')

    try {
      const nuevo = await subirCV(token, archivoSeleccionado)
      setCv(nuevo)
      setMostrarHistorial(false)
      setArchivoSeleccionado(null)
      if (inputArchivoRef.current) inputArchivoRef.current.value = ''

      const lista = await obtenerHistorialCV(token)
      setHistorial(lista)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setSubiendo(false)
    }
  }

  async function handleVerHistorial() {
    if (!token) return

    setError('')
    setCargandoHistorial(true)

    try {
      const lista = await obtenerHistorialCV(token)
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
            <p>Cargando tu CV...</p>
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
          <h1>Análisis de tu currículum</h1>
          <p className="text-muted">
            Sube tu CV en PDF y recibe un análisis con puntuación, fortalezas y recomendaciones
          </p>
        </div>

        <div className="analysis-actions" style={{ flexDirection: 'column', alignItems: 'center' }}>
          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', justifyContent: 'center' }}>
            <input
              ref={inputArchivoRef}
              type="file"
              accept="application/pdf,.pdf"
              onChange={handleSeleccionarArchivo}
              disabled={subiendo}
              style={{ display: 'none' }}
              id="input-cv"
            />

            <label htmlFor="input-cv" className="btn-secondary" style={{ cursor: subiendo ? 'not-allowed' : 'pointer' }}>
              <Upload size={16} />
              {archivoSeleccionado ? archivoSeleccionado.name : 'Seleccionar PDF'}
            </label>

            <button
              onClick={handleSubir}
              disabled={subiendo || !archivoSeleccionado}
              className="btn-primary"
            >
              {subiendo ? <Spinner size={14} variant="light" /> : <FileText size={16} />}
              {subiendo ? 'Analizando...' : 'Subir y analizar'}
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

          <p className="text-muted" style={{ fontSize: '12px', margin: 0 }}>
            Solo archivos PDF, máximo {TAMANO_MAXIMO_MB} MB.
          </p>
        </div>

        {error && <Alert type="error">{error}</Alert>}

        {cv && !mostrarHistorial && (
          <div className="analysis-result">
            <div className="analysis-score-section">
              <div className="analysis-score">
                <h2>Puntuación del CV</h2>

                <div className="score-progress">
                  <div
                    className={`score-progress-fill ${getScoreBadgeClass(cv.puntuacion)}`}
                    style={{ width: `${cv.puntuacion}%` }}
                  />
                </div>

                <p>
                  <strong>{cv.nombre_archivo}</strong> obtiene una puntuación de{' '}
                  <strong>{cv.puntuacion}%</strong>.
                </p>
              </div>

              <div className={`score-badge ${getScoreBadgeClass(cv.puntuacion)}`}>
                {cv.puntuacion}%
              </div>
            </div>

            <div className="analysis-summary">
              <p>
                <FileText size={16} style={{ verticalAlign: '-3px', marginRight: '6px' }} />
                <strong>Resumen:</strong> {cv.resumen}
              </p>
            </div>

            <div className="analysis-section strengths">
              <h3>
                <ThumbsUp size={18} /> Fortalezas
              </h3>
              {cv.fortalezas.length > 0 ? (
                <ul>
                  {cv.fortalezas.map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              ) : (
                <p className="text-muted" style={{ margin: 0 }}>
                  Aún no se han detectado fortalezas en este CV.
                </p>
              )}
            </div>

            {cv.debilidades.length > 0 && (
              <div className="analysis-section improvements">
                <h3>
                  <Target size={18} /> Debilidades
                </h3>
                <ul>
                  {cv.debilidades.map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              </div>
            )}

            {cv.recomendaciones.length > 0 && (
              <div className="analysis-section recommendations">
                <h3>
                  <Lightbulb size={18} /> Recomendaciones
                </h3>
                <ul>
                  {cv.recomendaciones.map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              </div>
            )}

            {cv.debilidades.length === 0 && (
              <div className="no-content">
                <CheckCircle2
                  size={18}
                  style={{ verticalAlign: '-4px', marginRight: '8px', color: 'var(--success)' }}
                />
                ¡Excelente! No se han detectado debilidades relevantes en tu CV.
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
                CV analizado el {cv.fecha_subida}
              </p>
            </div>
          </div>
        )}

        {mostrarHistorial && historial.length > 0 && (
          <div className="history-section">
            <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <History size={18} /> Historial de CV analizados
            </h3>

            <div className="history-list">
              {historial.map(item => (
                <div key={item.id} className="history-item">
                  <div className="history-item-header">
                    <div>
                      <div className="history-item-id">{item.nombre_archivo}</div>
                      <div className="history-item-date">{item.fecha_subida}</div>
                    </div>

                    <div className="history-item-score">{item.puntuacion}%</div>
                  </div>

                  <div className="score-progress history-progress">
                    <div
                      className={`score-progress-fill ${getScoreBadgeClass(item.puntuacion)}`}
                      style={{ width: `${item.puntuacion}%` }}
                    />
                  </div>

                  <p className="history-item-summary">{item.resumen}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {!cv && !mostrarHistorial && (
          <div className="analysis-result">
            <div style={{ textAlign: 'center', padding: '48px 24px' }}>
              <div className="card-icon" style={{ margin: '0 auto 16px' }}>
                <FileText size={26} />
              </div>

              <h3 style={{ margin: '0 0 8px 0' }}>Aún no has subido ningún CV</h3>

              <p className="text-muted" style={{ margin: '0 0 24px 0' }}>
                Sube tu currículum en PDF para recibir un análisis con puntuación,
                fortalezas, debilidades y recomendaciones.
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

export default AnalisisCVPage
