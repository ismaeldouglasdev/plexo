export type Priority = 'high' | 'medium' | 'low'
export type TaskStatus = 'todo' | 'in_progress' | 'done' | 'paused'

export type VimMode = 'NORMAL' | 'INSERT' | 'SEARCH'

export interface Task {
  id: string
  title: string
  description: string
  priority: Priority
  status: TaskStatus
  group: string
  value: number | null
  createdAt: string
  updatedAt: string
}

export interface GroupCount {
  group: string
  count: number
  priority: Priority
}
