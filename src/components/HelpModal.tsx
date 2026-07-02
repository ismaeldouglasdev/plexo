import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

interface HelpModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

const keys = [
  { key: 'j / k', desc: 'Navigate up / down' },
  { key: 'J / K', desc: 'First / last task' },
  { key: 'Enter', desc: 'Toggle task status' },
  { key: 'Space', desc: 'Toggle task status' },
  { key: 'a', desc: 'Add new task' },
  { key: 'e', desc: 'Edit selected task' },
  { key: 'd', desc: 'Delete selected task' },
  { key: '/', desc: 'Search / filter' },
  { key: 'Esc', desc: 'Cancel / back to NORMAL' },
  { key: 'Tab', desc: 'Switch Tasks / Dashboard' },
]

export function HelpModal({ open, onOpenChange }: HelpModalProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md border-zinc-800 bg-zinc-950">
        <DialogHeader>
          <DialogTitle className="text-zinc-100 font-mono text-base">keybindings</DialogTitle>
        </DialogHeader>
        <div className="space-y-1">
          {keys.map(k => (
            <div key={k.key} className="flex items-center gap-4 py-1.5">
              <kbd className="min-w-[80px] rounded border border-zinc-800 bg-zinc-900 px-2 py-0.5 text-xs font-mono text-amber-400 text-center">
                {k.key}
              </kbd>
              <span className="text-xs text-zinc-400">{k.desc}</span>
            </div>
          ))}
        </div>
        <div className="mt-4 border-t border-zinc-800 pt-3 text-[10px] text-zinc-600 font-mono">
          <span className="text-amber-500/70">NORMAL</span> mode is default.{' '}
          Press <kbd className="rounded border border-zinc-800 bg-zinc-900 px-1 text-[10px] text-zinc-400">Esc</kbd> to return.
        </div>
      </DialogContent>
    </Dialog>
  )
}
