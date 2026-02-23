import { Routes, Route, NavLink, Navigate } from 'react-router-dom'
import { LayoutDashboard, Upload, Database, Link2, Menu, X, Tag } from 'lucide-react'
import { useState } from 'react'
import Dashboard from './components/Dashboard'
import UploadFlow from './components/Upload'
import TagDatabase from './components/TagDatabase'
import ImpactAnalysis from './components/ImpactAnalysis'

const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/upload',    label: 'Verify Document', icon: Upload },
  { to: '/tags',      label: 'Tag Database', icon: Database },
  { to: '/impact',    label: 'Impact Analysis', icon: Link2 },
]

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="min-h-screen flex bg-gray-50">
      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-40 w-64 bg-navy-950 text-white flex flex-col
          transform transition-transform duration-200
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'} lg:relative lg:translate-x-0`}
      >
        {/* Logo */}
        <div className="flex items-center gap-3 px-6 py-5 border-b border-white/10">
          <div className="w-8 h-8 rounded-md bg-blue-500 flex items-center justify-center flex-shrink-0">
            <Tag size={16} className="text-white" />
          </div>
          <div>
            <div className="font-bold text-white text-lg leading-tight">Tag Verify</div>
            <div className="text-white/50 text-xs">Engineering Verification</div>
          </div>
          <button
            className="ml-auto lg:hidden text-white/60 hover:text-white"
            onClick={() => setSidebarOpen(false)}
          >
            <X size={18} />
          </button>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              onClick={() => setSidebarOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors
                ${isActive
                  ? 'bg-blue-600 text-white'
                  : 'text-white/70 hover:bg-white/10 hover:text-white'
                }`
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="px-6 py-4 border-t border-white/10 text-white/40 text-xs">
          Tag Verify v1.0 · Prototype
        </div>
      </aside>

      {/* Overlay for mobile */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <header className="bg-white border-b border-gray-200 px-4 py-3 flex items-center gap-3 lg:hidden">
          <button
            onClick={() => setSidebarOpen(true)}
            className="text-gray-500 hover:text-gray-700"
          >
            <Menu size={22} />
          </button>
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded bg-blue-500 flex items-center justify-center">
              <Tag size={12} className="text-white" />
            </div>
            <span className="font-bold text-navy-900">Tag Verify</span>
          </div>
        </header>

        <main className="flex-1 overflow-auto">
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/upload" element={<UploadFlow />} />
            <Route path="/upload/:docId" element={<UploadFlow />} />
            <Route path="/tags" element={<TagDatabase />} />
            <Route path="/impact" element={<ImpactAnalysis />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}
