import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { format } from 'date-fns'
import {
  Calendar, Filter, Download, Plus, Loader2,
  Clock, CheckCircle2, AlertCircle, UserX,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { attendanceApi, departmentApi } from '../services/api'
import clsx from 'clsx'

const STATUS_COLORS: Record<string, string> = {
  present:  'badge-green',
  late:     'badge-yellow',
  absent:   'badge-red',
  half_day: 'badge-yellow',
  on_leave: 'badge-blue',
  holiday:  'badge-purple',
}

export default function AttendancePage() {
  const qc = useQueryClient()
  const today = format(new Date(), 'yyyy-MM-dd')
  const [dateFrom, setDateFrom] = useState(today)
  const [dateTo, setDateTo] = useState(today)
  const [statusFilter, setStatusFilter] = useState('')
  const [showManual, setShowManual] = useState(false)
  const [manualForm, setManualForm] = useState({
    employee_id: '', date: today,
    check_in: '', check_out: '', status: 'present', notes: '',
  })

  const { data: logs = [], isLoading } = useQuery({
    queryKey: ['attendance-logs', dateFrom, dateTo, statusFilter],
    queryFn: () => attendanceApi.logs({
      start_date: dateFrom,
      end_date: dateTo,
      status: statusFilter || undefined,
      per_page: 200,
    }),
  })

  const { data: todaySummary } = useQuery({
    queryKey: ['today-summary'],
    queryFn: () => attendanceApi.todaySummary(),
    refetchInterval: 30_000,
  })

  const manualMutation = useMutation({
    mutationFn: (data: any) => attendanceApi.manual({
      ...data,
      check_in: data.check_in ? new Date(data.date + 'T' + data.check_in).toISOString() : undefined,
      check_out: data.check_out ? new Date(data.date + 'T' + data.check_out).toISOString() : undefined,
    }),
    onSuccess: () => {
      toast.success('Attendance recorded!')
      qc.invalidateQueries({ queryKey: ['attendance-logs'] })
      setShowManual(false)
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || 'Failed'),
  })

  return (
    <div className="space-y-5 animate-slide-up">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">Attendance</h1>
          <p className="text-slate-500 text-sm mt-0.5">Track and manage employee attendance</p>
        </div>
        <div className="flex gap-2">
          <button className="btn-secondary" onClick={() => setShowManual(true)}>
            <Plus size={14} /> Manual Entry
          </button>
        </div>
      </div>

      {/* Today summary strip */}
      {todaySummary && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: 'Present', value: todaySummary.present_today, icon: CheckCircle2, cls: 'text-green-400' },
            { label: 'Late',    value: todaySummary.late_today,    icon: AlertCircle,  cls: 'text-yellow-400' },
            { label: 'Absent',  value: todaySummary.absent_today,  icon: UserX,        cls: 'text-red-400' },
            { label: 'On Leave',value: todaySummary.on_leave_today,icon: Clock,        cls: 'text-blue-400' },
          ].map(({ label, value, icon: Icon, cls }) => (
            <div key={label} className="card px-4 py-3 flex items-center gap-3">
              <Icon size={18} className={cls} />
              <div>
                <p className="text-lg font-bold text-white">{value}</p>
                <p className="text-xs text-slate-500">{label}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Filters */}
      <div className="card p-4 flex flex-col sm:flex-row gap-3">
        <div className="flex items-center gap-2">
          <Calendar size={14} className="text-slate-500" />
          <input type="date" className="input w-40" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
        </div>
        <span className="text-slate-500 self-center">to</span>
        <input type="date" className="input w-40" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
        <select className="select w-40" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="">All Statuses</option>
          {['present','late','absent','half_day','on_leave','holiday'].map(s => (
            <option key={s} value={s}>{s.replace('_',' ')}</option>
          ))}
        </select>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        <div className="px-5 py-4 border-b border-white/[0.07] flex items-center justify-between">
          <p className="text-sm font-semibold text-white">{logs.length} records</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="border-b border-white/[0.07]">
              <tr>
                <th className="th">Employee</th>
                <th className="th">Date</th>
                <th className="th">Check In</th>
                <th className="th">Check Out</th>
                <th className="th">Hours</th>
                <th className="th">Method</th>
                <th className="th">Status</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr><td colSpan={7} className="td text-center py-10">
                  <Loader2 size={20} className="animate-spin mx-auto text-slate-500" />
                </td></tr>
              ) : logs.length === 0 ? (
                <tr><td colSpan={7} className="td text-center py-10 text-slate-500">No records found</td></tr>
              ) : logs.map((log: any) => (
                <tr key={log.id} className="table-row">
                  <td className="td font-medium text-slate-200">{log.employee_name ?? log.employee_id}</td>
                  <td className="td text-slate-400">{format(new Date(log.date), 'dd MMM yyyy')}</td>
                  <td className="td font-mono text-xs">
                    {log.check_in ? format(new Date(log.check_in), 'hh:mm a') : '—'}
                    {log.is_late && <span className="ml-1 badge badge-yellow py-0 text-[10px]">Late</span>}
                  </td>
                  <td className="td font-mono text-xs">
                    {log.check_out ? format(new Date(log.check_out), 'hh:mm a') : '—'}
                  </td>
                  <td className="td">
                    {log.work_hours > 0 ? (
                      <span className="text-slate-300">{log.work_hours.toFixed(1)}h</span>
                    ) : '—'}
                    {log.overtime_hours > 0 && (
                      <span className="text-yellow-400 text-xs ml-1">+{log.overtime_hours.toFixed(1)}</span>
                    )}
                  </td>
                  <td className="td">
                    <span className="badge badge-slate text-[10px]">{log.method}</span>
                  </td>
                  <td className="td">
                    <span className={clsx('badge', STATUS_COLORS[log.status] ?? 'badge-slate')}>
                      {log.status?.replace('_', ' ')}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Manual Entry Modal */}
      {showManual && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={() => setShowManual(false)} />
          <div className="relative card p-6 w-full max-w-md animate-slide-up">
            <h2 className="text-lg font-bold text-white mb-5">Manual Attendance Entry</h2>
            <div className="space-y-4">
              <div>
                <label className="label">Employee ID (UUID)</label>
                <input className="input" placeholder="Employee UUID" value={manualForm.employee_id}
                  onChange={(e) => setManualForm(p => ({ ...p, employee_id: e.target.value }))} />
              </div>
              <div>
                <label className="label">Date</label>
                <input type="date" className="input" value={manualForm.date}
                  onChange={(e) => setManualForm(p => ({ ...p, date: e.target.value }))} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label">Check In</label>
                  <input type="time" className="input" value={manualForm.check_in}
                    onChange={(e) => setManualForm(p => ({ ...p, check_in: e.target.value }))} />
                </div>
                <div>
                  <label className="label">Check Out</label>
                  <input type="time" className="input" value={manualForm.check_out}
                    onChange={(e) => setManualForm(p => ({ ...p, check_out: e.target.value }))} />
                </div>
              </div>
              <div>
                <label className="label">Status</label>
                <select className="select" value={manualForm.status}
                  onChange={(e) => setManualForm(p => ({ ...p, status: e.target.value }))}>
                  {['present','late','absent','half_day','on_leave','holiday'].map(s => (
                    <option key={s} value={s}>{s.replace('_',' ')}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="label">Notes</label>
                <input className="input" placeholder="Optional note" value={manualForm.notes}
                  onChange={(e) => setManualForm(p => ({ ...p, notes: e.target.value }))} />
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button className="btn-secondary" onClick={() => setShowManual(false)}>Cancel</button>
              <button
                className="btn-primary"
                disabled={manualMutation.isPending || !manualForm.employee_id}
                onClick={() => manualMutation.mutate(manualForm)}
              >
                {manualMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
