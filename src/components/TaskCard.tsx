import type { Task } from '../types'

interface TaskCardProps {
  task: Task
  isSelected: boolean
  onToggle: () => void
  onEdit: () => void
  onDelete: () => void
}

const prioColor = {
  high: 'border-l-red-500',
  medium: 'border-l-amber-500',
  low: 'border-l-emerald-500',
}

const prioDot = {
  high: 'bg-red-500',
  medium: 'bg-amber-500',
  low: 'bg-emerald-500',
}

const statusIcon = {
  todo: '○',
  in_progress: '◔',
  done: '●',
  paused: '⊘',
}

const statusLabel = {
  todo: 'todo',
  in_progress: 'doing',
  done: 'done',
  paused: 'hold',
}

export function TaskCard({ task, isSelected, onToggle, onEdit, onDelete }: TaskCardProps) {
  return (
    <div
      className={`group flex items-start gap-3 border-l-2 px-4 py-3 transition-all cursor-pointer ${
        prioColor[task.priority]
      } ${
        isSelected
          ? 'bg-zinc-800/60 border-zinc-600'
          : 'border-transparent hover:bg-zinc-800/30'
      }`}
      onClick={onToggle}
    >
      <span
        className={`mt-0.5 text-lg select-none ${
          task.status === 'done' ? 'text-emerald-500' :
          task.status === 'in_progress' ? 'text-amber-400' :
          task.status === 'paused' ? 'text-zinc-500' :
          'text-zinc-400'
        }`}
      >
        {statusIcon[task.status]}
      </span>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span
            className={`text-sm font-medium ${
              task.status === 'done' ? 'line-through text-zinc-500' : 'text-zinc-200'
            }`}
          >
            {task.title}
          </span>
          {task.value != null && (
            <span className="text-[11px] font-mono font-bold text-emerald-500 shrink-0">
              ${task.value >= 1000 ? `${(task.value / 1000).toFixed(1)}k` : task.value}
            </span>
          )}
          <span className={`h-1.5 w-1.5 rounded-full ${prioDot[task.priority]}`} />
          <span className="text-[10px] uppercase tracking-widest text-zinc-600 font-mono">
            {statusLabel[task.status]}
          </span>
        </div>
        {task.description && (
          <p className="mt-0.5 text-xs text-zinc-500 line-clamp-1">{task.description}</p>
        )}
        <span className="text-[10px] text-zinc-700 font-mono">#{task.group}</span>
      </div>
      <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          onClick={e => { e.stopPropagation(); onEdit() }}
          className="rounded px-1.5 py-0.5 text-[11px] text-zinc-500 hover:text-zinc-300 hover:bg-zinc-700/50 transition-colors font-mono"
        >
          e
        </button>
        <button
          onClick={e => { e.stopPropagation(); onDelete() }}
          className="rounded px-1.5 py-0.5 text-[11px] text-zinc-500 hover:text-red-400 hover:bg-red-900/30 transition-colors font-mono"
        >
          d
        </button>
      </div>
    </div>
  )
}
