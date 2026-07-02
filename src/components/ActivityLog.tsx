import type { LogEntry, LogLevel, LogAction } from '../hooks/useLogger'
import { Button } from '@/components/ui/button'

interface ActivityLogProps {
  logs: LogEntry[]
  onClear: () => void
  compact?: boolean
}

const levelDot: Record<LogLevel, string> = {
  info: 'bg-zinc-500',
  success: 'bg-emerald-500',
  warn: 'bg-amber-500',
  error: 'bg-red-500',
}

const actionStyles: Record<LogAction, string> = {
  TASK_CREATED: 'text-emerald-400',
  TASK_DELETED: 'text-red-400',
  TASK_UPDATED: 'text-sky-400',
  TASK_STATUS_CHANGED: 'text-amber-400',
  TASK_TOGGLED: 'text-amber-400',
  SYSTEM_ERROR: 'text-red-400 font-bold',
  STORAGE_WARNING: 'text-amber-400',
  VIEW_CHANGED: 'text-zinc-500',
  FILTER_CHANGED: 'text-zinc-500',
  APP_INIT: 'text-zinc-500',
}

const actionLabels: Record<LogAction, string> = {
  TASK_CREATED: 'CREATE',
  TASK_DELETED: 'DELETE',
  TASK_UPDATED: 'UPDATE',
  TASK_STATUS_CHANGED: 'STATUS',
  TASK_TOGGLED: 'TOGGLE',
  SYSTEM_ERROR: 'ERROR',
  STORAGE_WARNING: 'WARN',
  VIEW_CHANGED: 'VIEW',
  FILTER_CHANGED: 'FILTER',
  APP_INIT: 'INIT',
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  return `${days}d ago`
}

export function ActivityLog({ logs, onClear, compact = false }: ActivityLogProps) {
  const displayLogs = compact ? logs.slice(0, 10) : logs
  const errorCount = logs.filter(l => l.level === 'error' || l.level === 'warn').length

  return (
    <div className={compact ? '' : 'space-y-3'}>
      {/* Header */}
      {!compact && (
        <div className="flex items-center justify-between px-4 py-2 border-b border-zinc-800">
          <div className="flex items-center gap-2">
            <h3 className="text-xs font-mono text-zinc-400">Activity Log</h3>
            <span className="text-[10px] text-zinc-600">{logs.length} entries</span>
            {errorCount > 0 && (
              <span className="text-[10px] text-amber-500">
                {errorCount} {errorCount === 1 ? 'warning' : 'warnings'}
              </span>
            )}
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClear}
            className="h-6 text-[10px] font-mono text-zinc-600 hover:text-zinc-400"
          >
            clear
          </Button>
        </div>
      )}

      {/* Log entries */}
      <div className={`divide-y divide-zinc-800/30 ${compact ? 'max-h-[300px] overflow-y-auto' : ''}`}>
        {displayLogs.length === 0 ? (
          <div className="py-8 text-center text-xs font-mono text-zinc-700">
            no activity yet
          </div>
        ) : (
          displayLogs.map(entry => (
            <div key={entry.id} className="flex items-start gap-2 px-4 py-1.5 hover:bg-zinc-800/20 transition-colors">
              {/* Level dot */}
              <span className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${levelDot[entry.level]}`} />

              {/* Action badge */}
              <span className={`w-14 shrink-0 text-[10px] font-mono font-semibold ${actionStyles[entry.action]}`}>
                {actionLabels[entry.action]}
              </span>

              {/* Message */}
              <div className="flex-1 min-w-0">
                <p className="text-[11px] text-zinc-300 font-mono truncate">{entry.message}</p>
                {entry.details && !compact && (
                  <pre className="mt-0.5 text-[9px] text-zinc-600 font-mono overflow-x-auto">
                    {JSON.stringify(entry.details, null, compact ? undefined : 1).slice(0, 200)}
                  </pre>
                )}
              </div>

              {/* Timestamp */}
              <span className="shrink-0 text-[10px] text-zinc-700 font-mono">{timeAgo(entry.timestamp)}</span>
            </div>
          ))
        )}
      </div>

      {compact && logs.length > 10 && (
        <div className="px-4 py-2 text-center text-[10px] text-zinc-600 font-mono border-t border-zinc-800/30">
          +{logs.length - 10} more entries — switch to dashboard for full log
        </div>
      )}
    </div>
  )
}
