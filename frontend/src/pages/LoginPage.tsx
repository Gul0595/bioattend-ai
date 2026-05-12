import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Fingerprint, Eye, EyeOff, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { authApi } from '../services/api'
import { useAuthStore } from '../store/authStore'

export default function LoginPage() {
  const navigate = useNavigate()
  const setAuth = useAuthStore((s) => s.setAuth)

  const [form, setForm] = useState({
    email: '',
    password: '',
  })

  const [showPw, setShowPw] = useState(false)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)

    try {
      // LOGIN API
      const data = await authApi.login(form.email, form.password)

      // SAVE TOKEN TEMPORARILY FIRST
      localStorage.setItem(
        'bioattend-auth',
        JSON.stringify({
          state: {
            token: data.access_token,
            refreshToken: data.refresh_token,
            user: null,
            isAuthenticated: true,
          },
          version: 0,
        })
      )

      // NOW FETCH USER
      const me = await authApi.me()

      // SAVE FULL AUTH STATE
      setAuth(data.access_token, data.refresh_token, me)

      toast.success(`Welcome back, ${me.full_name}!`)

      navigate('/dashboard')
    } catch (err: any) {
      console.error(err)

      toast.error(
        err.response?.data?.detail || 'Invalid credentials'
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0a0e1a] p-4">
      {/* Ambient glow */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-96 h-96 bg-brand-500/5 rounded-full blur-3xl" />
      </div>

      <div className="w-full max-w-sm relative">
        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div className="w-14 h-14 rounded-2xl bg-brand-500 flex items-center justify-center shadow-lg shadow-brand-500/25 mb-4">
            <Fingerprint size={28} className="text-white" />
          </div>

          <h1 className="text-2xl font-bold text-white">
            BioAttend
          </h1>

          <p className="text-slate-500 text-sm mt-1">
            Biometric Attendance System
          </p>
        </div>

        {/* Form */}
        <div className="card p-6 space-y-4">
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* EMAIL */}
            <div>
              <label className="label">
                Email address
              </label>

              <input
                type="email"
                className="input"
                placeholder="admin@company.com"
                value={form.email}
                onChange={(e) =>
                  setForm((p) => ({
                    ...p,
                    email: e.target.value,
                  }))
                }
                required
                autoComplete="off"
              />
            </div>

            {/* PASSWORD */}
            <div>
              <label className="label">
                Password
              </label>

              <div className="relative">
                <input
                  type={showPw ? 'text' : 'password'}
                  className="input pr-10"
                  placeholder="••••••••"
                  value={form.password}
                  onChange={(e) =>
                    setForm((p) => ({
                      ...p,
                      password: e.target.value,
                    }))
                  }
                  required
                  autoComplete="off"
                />

                <button
                  type="button"
                  onClick={() => setShowPw(!showPw)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                >
                  {showPw ? (
                    <EyeOff size={15} />
                  ) : (
                    <Eye size={15} />
                  )}
                </button>
              </div>
            </div>

            {/* FORGOT PASSWORD */}
            <div className="flex justify-end">
              <Link
                to="/forgot-password"
                className="text-xs text-slate-500 hover:text-brand-400 transition-colors"
              >
                Forgot password?
              </Link>
            </div>

            {/* SUBMIT */}
            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full justify-center py-3"
            >
              {loading ? (
                <>
                  <Loader2
                    size={15}
                    className="animate-spin"
                  />
                  Signing in...
                </>
              ) : (
                'Sign In'
              )}
            </button>
          </form>
        </div>

        {/* FOOTER */}
        <p className="text-center text-xs text-slate-600 mt-4">
          BioAttend Ultimate v3.0 — Secured with JWT +
          Biometrics
        </p>
      </div>
    </div>
  )
}