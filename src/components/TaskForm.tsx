import { useState, useEffect, useRef } from 'react'
import type { Task, Priority, TaskStatus } from '../types'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Label } from '@/components/ui/label'

interface TaskFormProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSave: (data: Omit<Task, 'id' | 'createdAt' | 'updatedAt'>) => void
  editTask?: Task | null
}

const emptyForm: Omit<Task, 'id' | 'createdAt' | 'updatedAt'> = {
  title: '',
  description: '',
  priority: 'medium',
  status: 'todo',
  group: '',
  value: null,
}

export function TaskForm({ open, onOpenChange, onSave, editTask }: TaskFormProps) {
  const [form, setForm] = useState(emptyForm)
  const titleRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (open) {
      if (editTask) {
        setForm({
          title: editTask.title,
          description: editTask.description,
          priority: editTask.priority,
          status: editTask.status,
          group: editTask.group,
          value: editTask.value,
        })
      } else {
        setForm(emptyForm)
      }
      setTimeout(() => titleRef.current?.focus(), 100)
    }
  }, [open, editTask])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.title.trim()) return
    onSave(form)
    setForm(emptyForm)
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg border-zinc-800 bg-zinc-950">
        <DialogHeader>
          <DialogTitle className="text-zinc-100 font-mono text-base">
            {editTask ? ':edit' : ':new'} task
          </DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="title" className="text-zinc-400 text-xs font-mono">title</Label>
            <Input
              ref={titleRef}
              id="title"
              value={form.title}
              onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
              className="border-zinc-800 bg-zinc-900 text-zinc-100 focus-visible:ring-amber-500/50"
              placeholder="Task title"
              autoFocus
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="desc" className="text-zinc-400 text-xs font-mono">description</Label>
            <Textarea
              id="desc"
              value={form.description}
              onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              className="border-zinc-800 bg-zinc-900 text-zinc-100 focus-visible:ring-amber-500/50 min-h-[60px]"
              placeholder="Optional description"
            />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div className="space-y-2">
              <Label htmlFor="prio" className="text-zinc-400 text-xs font-mono">priority</Label>
              <Select
                value={form.priority}
                onValueChange={(v: Priority) => setForm(f => ({ ...f, priority: v }))}
              >
                <SelectTrigger className="border-zinc-800 bg-zinc-900 text-zinc-100">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="border-zinc-800 bg-zinc-900">
                  <SelectItem value="high" className="text-zinc-100">🔴 High</SelectItem>
                  <SelectItem value="medium" className="text-zinc-100">🟡 Medium</SelectItem>
                  <SelectItem value="low" className="text-zinc-100">🟢 Low</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="status" className="text-zinc-400 text-xs font-mono">status</Label>
              <Select
                value={form.status}
                onValueChange={(v: TaskStatus) => setForm(f => ({ ...f, status: v }))}
              >
                <SelectTrigger className="border-zinc-800 bg-zinc-900 text-zinc-100">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="border-zinc-800 bg-zinc-900">
                  <SelectItem value="todo" className="text-zinc-100">○ todo</SelectItem>
                  <SelectItem value="in_progress" className="text-zinc-100">◔ doing</SelectItem>
                  <SelectItem value="done" className="text-zinc-100">● done</SelectItem>
                  <SelectItem value="paused" className="text-zinc-100">⊘ hold</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="group" className="text-zinc-400 text-xs font-mono">group</Label>
              <Input
                id="group"
                value={form.group}
                onChange={e => setForm(f => ({ ...f, group: e.target.value }))}
                className="border-zinc-800 bg-zinc-900 text-zinc-100 focus-visible:ring-amber-500/50"
                placeholder="e.g. infra"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="value" className="text-zinc-400 text-xs font-mono">est. value ($)</Label>
              <Input
                id="value"
                type="number"
                value={form.value ?? ''}
                onChange={e => setForm(f => ({ ...f, value: e.target.value ? parseInt(e.target.value) : null }))}
                className="border-zinc-800 bg-zinc-900 text-zinc-100 focus-visible:ring-amber-500/50"
                placeholder="e.g. 500"
              />
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="ghost"
              onClick={() => onOpenChange(false)}
              className="text-zinc-400 hover:text-zinc-200 font-mono text-xs"
            >
              Esc
            </Button>
            <Button
              type="submit"
              className="bg-amber-600 hover:bg-amber-500 text-black font-mono text-xs"
            >
              :wq
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
