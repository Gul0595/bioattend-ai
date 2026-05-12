import { useState } from 'react'
import { NavLink, useNavigate, Outlet } from 'react-router-dom'
import {
  LayoutDashboard, Users, Clock, BarChart3, Settings,
  ScanFace, LogOut, Menu, X, Bell, ChevronRight,
  Building2, Fingerprint, Calendar
} from 'lucide-react'
import { useAuthStore } from '../../store/authStore'
import clsx from 'clsx'

const NAV = [
  { to: '/dashboard',  icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/employees',  icon: Users,            label: 'Employees' },
  { to: '/attendance', icon: Clock,            label: 'Attendance' },
  { to: '/reports',    icon: BarChart3,         label: 'Reports' },
  { to: '/leaves',     icon: Calendar,          label: 'Leaves' },
  { to: '/settings',  icon: Settings,          label: 'Settings' },
]

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login')
  }

  const sidebar = (
    <aside className="flex flex-col h-full w-64 bg-[#111827] border-r border-white/[0.07]">
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-5 border-b border-white/[0.07]">
        <div className="w-9 h-9 rounded-xl bg-brand-500 flex items-center justify-center">
          <Fingerprint size={20} className="text-white" />
        </div>
        <div>
          <p className="text-sm font-bold text-white">BioAttend</p>
          <p className="text-[10px] text-slate-500 font-medium tracking-wider uppercase">Ultimate</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {NAV.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) => clsx(isActive ? 'nav-item-active' : 'nav-item')}
            onClick={() => setSidebarOpen(false)}
          >
            <Icon size={17} />
            <span>{label}</span>
          </NavLink>
        ))}

        <div className="pt-3 border-t border-white/[0.07]">
          <NavLink
            to="/kiosk"
            className="nav-item text-purple-400 hover:text-purple-300 hover:bg-purple-500/10"
            onClick={() => setSidebarOpen(false)}
          >
            <ScanFace size={17} />
            <span>Face Kiosk</span>
          </NavLink>
        </div>
      </nav>

      {/* User footer */}
      <div className="p-3 border-t border-white/[0.07]">
        <div className="flex items-center gap-3 px-3 py-2.5 rounded-xl">
          <div className="w-8 h-8 rounded-full bg-brand-500/20 flex items-center justify-center text-brand-400 text-sm font-bold shrink-0">
            {user?.full_name?.[0] ?? '?'}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-semibold text-white truncate">{user?.full_name}</p>
            <p className="text-[10px] text-slate-500 capitalize">{user?.role}</p>
          </div>
          <button onClick={handleLogout} className="text-slate-500 hover:text-red-400 transition-colors">
            <LogOut size={15} />
          </button>
        </div>
      </div>
    </aside>
  )

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Desktop sidebar */}
      <div className="hidden lg:flex">{sidebar}</div>

      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setSidebarOpen(false)} />
          <div className="absolute left-0 top-0 h-full z-50 flex">{sidebar}</div>
        </div>
      )}

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Topbar */}
        <header className="flex items-center justify-between px-4 lg:px-6 py-3.5 border-b border-white/[0.07] bg-[#0a0e1a] shrink-0">
          <div className="flex items-center gap-3">
            <button
              className="lg:hidden text-slate-400 hover:text-white"
              onClick={() => setSidebarOpen(true)}
            >
              <Menu size={20} />
            </button>
          </div>
          <div className="flex items-center gap-2">
            <button className="btn-secondary text-xs px-3 py-2">
              <Bell size={14} />
            </button>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-4 lg:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
