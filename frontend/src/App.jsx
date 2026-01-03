import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Opponents from './pages/Opponents'
import TacticalAnalysis from './pages/TacticalAnalysis'
import Fixtures from './pages/Fixtures'

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <Layout>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/fixtures" element={<Fixtures />} />
                <Route path="/opponents" element={<Opponents />} />
                <Route path="/opponents/:teamId/analysis" element={<TacticalAnalysis />} />
              </Routes>
            </Layout>
          </ProtectedRoute>
        }
      />
    </Routes>
  )
}

export default App
