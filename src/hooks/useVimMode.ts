import { useState, useCallback, useEffect, useRef } from 'react'
import type { VimMode } from '../types'

interface UseVimModeOptions {
  itemCount: number
  onAdd: () => void
  onEdit: (index: number) => void
  onDelete: (index: number) => void
  onToggle: (index: number) => void
  onSearch: () => void
  enabled: boolean
}

export function useVimMode({
  itemCount,
  onAdd,
  onEdit,
  onDelete,
  onToggle,
  onSearch,
  enabled,
}: UseVimModeOptions) {
  const [mode, setMode] = useState<VimMode>('NORMAL')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const searchInputRef = useRef<HTMLInputElement>(null)

  // Reset selected index when filtered list changes
  useEffect(() => {
    setSelectedIndex(prev => Math.min(prev, Math.max(0, itemCount - 1)))
  }, [itemCount])

  const goToNormal = useCallback(() => setMode('NORMAL'), [])
  const goToInsert = useCallback(() => setMode('INSERT'), [])
  const goToSearch = useCallback(() => {
    setMode('SEARCH')
    setTimeout(() => searchInputRef.current?.focus(), 50)
  }, [])

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (!enabled) return

    // Global: Escape always goes to NORMAL or cancels
    if (e.key === 'Escape') {
      e.preventDefault()
      if (mode === 'SEARCH') {
        setMode('NORMAL')
      } else if (mode === 'INSERT') {
        // Let the form handle its own escape
        return
      } else {
        setMode('NORMAL')
      }
      return
    }

    if (mode === 'NORMAL') {
      switch (e.key) {
        case 'j':
          e.preventDefault()
          setSelectedIndex(prev => Math.min(prev + 1, itemCount - 1))
          break
        case 'k':
          e.preventDefault()
          setSelectedIndex(prev => Math.max(prev - 1, 0))
          break
        case 'J':
          e.preventDefault()
          setSelectedIndex(Math.max(0, itemCount - 1))
          break
        case 'K':
          e.preventDefault()
          setSelectedIndex(0)
          break
        case 'a':
          e.preventDefault()
          onAdd()
          break
        case 'e':
          e.preventDefault()
          if (itemCount > 0 && selectedIndex < itemCount) {
            onEdit(selectedIndex)
          }
          break
        case 'd':
          e.preventDefault()
          if (itemCount > 0 && selectedIndex < itemCount) {
            onDelete(selectedIndex)
          }
          break
        case 'Enter':
        case ' ':
          e.preventDefault()
          if (itemCount > 0 && selectedIndex < itemCount) {
            onToggle(selectedIndex)
          }
          break
        case '/':
          e.preventDefault()
          onSearch()
          break
        case 'n':
          e.preventDefault()
          // Just a placeholder - could cycle filters
          break
        case '?':
          e.preventDefault()
          // Help modal would be triggered at App level
          break
      }
    }
  }, [mode, selectedIndex, itemCount, enabled, onAdd, onEdit, onDelete, onToggle, onSearch])

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])

  return {
    mode,
    setMode,
    selectedIndex,
    setSelectedIndex,
    goToNormal,
    goToInsert,
    goToSearch,
    searchInputRef,
  }
}
