import { useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft, ScanFace, Fingerprint, Camera, Upload,
  Loader2, Calendar, Clock, CheckCircle2, AlertCircle,
  Building2, Mail, Phone, Edit2,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { format } from 'date-fns'
import { employeeApi, attendanceApi } from '../services/api'
import clsx from 'clsx'

const statusBadge = (status: string) => {
  const map: Record<string, string> = {
    present:  'badge-green',
    late:     'badge-yellow',
    absent:   'badge-red',
    half_day: 'badge-yellow',
    on_leave: 'badge-blue',
    holiday:  'badge-purple',
  }
  return clsx('badge', map[status] ?? 'badge-slate')
}

export default function EmployeeDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)
  const [enrolling, setEnrolling] = useState(false)

  const { data: employee, isLoading: empLoading } = useQuery({
    queryKey: ['employee', id],
    queryFn: () => employeeApi.get(id!),
    enabled: !!id,
  })

  const { data: logs = [] } = useQuery({
    queryKey: ['attendance', id],
    queryFn: () => attendanceApi.byEmployee(id!, { limit: 30 }),
    enabled: !!id,
  })

  async function handleFaceEnroll(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file || !id) return
    setEnrolling(true)
    try {
      await employeeApi.enrollFace(id, file)
      toast.success('Face enrolled successfully!')
      qc.invalidateQueries({ queryKey: ['employee', id] })
    } catch (err: any) {
      toast.error(err.response?.data?.detail ?? 'Face enrollment failed')
    } finally {
      setEnrolling(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  if (empLoading) return (
    <div className="flex items-center justify-center h-64">
      <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
    </div>
  )
  if (!employee) return (
    <div className="text-center py-12 text-slate-500">Employee not found</div>
  )

  return (
    <div className="space-y-6 animate-slide-up max-w-4xl">
      {/* Back + Header */}
      <div className="flex items-center gap-4">
        <button className="btn-secondary px-3 py-2" onClick={() => navigate('/employees')}>
          <ArrowLeft size={15} />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-white">{employee.full_name}</h1>
          <p className="text-slate-500 text-sm">{employee.employee_id} · {employee.designation ?? 'No designation'}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Profile info */}
        <div className="space-y-4">
          {/* Avatar + biometric status */}
          <div className="card p-5 text-center space-y-3">
            {employee.face_image_url ? (
              <img
                src={employee.face_image_url}
                alt="Face"
                className="w-24 h-24 rounded-full mx-auto object-cover border-2 border-brand-500/30"
              />
            ) : (
              <div className="w-24 h-24 rounded-full mx-auto bg-brand-500/10 border border-brand-500/20 flex items-center justify-center text-3xl font-bold text-brand-400">
                {employee.first_name?.[0]}{employee.last_name?.[0]}
              </div>
            )}
            <div>
              <p className="text-white font-semibold">{employee.full_name}</p>
              <p className="text-xs text-slate-500">{employee.email}</p>
            </div>
            <div className="flex justify-center gap-2">
              <span className={clsx('badge', employee.face_image_url ? 'badge-green' : 'badge-slate')}>
                <ScanFace size={11} /> Face
              </span>
              <span className={clsx('badge', employee.fingerprint_id ? 'badge-green' : 'badge-slate')}>
                <Fingerprint size={11} /> FP
              </span>
            </div>
          </div>

          {/* Info */}
          <div className="card p-5 space-y-3">
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Details</h3>
            {[
              { icon: Building2, label: 'Department', value: employee.department?.name ?? '—' },
              { icon: Clock,     label: 'Shift',      value: employee.shift?.name ?? '—' },
              { icon: Mail,      label: 'Email',      value: employee.email },
              { icon: Phone,     label: 'Phone',      value: employee.phone ?? '—' },
              { icon: Calendar,  label: 'Joined',     value: employee.date_of_joining ? format(new Date(employee.date_of_joining), 'dd MMM yyyy') : '—' },
            ].map(({ icon: Icon, label, value }) => (
              <div key={label} className="flex items-start gap-3">
                <Icon size={14} className="text-slate-500 mt-0.5 shrink-0" />
                <div className="min-w-0">
                  <p className="text-[10px] text-slate-500 uppercase tracking-wider">{label}</p>
                  <p className="text-sm text-slate-300 truncate">{value}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Face enrollment */}
          <div className="card p-5 space-y-3">
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Biometric Enrollment</h3>
            <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={handleFaceEnroll} />
            <button
              className="btn-secondary w-full justify-center"
              disabled={enrolling}
              onClick={() => fileRef.current?.click()}
            >
              {enrolling
                ? <><Loader2 size={14} className="animate-spin" /> Enrolling…</>
                : <><Camera size={14} /> {employee.face_image_url ? 'Re-enroll Face' : 'Enroll Face'}</>
              }
            </button>
            {employee.biometric_enrolled_at && (
              <p className="text-xs text-slate-600 text-center">
                Last enrolled: {format(new Date(employee.biometric_enrolled_at), 'dd MMM yyyy')}
              </p>
            )}
          </div>
        </div>

        {/* Right: Attendance history */}
        <div className="lg:col-span-2 card overflow-hidden">
          <div className="px-5 py-4 border-b border-white/[0.07]">
            <h3 className="font-semibold text-white">Recent Attendance (30 days)</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b border-white/[0.07]">
                <tr>
                  <th className="th">Date</th>
                  <th className="th">Check In</th>
                  <th className="th">Check Out</th>
                  <th className="th">Hours</th>
                  <th className="th">Status</th>
                </tr>
              </thead>
              <tbody>
                {logs.length === 0 ? (
                  <tr><td colSpan={5} className="td text-center py-8 text-slate-500">No attendance records</td></tr>
                ) : logs.map((log: any) => (
                  <tr key={log.id} className="table-row">
                    <td className="td font-medium text-slate-200">
                      {format(new Date(log.date), 'dd MMM')}
                    </td>
                    <td className="td font-mono text-xs">
                      {log.check_in ? format(new Date(log.check_in), 'hh:mm a') : '—'}
                    </td>
                    <td className="td font-mono text-xs">
                      {log.check_out ? format(new Date(log.check_out), 'hh:mm a') : '—'}
                    </td>
                    <td className="td">
                      {log.work_hours > 0 ? (
                        <span className="text-slate-300">{log.work_hours.toFixed(1)}h</span>
                      ) : '—'}
                      {log.overtime_hours > 0 && (
                        <span className="text-yellow-400 text-xs ml-1">+{log.overtime_hours.toFixed(1)}OT</span>
                      )}
                    </td>
                    <td className="td">
                      <span className={statusBadge(log.status)}>
                        {log.is_late && <AlertCircle size={10} />}
                        {log.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
