"""Regressão: endpoints de escrita não podem corromper tasks.json / logs.json.

Achados na auditoria de 2026-10-05, todos reproduzidos antes de corrigir.
O tema comum: dado inválido entrava no arquivo e o整机 TUI deixava de
construir o Task no próximo start — a mesma classe do crash de 2026-10-03.
"""

import json
import sys
import threading
import urllib.error
import urllib.request
from http.server import HTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import server as srv
from conftest import full_task


@pytest.fixture
def api(tmp_path, monkeypatch):
    monkeypatch.setattr(srv, "TASKS_PATH", tmp_path / "tasks.json")
    monkeypatch.setattr(srv, "LOGS_PATH", tmp_path / "logs.json")
    monkeypatch.setattr(srv, "CONTEXTS_DIR", tmp_path / "contexts")
    (tmp_path / "tasks.json").write_text(
        json.dumps([full_task(id="t-1")]), encoding="utf-8"
    )
    (tmp_path / "logs.json").write_text("[]", encoding="utf-8")

    httpd = HTTPServer(("127.0.0.1", 0), srv.PlexoHandler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}", tmp_path
    httpd.shutdown()
    httpd.server_close()


def call(api, path, payload=None, raw=None):
    base, _ = api
    data = raw if raw is not None else json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{base}{path}", data=data,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        resp = urllib.request.urlopen(req, timeout=5)
        return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"{}")
        except json.JSONDecodeError:
            return e.code, {}


def saved(api):
    return json.loads((api[1] / "tasks.json").read_text(encoding="utf-8"))


# ── _add_task: enums ────────────────────────────────────────────────────────

def test_add_normaliza_priority_invalida(api):
    call(api, "/api/tasks/add", {"title": "p", "priority": "URGENTE"})
    assert saved(api)[-1]["priority"] == "medium"


def test_add_normaliza_status_invalido(api):
    call(api, "/api/tasks/add", {"title": "p", "status": "hacked"})
    assert saved(api)[-1]["status"] == "todo"


def test_add_normaliza_none_e_vazio(api):
    call(api, "/api/tasks/add", {"title": "p", "priority": None, "status": None})
    call(api, "/api/tasks/add", {"title": "q", "priority": "", "status": ""})
    for t in saved(api)[1:]:
        assert t["priority"] in ("high", "medium", "low")
        assert t["status"] in ("todo", "in_progress", "done", "paused")


def test_add_aceita_status_valido(api):
    call(api, "/api/tasks/add", {"title": "p", "status": "in_progress", "priority": "high"})
    t = saved(api)[-1]
    assert (t["status"], t["priority"]) == ("in_progress", "high")


# ── _add_task: shape e tamanho ─────────────────────────────────────────────

def test_add_rejeita_title_nao_string(api):
    status, _ = call(api, "/api/tasks/add", {"title": 123})
    assert status == 400


def test_add_rejeita_title_vazio(api):
    status, _ = call(api, "/api/tasks/add", {"title": "   "})
    assert status == 400


def test_add_limita_title(api):
    call(api, "/api/tasks/add", {"title": "A" * 5000})
    assert len(saved(api)[-1]["title"]) <= srv.TASK_MAX_TITLE


def test_add_rejeita_body_lista(api):
    status, _ = call(api, "/api/tasks/add", ["a", "b"])
    assert status == 400


# ── _update_task_status ────────────────────────────────────────────────────

def test_update_status_rejeita_enum_invalido(api):
    status, _ = call(api, "/api/tasks/update-status", {"id": "t-1", "status": "EXPLODIDO"})
    assert status == 400
    assert saved(api)[0]["status"] == "todo"


def test_update_status_aceita_enum_valido(api):
    status, _ = call(api, "/api/tasks/update-status", {"id": "t-1", "status": "done"})
    assert status == 200
    assert saved(api)[0]["status"] == "done"


# ── _read_body: body malformado ────────────────────────────────────────────

def test_json_truncado_responde_400_e_nao_derruba_conexao(api):
    status, _ = call(api, "/api/tasks/add", raw=b"{isso nao eh json")
    assert status == 400


def test_body_binario_responde_400(api):
    status, _ = call(api, "/api/tasks/add", raw=b"\xff\xfe\x00binario")
    assert status == 400


def test_body_valido_continua_funcionando(api):
    status, _ = call(api, "/api/tasks/add", {"title": "ok"})
    assert status == 200


# ── _set_task_context ──────────────────────────────────────────────────────

def test_context_de_task_inexistente_e_404(api):
    _, tmp = api
    status, _ = call(api, "/api/tasks/nao-existe-999/context", {"content": "fantasma"})
    assert status == 404
    assert not (tmp / "contexts" / "nao-existe-999.md").exists()


def test_context_de_task_real_e_aceito(api):
    _, tmp = api
    status, _ = call(api, "/api/tasks/t-1/context", {"content": "contexto legitimo"})
    assert status == 200
    assert (tmp / "contexts" / "t-1.md").read_text(encoding="utf-8") == "contexto legitimo"


# ── _add_log: integridade do log ───────────────────────────────────────────

def test_log_nao_aceita_id_forjado(api):
    call(api, "/api/logs", {
        "level": "info", "action": "FAKE", "message": "m",
        "id": "FORJADO", "timestamp": "1999-01-01T00:00:00Z",
    })
    entry = json.loads((api[1] / "logs.json").read_text(encoding="utf-8"))[0]
    assert entry["id"] != "FORJADO"
    assert not entry["timestamp"].startswith("1999")


def test_log_normaliza_level_invalido(api):
    call(api, "/api/logs", {"level": "catastrophe", "action": "X", "message": "m"})
    entry = json.loads((api[1] / "logs.json").read_text(encoding="utf-8"))[0]
    assert entry["level"] == "info"


def test_log_rejeita_body_lista(api):
    status, _ = call(api, "/api/logs", ["a"])
    assert status == 400


# ── _write_json: escrita atômica ───────────────────────────────────────────

def test_write_json_nao_deixa_tmp_para_trás(api):
    call(api, "/api/tasks/add", {"title": "p"})
    assert not (api[1] / "tasks.json.tmp").exists()


def test_write_json_substitui_ao_ves_de_truncar(api, tmp_path):
    srv._write_json(tmp_path / "t.json", [{"id": "1"}])
    assert json.loads((tmp_path / "t.json").read_text()) == [{"id": "1"}]
    srv._write_json(tmp_path / "t.json", [{"id": "2"}, {"id": "3"}])
    assert json.loads((tmp_path / "t.json").read_text()) == [{"id": "2"}, {"id": "3"}]


# ── _get_stats: status legado inválido ─────────────────────────────────────

def test_stats_nao_cria_chave_para_status_invalido(api):
    api_base, tmp = api
    (tmp / "tasks.json").write_text(json.dumps([
        full_task(id="a", status="todo"),
        {"id": "b", "status": "STATUS_BIZARRO"},  # legado/corrompido
    ]), encoding="utf-8")
    resp = urllib.request.urlopen(f"{api_base}/api/stats", timeout=5)
    counts = json.loads(resp.read())
    assert set(counts) == {"total", "todo", "in_progress", "done", "paused"}
    assert counts["total"] == 2
