import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import {
  Shield, Key, Database, Save, Loader2, CheckCircle2,
  Building2, Clock, Plus, Trash2, MapPin
} from 'lucide-react'
import toast from 'react-hot-toast'
import { useQuery, useQueryClient, useMutation as useM } from '@tanstack/react-query'
import { authApi, departmentApi, shiftApi, geofenceApi } from '../services/api'
import { useAuthStore } from '../store/authStore'
import clsx from 'clsx'

const Section = ({
  icon: Icon, title, description, children
}: { icon: any; title: string; description: string; children: React.ReactNode }) => (
  <div className="card p-6">
    <div className="flex items-center gap-3 mb-5">
      <div className="w-9 h-9 rounded-xl bg-[#111827] border border-white/10 flex items-center justify-center">
        <Icon size={17} className="text-brand-400" />
      </div>
      <div>
        <h2 className="font-semibold text-white">{title}</h2>
        <p className="text-xs text-slate-500">{description}</p>
      </div>
    </div>
    {children}
  </div>
)

export default function SettingsPage() {
  const { user } = useAuthStore()
  const qc = useQueryClient()
  const [pwForm, setPwForm] = useState({ current_password: '', new_password: '', confirm: '' })
  const [deptForm, setDeptForm] = useState({ name: '', code: '' })
  const [shiftForm, setShiftForm] = useState({ name: '', start_time: '09:00', end_time: '18:00', grace_minutes: 15 })

  const { data: departments = [] } = useQuery({ queryKey: ['departments'], queryFn: () => departmentApi.list() })
  const { data: zones = [] } = useQuery({ queryKey: ['geofence-zones'], queryFn: () => geofenceApi.listZones() })
  const [zoneForm, setZoneForm] = useState({ name: '', latitude: '', longitude: '', radius_meters: 100 })

  const createZoneMutation = useMutation({
    mutationFn: (data: any) => geofenceApi.createZone({ ...data, latitude: parseFloat(data.latitude), longitude: parseFloat(data.longitude) }),
    onSuccess: () => { toast.success('Zone created!'); qc.invalidateQueries({ queryKey: ['geofence-zones'] }); setZoneForm({ name:'', latitude:'', longitude:'', radius_meters:100 }) },
    onError: (err: any) => toast.error(err.response?.data?.detail || 'Failed'),
  })

  const deleteZoneMutation = useMutation({
    mutationFn: (id: string) => geofenceApi.deleteZone(id),
    onSuccess: () => { toast.success('Zone removed'); qc.invalidateQueries({ queryKey: ['geofence-zones'] }) },
  })
  const { data: shifts = [] }      = useQuery({ queryKey: ['shifts'],      queryFn: () => shiftApi.list() })

  const changePwMutation = useMutation({
    mutationFn: (data: any) => authApi.changePassword(data),
    onSuccess: () => {
      toast.success('Password changed!')
      setPwForm({ current_password: '', new_password: '', confirm: '' })
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || 'Failed'),
  })

  const createDeptMutation = useMutation({
    mutationFn: (data: any) => departmentApi.create(data),
    onSuccess: () => { toast.success('Department created!'); qc.invalidateQueries({ queryKey: ['departments'] }); setDeptForm({ name: '', code: '' }) },
    onError: (err: any) => toast.error(err.response?.data?.detail || 'Failed'),
  })

  const deleteDeptMutation = useMutation({
    mutationFn: (id: string) => departmentApi.delete(id),
    onSuccess: () => { toast.success('Department removed'); qc.invalidateQueries({ queryKey: ['departments'] }) },
  })

  const createShiftMutation = useMutation({
    mutationFn: (data: any) => shiftApi.create(data),
    onSuccess: () => { toast.success('Shift created!'); qc.invalidateQueries({ queryKey: ['shifts'] }); setShiftForm({ name: '', start_time: '09:00', end_time: '18:00', grace_minutes: 15 }) },
    onError: (err: any) => toast.error(err.response?.data?.detail || 'Failed'),
  })

  const deleteShiftMutation = useMutation({
    mutationFn: (id: string) => shiftApi.delete(id),
    onSuccess: () => { toast.success('Shift removed'); qc.invalidateQueries({ queryKey: ['shifts'] }) },
  })

  function handlePwSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (pwForm.new_password !== pwForm.confirm) return toast.error('Passwords do not match')
    if (pwForm.new_password.length < 8) return toast.error('Min 8 characters')
    changePwMutation.mutate({ current_password: pwForm.current_password, new_password: pwForm.new_password })
  }

  return (
    <div className="space-y-6 max-w-2xl animate-slide-up">
      <div>
        <h1 className="text-2xl font-bold text-white">Settings</h1>
        <p className="text-slate-500 text-sm mt-0.5">System configuration and preferences</p>
      </div>

      {/* Profile */}
      <Section icon={Shield} title="Profile" description="Your account information">
        <div className="grid grid-cols-2 gap-4">
          <div><label className="label">Full Name</label><input className="input" value={user?.full_name || ''} disabled /></div>
          <div><label className="label">Email</label><input className="input" value={user?.email || ''} disabled /></div>
          <div><label className="label">Role</label><input className="input capitalize" value={user?.role || ''} disabled /></div>
        </div>
      </Section>

      {/* Change Password */}
      <Section icon={Key} title="Change Password" description="Update your login credentials">
        <form onSubmit={handlePwSubmit} className="space-y-3">
          <div><label className="label">Current Password</label>
            <input type="password" className="input" value={pwForm.current_password}
              onChange={e => setPwForm(p => ({ ...p, current_password: e.target.value }))} required />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div><label className="label">New Password</label>
              <input type="password" className="input" placeholder="Min 8 characters" value={pwForm.new_password}
                onChange={e => setPwForm(p => ({ ...p, new_password: e.target.value }))} required />
            </div>
            <div><label className="label">Confirm</label>
              <input type="password" className="input" value={pwForm.confirm}
                onChange={e => setPwForm(p => ({ ...p, confirm: e.target.value }))} required />
            </div>
          </div>
          <button type="submit" disabled={changePwMutation.isPending} className="btn-primary">
            {changePwMutation.isPending ? <><Loader2 size={14} className="animate-spin" /> Saving…</> : <><Save size={14} /> Change Password</>}
          </button>
        </form>
      </Section>

      {/* Departments */}
      <Section icon={Building2} title="Departments" description="Manage company departments">
        <div className="space-y-2 mb-4">
          {departments.map((d: any) => (
            <div key={d.id} className="flex items-center justify-between p-3 rounded-xl bg-[#111827] border border-white/[0.06]">
              <div>
                <p className="text-sm font-medium text-slate-200">{d.name}</p>
                <p className="text-xs text-slate-500 font-mono">{d.code}</p>
              </div>
              <button className="btn-danger px-2 py-1 text-xs" onClick={() => deleteDeptMutation.mutate(d.id)}>
                <Trash2 size={12} />
              </button>
            </div>
          ))}
        </div>
        <div className="flex gap-2">
          <input className="input flex-1" placeholder="Name" value={deptForm.name} onChange={e => setDeptForm(p => ({ ...p, name: e.target.value }))} />
          <input className="input w-24" placeholder="Code" value={deptForm.code} onChange={e => setDeptForm(p => ({ ...p, code: e.target.value }))} />
          <button className="btn-primary px-3"
            disabled={!deptForm.name || !deptForm.code || createDeptMutation.isPending}
            onClick={() => createDeptMutation.mutate(deptForm)}>
            <Plus size={14} />
          </button>
        </div>
      </Section>

      {/* Shifts */}
      <Section icon={Clock} title="Shifts" description="Manage work shifts and timings">
        <div className="space-y-2 mb-4">
          {shifts.map((s: any) => (
            <div key={s.id} className="flex items-center justify-between p-3 rounded-xl bg-[#111827] border border-white/[0.06]">
              <div>
                <p className="text-sm font-medium text-slate-200">{s.name}</p>
                <p className="text-xs text-slate-500">{s.start_time} – {s.end_time} · Grace: {s.grace_minutes}m</p>
              </div>
              <button className="btn-danger px-2 py-1 text-xs" onClick={() => deleteShiftMutation.mutate(s.id)}>
                <Trash2 size={12} />
              </button>
            </div>
          ))}
        </div>
        <div className="grid grid-cols-2 gap-2">
          <input className="input col-span-2" placeholder="Shift name (e.g. Morning)" value={shiftForm.name}
            onChange={e => setShiftForm(p => ({ ...p, name: e.target.value }))} />
          <input type="time" className="input" value={shiftForm.start_time}
            onChange={e => setShiftForm(p => ({ ...p, start_time: e.target.value }))} />
          <input type="time" className="input" value={shiftForm.end_time}
            onChange={e => setShiftForm(p => ({ ...p, end_time: e.target.value }))} />
        </div>
        <button className="btn-primary mt-2"
          disabled={!shiftForm.name || createShiftMutation.isPending}
          onClick={() => createShiftMutation.mutate(shiftForm)}>
          <Plus size={14} /> Add Shift
        </button>
      </Section>

      {/* System Info */}
      <Section icon={Database} title="System Information" description="Current configuration">
        <div className="space-y-0">
          {[
            { label: 'App Version', value: 'BioAttend Ultimate v3.0.0' },
            { label: 'Face Model', value: 'Facenet512 (DeepFace)' },
            { label: 'Face Detector', value: 'RetinaFace' },
            { label: 'Match Threshold', value: '0.40 (Cosine Distance)' },
            { label: 'Queue System', value: 'Redis + Celery' },
            { label: 'Database', value: 'PostgreSQL (Async / asyncpg)' },
            { label: 'Auth', value: 'JWT (Access + Refresh)' },
            { label: 'Rate Limiting', value: '60 req/min per IP (SlowAPI)' },
            { label: 'Observability', value: 'Prometheus + Loguru' },
          ].map(({ label, value }) => (
            <div key={label} className="flex items-center justify-between py-2.5 border-b border-white/[0.05] last:border-0">
              <span className="text-sm text-slate-500">{label}</span>
              <span className="text-sm text-slate-300 font-mono">{value}</span>
            </div>
          ))}
        </div>
      </Section>

      {/* Geofencing */}
      <Section icon={MapPin} title="Geofence Zones" description="Restrict check-in to office premises only">
        <div className="space-y-2 mb-4">
          {zones.length === 0 && (
            <p className="text-xs text-slate-500 py-2">No zones configured — check-in allowed from anywhere (open mode)</p>
          )}
          {zones.map((z: any) => (
            <div key={z.id} className="flex items-center justify-between p-3 rounded-xl bg-[#111827] border border-white/[0.06]">
              <div>
                <p className="text-sm font-medium text-slate-200">{z.name}</p>
                <p className="text-xs text-slate-500 font-mono">{z.latitude}, {z.longitude} · {z.radius_meters}m radius</p>
                {z.bypass_kiosk && <span className="badge badge-blue text-[10px]">Kiosk bypass</span>}
              </div>
              <button className="btn-danger px-2 py-1 text-xs" onClick={() => deleteZoneMutation.mutate(z.id)}>
                <Trash2 size={12} />
              </button>
            </div>
          ))}
        </div>
        <div className="grid grid-cols-2 gap-2">
          <input className="input col-span-2" placeholder="Zone name (e.g. Head Office)" value={zoneForm.name}
            onChange={e => setZoneForm(p => ({ ...p, name: e.target.value }))} />
          <input className="input" placeholder="Latitude (28.6139)" value={zoneForm.latitude}
            onChange={e => setZoneForm(p => ({ ...p, latitude: e.target.value }))} />
          <input className="input" placeholder="Longitude (77.2090)" value={zoneForm.longitude}
            onChange={e => setZoneForm(p => ({ ...p, longitude: e.target.value }))} />
          <div className="flex items-center gap-2 col-span-2">
            <label className="label mb-0 whitespace-nowrap">Radius (m):</label>
            <input type="number" className="input w-24" value={zoneForm.radius_meters}
              onChange={e => setZoneForm(p => ({ ...p, radius_meters: parseInt(e.target.value) || 100 }))} />
            <p className="text-xs text-slate-500">Typical: 100m for building, 500m for campus</p>
          </div>
        </div>
        <button className="btn-primary mt-2"
          disabled={!zoneForm.name || !zoneForm.latitude || createZoneMutation.isPending}
          onClick={() => createZoneMutation.mutate(zoneForm)}>
          <Plus size={14} /> Add Zone
        </button>
      </Section>

      {/* Security Features */}
      <Section icon={Shield} title="Security" description="Active security features">
        <div className="space-y-2">
          {[
            { label: 'JWT Authentication', desc: 'Access + refresh token rotation' },
            { label: 'Rate Limiting', desc: '60 requests/minute per IP (SlowAPI)' },
            { label: 'GZip Compression', desc: 'All responses ≥ 1 KB compressed' },
            { label: 'Prometheus Metrics', desc: 'Endpoint at /metrics' },
            { label: 'Request Logging', desc: 'All requests logged with timing' },
            { label: 'Audit Logging', desc: 'All admin actions recorded' },
            { label: 'Biometric Encryption', desc: 'Face vectors stored as float arrays' },
          ].map(({ label, desc }) => (
            <div key={label} className="flex items-center justify-between p-3 rounded-xl bg-[#111827] border border-white/[0.05]">
              <div>
                <p className="text-sm font-medium text-slate-200">{label}</p>
                <p className="text-xs text-slate-500">{desc}</p>
              </div>
              <div className="flex items-center gap-1.5 text-xs font-semibold text-green-400">
                <CheckCircle2 size={13} /> Active
              </div>
            </div>
          ))}
        </div>
      </Section>
    </div>
  )
}
