import { useState, useCallback, useEffect, useRef } from 'react'
import type { Task, Priority, TaskStatus } from '../types'
import { seedTasks } from '../data/seed'
import type { LogAction } from './useLogger'

const STORAGE_KEY = 'plexo-tasks'
const API_BASE = '/api'

interface LogFn {
  (level: 'info' | 'success' | 'warn' | 'error', action: LogAction, message: string, extras?: { details?: Record<string, unknown>; taskId?: string; taskTitle?: string }): void
}

async function apiGetTasks(): Promise<Task[] | null> {
  try {
    const res = await fetch(`${API_BASE}/tasks`)
    if (!res.ok) return null
    const data = await res.json()
    return data.tasks ?? null
  } catch {
    return null
  }
}

function loadTasks(): Task[] {
  const raw = localStorage.getItem(STORAGE_KEY)
  if (raw) {
    try {
      const parsed = JSON.parse(raw)
      if (Array.isArray(parsed) && parsed.length > 0) return parsed
    } catch { /* ignore */ }
  }
  return seedTasks
}

export function useTasks(log?: LogFn) {
  const [tasks, setTasks] = useState<Task[]>(() => {
    const fromStorage = localStorage.getItem(STORAGE_KEY)
    const hasStorage = fromStorage && JSON.parse(fromStorage).length > 0
    if (log) {
      log('info', 'APP_INIT', hasStorage ? 'Loaded tasks from storage' : 'Using seed data', {
        details: { source: hasStorage ? 'localStorage' : 'seed' }
      })
    }
    return loadTasks()
  })
  const [searchTerm, setSearchTerm] = useState('')
  const [priorityFilter, setPriorityFilter] = useState<Priority | 'all'>('all')
  const saveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const lastSavedTasks = useRef('')

  useEffect(() => {
    function poll() {
      apiGetTasks().then(apiTasks => {
        if (!apiTasks || apiTasks.length === 0) return
        setTasks(apiTasks)
        try { localStorage.setItem(STORAGE_KEY, JSON.stringify(apiTasks)) } catch {}
      })
    }
    poll()
    const id = setInterval(poll, 10_000)
    return () => clearInterval(id)
  }, [])
  useEffect(() => {
    const serialized = JSON.stringify(tasks)
    if (serialized === lastSavedTasks.current) return
    if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current)
    saveTimeoutRef.current = setTimeout(() => {
      try {
        localStorage.setItem(STORAGE_KEY, serialized)
        lastSavedTasks.current = serialized
      } catch (e) {
        console.error('[plexo] Failed to save tasks:', e)
        if (log) {
          log('error', 'STORAGE_WARNING', 'Failed to persist tasks to localStorage', {
            details: { error: String(e), taskCount: tasks.length }
          })
        }
      }
    }, 300)
    return () => {
      if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current)
    }
  }, [tasks, log])

  const addTask = useCallback((data: Omit<Task, 'id' | 'createdAt' | 'updatedAt'>) => {
    const now = new Date().toISOString()
    const newTask: Task = {
      ...data,
      id: Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 6),
      createdAt: now,
      updatedAt: now,
    }
    setTasks(prev => {
      if (log) {
        log('success', 'TASK_CREATED', `Created "${data.title}"`, {
          taskId: newTask.id,
          taskTitle: data.title,
          details: { priority: data.priority, status: data.status, group: data.group }
        })
      }
      return [...prev, newTask]
    })
    return newTask
  }, [log])

  const updateTask = useCallback((id: string, updates: Partial<Omit<Task, 'id' | 'createdAt'>>) => {
    setTasks(prev => {
      const task = prev.find(t => t.id === id)
      if (!task) return prev
      if (log) {
        const changedFields = Object.keys(updates).filter(k => (updates as any)[k] !== (task as any)[k])
        log('info', 'TASK_UPDATED', `Updated "${task.title}"`, {
          taskId: id,
          taskTitle: task.title,
          details: { changes: changedFields, before: { title: task.title, priority: task.priority, status: task.status }, after: updates }
        })
      }
      return prev.map(t => t.id === id ? { ...t, ...updates, updatedAt: new Date().toISOString() } : t)
    })
  }, [log])

  const deleteTask = useCallback((id: string) => {
    setTasks(prev => {
      const task = prev.find(t => t.id === id)
      if (!task) return prev
      if (log) {
        log('success', 'TASK_DELETED', `Deleted "${task.title}"`, {
          taskId: id,
          taskTitle: task.title,
          details: { priority: task.priority, status: task.status, group: task.group }
        })
      }
      return prev.filter(t => t.id !== id)
    })
  }, [log])

  const toggleStatus = useCallback((id: string) => {
    setTasks(prev => prev.map(t => {
      if (t.id !== id) return t
      const statusCycle: TaskStatus[] = ['todo', 'in_progress', 'done', 'paused']
      const currentIdx = statusCycle.indexOf(t.status)
      const nextStatus = statusCycle[(currentIdx + 1) % statusCycle.length]
      if (log) {
        log('info', 'TASK_STATUS_CHANGED', `"${t.title}": ${t.status} → ${nextStatus}`, {
          taskId: id,
          taskTitle: t.title,
          details: { from: t.status, to: nextStatus }
        })
      }
      return { ...t, status: nextStatus, updatedAt: new Date().toISOString() }
    }))
  }, [log])

  const setSearchLogged = useCallback((term: string) => {
    setSearchTerm(prev => {
      if (prev !== term && log) {
        log('info', 'FILTER_CHANGED', term ? `Search: "${term}"` : 'Search cleared', {
          details: { searchTerm: term, filter: priorityFilter }
        })
      }
      return term
    })
  }, [log, priorityFilter])

  const setPriorityLogged = useCallback((p: Priority | 'all') => {
    setPriorityFilter(prev => {
      if (prev !== p && log) {
        log('info', 'FILTER_CHANGED', `Priority filter: ${p}`, {
          details: { from: prev, to: p, searchTerm }
        })
      }
      return p
    })
  }, [log, searchTerm])

  const filteredTasks = tasks.filter(t => {
    if (priorityFilter !== 'all' && t.priority !== priorityFilter) return false
    if (searchTerm) {
      const q = searchTerm.toLowerCase()
      if (!t.title.toLowerCase().includes(q) &&
          !t.description.toLowerCase().includes(q) &&
          !t.group.toLowerCase().includes(q)) {
        return false
      }
    }
    return true
  })

  const counts = {
    total: tasks.length,
    todo: tasks.filter(t => t.status === 'todo').length,
    in_progress: tasks.filter(t => t.status === 'in_progress').length,
    done: tasks.filter(t => t.status === 'done').length,
    paused: tasks.filter(t => t.status === 'paused').length,
    high: tasks.filter(t => t.priority === 'high').length,
    medium: tasks.filter(t => t.priority === 'medium').length,
    low: tasks.filter(t => t.priority === 'low').length,
  }

  return {
    tasks, filteredTasks, searchTerm, setSearchTerm: setSearchLogged,
    priorityFilter, setPriorityFilter: setPriorityLogged,
    addTask, updateTask, deleteTask, toggleStatus, counts,
  }
}
