import { useQuery } from '@tanstack/react-query'
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend,
} from 'recharts'
import {
  Users, UserCheck, UserX, Clock, TrendingUp, ArrowUpRight,
  Building2, Activity, Timer, AlertCircle,
} from 'lucide-react'
import { dashboardApi } from '../services/api'
import clsx from 'clsx'

const COLORS = ['#3b82f6', '#22c55e', '#ef4444', '#f59e0b', '#a855f7']

const StatCard = ({
  icon: Icon, label, value, sub, color = 'blue', trend
}: {
  icon: any; label: string; value: any; sub?: string; color?: string; trend?: number
}) => {
  const colorMap: Record<string, string> = {
    blue:   'text-blue-400 bg-blue-500/10 border-blue-500/20',
    green:  'text-green-400 bg-green-500/10 border-green-500/20',
    red:    'text-red-400 bg-red-500/10 border-red-500/20',
    yellow: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20',
    purple: 'text-purple-400 bg-purple-500/10 border-purple-500/20',
    cyan:   'text-cyan-400 bg-cyan-500/10 border-cyan-500/20',
  }
  return (
    <div className="stat-card group">
      <div className="flex items-start justify-between">
        <div className={clsx('w-10 h-10 rounded-xl border flex items-center justify-center', colorMap[color])}>
          <Icon size={18} />
        </div>
        {trend !== undefined && (
          <div className="flex items-center gap-1 text-xs text-green-400">
            <ArrowUpRight size={13} /><span>{trend}%</span>
          </div>
        )}
      </div>
      <div>
        <p className="text-2xl font-bold text-white">{value ?? '—'}</p>
        <p className="text-xs text-slate-500 mt-0.5">{label}</p>
        {sub && <p className="text-xs text-slate-600 mt-0.5">{sub}</p>}
      </div>
    </div>
  )
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div className="card px-3 py-2 text-xs border-white/10">
      <p className="text-slate-400 mb-1">{label}</p>
      {payload.map((p: any) => (
        <p key={p.name} style={{ color: p.color }}>{p.name}: <strong>{p.value}</strong></p>
      ))}
    </div>
  )
}

export default function DashboardPage() {
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: () => dashboardApi.stats(),
    refetchInterval: 60_000,
  })

  const { data: trend = [] } = useQuery({
    queryKey: ['dashboard-trend'],
    queryFn: () => dashboardApi.trend(30),
  })

  const { data: deptBreakdown = [] } = useQuery({
    queryKey: ['dashboard-dept'],
    queryFn: () => dashboardApi.departmentBreakdown(),
  })

  const pieData = stats
    ? [
        { name: 'Present',  value: stats.present_today },
        { name: 'Absent',   value: stats.absent_today },
        { name: 'Late',     value: stats.late_today },
        { name: 'On Leave', value: stats.on_leave_today },
      ]
    : []

  return (
    <div className="space-y-6 animate-slide-up">
      <div>
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <p className="text-slate-500 text-sm mt-0.5">Real-time attendance overview</p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard icon={Users}     label="Total Employees"   value={statsLoading ? '…' : stats?.total_employees}   color="blue"  />
        <StatCard icon={UserCheck} label="Present Today"     value={statsLoading ? '…' : stats?.present_today}     color="green" trend={stats?.attendance_rate} />
        <StatCard icon={UserX}     label="Absent Today"      value={statsLoading ? '…' : stats?.absent_today}      color="red"   />
        <StatCard icon={Clock}     label="Late Arrivals"     value={statsLoading ? '…' : stats?.late_today}        color="yellow"/>
        <StatCard icon={Timer}     label="Checked In Now"    value={statsLoading ? '…' : stats?.checked_in_now}    color="cyan"  />
        <StatCard icon={Activity}  label="Attendance Rate"   value={statsLoading ? '…' : `${stats?.attendance_rate ?? 0}%`} color="purple"/>
        <StatCard icon={AlertCircle} label="On Leave"        value={statsLoading ? '…' : stats?.on_leave_today}   color="yellow"/>
        <StatCard icon={TrendingUp} label="Enrolled Biometric" value="—" color="blue" />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Attendance trend */}
        <div className="xl:col-span-2 card p-5">
          <h2 className="text-sm font-semibold text-white mb-4">30-Day Attendance Trend</h2>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={trend} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="grad-present" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#3b82f6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 10 }} tickLine={false} />
              <YAxis tick={{ fill: '#64748b', fontSize: 10 }} tickLine={false} axisLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Area type="monotone" dataKey="present" name="Present" stroke="#3b82f6" fill="url(#grad-present)" strokeWidth={2} />
              <Area type="monotone" dataKey="late"    name="Late"    stroke="#f59e0b" fill="none"               strokeWidth={1.5} strokeDasharray="4 2" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Pie chart */}
        <div className="card p-5">
          <h2 className="text-sm font-semibold text-white mb-4">Today's Status</h2>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={pieData} cx="50%" cy="50%" innerRadius={55} outerRadius={80}
                   dataKey="value" paddingAngle={3}>
                {pieData.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ fontSize: 11, color: '#94a3b8' }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Department breakdown */}
      {deptBreakdown.length > 0 && (
        <div className="card p-5">
          <h2 className="text-sm font-semibold text-white mb-4">Department Breakdown</h2>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={deptBreakdown} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="department" tick={{ fill: '#64748b', fontSize: 10 }} tickLine={false} />
              <YAxis tick={{ fill: '#64748b', fontSize: 10 }} tickLine={false} axisLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="present" name="Present" fill="#3b82f6" radius={[4,4,0,0]} />
              <Bar dataKey="absent"  name="Absent"  fill="#ef4444" radius={[4,4,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}
