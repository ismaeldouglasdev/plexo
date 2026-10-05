"""
Data layer: JSON persistence, activity log, seed data.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
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
    {"id": "1", "title": "Build landing page", "description": "Design and develop the marketing landing page with Tailwind.", "priority": "high", "status": "todo", "group": "web", "value": 500, "created_at": "2026-06-28T00:00:00Z", "updated_at": "2026-06-28T00:00:00Z"},
    {"id": "2", "title": "Fix login redirect loop", "description": "Users get stuck in infinite redirect after password reset.", "priority": "high", "status": "in_progress", "group": "backend", "value": None, "created_at": "2026-06-27T00:00:00Z", "updated_at": "2026-06-28T00:00:00Z"},
    {"id": "3", "title": "Set up CI/CD pipeline", "description": "GitHub Actions: lint, test, deploy to staging on push.", "priority": "high", "status": "done", "group": "devops", "value": 200, "created_at": "2026-06-20T00:00:00Z", "updated_at": "2026-06-28T00:00:00Z"},
    {"id": "4", "title": "Design system: color tokens", "description": "Define and document the full color palette + dark mode.", "priority": "medium", "status": "done", "group": "design", "value": None, "created_at": "2026-06-15T00:00:00Z", "updated_at": "2026-06-25T00:00:00Z"},
    {"id": "5", "title": "API rate limiting middleware", "description": "Implement token-bucket rate limiter for public endpoints.", "priority": "high", "status": "done", "group": "backend", "value": 300, "created_at": "2026-06-10T00:00:00Z", "updated_at": "2026-06-22T00:00:00Z"},
    {"id": "6", "title": "Mobile nav hamburger menu", "description": "Responsive sidebar with collapsible groups for mobile.", "priority": "medium", "status": "todo", "group": "web", "value": 150, "created_at": "2026-06-26T00:00:00Z", "updated_at": "2026-06-26T00:00:00Z"},
    {"id": "7", "title": "Database migration: orders table", "description": "Add status, timestamps, and FK constraints to orders.", "priority": "high", "status": "in_progress", "group": "backend", "value": None, "created_at": "2026-06-25T00:00:00Z", "updated_at": "2026-06-28T00:00:00Z"},
    {"id": "8", "title": "User onboarding flow", "description": "Welcome wizard: profile pic, preferences, first project.", "priority": "medium", "status": "todo", "group": "web", "value": 400, "created_at": "2026-06-24T00:00:00Z", "updated_at": "2026-06-24T00:00:00Z"},
    {"id": "9", "title": "Load testing with k6", "description": "Write scenarios for 1000 concurrent users, report p50/p95/p99.", "priority": "low", "status": "done", "group": "devops", "value": None, "created_at": "2026-06-18T00:00:00Z", "updated_at": "2026-06-23T00:00:00Z"},
    {"id": "10", "title": "Email template redesign", "description": "Responsive email templates for reset, welcome, digest.", "priority": "medium", "status": "done", "group": "design", "value": 250, "created_at": "2026-06-12T00:00:00Z", "updated_at": "2026-06-20T00:00:00Z"},
    {"id": "11", "title": "Webhook receiver service", "description": "Verify signatures, deduplicate events, dispatch to handlers.", "priority": "high", "status": "todo", "group": "backend", "value": 600, "created_at": "2026-06-22T00:00:00Z", "updated_at": "2026-06-22T00:00:00Z"},
    {"id": "12", "title": "Component library audit", "description": "Review all 23 components for a11y gaps and motion bugs.", "priority": "medium", "status": "todo", "group": "web", "value": None, "created_at": "2026-06-21T00:00:00Z", "updated_at": "2026-06-21T00:00:00Z"},
    {"id": "13", "title": "Terraform: staging environment", "description": "Module for VPC, ECS, RDS, ElastiCache in us-east-1.", "priority": "high", "status": "done", "group": "devops", "value": 350, "created_at": "2026-06-05T00:00:00Z", "updated_at": "2026-06-18T00:00:00Z"},
    {"id": "14", "title": "Search: debounce + highlight", "description": "Debounce input, highlight matches in results, keyboard nav.", "priority": "low", "status": "paused", "group": "web", "value": None, "created_at": "2026-06-19T00:00:00Z", "updated_at": "2026-06-19T00:00:00Z"},
    {"id": "15", "title": "S3 log archival lambda", "description": "Weekly job to compress and move logs older than 30 days.", "priority": "low", "status": "todo", "group": "devops", "value": 100, "created_at": "2026-06-17T00:00:00Z", "updated_at": "2026-06-17T00:00:00Z"},
]

MOCK_TASKS = [
    {"id": "m1", "title": "Homepage redesign", "description": "New hero section, value props, and CTA layout.", "priority": "high", "status": "in_progress", "group": "frontend", "value": 800, "created_at": "2026-07-01T00:00:00Z", "updated_at": "2026-07-02T00:00:00Z"},
    {"id": "m2", "title": "User authentication module", "description": "Login, signup, password reset with JWT.", "priority": "high", "status": "todo", "group": "backend", "value": 1200, "created_at": "2026-07-01T00:00:00Z", "updated_at": "2026-07-01T00:00:00Z"},
    {"id": "m3", "title": "Dashboard analytics widget", "description": "Interactive charts for daily active users and revenue.", "priority": "medium", "status": "todo", "group": "frontend", "value": 600, "created_at": "2026-06-30T00:00:00Z", "updated_at": "2026-06-30T00:00:00Z"},
    {"id": "m4", "title": "REST API documentation", "description": "OpenAPI/Swagger specs for all public endpoints.", "priority": "medium", "status": "done", "group": "docs", "value": 300, "created_at": "2026-06-28T00:00:00Z", "updated_at": "2026-07-01T00:00:00Z"},
    {"id": "m5", "title": "Database indexing review", "description": "Analyze slow queries and add composite indexes.", "priority": "high", "status": "in_progress", "group": "backend", "value": None, "created_at": "2026-06-29T00:00:00Z", "updated_at": "2026-07-01T00:00:00Z"},
    {"id": "m6", "title": "Email notification service", "description": "Transactional emails via SES with templates.", "priority": "medium", "status": "done", "group": "backend", "value": 400, "created_at": "2026-06-25T00:00:00Z", "updated_at": "2026-06-30T00:00:00Z"},
    {"id": "m7", "title": "Dark mode toggle", "description": "Persist theme preference, smooth CSS transition.", "priority": "low", "status": "done", "group": "frontend", "value": 150, "created_at": "2026-06-20T00:00:00Z", "updated_at": "2026-06-28T00:00:00Z"},
    {"id": "m8", "title": "Payment integration (Stripe)", "description": "Checkout session, webhooks, subscription management.", "priority": "high", "status": "todo", "group": "backend", "value": 2000, "created_at": "2026-06-27T00:00:00Z", "updated_at": "2026-06-27T00:00:00Z"},
    {"id": "m9", "title": "Accessibility audit", "description": "WCAG 2.1 AA compliance scan + manual testing.", "priority": "medium", "status": "todo", "group": "frontend", "value": 500, "created_at": "2026-06-26T00:00:00Z", "updated_at": "2026-06-26T00:00:00Z"},
    {"id": "m10", "title": "CI/CD pipeline optimization", "description": "Cache dependencies, parallelize test suites, reduce build time.", "priority": "low", "status": "in_progress", "group": "devops", "value": 250, "created_at": "2026-06-24T00:00:00Z", "updated_at": "2026-06-29T00:00:00Z"},
    {"id": "m11", "title": "Mobile push notifications", "description": "Firebase Cloud Messaging integration for iOS/Android.", "priority": "medium", "status": "done", "group": "mobile", "value": 900, "created_at": "2026-06-22T00:00:00Z", "updated_at": "2026-06-28T00:00:00Z"},
    {"id": "m12", "title": "Rate limiting dashboard", "description": "Admin panel to monitor and configure API rate limits.", "priority": "low", "status": "todo", "group": "frontend", "value": 350, "created_at": "2026-06-23T00:00:00Z", "updated_at": "2026-06-23T00:00:00Z"},
    {"id": "m13", "title": "Container registry migration", "description": "Migrate from Docker Hub to ECR with signed images.", "priority": "medium", "status": "done", "group": "devops", "value": None, "created_at": "2026-06-15T00:00:00Z", "updated_at": "2026-06-25T00:00:00Z"},
    {"id": "m14", "title": "Error tracking setup (Sentry)", "description": "Source maps, release tracking, alert rules in Sentry.", "priority": "high", "status": "done", "group": "backend", "value": 200, "created_at": "2026-06-10T00:00:00Z", "updated_at": "2026-06-20T00:00:00Z"},
    {"id": "m15", "title": "Onboarding tutorial videos", "description": "Record and embed walkthrough videos for new users.", "priority": "low", "status": "paused", "group": "docs", "value": 700, "created_at": "2026-06-18T00:00:00Z", "updated_at": "2026-06-18T00:00:00Z"},
]

STATUS_CYCLE = {"todo": "in_progress", "in_progress": "done", "done": "paused", "paused": "todo"}
PRIO_COLORS = {"high": "red", "medium": "yellow", "low": "green"}
STATUS_ICONS = {"todo": "○", "in_progress": "◔", "done": "●", "paused": "⊘"}

# ─── Storage ──────────────────────────────────────────────────────────────────

class TaskStore:
    def __init__(self, log_callback=None, use_mock=False):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.log_callback = log_callback
        # logs ANTES de tasks: _load/_coerce podem chamar _write_log em caso de
        # dados corrompidos, e _write_log depende de self.logs existir.
        self.logs = self._load_logs()
        self.tasks = self._load(use_mock)
        self._write_log("info", "APP_INIT", f"Store initialized with {len(self.tasks)} tasks")

    def _load(self, use_mock=False) -> list[Task]:
        if use_mock:
            return [Task(**t) for t in MOCK_TASKS]
        if TASKS_FILE.exists():
            try:
                raw = json.loads(TASKS_FILE.read_text())
            except (json.JSONDecodeError, OSError) as e:
                self._write_log("error", "SYSTEM_ERROR", f"tasks.json ilegível: {e}")
                return [Task(**t) for t in SEED_TASKS]
            return self._coerce(raw)
        return [Task(**t) for t in SEED_TASKS]

    def _coerce(self, raw) -> list[Task]:
        """Normaliza registros em Task; um record ruim não derruba o arquivo inteiro.

        Tolera campos ausentes/inválidos de propósito: tasks.json é estado de usuário
        editado por vários caminhos (server.py, TUI, scripts antigos) e já teve
        record com schema de versão antiga (bug 2026-10-03).
        """
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        tasks: list[Task] = []
        salvaged = 0
        for i, t in enumerate(raw):
            if not isinstance(t, dict):
                salvaged += 1
                continue
            known = {k: v for k, v in t.items() if k in Task.__dataclass_fields__}
            # setdefault só cobre chave ausente; campo presente porém vazio também
            # quebra a UI (linha em branco), então normaliza os dois casos.
            if not known.get("title"):
                known["title"] = "(sem título — registro legado)"
                salvaged += 1
            if not known.get("description"):
                known["description"] = ""
            if not known.get("group"):
                known["group"] = "general"
            known.setdefault("id", f"legacy-{i}")
            known.setdefault("priority", "medium")
            known.setdefault("status", "todo")
            known.setdefault("created_at", known.get("updated_at") or now)
            known.setdefault("updated_at", now)
            if known.get("status") not in STATUS_CYCLE:
                known["status"] = "todo"
            if known.get("priority") not in PRIO_COLORS:
                known["priority"] = "medium"
            try:
                tasks.append(Task(**known))
            except TypeError as e:
                salvaged += 1
                self._write_log(
                    "error", "SYSTEM_ERROR", f"registro {known.get('id')} descartado: {e}"
                )
        if salvaged:
            self._write_log(
                "warn", "SYSTEM_ERROR",
                f"{salvaged} registro(s) com schema divergente reparado(s) ao carregar",
            )
        return tasks

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
