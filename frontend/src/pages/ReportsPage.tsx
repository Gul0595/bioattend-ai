import { useState, useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { format, subDays } from 'date-fns'
import { Download, Loader2, CheckCircle2, AlertCircle, ExternalLink } from 'lucide-react'
import toast from 'react-hot-toast'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { attendanceApi, departmentApi, reportApi } from '../services/api'

type TaskState = { taskId: string|null; state: 'idle'|'pending'|'success'|'failure'; downloadUrl: string|null; filename: string|null; rows: number; error: string|null }

export default function ReportsPage() {
  const [startDate, setStartDate] = useState(format(subDays(new Date(), 30), 'yyyy-MM-dd'))
  const [endDate, setEndDate]     = useState(format(new Date(), 'yyyy-MM-dd'))
  const [deptId, setDeptId]       = useState('')
  const [task, setTask] = useState<TaskState>({ taskId:null, state:'idle', downloadUrl:null, filename:null, rows:0, error:null })
  const pollRef = useRef<ReturnType<typeof setInterval>|null>(null)

  const { data: departments = [] } = useQuery({ queryKey:['departments'], queryFn:()=>departmentApi.list() })
  const { data: logs = [] } = useQuery({ queryKey:['report-logs', startDate, endDate], queryFn:()=>attendanceApi.logs({ start_date:startDate, end_date:endDate, per_page:200 }) })

  const chartData = Object.values(logs.reduce((acc:any, log:any) => {
    const d = log.date
    if (!acc[d]) acc[d] = { date:d, present:0, late:0, absent:0, on_leave:0 }
    const s = log.status
    if (s==='present') acc[d].present++
    else if (s==='late') acc[d].late++
    else if (s==='absent') acc[d].absent++
    else if (s==='on_leave') acc[d].on_leave++
    return acc
  }, {})).slice(-30) as any[]

  useEffect(() => {
    if (task.state === 'pending' && task.taskId) {
      pollRef.current = setInterval(async () => {
        try {
          const res = await reportApi.status(task.taskId!)
          if (res.state === 'SUCCESS') {
            clearInterval(pollRef.current!)
            setTask(p => ({ ...p, state:'success', downloadUrl:res.download_url, filename:res.filename, rows:res.rows }))
            toast.success(`Report ready — ${res.rows} rows`)
          } else if (res.state === 'FAILURE') {
            clearInterval(pollRef.current!)
            setTask(p => ({ ...p, state:'failure', error:res.error }))
          }
        } catch { /* keep polling */ }
      }, 3000)
    }
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [task.state, task.taskId])

  async function handleGenerate() {
    setTask({ taskId:null, state:'pending', downloadUrl:null, filename:null, rows:0, error:null })
    try {
      const res = await reportApi.generate({ start_date:startDate, end_date:endDate, ...(deptId ? { department_id:deptId } : {}) })
      setTask(p => ({ ...p, taskId:res.task_id }))
    } catch (err:any) {
      setTask(p => ({ ...p, state:'failure', error:err.response?.data?.detail||'Failed' }))
      toast.error('Failed to start report')
    }
  }

  const CT = ({ active, payload, label }:any) => !active||!payload?.length ? null : (
    <div className="card px-3 py-2 text-xs border-white/10">
      <p className="text-slate-400 mb-1">{label}</p>
      {payload.map((p:any) => <p key={p.name} style={{color:p.color}}>{p.name}: <b>{p.value}</b></p>)}
    </div>
  )

  const total = logs.length
  const present = logs.filter((l:any)=>l.status==='present').length
  const late    = logs.filter((l:any)=>l.status==='late').length
  const absent  = logs.filter((l:any)=>l.status==='absent').length

  return (
    <div className="space-y-6 animate-slide-up max-w-5xl">
      <div>
        <h1 className="text-2xl font-bold text-white">Reports</h1>
        <p className="text-slate-500 text-sm mt-0.5">Attendance analytics and CSV export</p>
      </div>

      <div className="card p-5 space-y-4">
        <h2 className="text-sm font-semibold text-white">Generate Report</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div><label className="label">Start Date</label><input type="date" className="input" value={startDate} onChange={e=>setStartDate(e.target.value)} /></div>
          <div><label className="label">End Date</label><input type="date" className="input" value={endDate} onChange={e=>setEndDate(e.target.value)} /></div>
          <div>
            <label className="label">Department</label>
            <select className="select" value={deptId} onChange={e=>setDeptId(e.target.value)}>
              <option value="">All Departments</option>
              {departments.map((d:any) => <option key={d.id} value={d.id}>{d.name}</option>)}
            </select>
          </div>
        </div>

        <button className="btn-primary" onClick={handleGenerate} disabled={task.state==='pending'}>
          {task.state==='pending' ? <><Loader2 size={14} className="animate-spin"/> Generating...</> : <><Download size={14}/> Generate CSV</>}
        </button>

        {task.state==='pending' && (
          <div className="flex items-center gap-2 text-sm text-blue-400 bg-blue-500/10 border border-blue-500/20 rounded-xl px-4 py-3">
            <Loader2 size={13} className="animate-spin"/> Generating in background... auto-polling every 3s
          </div>
        )}
        {task.state==='success' && task.downloadUrl && (
          <div className="flex items-center justify-between gap-3 bg-green-500/10 border border-green-500/20 rounded-xl px-4 py-3">
            <div className="flex items-center gap-2 text-sm text-green-400">
              <CheckCircle2 size={14}/> Report ready — <span className="font-mono text-xs">{task.filename}</span> ({task.rows} rows)
            </div>
            <a href={task.downloadUrl} download={task.filename} target="_blank" rel="noopener noreferrer"
               className="btn-primary text-xs px-3 py-1.5">
              <ExternalLink size={12}/> Download
            </a>
          </div>
        )}
        {task.state==='failure' && (
          <div className="flex items-center gap-2 text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3">
            <AlertCircle size={13}/> {task.error}
          </div>
        )}
      </div>

      {chartData.length > 0 && (
        <div className="card p-5">
          <h2 className="text-sm font-semibold text-white mb-4">
            Attendance — {format(new Date(startDate), 'dd MMM')} to {format(new Date(endDate), 'dd MMM yyyy')}
          </h2>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={chartData} margin={{ top:5, right:10, left:-20, bottom:0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)"/>
              <XAxis dataKey="date" tick={{ fill:'#64748b', fontSize:10 }} tickLine={false}/>
              <YAxis tick={{ fill:'#64748b', fontSize:10 }} tickLine={false} axisLine={false}/>
              <Tooltip content={<CT/>}/>
              <Legend wrapperStyle={{ fontSize:11, color:'#94a3b8' }}/>
              <Bar dataKey="present" name="Present" fill="#3b82f6" radius={[4,4,0,0]} stackId="a"/>
              <Bar dataKey="late"    name="Late"    fill="#f59e0b" stackId="a"/>
              <Bar dataKey="absent"  name="Absent"  fill="#ef4444" stackId="a"/>
              <Bar dataKey="on_leave" name="On Leave" fill="#a855f7" radius={[4,4,0,0]} stackId="a"/>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {total > 0 && (
        <div className="grid grid-cols-3 gap-4">
          {[
            { label:'Present', value:present, pct:((present/total)*100).toFixed(1), color:'text-green-400' },
            { label:'Late',    value:late,    pct:((late/total)*100).toFixed(1),    color:'text-yellow-400' },
            { label:'Absent',  value:absent,  pct:((absent/total)*100).toFixed(1),  color:'text-red-400' },
          ].map(({ label, value, pct, color }) => (
            <div key={label} className="card p-4 text-center">
              <p className={`text-2xl font-bold ${color}`}>{value}</p>
              <p className="text-xs text-slate-500 mt-0.5">{label}</p>
              <p className="text-xs text-slate-600">{pct}%</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
