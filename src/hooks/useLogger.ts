import { useState, useCallback, useEffect, useRef } from 'react'

export type LogLevel = 'info' | 'success' | 'warn' | 'error'
export type LogAction =
  | 'TASK_CREATED'
  | 'TASK_UPDATED'
  | 'TASK_DELETED'
  | 'TASK_STATUS_CHANGED'
  | 'TASK_TOGGLED'
  | 'SYSTEM_ERROR'
  | 'STORAGE_WARNING'
  | 'VIEW_CHANGED'
  | 'FILTER_CHANGED'
  | 'APP_INIT'

export interface LogEntry {
  id: string
  timestamp: string
  level: LogLevel
  action: LogAction
  message: string
  details?: Record<string, unknown>
  taskId?: string
  taskTitle?: string
}

const MAX_LOG_ENTRIES = 500
const STORAGE_KEY = 'plexo-logs'
const API_BASE = '/api'

// In-memory buffer for high-frequency writes
let writeBuffer: LogEntry[] = []
let flushTimer: ReturnType<typeof setTimeout> | null = null

function loadLogs(): LogEntry[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const parsed = JSON.parse(raw)
      if (Array.isArray(parsed)) return parsed.slice(0, MAX_LOG_ENTRIES)
    }
  } catch (e) {
    console.warn('[plexo] Failed to load logs from localStorage:', e)
  }
  return []
}

async function apiAddLog(entry: LogEntry): Promise<void> {
  try {
    await fetch(`${API_BASE}/logs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(entry),
    })
  } catch {
    // silent — API unavailable is fine
  }
}

function flushToStorage() {
  if (writeBuffer.length === 0) return
  try {
    const existing = loadLogs()
    const merged = [...writeBuffer, ...existing].slice(0, MAX_LOG_ENTRIES)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(merged))
    writeBuffer = []
  } catch (e) {
    console.warn('[plexo] Failed to persist logs:', e)
  }
}

function scheduleFlush() {
  if (flushTimer) clearTimeout(flushTimer)
  flushTimer = setTimeout(flushToStorage, 2000)
}

let globalLogCallback: ((entry: LogEntry) => void) | null = null

export function setGlobalLogCallback(cb: (entry: LogEntry) => void) {
  globalLogCallback = cb
}

export function useLogger() {
  const [logs, setLogs] = useState<LogEntry[]>(loadLogs)
  const logsRef = useRef(logs)
  logsRef.current = logs

  // Periodic sync from storage (for multi-tab)
  useEffect(() => {
    const interval = setInterval(() => {
      const fresh = loadLogs()
      if (fresh.length !== logsRef.current.length) {
        setLogs(fresh)
      }
    }, 5000)
    return () => clearInterval(interval)
  }, [])

  const log = useCallback((
    level: LogLevel,
    action: LogAction,
    message: string,
    extras?: { details?: Record<string, unknown>; taskId?: string; taskTitle?: string },
  ) => {
    const entry: LogEntry = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
      timestamp: new Date().toISOString(),
      level,
      action,
      message,
      details: extras?.details,
      taskId: extras?.taskId,
      taskTitle: extras?.taskTitle,
    }

    // Browser console logging with colors
    const consoleFn = level === 'error' ? 'error' : level === 'warn' ? 'warn' : 'log'
    const prefix = `[plexo:${action}]`
    const style = level === 'error'
      ? 'color:#ef4444;font-weight:bold'
      : level === 'warn'
      ? 'color:#f59e0b;font-weight:bold'
      : level === 'success'
      ? 'color:#10b981;font-weight:bold'
      : 'color:#a1a1aa;font-weight:bold'

    console[consoleFn](`%c${prefix}`, style, message, extras?.details ?? '')

    // Add to buffer and update state
    writeBuffer.push(entry)

    // Trim buffer if too large
    if (writeBuffer.length > 100) {
      flushToStorage()
    } else {
      scheduleFlush()
    }

    setLogs(prev => [entry, ...prev].slice(0, MAX_LOG_ENTRIES))

    // Notify global listener (for toast notifications)
    if (globalLogCallback) {
      globalLogCallback(entry)
    }

    // Sync to API (fire-and-forget)
    apiAddLog(entry)
  }, [])

  const clearLogs = useCallback(() => {
    try {
      localStorage.removeItem(STORAGE_KEY)
      writeBuffer = []
      setLogs([])
      log('info', 'APP_INIT', 'Logs cleared manually')
    } catch (e) {
      console.warn('[plexo] Failed to clear logs:', e)
    }
  }, [log])

  const getLogsByAction = useCallback((action: LogAction) => {
    return logsRef.current.filter(l => l.action === action)
  }, [])

  const getLogsByLevel = useCallback((level: LogLevel) => {
    return logsRef.current.filter(l => l.level === level)
  }, [])

  const getErrors = useCallback(() => {
    return logsRef.current.filter(l => l.level === 'error' || l.level === 'warn')
  }, [])

  return {
    logs,
    log,
    clearLogs,
    getLogsByAction,
    getLogsByLevel,
    getErrors,
  }
}

// Cleanup on page unload
window.addEventListener('beforeunload', flushToStorage)
