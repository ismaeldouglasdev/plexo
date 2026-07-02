import { useState, useCallback } from 'react'
import { useTasks } from './hooks/useTasks'
import { useLogger } from './hooks/useLogger'
import { useVimMode } from './hooks/useVimMode'
import { TaskList } from './components/TaskList'
import { TaskForm } from './components/TaskForm'
import { Dashboard } from './components/Dashboard'
import { ActivityLog } from './components/ActivityLog'
import { FilterBar } from './components/FilterBar'
import { StatusBar } from './components/StatusBar'
import { HelpModal } from './components/HelpModal'
import type { Task } from './types'

type View = 'tasks' | 'dashboard' | 'logs'

function App() {
  const { log, logs, clearLogs } = useLogger()

  const {
    tasks,
    filteredTasks,
    searchTerm,
    setSearchTerm,
    priorityFilter,
    setPriorityFilter,
    addTask,
    updateTask,
    deleteTask,
    toggleStatus,
    counts,
  } = useTasks(log)

  const [view, setView] = useState<View>('tasks')
  const [formOpen, setFormOpen] = useState(false)
  const [editTask, setEditTask] = useState<Task | null>(null)
  const [helpOpen, setHelpOpen] = useState(false)
  const [searchOpen, setSearchOpen] = useState(false)
  const [isMobileOpen, setIsMobileOpen] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<number | null>(null)

  const handleAdd = useCallback(() => {
    setEditTask(null)
    setFormOpen(true)
    log('info', 'VIEW_CHANGED', 'Opened task creation form')
  }, [log])

  const handleEdit = useCallback((index: number) => {
    const task = filteredTasks[index]
    if (task) {
      setEditTask(task)
      setFormOpen(true)
      log('info', 'VIEW_CHANGED', `Opened edit form for "${task.title}"`)
    }
  }, [filteredTasks, log])

  const handleDelete = useCallback((index: number) => {
    setShowDeleteConfirm(index)
  }, [])

  const confirmDelete = useCallback(() => {
    if (showDeleteConfirm !== null && filteredTasks[showDeleteConfirm]) {
      deleteTask(filteredTasks[showDeleteConfirm].id)
      setShowDeleteConfirm(null)
    }
  }, [showDeleteConfirm, filteredTasks, deleteTask])

  const handleToggle = useCallback((index: number) => {
    const task = filteredTasks[index]
    if (task) toggleStatus(task.id)
  }, [filteredTasks, toggleStatus])

  const handleSave = useCallback((data: Omit<Task, 'id' | 'createdAt' | 'updatedAt'>) => {
    if (editTask) updateTask(editTask.id, data)
    else addTask(data)
  }, [editTask, updateTask, addTask])

  const handleSearch = useCallback(() => {
    setSearchOpen(true)
  }, [])

  const vim = useVimMode({
    itemCount: filteredTasks.length,
    onAdd: handleAdd,
    onEdit: handleEdit,
    onDelete: handleDelete,
    onToggle: handleToggle,
    onSearch: handleSearch,
    enabled: view === 'tasks',
  })

  const cycleView = useCallback(() => {
    setView(v => {
      const next: View = v === 'tasks' ? 'dashboard' : v === 'dashboard' ? 'logs' : 'tasks'
      log('info', 'VIEW_CHANGED', `Switched to ${next} view`)
      return next
    })
  }, [log])

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 pb-8">
      {/* Delete confirmation */}
      {showDeleteConfirm !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-5 shadow-xl max-w-sm mx-4">
            <p className="text-sm font-mono text-zinc-200 mb-1">Delete task?</p>
            <p className="text-xs text-zinc-500 font-mono mb-4 line-clamp-1">
              {filteredTasks[showDeleteConfirm]?.title}
            </p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setShowDeleteConfirm(null)}
                className="px-3 py-1.5 text-xs font-mono text-zinc-400 hover:text-zinc-200 transition-colors"
              >Esc</button>
              <button onClick={confirmDelete}
                className="px-3 py-1.5 text-xs font-mono bg-red-600 hover:bg-red-500 text-white rounded transition-colors"
              >:wq!</button>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <header className="border-b border-zinc-800">
        <div className="mx-auto max-w-4xl">
          <div className="flex items-center gap-3 px-3 py-3">
            <div className="flex items-center gap-2">
              <span className="text-amber-500 font-mono text-lg font-bold">~</span>
              <h1 className="text-sm font-mono font-semibold text-zinc-100 tracking-tight">
                plexo
              </h1>
            </div>
            <span className="text-zinc-700 text-[10px] font-mono hidden sm:inline">
              # opentasks · {counts.total} tasks
            </span>
            {view === 'logs' && (
              <span className="text-[10px] font-mono text-sky-400">viewing logs</span>
            )}
          </div>
          <FilterBar
            searchTerm={searchTerm}
            onSearchChange={setSearchTerm}
            priorityFilter={priorityFilter}
            onPriorityChange={setPriorityFilter}
            onToggleView={cycleView}
            view={view}
            searchOpen={searchOpen}
            searchInputRef={vim.searchInputRef}
            onSearchClose={() => { setSearchOpen(false); vim.goToNormal() }}
            isMobileOpen={isMobileOpen}
            onMobileToggle={() => setIsMobileOpen(o => !o)}
          />
        </div>
      </header>

      {/* Main */}
      <main className="mx-auto max-w-4xl">
        {view === 'tasks' && (
          <TaskList
            tasks={filteredTasks}
            selectedIndex={vim.selectedIndex}
            onToggle={handleToggle}
            onEdit={handleEdit}
            onDelete={handleDelete}
          />
        )}
        {view === 'dashboard' && (
          <Dashboard tasks={tasks} logs={logs} onClearLogs={clearLogs} />
        )}
        {view === 'logs' && (
          <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 overflow-hidden mt-4 mx-4">
            <ActivityLog logs={logs} onClear={clearLogs} />
          </div>
        )}
      </main>

      {/* Task Form */}
      <TaskForm
        open={formOpen}
        onOpenChange={o => { setFormOpen(o); if (!o) vim.goToNormal() }}
        onSave={handleSave}
        editTask={editTask}
      />

      {/* Help */}
      <HelpModal open={helpOpen} onOpenChange={setHelpOpen} />

      {/* Status Bar */}
      <StatusBar
        mode={vim.mode}
        taskCount={counts.total}
        filteredCount={filteredTasks.length}
        selectedIndex={vim.selectedIndex}
        priorityFilter={priorityFilter}
        onResetFilter={() => { setPriorityFilter('all'); setSearchTerm('') }}
      />

      {/* Mobile FAB */}
      {view === 'tasks' && (
        <button onClick={handleAdd}
          className="fixed bottom-12 right-4 z-40 flex h-10 w-10 items-center justify-center rounded-full bg-amber-600 text-black shadow-lg md:hidden hover:bg-amber-500 transition-colors"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M12 5v14M5 12h14" />
          </svg>
        </button>
      )}
    </div>
  )
}

export default App
