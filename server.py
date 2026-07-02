#!/usr/bin/env python3
"""plexo API server — serves static UI + REST endpoints for tasks & logs."""

import json
import os
import sys
import mimetypes
import time
from http import HTTPStatus
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime, timezone

HOME = os.path.expanduser("~")
TASKS_PATH = Path(f"{HOME}/.plexo/tasks.json")
LOGS_PATH = Path(f"{HOME}/.plexo/logs.json")
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
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    # touch the file's mtime to trigger inotify watchers
    os.utime(path, None)


class PlexoHandler(BaseHTTPRequestHandler):
    """HTTP handler that serves static files and REST API endpoints."""

    def log_message(self, fmt, *args):
        print(f"[plexo] {args[0] if args else fmt}", file=sys.stderr)

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
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return None
        return json.loads(self.rfile.read(length))

    def _parse_path(self):
        parsed = urlparse(self.path)
        return parsed.path.rstrip("/") or "/"

    # ── routing ──────────────────────────────────────────────────────────

    def do_GET(self):
        path = self._parse_path()
        if path == "/api/tasks":
            return self._get_tasks()
        elif path == "/api/logs":
            return self._get_logs()
        elif path == "/api/stats":
            return self._get_stats()
        else:
            return self._serve_static()

    def do_POST(self):
        path = self._parse_path()
        if path == "/api/tasks":
            return self._set_tasks()
        elif path == "/api/tasks/add":
            return self._add_task()
        elif path == "/api/tasks/update-status":
            return self._update_task_status()
        elif path == "/api/tasks/delete":
            return self._delete_task()
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
        body = self._read_body()
        if body is None:
            return self._send_error(400, "Request body required")
        tasks = body.get("tasks", body if isinstance(body, list) else [body])
        # convert camelCase → snake_case for storage
        snake = [_snake_keys(t) for t in tasks]
        _write_json(TASKS_PATH, snake)
        self._send_json({"ok": True, "count": len(snake)})

    def _add_task(self):
        """Append a single task with auto-generated ID and timestamp."""
        body = self._read_body()
        if body is None:
            return self._send_error(400, "Request body required")
        tasks = _read_json(TASKS_PATH)

        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        import os as _os, time as _time
        task = {
            "id": f"{int(_time.time())}-{_os.urandom(3).hex()}",
            "title": body.get("title", "Untitled"),
            "description": body.get("description", ""),
            "priority": body.get("priority", "medium"),
            "status": body.get("status", "todo"),
            "group": body.get("group", "general"),
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

        tasks = _read_json(TASKS_PATH)
        found = None
        for t in tasks:
            if t.get("id") == task_id:
                old_status = t.get("status", "todo")
                t["status"] = new_status
                t["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                found = t
                break

        if not found:
            return self._send_error(404, f"Task {task_id} not found")

        _write_json(TASKS_PATH, tasks)
        self._append_log({
            "level": "info",
            "action": "TASK_STATUS_CHANGED",
            "message": f'"{found["title"]}": {old_status} → {new_status}',
            "task_id": task_id,
            "task_title": found["title"],
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
        import os as _os, time as _time
        log_entry = {
            "id": f"{int(_time.time()*1000)}-{_os.urandom(2).hex()}",
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            **entry,
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
        logs = _read_json(LOGS_PATH)
        entry = _snake_keys(body)
        logs.insert(0, entry)
        _write_json(LOGS_PATH, logs)
        self._send_json({"ok": True})

    def _get_stats(self):
        tasks = _read_json(TASKS_PATH)
        counts = {"total": 0, "todo": 0, "in_progress": 0, "done": 0, "paused": 0}
        for t in tasks:
            s = t.get("status", "todo")
            counts[s] = counts.get(s, 0) + 1
            counts["total"] += 1
        self._send_json(counts)

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

    server = HTTPServer(("0.0.0.0", port), PlexoHandler)
    addr = "localhost"
    print(f"🚀 plexo API + UI at http://0.0.0.0:{port}")
    print(f"   PC:  http://{addr}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n⏹  plexo server stopped")
        server.server_close()


if __name__ == "__main__":
    main()
