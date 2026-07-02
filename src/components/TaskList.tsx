import type { Task } from '../types'
import { TaskCard } from './TaskCard'

interface TaskListProps {
  tasks: Task[]
  selectedIndex: number
  onToggle: (index: number) => void
  onEdit: (index: number) => void
  onDelete: (index: number) => void
}

export function TaskList({ tasks, selectedIndex, onToggle, onEdit, onDelete }: TaskListProps) {
  if (tasks.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <span className="text-4xl text-zinc-700 mb-3">~</span>
        <p className="text-sm text-zinc-600 font-mono">no tasks found</p>
        <p className="text-xs text-zinc-700 font-mono mt-1">press <kbd className="rounded border border-zinc-800 bg-zinc-900 px-1 text-zinc-500">a</kbd> to add one</p>
      </div>
    )
  }

  return (
    <div className="divide-y divide-zinc-800/50">
      {tasks.map((task, i) => (
        <TaskCard
          key={task.id}
          task={task}
          isSelected={i === selectedIndex}
          onToggle={() => onToggle(i)}
          onEdit={() => onEdit(i)}
          onDelete={() => onDelete(i)}
        />
      ))}
    </div>
  )
}
