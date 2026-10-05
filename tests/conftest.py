import importlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def plexo_home(tmp_path, monkeypatch):
    """Redirect storage paths to a tmp dir so tests never touch ~/.plexo."""
    data = tmp_path / ".plexo"
    data.mkdir()
    monkeypatch.setenv("HOME", str(tmp_path))
    import tui.storage as storage

    monkeypatch.setattr(storage, "DATA_DIR", data)
    monkeypatch.setattr(storage, "TASKS_FILE", data / "tasks.json")
    monkeypatch.setattr(storage, "LOGS_FILE", data / "logs.json")
    return data


@pytest.fixture
def write_tasks(plexo_home):
    def _write(records):
        (plexo_home / "tasks.json").write_text(json.dumps(records), encoding="utf-8")

    return _write


def full_task(**over):
    base = {
        "id": "t-1",
        "title": "Tarefa completa",
        "description": "desc",
        "priority": "high",
        "status": "todo",
        "group": "geral",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }
    base.update(over)
    return base
