import { useState } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import { Fingerprint, Loader2, ArrowLeft, CheckCircle2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { passwordApi } from '../services/api'

export function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [sent, setSent]   = useState(false)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    try {
      const res = await passwordApi.forgot(email)
      setSent(true)
      toast.success(res.message)
    } catch {
      toast.error('Something went wrong. Try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0a0e1a] p-4">
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center mb-8">
          <div className="w-14 h-14 rounded-2xl bg-brand-500 flex items-center justify-center shadow-lg shadow-brand-500/25 mb-4">
            <Fingerprint size={28} className="text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white">Forgot Password</h1>
          <p className="text-slate-500 text-sm mt-1">We'll send a reset link to your email</p>
        </div>

        <div className="card p-6">
          {sent ? (
            <div className="text-center space-y-3 py-4">
              <CheckCircle2 size={40} className="text-green-400 mx-auto" />
              <p className="text-white font-semibold">Check your inbox!</p>
              <p className="text-slate-400 text-sm">
                If <span className="text-brand-400">{email}</span> is registered, a reset link has been sent.
                Link expires in 30 minutes.
              </p>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="label">Email address</label>
                <input type="email" className="input" placeholder="your@email.com"
                  value={email} onChange={e => setEmail(e.target.value)} required />
              </div>
              <button type="submit" disabled={loading} className="btn-primary w-full justify-center py-3">
                {loading ? <><Loader2 size={15} className="animate-spin"/> Sending...</> : 'Send Reset Link'}
              </button>
            </form>
          )}
        </div>

        <Link to="/login" className="flex items-center gap-2 justify-center mt-4 text-sm text-slate-500 hover:text-slate-300 transition-colors">
          <ArrowLeft size={14} /> Back to Login
        </Link>
      </div>
    </div>
  )
}

export function ResetPasswordPage() {
  const [params]    = useSearchParams()
  const navigate    = useNavigate()
  const token       = params.get('token') || ''
  const [pw, setPw] = useState('')
  const [cpw, setCpw] = useState('')
  const [loading, setLoading] = useState(false)
  const [done, setDone] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (pw !== cpw) return toast.error('Passwords do not match')
    if (pw.length < 8) return toast.error('Minimum 8 characters')
    setLoading(true)
    try {
      const res = await passwordApi.reset(token, pw)
      toast.success(res.message)
      setDone(true)
      setTimeout(() => navigate('/login'), 2000)
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Reset failed. Link may have expired.')
    } finally {
      setLoading(false)
    }
  }

  if (!token) return (
    <div className="min-h-screen flex items-center justify-center bg-[#0a0e1a] p-4">
      <div className="card p-6 text-center max-w-sm w-full">
        <p className="text-red-400 font-semibold">Invalid reset link</p>
        <Link to="/forgot-password" className="btn-primary mt-4 justify-center">Request new link</Link>
      </div>
    </div>
  )

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0a0e1a] p-4">
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center mb-8">
          <div className="w-14 h-14 rounded-2xl bg-brand-500 flex items-center justify-center shadow-lg shadow-brand-500/25 mb-4">
            <Fingerprint size={28} className="text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white">Set New Password</h1>
        </div>
        <div className="card p-6">
          {done ? (
            <div className="text-center py-4 space-y-2">
              <CheckCircle2 size={40} className="text-green-400 mx-auto" />
              <p className="text-white font-semibold">Password reset!</p>
              <p className="text-slate-400 text-sm">Redirecting to login...</p>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="label">New Password</label>
                <input type="password" className="input" placeholder="Min 8 characters"
                  value={pw} onChange={e => setPw(e.target.value)} required />
              </div>
              <div>
                <label className="label">Confirm Password</label>
                <input type="password" className="input"
                  value={cpw} onChange={e => setCpw(e.target.value)} required />
              </div>
              <button type="submit" disabled={loading} className="btn-primary w-full justify-center py-3">
                {loading ? <><Loader2 size={14} className="animate-spin"/> Setting...</> : 'Reset Password'}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}
