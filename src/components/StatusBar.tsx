import type { VimMode, Priority } from '../types'

interface StatusBarProps {
  mode: VimMode
  taskCount: number
  filteredCount: number
  selectedIndex: number
  priorityFilter: Priority | 'all'
  onResetFilter: () => void
}

const modeLabels: Record<VimMode, string> = {
  NORMAL: 'NORMAL',
  INSERT: '-- INSERT --',
  SEARCH: 'SEARCH',
}

const modeColors: Record<VimMode, string> = {
  NORMAL: 'text-emerald-400',
  INSERT: 'text-amber-400',
  SEARCH: 'text-sky-400',
}

export function StatusBar({
  mode,
  taskCount,
  filteredCount,
  selectedIndex,
  priorityFilter,
  onResetFilter,
}: StatusBarProps) {
  const showFiltered = filteredCount !== taskCount

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 border-t border-zinc-800 bg-zinc-950/95 backdrop-blur-sm">
      <div className="mx-auto flex h-8 max-w-4xl items-center justify-between px-3 text-xs font-mono">
        <div className="flex items-center gap-3">
          <span className={modeColors[mode]}>{modeLabels[mode]}</span>
          <span className="text-zinc-500">
            {selectedIndex + 1}/{filteredCount}
          </span>
          {showFiltered && (
            <button
              onClick={onResetFilter}
              className="text-zinc-500 hover:text-zinc-300 transition-colors"
            >
              @filtered <span className="text-zinc-600">x</span>
            </button>
          )}
        </div>
        <div className="flex items-center gap-3 text-zinc-600">
          {priorityFilter !== 'all' && (
            <span className="text-amber-500">
              prio:{priorityFilter}
            </span>
          )}
          <span className="hidden sm:inline">
            {taskCount} tasks
          </span>
          {mode === 'NORMAL' && (
            <span className="hidden sm:inline text-zinc-700">
              ? for help
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
