import React from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { Calendar, Target, TrendingUp, LogOut } from 'lucide-react'

const Layout = ({ children }) => {
  const location = useLocation()
  const navigate = useNavigate()
  
  const navItems = [
    { path: '/', label: 'Próximo Adversário', icon: Target },
    { path: '/calendar', label: 'Calendário', icon: Calendar },
  ]
  
  const handleLogout = () => {
    localStorage.removeItem('isAuthenticated')
    navigate('/login')
  }
  
  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="bg-[#003C71] text-white shadow-lg">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <TrendingUp size={32} />
              <div>
                <h1 className="text-2xl font-bold">Gil Vicente FC</h1>
                <p className="text-sm text-gray-300">Tactical Intelligence Platform</p>
              </div>
            </div>
            <button
              onClick={handleLogout}
              className="flex items-center space-x-2 px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg transition-colors"
            >
              <LogOut size={20} />
              <span>Sair</span>
            </button>
          </div>
        </div>
      </header>
      
      {/* Navigation */}
      <nav className="bg-white border-b shadow-sm">
        <div className="container mx-auto px-4">
          <div className="flex space-x-8">
            {navItems.map(({ path, label, icon: Icon }) => (
              <Link
                key={path}
                to={path}
                className={`flex items-center space-x-2 py-4 border-b-2 transition-colors ${
                  (path === '/' ? location.pathname === '/' : location.pathname.startsWith(path))
                    ? 'border-[#C41E3A] text-[#C41E3A]'
                    : 'border-transparent text-gray-600 hover:text-[#C41E3A]'
                }`}
              >
                <Icon size={20} />
                <span className="font-medium">{label}</span>
              </Link>
            ))}
          </div>
        </div>
      </nav>
      
      {/* Main Content */}
      <main className="flex-1 container mx-auto px-4 py-8">
        {children}
      </main>
      
      {/* Footer */}
      <footer className="bg-gray-800 text-white py-4">
        <div className="container mx-auto px-4 text-center">
          <p className="text-sm">© 2025-2026 Gil Vicente FC - Tactical Intelligence Platform</p>
        </div>
      </footer>
    </div>
  )
}

export default Layout
