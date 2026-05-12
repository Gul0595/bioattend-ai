import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { format } from 'date-fns'
import {
  Plus, CheckCircle2, XCircle, Clock, Loader2,
  Calendar, AlertTriangle, ChevronRight, Wallet,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { leaveApi, employeeApi } from '../services/api'
import { useAuthStore } from '../store/authStore'
import clsx from 'clsx'

const STATUS_BADGE: Record<string, string> = {
  pending:  'badge-yellow',
  approved: 'badge-green',
  rejected: 'badge-red',
}

const LEAVE_COLORS: Record<string, string> = {
  casual:    'text-blue-400',
  sick:      'text-red-400',
  earned:    'text-green-400',
  maternity: 'text-pink-400',
  paternity: 'text-purple-400',
  unpaid:    'text-slate-400',
}

export default function LeavesPage() {
  const qc = useQueryClient()
  const { user } = useAuthStore()
  const [showApply, setShowApply] = useState(false)
  const [selectedEmployee, setSelectedEmployee] = useState('')
  const [form, setForm] = useState({
    employee_id: '', leave_type: 'casual',
    start_date: '', end_date: '', reason: '',
  })
  const isHR = user?.role === 'admin' || user?.role === 'hr' || user?.role === 'manager'

  const { data: leaves = [], isLoading } = useQuery({
    queryKey: ['leaves'],
    queryFn: () => leaveApi.list(),
  })

  const { data: employees = [] } = useQuery({
    queryKey: ['employees'],
    queryFn: () => employeeApi.list(),
    enabled: isHR,
  })

  const { data: balance = [] } = useQuery({
    queryKey: ['leave-balance', selectedEmployee],
    queryFn: () => leaveApi.balance(selectedEmployee),
    enabled: !!selectedEmployee,
  })

  const createMutation = useMutation({
    mutationFn: (data: any) => leaveApi.create(data),
    onSuccess: (res) => {
      toast.success(res.message || 'Leave request submitted!')
      qc.invalidateQueries({ queryKey: ['leaves'] })
      qc.invalidateQueries({ queryKey: ['leave-balance'] })
      setShowApply(false)
      setForm({ employee_id: '', leave_type: 'casual', start_date: '', end_date: '', reason: '' })
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || 'Failed to submit leave'),
  })

  const actionMutation = useMutation({
    mutationFn: ({ id, status, reason }: any) => leaveApi.action(id, { status, rejection_reason: reason }),
    onSuccess: (_, vars) => {
      toast.success(`Leave ${vars.status}`)
      qc.invalidateQueries({ queryKey: ['leaves'] })
      qc.invalidateQueries({ queryKey: ['leave-balance'] })
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || 'Action failed'),
  })

  const pending = leaves.filter((l: any) => l.status === 'pending')
  const others  = leaves.filter((l: any) => l.status !== 'pending')

  return (
    <div className="space-y-5 animate-slide-up">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">Leave Management</h1>
          <p className="text-slate-500 text-sm mt-0.5">
            {pending.length} pending approval · {leaves.length} total requests
          </p>
        </div>
        <button className="btn-primary" onClick={() => setShowApply(true)}>
          <Plus size={15} /> Apply Leave
        </button>
      </div>

      {/* Balance checker */}
      {isHR && (
        <div className="card p-4">
          <div className="flex items-center gap-3 mb-3">
            <Wallet size={16} className="text-brand-400" />
            <h2 className="text-sm font-semibold text-white">Check Leave Balance</h2>
          </div>
          <div className="flex gap-3">
            <select className="select flex-1"
              value={selectedEmployee}
              onChange={e => setSelectedEmployee(e.target.value)}>
              <option value="">Select employee...</option>
              {employees.map((e: any) => (
                <option key={e.id} value={e.id}>{e.full_name} ({e.employee_id})</option>
              ))}
            </select>
          </div>
          {selectedEmployee && balance.length > 0 && (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 mt-3">
              {balance.map((b: any) => (
                <div key={b.leave_type} className="bg-[#111827] rounded-xl p-3 text-center border border-white/[0.06]">
                  <p className={clsx('text-lg font-bold', LEAVE_COLORS[b.leave_type] || 'text-white')}>
                    {b.available}
                  </p>
                  <p className="text-[10px] text-slate-500 capitalize mt-0.5">{b.leave_type}</p>
                  <p className="text-[10px] text-slate-600">of {b.entitled} days</p>
                  {b.pending > 0 && (
                    <p className="text-[10px] text-yellow-500">{b.pending} pending</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Pending approvals */}
      {isHR && pending.length > 0 && (
        <div className="card overflow-hidden">
          <div className="px-5 py-4 border-b border-white/[0.07] flex items-center gap-2">
            <AlertTriangle size={15} className="text-yellow-400" />
            <h2 className="text-sm font-semibold text-white">Pending Approval ({pending.length})</h2>
          </div>
          <div className="divide-y divide-white/[0.05]">
            {pending.map((l: any) => (
              <div key={l.id} className="px-5 py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-medium text-white">{l.employee_name}</p>
                  <p className="text-xs text-slate-500 mt-0.5 capitalize">
                    {l.leave_type} leave · {l.days} day{l.days !== 1 ? 's' : ''}
                    &nbsp;· {format(new Date(l.start_date), 'dd MMM')} – {format(new Date(l.end_date), 'dd MMM yyyy')}
                  </p>
                  {l.reason && <p className="text-xs text-slate-600 mt-0.5 italic">"{l.reason}"</p>}
                </div>
                <div className="flex gap-2 shrink-0">
                  <button
                    className="btn-secondary px-3 py-2 text-xs border-green-500/30 text-green-400 hover:bg-green-500/10"
                    disabled={actionMutation.isPending}
                    onClick={() => actionMutation.mutate({ id: l.id, status: 'approved' })}
                  >
                    <CheckCircle2 size={13} /> Approve
                  </button>
                  <button
                    className="btn-danger px-3 py-2 text-xs"
                    disabled={actionMutation.isPending}
                    onClick={() => {
                      const reason = window.prompt('Rejection reason (optional):')
                      actionMutation.mutate({ id: l.id, status: 'rejected', reason })
                    }}
                  >
                    <XCircle size={13} /> Reject
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* All leave requests table */}
      <div className="card overflow-hidden">
        <div className="px-5 py-4 border-b border-white/[0.07]">
          <h2 className="text-sm font-semibold text-white">All Leave Requests</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="border-b border-white/[0.07]">
              <tr>
                <th className="th">Employee</th>
                <th className="th">Type</th>
                <th className="th">Dates</th>
                <th className="th">Days</th>
                <th className="th">Status</th>
                <th className="th">Applied</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr><td colSpan={6} className="td text-center py-10">
                  <Loader2 size={20} className="animate-spin mx-auto text-slate-500" />
                </td></tr>
              ) : leaves.length === 0 ? (
                <tr><td colSpan={6} className="td text-center py-10 text-slate-500">
                  No leave requests found
                </td></tr>
              ) : leaves.map((l: any) => (
                <tr key={l.id} className="table-row">
                  <td className="td font-medium text-slate-200">{l.employee_name}</td>
                  <td className="td capitalize">
                    <span className={clsx('text-sm font-medium', LEAVE_COLORS[l.leave_type])}>
                      {l.leave_type}
                    </span>
                  </td>
                  <td className="td text-slate-400 text-xs">
                    {format(new Date(l.start_date), 'dd MMM')} – {format(new Date(l.end_date), 'dd MMM yyyy')}
                  </td>
                  <td className="td text-slate-300">{l.days}d</td>
                  <td className="td">
                    <span className={clsx('badge', STATUS_BADGE[l.status] || 'badge-slate')}>
                      {l.status}
                    </span>
                    {l.status === 'rejected' && l.rejection_reason && (
                      <p className="text-[10px] text-slate-600 mt-0.5 max-w-[160px] truncate">
                        {l.rejection_reason}
                      </p>
                    )}
                  </td>
                  <td className="td text-slate-500 text-xs">
                    {l.created_at ? format(new Date(l.created_at), 'dd MMM yyyy') : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Apply Leave Modal */}
      {showApply && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={() => setShowApply(false)} />
          <div className="relative card p-6 w-full max-w-md animate-slide-up">
            <h2 className="text-lg font-bold text-white mb-5">Apply for Leave</h2>
            <div className="space-y-3">
              {isHR && (
                <div>
                  <label className="label">Employee</label>
                  <select className="select" value={form.employee_id}
                    onChange={e => setForm(p => ({ ...p, employee_id: e.target.value }))}>
                    <option value="">Select employee...</option>
                    {employees.map((e: any) => (
                      <option key={e.id} value={e.id}>{e.full_name}</option>
                    ))}
                  </select>
                </div>
              )}
              <div>
                <label className="label">Leave Type</label>
                <select className="select" value={form.leave_type}
                  onChange={e => setForm(p => ({ ...p, leave_type: e.target.value }))}>
                  {['casual', 'sick', 'earned', 'maternity', 'paternity', 'unpaid'].map(t => (
                    <option key={t} value={t} className="capitalize">{t}</option>
                  ))}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label">Start Date</label>
                  <input type="date" className="input" value={form.start_date}
                    onChange={e => setForm(p => ({ ...p, start_date: e.target.value }))} />
                </div>
                <div>
                  <label className="label">End Date</label>
                  <input type="date" className="input" value={form.end_date}
                    onChange={e => setForm(p => ({ ...p, end_date: e.target.value }))} />
                </div>
              </div>
              <div>
                <label className="label">Reason (optional)</label>
                <textarea className="input min-h-[80px] resize-none" placeholder="Reason for leave..."
                  value={form.reason}
                  onChange={e => setForm(p => ({ ...p, reason: e.target.value }))} />
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-5">
              <button className="btn-secondary" onClick={() => setShowApply(false)}>Cancel</button>
              <button
                className="btn-primary"
                disabled={createMutation.isPending || !form.start_date || !form.end_date || (isHR && !form.employee_id)}
                onClick={() => createMutation.mutate({
                  ...form,
                  employee_id: form.employee_id || undefined,
                })}
              >
                {createMutation.isPending
                  ? <><Loader2 size={14} className="animate-spin" /> Submitting...</>
                  : <><Calendar size={14} /> Submit Request</>}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
