#!/usr/bin/env python3
"""plexo API server — serves static UI + REST endpoints for tasks & logs."""

import json
import os
import sys
import mimetypes
from http import HTTPStatus
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime, timezone

TASKS_PATH = Path(os.path.expanduser("~/.plexo/tasks.json"))
LOGS_PATH = Path(os.path.expanduser("~/.plexo/logs.json"))
STATIC_DIR = Path(__file__).resolve().parent / "dist"

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
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080

    # ensure JSON files exist
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
