import type { Task } from '../types'
import type { LogEntry } from '../hooks/useLogger'
import { ActivityLog } from './ActivityLog'
import {
  PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis,
  Tooltip, ResponsiveContainer,
} from 'recharts'

interface DashboardProps {
  tasks: Task[]
  logs: LogEntry[]
  onClearLogs: () => void
}

const COLORS = {
  high: '#ef4444',
  medium: '#f59e0b',
  low: '#10b981',
}

const STATUS_COLORS = {
  todo: '#52525b',
  in_progress: '#fbbf24',
  done: '#10b981',
  paused: '#78716c',
}

export function Dashboard({ tasks, logs, onClearLogs }: DashboardProps) {
  const total = tasks.length
  const done = tasks.filter(t => t.status === 'done').length
  const todo = tasks.filter(t => t.status === 'todo').length
  const inProgress = tasks.filter(t => t.status === 'in_progress').length
  const paused = tasks.filter(t => t.status === 'paused').length

  const priorityData = [
    { name: 'High', value: tasks.filter(t => t.priority === 'high').length, color: COLORS.high },
    { name: 'Medium', value: tasks.filter(t => t.priority === 'medium').length, color: COLORS.medium },
    { name: 'Low', value: tasks.filter(t => t.priority === 'low').length, color: COLORS.low },
  ].filter(d => d.value > 0)

  const statusData = [
    { name: 'todo', value: todo, color: STATUS_COLORS.todo },
    { name: 'doing', value: inProgress, color: STATUS_COLORS.in_progress },
    { name: 'done', value: done, color: STATUS_COLORS.done },
    { name: 'hold', value: paused, color: STATUS_COLORS.paused },
  ].filter(d => d.value > 0)

  const groupMap = new Map<string, number>()
  tasks.forEach(t => groupMap.set(t.group, (groupMap.get(t.group) || 0) + 1))
  const groupData = Array.from(groupMap.entries())
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)

  const completionRate = total > 0 ? Math.round((done / total) * 100) : 0
  const errorCount = logs.filter(l => l.level === 'error' || l.level === 'warn').length

  return (
    <div className="space-y-6 p-4 pb-16">
      {/* Hero stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: 'Total', value: total, color: 'text-zinc-100' },
          { label: 'To Do', value: todo, color: 'text-zinc-400' },
          { label: 'Doing', value: inProgress, color: 'text-amber-400' },
          { label: 'Done', value: done, color: 'text-emerald-400' },
        ].map(s => (
          <div key={s.label} className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-3">
            <div className="text-[10px] uppercase tracking-widest text-zinc-600 font-mono">{s.label}</div>
            <div className={`text-2xl font-bold mt-1 ${s.color}`}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-4">
          <h3 className="text-xs font-mono text-zinc-400 mb-3">Priority Distribution</h3>
          {priorityData.length > 0 ? (
            <div className="flex items-center justify-center">
              <ResponsiveContainer width="100%" height={180}>
                <PieChart>
                  <Pie data={priorityData} cx="50%" cy="50%" innerRadius={50} outerRadius={70} paddingAngle={4} dataKey="value">
                    {priorityData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                  </Pie>
                  <Tooltip contentStyle={{ background: '#18181b', border: '1px solid #27272a', borderRadius: '8px', fontSize: '12px', fontFamily: 'monospace' }} />
                </PieChart>
              </ResponsiveContainer>
              <div className="space-y-1.5">
                {priorityData.map(d => (
                  <div key={d.name} className="flex items-center gap-2 text-xs font-mono">
                    <span className="h-2 w-2 rounded-full" style={{ background: d.color }} />
                    <span className="text-zinc-400">{d.name}</span>
                    <span className="text-zinc-200">{d.value}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : <p className="text-xs text-zinc-600 font-mono text-center py-8">no data</p>}
        </div>

        <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-4">
          <h3 className="text-xs font-mono text-zinc-400 mb-3">Status Overview</h3>
          {statusData.length > 0 ? (
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={statusData}>
                <XAxis dataKey="name" tick={{ fill: '#71717a', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis hide />
                <Tooltip contentStyle={{ background: '#18181b', border: '1px solid #27272a', borderRadius: '8px', fontSize: '12px', fontFamily: 'monospace' }} />
                <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                  {statusData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : <p className="text-xs text-zinc-600 font-mono text-center py-8">no data</p>}
        </div>
      </div>

      {/* Completion + Groups */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-4">
          <h3 className="text-xs font-mono text-zinc-400 mb-3">Completion Rate</h3>
          <div className="flex items-center gap-4">
            <div className="relative h-20 w-20">
              <svg className="h-20 w-20 -rotate-90" viewBox="0 0 36 36">
                <circle cx="18" cy="18" r="15.5" fill="none" stroke="#27272a" strokeWidth="3" />
                <circle cx="18" cy="18" r="15.5" fill="none" stroke="#10b981" strokeWidth="3"
                  strokeDasharray={`${completionRate} ${100 - completionRate}`} strokeLinecap="round" />
              </svg>
              <span className="absolute inset-0 flex items-center justify-center text-sm font-bold text-zinc-200 font-mono">{completionRate}%</span>
            </div>
            <div className="text-xs text-zinc-500 font-mono">
              <span className="text-emerald-400">{done}</span> done of <span className="text-zinc-300">{total}</span> total
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-4">
          <h3 className="text-xs font-mono text-zinc-400 mb-3">By Group</h3>
          {groupData.length > 0 ? (
            <div className="space-y-2">
              {groupData.map(g => (
                <div key={g.name} className="flex items-center gap-2">
                  <span className="text-xs font-mono text-zinc-400 w-16 truncate">#{g.name}</span>
                  <div className="flex-1 h-4 rounded-full bg-zinc-800 overflow-hidden">
                    <div className="h-full rounded-full bg-amber-600/60 transition-all" style={{ width: `${(g.value / total) * 100}%` }} />
                  </div>
                  <span className="text-xs font-mono text-zinc-500 w-4 text-right">{g.value}</span>
                </div>
              ))}
            </div>
          ) : <p className="text-xs text-zinc-600 font-mono text-center py-8">no data</p>}
        </div>
      </div>

      {/* System Health */}
      {errorCount > 0 && (
        <div className="rounded-lg border border-amber-900/50 bg-amber-950/20 p-4">
          <h3 className="text-xs font-mono text-amber-400 mb-2">⚠ System ({errorCount})</h3>
          {logs.filter(l => l.level === 'error' || l.level === 'warn').slice(0, 3).map(entry => (
            <div key={entry.id} className="flex items-start gap-2 py-0.5 text-[11px] font-mono">
              <span className="text-amber-500 shrink-0">!</span>
              <span className="text-zinc-400">{entry.message}</span>
            </div>
          ))}
        </div>
      )}

      {/* Activity */}
      <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 overflow-hidden">
        <ActivityLog logs={logs} onClear={onClearLogs} compact />
      </div>
    </div>
  )
}
