import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'
import { useAuthStore } from './store/authStore'
import Layout from './components/layout/Layout'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import EmployeesPage from './pages/EmployeesPage'
import EmployeeDetailPage from './pages/EmployeeDetailPage'
import AttendancePage from './pages/AttendancePage'
import FaceKioskPage from './pages/FaceKioskPage'
import ReportsPage from './pages/ReportsPage'
import SettingsPage from './pages/SettingsPage'
import LeavesPage from './pages/LeavesPage'
import { ForgotPasswordPage, ResetPasswordPage } from './pages/PasswordResetPages'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Toaster
          position="top-right"
          toastOptions={{
            style: {
              background: '#1c2536',
              color: '#e2e8f0',
              border: '1px solid rgba(59,130,246,0.3)',
              borderRadius: '12px',
              fontFamily: 'Sora, sans-serif',
              fontSize: '14px',
            },
            success: { iconTheme: { primary: '#22c55e', secondary: '#0a0e1a' } },
            error:   { iconTheme: { primary: '#ef4444', secondary: '#0a0e1a' } },
          }}
        />
        <Routes>
          {/* Public routes */}
          <Route path="/login"           element={<LoginPage />} />
          <Route path="/kiosk"           element={<FaceKioskPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/reset-password"  element={<ResetPasswordPage />} />

          {/* Protected routes inside Layout */}
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard"          element={<DashboardPage />} />
            <Route path="employees"          element={<EmployeesPage />} />
            <Route path="employees/:id"      element={<EmployeeDetailPage />} />
            <Route path="attendance"         element={<AttendancePage />} />
            <Route path="reports"            element={<ReportsPage />} />
            <Route path="leaves"             element={<LeavesPage />} />
            <Route path="settings"           element={<SettingsPage />} />
          </Route>

          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
