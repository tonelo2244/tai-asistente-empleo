// URL base del backend
const BASE_URL = 'http://127.0.0.1:8000/api'

// --- Tipos ---

export interface RespuestaLogin {
  token:    string
  rol:      string
  username: string
}

export interface RespuestaRegistro {
  message: string
  token:   string
}

export interface RespuestaYo {
  username: string
  email:    string
  rol:      string
}

export interface PerfilProfesional {
  username:        string
  nombre_completo: string
  telefono:        string
  ciudad:          string
  estudios:        string
  experiencia:     string
  habilidades:     string
}

export interface ResultadoAnalisis {
  id:                     number
  resumen:                string
  fortalezas:             string[]
  aspectos_mejora:        string[]
  recomendaciones:        string[]
  puntuacion_completitud: number
  fecha_creacion:         string
}

// --- Autenticación ---

// Los errores de DRF llegan como { campo: ["mensaje"] } o { non_field_errors: ["mensaje"] }.
// Devolvemos el primer mensaje disponible, sin asumir en qué campo vendrá el error.
function extraerPrimerError(errorData: unknown, fallback: string): string {
  if (!errorData || typeof errorData !== 'object') return fallback

  for (const valor of Object.values(errorData as Record<string, unknown>)) {
    if (Array.isArray(valor) && typeof valor[0] === 'string') return valor[0]
  }

  return fallback
}

export async function loginUsuario(username: string, password: string): Promise<RespuestaLogin> {
  const respuesta = await fetch(`${BASE_URL}/usuarios/login/`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({ username, password })
  })
  if (!respuesta.ok) {
    const error = await respuesta.json()
    throw new Error(extraerPrimerError(error, 'Error al iniciar sesión'))
  }
  return respuesta.json()
}

export async function registrarUsuario(
  username: string,
  email:    string,
  password: string,
  rol:      string
): Promise<RespuestaRegistro> {
  const respuesta = await fetch(`${BASE_URL}/usuarios/registro/`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({ username, email, password, rol })
  })
  if (!respuesta.ok) {
    const error = await respuesta.json()
    throw new Error(extraerPrimerError(error, 'Error al registrarse'))
  }
  return respuesta.json()
}

export async function obtenerUsuarioAutenticado(token: string): Promise<RespuestaYo> {
  const respuesta = await fetch(`${BASE_URL}/usuarios/yo/`, {
    headers: { 'Authorization': `Token ${token}` }
  })
  if (!respuesta.ok) throw new Error('Token inválido o expirado')
  return respuesta.json()
}

export async function ping(): Promise<{ message: string }> {
  const respuesta = await fetch(`${BASE_URL}/ping/`)
  return respuesta.json()
}

// --- Perfil profesional ---

export async function obtenerPerfilProfesional(token: string): Promise<PerfilProfesional> {
  const respuesta = await fetch(`${BASE_URL}/usuarios/perfil-profesional/`, {
    headers: { 'Authorization': `Token ${token}` }
  })
  if (!respuesta.ok) throw new Error('Error al obtener el perfil profesional')
  return respuesta.json()
}

export async function actualizarPerfilProfesional(
  token: string,
  datos: Partial<PerfilProfesional>
): Promise<PerfilProfesional> {
  const respuesta = await fetch(`${BASE_URL}/usuarios/perfil-profesional/`, {
    method:  'PUT',
    headers: {
      'Content-Type':  'application/json',
      'Authorization': `Token ${token}`
    },
    body: JSON.stringify(datos)
  })
  if (!respuesta.ok) {
    const error = await respuesta.json()
    throw new Error(extraerPrimerError(error, 'Error al guardar el perfil profesional'))
  }
  return respuesta.json()
}

// --- Análisis persistente (Fase 5) ---

// POST — genera un análisis nuevo y lo guarda
export async function generarAnalisisPerfil(token: string): Promise<ResultadoAnalisis> {
  const respuesta = await fetch(`${BASE_URL}/usuarios/analisis/generar/`, {
    method:  'POST',
    headers: { 'Authorization': `Token ${token}` }
  })
  if (!respuesta.ok) throw new Error('Error al generar el análisis')
  return respuesta.json()
}

// GET — devuelve el análisis más reciente
export async function obtenerUltimoAnalisis(token: string): Promise<ResultadoAnalisis> {
  const respuesta = await fetch(`${BASE_URL}/usuarios/analisis/ultimo/`, {
    headers: { 'Authorization': `Token ${token}` }
  })
  if (!respuesta.ok) throw new Error('Sin análisis previo')
  return respuesta.json()
}

// GET — devuelve todos los análisis del usuario
export async function obtenerHistorialAnalisis(token: string): Promise<ResultadoAnalisis[]> {
  const respuesta = await fetch(`${BASE_URL}/usuarios/analisis/historial/`, {
    headers: { 'Authorization': `Token ${token}` }
  })
  if (!respuesta.ok) throw new Error('Error al obtener el historial')
  return respuesta.json()
}