"""
Data layer: JSON persistence, activity log, seed data.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

DATA_DIR = Path.home() / ".plexo"
TASKS_FILE = DATA_DIR / "tasks.json"
LOGS_FILE = DATA_DIR / "logs.json"

# ─── Data types ──────────────────────────────────────────────────────────────

@dataclass
class Task:
    id: str
    title: str
    description: str
    priority: str  # high | medium | low
    status: str    # todo | in_progress | done | paused
    group: str
    value: Optional[int] = None  # estimated revenue in USD
    created_at: str = ""
    updated_at: str = ""

@dataclass
class LogEntry:
    id: str
    timestamp: str
    level: str       # info | success | warn | error
    action: str      # TASK_CREATED | TASK_UPDATED | TASK_DELETED | TASK_STATUS_CHANGED | FILTER_CHANGED | VIEW_CHANGED | APP_INIT | SYSTEM_ERROR
    message: str
    task_id: Optional[str] = None
    task_title: Optional[str] = None
    details: Optional[dict] = None

# ─── Seed data ────────────────────────────────────────────────────────────────

SEED_TASKS = [
    {"id": "1", "title": "Finalizar anime-dl-br (source animesdigital.org)", "description": "Implementar source animesdigital.org, testar --embed-subs, --all e --max, e download real.", "priority": "high", "status": "todo", "group": "anime-dl-br", "value": 150, "created_at": "2026-06-01T00:00:00Z", "updated_at": "2026-06-21T00:00:00Z"},
    {"id": "2", "title": "Site da Loja Online + Inventory Service", "description": "Tirar fotos, deploy real, normalizar categorias OSPOS, configurar WooCommerce, logotipo, autenticar ML OAuth.", "priority": "high", "status": "todo", "group": "loja", "value": 3000, "created_at": "2026-05-29T00:00:00Z", "updated_at": "2026-06-21T00:00:00Z"},
    {"id": "3", "title": "Cronograma de Estudos (Bugs Críticos)", "description": "Corrigir XSS em areaNome, area_id não validado, XP duplicado, race conditions. Migrar PostgreSQL, tests.", "priority": "high", "status": "todo", "group": "cronograma", "value": None, "created_at": "2026-05-15T00:00:00Z", "updated_at": "2026-06-21T00:00:00Z"},
    {"id": "4", "title": "Portfolio Upgrade (Análise ChatGPT)", "description": "Aumentar stats Hero, resolver experiência, reordenar projetos, aumentar preços.", "priority": "high", "status": "todo", "group": "portfolio", "value": 2000, "created_at": "2026-05-10T00:00:00Z", "updated_at": "2026-06-21T00:00:00Z"},
    {"id": "5", "title": "Lead Acquisition Pipeline (Stack $0)", "description": "Setup infra, módulos core, orquestração, produção cron 3x/dia.", "priority": "high", "status": "todo", "group": "leads", "value": 5000, "created_at": "2026-06-21T00:00:00Z", "updated_at": "2026-06-21T00:00:00Z"},
    {"id": "6", "title": "Sincronização Música (Musicolet → MPD)", "description": "Backup Musicolet, testar extract script, configurar MacroDroid automático.", "priority": "medium", "status": "paused", "group": "musica", "value": None, "created_at": "2026-05-20T00:00:00Z", "updated_at": "2026-06-21T00:00:00Z"},
    {"id": "7", "title": "Testar 9router (substitui Agent Daemon)", "description": "Pesquisar, instalar/configurar, testar integração com agentes.", "priority": "medium", "status": "todo", "group": "infra", "value": 300, "created_at": "2026-06-21T00:00:00Z", "updated_at": "2026-06-21T00:00:00Z"},
    {"id": "8", "title": "Plano Estudos: Cloud & Infraestrutura", "description": "Azure, AWS, Terraform, Serverless, Containers, Projeto Final.", "priority": "medium", "status": "todo", "group": "cloud", "value": None, "created_at": "2026-06-21T00:00:00Z", "updated_at": "2026-06-21T00:00:00Z"},
    {"id": "9", "title": "P.U.L.S.O. MVP (Pausado)", "description": "Cliente não decidiu ainda. Se voltar: domínio, remover Brave, expansão.", "priority": "low", "status": "paused", "group": "pulso", "value": 5000, "created_at": "2026-04-10T00:00:00Z", "updated_at": "2026-06-21T00:00:00Z"},
]

STATUS_CYCLE = {"todo": "in_progress", "in_progress": "done", "done": "paused", "paused": "todo"}
PRIO_COLORS = {"high": "red", "medium": "yellow", "low": "green"}
STATUS_ICONS = {"todo": "○", "in_progress": "◔", "done": "●", "paused": "⊘"}

# ─── Storage ──────────────────────────────────────────────────────────────────

class TaskStore:
    def __init__(self, log_callback=None):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.log_callback = log_callback
        self.tasks = self._load()
        self.logs = self._load_logs()
        self._write_log("info", "APP_INIT", f"Store initialized with {len(self.tasks)} tasks")

    def _load(self) -> list[Task]:
        if TASKS_FILE.exists():
            try:
                raw = json.loads(TASKS_FILE.read_text())
                return [Task(**{k: v for k, v in t.items() if k in Task.__dataclass_fields__}) for t in raw]
            except (json.JSONDecodeError, KeyError) as e:
                self._write_log("error", "SYSTEM_ERROR", f"Corrupted tasks.json: {e}")
        return [Task(**t) for t in SEED_TASKS]

    def _save(self):
        TASKS_FILE.write_text(json.dumps([asdict(t) for t in self.tasks], indent=2))

    def _load_logs(self) -> list[LogEntry]:
        if LOGS_FILE.exists():
            try:
                raw = json.loads(LOGS_FILE.read_text())
                return [LogEntry(**l) for l in raw][:500]
            except (json.JSONDecodeError, KeyError):
                pass
        return []

    def _save_logs(self):
        LOGS_FILE.write_text(json.dumps([asdict(l) for l in self.logs[:500]], indent=2))

    def _write_log(self, level: str, action: str, message: str, **extras):
        entry = LogEntry(
            id=f"{int(time.time()*1000)}-{os.urandom(2).hex()}",
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            level=level, action=action, message=message,
            task_id=extras.pop("task_id", None),
            task_title=extras.pop("task_title", None),
            details=extras if extras else None,
        )
        self.logs.insert(0, entry)
        if len(self.logs) > 500:
            self.logs = self.logs[:500]
        self._save_logs()
        if self.log_callback:
            self.log_callback(entry)

    # ── CRUD ──

    def add_task(self, title: str, description: str = "", priority: str = "medium",
                 status: str = "todo", group: str = "", value: Optional[int] = None) -> Task:
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        task = Task(
            id=f"{int(time.time())}-{os.urandom(3).hex()}",
            title=title, description=description,
            priority=priority, status=status, group=group,
            value=value, created_at=now, updated_at=now,
        )
        self.tasks.append(task)
        self._save()
        self._write_log("success", "TASK_CREATED", f'Created "{title}"',
                        task_id=task.id, task_title=title,
                        priority=priority, status=status, group=group)
        return task

    def update_task(self, task_id: str, **updates):
        for t in self.tasks:
            if t.id == task_id:
                before = {k: getattr(t, k) for k in updates}
                for k, v in updates.items():
                    setattr(t, k, v)
                t.updated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                self._save()
                changed = [k for k in updates if before.get(k) != updates[k]]
                self._write_log("info", "TASK_UPDATED", f'Updated "{t.title}"',
                                task_id=task_id, task_title=t.title,
                                changes=changed, before=before, after=updates)
                return t
        return None

    def delete_task(self, task_id: str):
        for i, t in enumerate(self.tasks):
            if t.id == task_id:
                removed = self.tasks.pop(i)
                self._save()
                self._write_log("success", "TASK_DELETED", f'Deleted "{removed.title}"',
                                task_id=task_id, task_title=removed.title,
                                priority=removed.priority, status=removed.status)
                return removed
        return None

    def toggle_status(self, task_id: str):
        for t in self.tasks:
            if t.id == task_id:
                old = t.status
                t.status = STATUS_CYCLE.get(t.status, "todo")
                t.updated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                self._save()
                self._write_log("info", "TASK_STATUS_CHANGED",
                                f'"{t.title}": {old} → {t.status}',
                                task_id=task_id, task_title=t.title,
                                from_status=old, to_status=t.status)
                return t
        return None

    def get_task_by_index(self, index: int) -> Task | None:
        if 0 <= index < len(self.tasks):
            return self.tasks[index]
        return None

    # ── Stats ──

    @property
    def counts(self) -> dict:
        return {
            "total": len(self.tasks),
            "todo": sum(1 for t in self.tasks if t.status == "todo"),
            "in_progress": sum(1 for t in self.tasks if t.status == "in_progress"),
            "done": sum(1 for t in self.tasks if t.status == "done"),
            "paused": sum(1 for t in self.tasks if t.status == "paused"),
            "high": sum(1 for t in self.tasks if t.priority == "high"),
            "medium": sum(1 for t in self.tasks if t.priority == "medium"),
            "low": sum(1 for t in self.tasks if t.priority == "low"),
        }

    @property
    def group_counts(self) -> list[tuple[str, int]]:
        groups = {}
        for t in self.tasks:
            groups[t.group] = groups.get(t.group, 0) + 1
        return sorted(groups.items(), key=lambda x: -x[1])

    @property
    def completion_rate(self) -> float:
        if not self.tasks:
            return 0
        return sum(1 for t in self.tasks if t.status == "done") / len(self.tasks) * 100
