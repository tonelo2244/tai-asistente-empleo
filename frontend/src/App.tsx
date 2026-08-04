import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'

import './App.css'

import { AuthProvider, useAuth } from './context/AuthContext'

import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import PerfilProfesional from './pages/PerfilProfesional'
import AnalisisPerfilPage from './pages/AnalisisPerfil'
import AnalisisCVPage from './pages/AnalisisCV'
import CompararOfertaPage from './pages/CompararOferta'
import OptimizarLinkedInPage from './pages/OptimizarLinkedIn'

function RutaProtegida({ children }: { children: React.ReactNode }) {
  const { token } = useAuth()

  return token ? <>{children}</> : <Navigate to="/login" replace />
}

function AppRoutes() {
  const { token } = useAuth()

  return (
    <Routes>
      <Route path="/" element={<Navigate to={token ? '/dashboard' : '/login'} replace />} />

      <Route path="/login" element={<Login />} />
      <Route path="/registro" element={<Register />} />

      <Route
        path="/dashboard"
        element={
          <RutaProtegida>
            <Dashboard />
          </RutaProtegida>
        }
      />

      <Route
        path="/perfil"
        element={
          <RutaProtegida>
            <PerfilProfesional />
          </RutaProtegida>
        }
      />

      <Route
        path="/analisis"
        element={
          <RutaProtegida>
            <AnalisisPerfilPage />
          </RutaProtegida>
        }
      />

      <Route
        path="/cv"
        element={
          <RutaProtegida>
            <AnalisisCVPage />
          </RutaProtegida>
        }
      />

      <Route
        path="/ofertas"
        element={
          <RutaProtegida>
            <CompararOfertaPage />
          </RutaProtegida>
        }
      />

      <Route
        path="/linkedin"
        element={
          <RutaProtegida>
            <OptimizarLinkedInPage />
          </RutaProtegida>
        }
      />
    </Routes>
  )
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App