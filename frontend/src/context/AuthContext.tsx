import { createContext, useContext, useState } from 'react'
import type { ReactNode } from 'react'

// --- Forma del contexto: qué datos y funciones expone ---
interface AuthContextType {
  token: string | null
  rol: string | null
  username: string | null
  login: (token: string, rol: string, username: string) => void
  logout: () => void
}

// Creamos el contexto con valor inicial null
// El '!' le dice a TypeScript que confiamos en que siempre estará dentro del Provider
const AuthContext = createContext<AuthContextType>(null!)

// --- Hook personalizado para usar el contexto fácilmente ---
// En cualquier componente: const { token, login, logout } = useAuth()
export function useAuth() {
  return useContext(AuthContext)
}

// --- Provider: envuelve la app y comparte el estado ---
export function AuthProvider({ children }: { children: ReactNode }) {

  // Inicializamos leyendo de localStorage por si ya había una sesión activa
  const [token, setToken]       = useState<string | null>(localStorage.getItem('token'))
  const [rol, setRol]           = useState<string | null>(localStorage.getItem('rol'))
  const [username, setUsername] = useState<string | null>(localStorage.getItem('username'))

  // Se llama tras login o registro exitoso
  function login(nuevoToken: string, nuevoRol: string, nuevoUsername: string) {
    // Guardamos en estado React (actualiza la UI)
    setToken(nuevoToken)
    setRol(nuevoRol)
    setUsername(nuevoUsername)

    // Guardamos en localStorage (persiste al recargar)
    localStorage.setItem('token', nuevoToken)
    localStorage.setItem('rol', nuevoRol)
    localStorage.setItem('username', nuevoUsername)
  }

  // Se llama al pulsar logout
  function logout() {
    setToken(null)
    setRol(null)
    setUsername(null)

    localStorage.removeItem('token')
    localStorage.removeItem('rol')
    localStorage.removeItem('username')
  }

  return (
    <AuthContext.Provider value={{ token, rol, username, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}