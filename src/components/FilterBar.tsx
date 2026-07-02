import type { Priority } from '../types'
import { Input } from '@/components/ui/input'

interface FilterBarProps {
  searchTerm: string
  onSearchChange: (term: string) => void
  priorityFilter: Priority | 'all'
  onPriorityChange: (p: Priority | 'all') => void
  onToggleView: () => void
  view: 'tasks' | 'dashboard' | 'logs'
  searchOpen: boolean
  searchInputRef: React.RefObject<HTMLInputElement | null>
  onSearchClose: () => void
  isMobileOpen: boolean
  onMobileToggle: () => void
}

const prioLabels: Record<string, string> = {
  all: 'all',
  high: '🔴',
  medium: '🟡',
  low: '🟢',
}

export function FilterBar({
  searchTerm,
  onSearchChange,
  priorityFilter,
  onPriorityChange,
  onToggleView,
  view,
  searchOpen,
  searchInputRef,
  onSearchClose,
  isMobileOpen,
  onMobileToggle,
}: FilterBarProps) {
  return (
    <div className="flex items-center gap-3 px-3 py-2">
      {/* Mobile menu toggle */}
      <button
        onClick={onMobileToggle}
        className="md:hidden text-zinc-400 hover:text-zinc-200 transition-colors"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d={isMobileOpen ? "M18 6L6 18M6 6l12 12" : "M4 6h16M4 12h16M4 18h16"} />
        </svg>
      </button>

      {/* View toggle */}
      <button
        onClick={onToggleView}
        className="flex items-center gap-1.5 text-xs font-mono text-zinc-400 hover:text-zinc-200 transition-colors"
      >
        <span className={view === 'tasks' ? 'text-amber-400' : ''}>tasks</span>
        <span className="text-zinc-600">/</span>
        <span className={view === 'dashboard' ? 'text-amber-400' : ''}>dash</span>
        <span className="text-zinc-600">/</span>
        <span className={view === 'logs' ? 'text-amber-400' : ''}>logs</span>
      </button>

      <span className="text-zinc-700">|</span>

      {/* Search */}
      <div className="flex-1 max-w-sm">
        {searchOpen ? (
          <div className="relative">
            <span className="absolute left-2 top-1/2 -translate-y-1/2 text-zinc-500 font-mono text-xs">/</span>
            <Input
              ref={searchInputRef as React.RefObject<HTMLInputElement>}
              value={searchTerm}
              onChange={e => onSearchChange(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Escape') {
                  onSearchChange('')
                  onSearchClose()
                }
                if (e.key === 'Enter') {
                  onSearchClose()
                }
              }}
              className="h-7 border-zinc-800 bg-zinc-900 text-zinc-100 text-xs font-mono pl-6 focus-visible:ring-amber-500/50"
              placeholder="search..."
            />
          </div>
        ) : (
          <button
            onClick={() => searchInputRef.current?.focus()}
            className="flex items-center gap-1.5 text-xs font-mono text-zinc-600 hover:text-zinc-400 transition-colors"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8" />
              <path d="m21 21-4.3-4.3" />
            </svg>
            / search
          </button>
        )}
      </div>

      <span className="text-zinc-700">|</span>

      {/* Priority filter */}
      <div className="flex gap-1">
        {(['all', 'high', 'medium', 'low'] as const).map(p => (
          <button
            key={p}
            onClick={() => onPriorityChange(p)}
            className={`px-1.5 py-0.5 rounded text-xs font-mono transition-colors ${
              priorityFilter === p
                ? 'bg-zinc-800 text-zinc-200'
                : 'text-zinc-600 hover:text-zinc-400'
            }`}
          >
            {prioLabels[p]}
          </button>
        ))}
      </div>
    </div>
  )
}
