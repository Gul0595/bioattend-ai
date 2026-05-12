import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import {
  Plus, Search, Filter, ScanFace, Fingerprint,
  ChevronRight, Loader2, UserCheck, UserX, Building2, Edit2,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { employeeApi, departmentApi, shiftApi } from '../services/api'
import clsx from 'clsx'

export default function EmployeesPage() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [search, setSearch] = useState('')
  const [deptFilter, setDeptFilter] = useState('')
  const [showAddModal, setShowAddModal] = useState(false)
  const [form, setForm] = useState({
    employee_id: '', first_name: '', last_name: '', email: '',
    phone: '', designation: '', department_id: '', shift_id: '',
    create_user: false, password: '', role: 'employee',
  })

  const { data: employees = [], isLoading } = useQuery({
    queryKey: ['employees', search, deptFilter],
    queryFn: () => employeeApi.list({ search: search || undefined, department_id: deptFilter || undefined }),
  })

  const { data: departments = [] } = useQuery({
    queryKey: ['departments'],
    queryFn: () => departmentApi.list(),
  })

  const { data: shifts = [] } = useQuery({
    queryKey: ['shifts'],
    queryFn: () => shiftApi.list(),
  })

  const createMutation = useMutation({
    mutationFn: (data: typeof form) => employeeApi.create(data),
    onSuccess: () => {
      toast.success('Employee created!')
      qc.invalidateQueries({ queryKey: ['employees'] })
      setShowAddModal(false)
      setForm({
        employee_id: '', first_name: '', last_name: '', email: '',
        phone: '', designation: '', department_id: '', shift_id: '',
        create_user: false, password: '', role: 'employee',
      })
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || 'Failed to create employee'),
  })

  const filtered = employees.filter((e: any) =>
    !search || e.full_name?.toLowerCase().includes(search.toLowerCase()) ||
    e.employee_id?.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="space-y-5 animate-slide-up">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">Employees</h1>
          <p className="text-slate-500 text-sm mt-0.5">{employees.length} total employees</p>
        </div>
        <button className="btn-primary" onClick={() => setShowAddModal(true)}>
          <Plus size={15} /> Add Employee
        </button>
      </div>

      {/* Search + Filter */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input className="input pl-9" placeholder="Search by name or ID..."
            value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <select className="select sm:w-52" value={deptFilter} onChange={(e) => setDeptFilter(e.target.value)}>
          <option value="">All Departments</option>
          {departments.map((d: any) => (
            <option key={d.id} value={d.id}>{d.name}</option>
          ))}
        </select>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="border-b border-white/[0.07]">
              <tr>
                <th className="th">Employee</th>
                <th className="th">Dept / Shift</th>
                <th className="th">Biometric</th>
                <th className="th">Status</th>
                <th className="th"></th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr><td colSpan={5} className="td text-center py-12 text-slate-500">
                  <Loader2 size={20} className="animate-spin mx-auto" />
                </td></tr>
              ) : filtered.length === 0 ? (
                <tr><td colSpan={5} className="td text-center py-12 text-slate-500">No employees found</td></tr>
              ) : filtered.map((emp: any) => (
                <tr key={emp.id} className="table-row cursor-pointer" onClick={() => navigate(`/employees/${emp.id}`)}>
                  <td className="td">
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-full bg-brand-500/10 flex items-center justify-center text-brand-400 font-bold text-sm shrink-0">
                        {emp.first_name?.[0]}{emp.last_name?.[0]}
                      </div>
                      <div>
                        <p className="font-medium text-white">{emp.full_name}</p>
                        <p className="text-xs text-slate-500">{emp.employee_id} · {emp.email}</p>
                      </div>
                    </div>
                  </td>
                  <td className="td">
                    <p className="text-slate-300">{emp.department?.name ?? '—'}</p>
                    <p className="text-xs text-slate-500">{emp.shift?.name ?? 'No shift'}</p>
                  </td>
                  <td className="td">
                    <div className="flex items-center gap-2">
                      <span className={clsx('badge', emp.face_image_url ? 'badge-green' : 'badge-slate')}>
                        <ScanFace size={11} /> Face
                      </span>
                      <span className={clsx('badge', emp.fingerprint_id ? 'badge-green' : 'badge-slate')}>
                        <Fingerprint size={11} /> FP
                      </span>
                    </div>
                  </td>
                  <td className="td">
                    <span className={clsx('badge', emp.is_active ? 'badge-green' : 'badge-red')}>
                      {emp.is_active ? <UserCheck size={11} /> : <UserX size={11} />}
                      {emp.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="td">
                    <ChevronRight size={15} className="text-slate-600 ml-auto" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add Employee Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={() => setShowAddModal(false)} />
          <div className="relative card p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto animate-slide-up">
            <h2 className="text-lg font-bold text-white mb-5">Add New Employee</h2>

            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label">Employee ID*</label>
                  <input className="input" placeholder="EMP001" value={form.employee_id}
                    onChange={(e) => setForm(p => ({ ...p, employee_id: e.target.value }))} />
                </div>
                <div>
                  <label className="label">Designation</label>
                  <input className="input" placeholder="Software Engineer" value={form.designation}
                    onChange={(e) => setForm(p => ({ ...p, designation: e.target.value }))} />
                </div>
                <div>
                  <label className="label">First Name*</label>
                  <input className="input" value={form.first_name}
                    onChange={(e) => setForm(p => ({ ...p, first_name: e.target.value }))} />
                </div>
                <div>
                  <label className="label">Last Name*</label>
                  <input className="input" value={form.last_name}
                    onChange={(e) => setForm(p => ({ ...p, last_name: e.target.value }))} />
                </div>
              </div>
              <div>
                <label className="label">Email*</label>
                <input className="input" type="email" value={form.email}
                  onChange={(e) => setForm(p => ({ ...p, email: e.target.value }))} />
              </div>
              <div>
                <label className="label">Phone</label>
                <input className="input" value={form.phone}
                  onChange={(e) => setForm(p => ({ ...p, phone: e.target.value }))} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label">Department</label>
                  <select className="select" value={form.department_id}
                    onChange={(e) => setForm(p => ({ ...p, department_id: e.target.value }))}>
                    <option value="">None</option>
                    {departments.map((d: any) => <option key={d.id} value={d.id}>{d.name}</option>)}
                  </select>
                </div>
                <div>
                  <label className="label">Shift</label>
                  <select className="select" value={form.shift_id}
                    onChange={(e) => setForm(p => ({ ...p, shift_id: e.target.value }))}>
                    <option value="">None</option>
                    {shifts.map((s: any) => <option key={s.id} value={s.id}>{s.name}</option>)}
                  </select>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <input type="checkbox" id="create_user" checked={form.create_user}
                  onChange={(e) => setForm(p => ({ ...p, create_user: e.target.checked }))} />
                <label htmlFor="create_user" className="text-sm text-slate-400 cursor-pointer">
                  Create login account
                </label>
              </div>
              {form.create_user && (
                <div>
                  <label className="label">Password*</label>
                  <input className="input" type="password" placeholder="Min 8 chars" value={form.password}
                    onChange={(e) => setForm(p => ({ ...p, password: e.target.value }))} />
                </div>
              )}
            </div>

            <div className="flex justify-end gap-3 mt-6">
              <button className="btn-secondary" onClick={() => setShowAddModal(false)}>Cancel</button>
              <button
                className="btn-primary"
                onClick={() => createMutation.mutate(form)}
                disabled={createMutation.isPending || !form.employee_id || !form.first_name || !form.email}
              >
                {createMutation.isPending ? <><Loader2 size={14} className="animate-spin" /> Creating…</> : 'Create Employee'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
