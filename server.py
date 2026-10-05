#!/usr/bin/env python3
"""plexo API server — serves static UI + REST endpoints for tasks & logs."""

import json
import os
import sys
import mimetypes
import socket
import time
from http import HTTPStatus
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime, timezone

HOME = os.path.expanduser("~")
TASKS_PATH = Path(f"{HOME}/.plexo/tasks.json")
LOGS_PATH = Path(f"{HOME}/.plexo/logs.json")
CONTEXTS_DIR = Path(f"{HOME}/.plexo/contexts")
STATIC_DIR = Path(__file__).resolve().parent / "dist"

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

SNAKE_CASE_MAP = {
    "createdAt": "created_at",
    "updatedAt": "updated_at",
    "taskId": "task_id",
    "taskTitle": "task_title"
}
CAMEL_CASE_MAP = {v: k for k, v in SNAKE_CASE_MAP.items()}

TASK_REQUIRED_FIELDS = ("id", "title", "description", "priority", "status", "group")
TASK_VALID_STATUS = ("todo", "in_progress", "done", "paused")
TASK_VALID_PRIORITY = ("high", "medium", "low")
TASK_MAX_TITLE = 200

class _BadRequest(Exception):
    """Body malformado: vira 400 em vez de derrubar a conexao sem resposta."""

def _clean_enum(value, allowed, default):
    """Normaliza um enum, devolvendo o default quando o valor nao serve.

    Sem isto, _add_task/_update_task_status gravam 'URGENTE' ou 'hacked' direto no
    tasks.json e a TUI deixa de conseguir construir o Task no proximo start.
    """
    if isinstance(value, str) and value.strip().lower() in allowed:
        return value.strip().lower()
    return default

def _validate_tasks(tasks):
    """Devolve (ok, erro). Bulk replace grava o arquivo inteiro: validar é obrigatório."""
    if not isinstance(tasks, list):
        return False, "'tasks' must be a list"
    if not tasks:
        return False, "refusing to write an empty task list"
    for i, t in enumerate(tasks):
        if not isinstance(t, dict):
            return False, f"task[{i}] is not an object"
        missing = [f for f in TASK_REQUIRED_FIELDS if f not in t or t[f] in (None, "")]
        if missing:
            return False, f"task[{i}] ({t.get('id', '?')}) missing: {', '.join(missing)}"
        if t["status"] not in TASK_VALID_STATUS:
            return False, f"task[{i}] invalid status {t['status']!r}"
        if t["priority"] not in TASK_VALID_PRIORITY:
            return False, f"task[{i}] invalid priority {t['priority']!r}"
    ids = [t["id"] for t in tasks]
    if len(set(ids)) != len(ids):
        return False, "duplicate task ids"
    return True, None

def _snake_keys(d: dict) -> dict:
    return {SNAKE_CASE_MAP.get(k, k): v for k, v in d.items()}

def _camel_keys(d: dict) -> dict:
    return {CAMEL_CASE_MAP.get(k, k): v for k, v in d.items()}

def _read_json(path: Path):
    if not path.exists():
        return []
    with open(path) as f:
        return json.load(f)

def _write_json(path: Path, data):
    """Escrita atomica: grava em .tmp e renomeia.

    Abrir o arquivo direto trunca se o processo morrer no meio -- e um tasks.json
    truncado foi exatamente o que matou a TUI no boot em 2026-10-03.
    """
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    # touch the file's mtime to trigger inotify watchers
    os.utime(path, None)


class PlexoHandler(BaseHTTPRequestHandler):
    """HTTP handler that serves static files and REST API endpoints."""

    def log_message(self, format, *args):  # noqa: A002 - nome herdado de BaseHTTPRequestHandler
        print(f"[plexo] {args[0] if args else format}", file=sys.stderr)

    # ── helpers ──────────────────────────────────────────────────────────

    def _send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, status, message):
        self._send_json({"error": message}, status)

    def _read_body(self):
        """Retorna o body parseado, ou None se ausente/invalido (raise _BadRequest)."""
        raw_len = self.headers.get("Content-Length", 0)
        try:
            length = int(raw_len)
        except (TypeError, ValueError):
            raise _BadRequest("invalid Content-Length")
        if length <= 0:
            return None
        try:
            return json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise _BadRequest(f"malformed JSON body: {e}") from e

    def _parse_path(self):
        parsed = urlparse(self.path)
        return parsed.path.rstrip("/") or "/"

    # ── routing ──────────────────────────────────────────────────────────

    def do_GET(self):
        path = self._parse_path()
        if path == "/api/tasks":
            return self._get_tasks()
        elif path.startswith("/api/tasks/") and path.endswith("/context"):
            # /api/tasks/<id>/context
            task_id = path.split("/")[3]
            return self._get_task_context(task_id)
        elif path == "/api/logs":
            return self._get_logs()
        elif path == "/api/stats":
            return self._get_stats()
        else:
            return self._serve_static()

    def do_POST(self):
        try:
            self._dispatch_post()
        except _BadRequest as e:
            self._send_error(400, str(e))
        except Exception as e:  # noqa: BLE001
            # Nunca derrubar a conexao sem resposta: o cliente ficava sem status.
            self._send_error(500, f"internal error: {type(e).__name__}: {e}")

    def _dispatch_post(self):
        path = self._parse_path()
        if path == "/api/tasks":
            return self._set_tasks()
        elif path == "/api/tasks/add":
            return self._add_task()
        elif path == "/api/tasks/update-status":
            return self._update_task_status()
        elif path == "/api/tasks/delete":
            return self._delete_task()
        elif path.startswith("/api/tasks/") and path.endswith("/context"):
            task_id = path.split("/")[3]
            return self._set_task_context(task_id)
        elif path == "/api/logs":
            return self._add_log()
        else:
            self._send_error(404, "Not found")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    # ── API endpoints ────────────────────────────────────────────────────

    def _get_tasks(self):
        tasks = _read_json(TASKS_PATH)
        # convert snake_case → camelCase for frontend
        camel = [_camel_keys(t) for t in tasks]
        self._send_json({"tasks": camel, "count": len(camel)})

    def _set_tasks(self):
        """Bulk replace: sobrescreve TASKS_PATH inteiro. Exige replace:true + payload valido.

        Endpoint nao documentado e sem callers conhecidos. Sem o replace:true explicito
        um cliente que envie uma lista parcial apaga as outras tasks e recebe ok:true
        (foi como a task 1788884267-f43ad7 perdeu titulo/descricao em 2026-09).
        """
        body = self._read_body()
        if body is None:
            return self._send_error(400, "Request body required")
        if not isinstance(body, dict) or not body.get("replace"):
            return self._send_error(
                400,
                "Bulk replace refused. Send {\"replace\": true, \"tasks\": [...]} "
                "to overwrite every task. Use /api/tasks/add or "
                "/api/tasks/update-status for single-task changes.",
            )
        raw = body.get("tasks")
        incoming = raw if isinstance(raw, list) else []
        ok, err = _validate_tasks(incoming)
        if not ok:
            return self._send_error(400, f"Invalid task list: {err}")
        snake = [_snake_keys(t) if isinstance(t, dict) else {} for t in incoming]
        before = len(_read_json(TASKS_PATH))
        _write_json(TASKS_PATH, snake)
        self._append_log({
            "level": "warn",
            "action": "TASKS_REPLACED",
            "message": f"Bulk replace: {before} -> {len(snake)} tasks",
        })
        self._send_json({"ok": True, "count": len(snake)})

    def _add_task(self):
        """Append a single task with auto-generated ID and timestamp."""
        body = self._read_body()
        if body is None:
            return self._send_error(400, "Request body required")
        if not isinstance(body, dict):
            return self._send_error(400, "Body must be a JSON object")
        title = body.get("title", "Untitled")
        if not isinstance(title, str) or not title.strip():
            return self._send_error(400, "'title' must be a non-empty string")
        title = title.strip()[:TASK_MAX_TITLE]
        tasks = _read_json(TASKS_PATH)

        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        task = {
            "id": f"{int(time.time())}-{os.urandom(3).hex()}",
            "title": title,
            "description": str(body.get("description", "") or "")[:2000],
            "priority": _clean_enum(body.get("priority"), TASK_VALID_PRIORITY, "medium"),
            "status": _clean_enum(body.get("status"), TASK_VALID_STATUS, "todo"),
            "group": str(body.get("group", "general") or "general")[:50],
            "created_at": now,
            "updated_at": now,
        }
        tasks.append(task)
        _write_json(TASKS_PATH, tasks)

        self._append_log({
            "level": "success",
            "action": "TASK_CREATED",
            "message": f'Created "{task["title"]}"',
            "task_id": task["id"],
            "task_title": task["title"],
        })
        self._send_json({"ok": True, "task": _camel_keys(task)})

    def _update_task_status(self):
        """Update status of a task by ID. Body: {id, status}."""
        body = self._read_body()
        if body is None:
            return self._send_error(400, "Request body required")
        task_id = body.get("id")
        new_status = body.get("status")
        if not task_id or not new_status:
            return self._send_error(400, "Fields 'id' and 'status' required")
        if not isinstance(task_id, str):
            return self._send_error(400, "'id' must be a string")
        clean_status = _clean_enum(new_status, TASK_VALID_STATUS, None)
        if clean_status is None:
            return self._send_error(
                400, f"Invalid status {new_status!r}. Valid: {', '.join(TASK_VALID_STATUS)}"
            )

        tasks = _read_json(TASKS_PATH)
        found = None
        old_status = None
        for t in tasks:
            if isinstance(t, dict) and t.get("id") == task_id:
                old_status = t.get("status", "todo")
                t["status"] = clean_status
                t["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                found = t
                break

        if found is None:
            return self._send_error(404, f"Task {task_id} not found")

        title = found.get("title") or "(sem título)"
        _write_json(TASKS_PATH, tasks)
        self._append_log({
            "level": "info",
            "action": "TASK_STATUS_CHANGED",
            "message": f'"{title}": {old_status} → {new_status}',
            "task_id": task_id,
            "task_title": title,
        })
        self._send_json({"ok": True, "task": _camel_keys(found)})

    def _delete_task(self):
        """Delete a task by ID. Body: {id}."""
        body = self._read_body()
        if body is None:
            return self._send_error(400, "Request body required")
        task_id = body.get("id")
        if not task_id:
            return self._send_error(400, "Field 'id' required")

        tasks = _read_json(TASKS_PATH)
        removed = None
        for i, t in enumerate(tasks):
            if t.get("id") == task_id:
                removed = tasks.pop(i)
                break

        if not removed:
            return self._send_error(404, f"Task {task_id} not found")

        _write_json(TASKS_PATH, tasks)
        self._append_log({
            "level": "success",
            "action": "TASK_DELETED",
            "message": f'Deleted "{removed["title"]}"',
            "task_id": task_id,
            "task_title": removed["title"],
        })
        self._send_json({"ok": True})

    def _append_log(self, entry: dict):
        """Internal: append a log entry to logs.json."""
        logs = _read_json(LOGS_PATH)
        # id/timestamp depois do spread: um caller nao pode forjar a ordem do log.
        log_entry = {
            **entry,
            "id": f"{int(time.time()*1000)}-{os.urandom(2).hex()}",
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        logs.insert(0, log_entry)
        if len(logs) > 500:
            logs = logs[:500]
        _write_json(LOGS_PATH, logs)

    def _get_logs(self):
        logs = _read_json(LOGS_PATH)
        camel = [_camel_keys(l) for l in logs]
        self._send_json({"logs": camel, "count": len(camel)})

    def _add_log(self):
        body = self._read_body()
        if body is None:
            return self._send_error(400, "Request body required")
        if not isinstance(body, dict):
            return self._send_error(400, "Body must be a JSON object")
        level = _clean_enum(body.get("level"), ("info", "success", "warn", "error"), "info")
        action = str(body.get("action", "MANUAL"))[:60]
        message = str(body.get("message", ""))[:500]
        task_id = body.get("task_id")
        self._append_log({
            "level": level,
            "action": action,
            "message": message,
            "task_id": task_id if isinstance(task_id, str) else None,
            "task_title": body.get("task_title") if isinstance(body.get("task_title"), str) else None,
        })
        self._send_json({"ok": True})

    def _get_stats(self):
        tasks = _read_json(TASKS_PATH)
        counts = {"total": 0, "todo": 0, "in_progress": 0, "done": 0, "paused": 0}
        for t in tasks:
            # .get() com default, e nao counts[s] solto: um status invalido legado
            # criaria uma chave nova e falsearia um contador.
            s = t.get("status") if isinstance(t, dict) else None
            if s in ("todo", "in_progress", "done", "paused"):
                counts[s] += 1
            counts["total"] += 1
        self._send_json(counts)

    # ── task context endpoints ───────────────────────────────────────────

    def _get_task_context(self, task_id):
        ctx_path = CONTEXTS_DIR / f"{task_id}.md"
        if not ctx_path.exists():
            self._send_error(404, f"Context for task {task_id} not found")
            return
        body = ctx_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/markdown; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _set_task_context(self, task_id):
        body = self._read_body()
        if body is None:
            return self._send_error(400, "Request body required")
        if not isinstance(body, dict):
            return self._send_error(400, "Body must be a JSON object")
        if not any(isinstance(t, dict) and t.get("id") == task_id for t in _read_json(TASKS_PATH)):
            return self._send_error(404, f"Task {task_id} not found")
        CONTEXTS_DIR.mkdir(parents=True, exist_ok=True)
        ctx_path = CONTEXTS_DIR / f"{task_id}.md"
        content = str(body.get("content", "") or "")
        tmp = ctx_path.with_suffix(".md.tmp")
        tmp.write_text(content, encoding="utf-8")
        os.replace(tmp, ctx_path)
        self._append_log({
            "level": "info",
            "action": "CONTEXT_UPDATED",
            "message": f"Context updated for task {task_id}",
            "task_id": task_id,
        })
        self._send_json({"ok": True, "task_id": task_id})

    # ── static file serving ──────────────────────────────────────────────

    def _serve_static(self):
        path = self._parse_path()
        if path == "/":
            path = "/index.html"

        # sanitize: prevent directory traversal
        rel = path.lstrip("/")
        filepath = (STATIC_DIR / rel).resolve()
        if not str(filepath).startswith(str(STATIC_DIR)):
            self._send_error(403, "Forbidden")
            return

        if filepath.is_dir():
            filepath = filepath / "index.html"

        if not filepath.exists() or not filepath.is_file():
            self._send_error(404, "Not found")
            return

        mime, _ = mimetypes.guess_type(str(filepath))
        if mime is None:
            mime = "application/octet-stream"

        body = filepath.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    port = int(args[0]) if args else 8080
    use_mock = "--mock" in flags

    if use_mock:
        mock_path = Path("/tmp/plexo-mock-tasks.json")
        _write_json(mock_path, MOCK_TASKS)
        # Patch TASKS_PATH to point to mock data
        import builtins
        global TASKS_PATH, LOGS_PATH
        TASKS_PATH = mock_path
        LOGS_PATH = Path("/dev/null")
        print("📸 Mock mode — serving demo data, real tasks untouched")
    else:
        TASKS_PATH.parent.mkdir(parents=True, exist_ok=True)
        if not TASKS_PATH.exists():
            _write_json(TASKS_PATH, [])
        if not LOGS_PATH.exists():
            _write_json(LOGS_PATH, [])

    bind = os.environ.get("PLEXO_BIND", "127.0.0.1")
    server = HTTPServer((bind, port), PlexoHandler)
    server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    addr = "localhost" if bind in ("127.0.0.1", "localhost") else bind
    print(f"🚀 plexo API + UI at http://{bind}:{port}")
    print(f"   PC:  http://{addr}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n⏹  plexo server stopped")
        server.server_close()


if __name__ == "__main__":
    main()
