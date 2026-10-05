"""Regressão: POST /api/tasks não pode mais destruir tasks.json em silêncio.

Prova original (2026-10-05): um POST com lista parcial sobrescrevia o arquivo
inteiro, apagava as demais tasks e respondia {"ok": true}. A task
1788884267-f43ad7 ficou com 3 de 8 campos por causa disso.
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
        json.dumps([full_task(id="keep-1"), full_task(id="keep-2")]), encoding="utf-8"
    )
    (tmp_path / "logs.json").write_text("[]", encoding="utf-8")

    httpd = HTTPServer(("127.0.0.1", 0), srv.PlexoHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    yield base
    httpd.shutdown()
    httpd.server_close()


def call(api, path, payload, method="POST"):
    req = urllib.request.Request(
        f"{api}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method=method,
    )
    try:
        resp = urllib.request.urlopen(req, timeout=5)
        return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def tasks_on_disk(tmp_path):
    return json.loads((tmp_path / "tasks.json").read_text(encoding="utf-8"))


def test_lista_parcial_sem_replace_e_recusada(api, tmp_path):
    status, body = call(api, "/api/tasks", {"tasks": [{"id": "keep-1", "status": "done"}]})

    assert status == 400
    assert "replace" in body["error"]
    assert [t["id"] for t in tasks_on_disk(tmp_path)] == ["keep-1", "keep-2"]


def test_replace_com_registro_incompleto_e_recusado(api, tmp_path):
    status, body = call(api, "/api/tasks", {"replace": True, "tasks": [{"id": "k", "status": "done"}]})

    assert status == 400
    assert "missing" in body["error"]
    assert len(tasks_on_disk(tmp_path)) == 2


def test_replace_com_status_invalido_e_recusado(api, tmp_path):
    bad = full_task(id="k", status="banana")
    status, _ = call(api, "/api/tasks", {"replace": True, "tasks": [bad]})

    assert status == 400
    assert len(tasks_on_disk(tmp_path)) == 2


def test_replace_com_prioridade_invalida_e_recusado(api, tmp_path):
    bad = full_task(id="k", priority="URGENTE")
    status, _ = call(api, "/api/tasks", {"replace": True, "tasks": [bad]})

    assert status == 400
    assert len(tasks_on_disk(tmp_path)) == 2


def test_replace_com_lista_vazia_e_recusado(api, tmp_path):
    status, _ = call(api, "/api/tasks", {"replace": True, "tasks": []})

    assert status == 400
    assert len(tasks_on_disk(tmp_path)) == 2


def test_replace_com_id_duplicado_e_recusado(api, tmp_path):
    status, body = call(api, "/api/tasks", {"replace": True, "tasks": [full_task(id="dup"), full_task(id="dup")]})

    assert status == 400
    assert "duplicate" in body["error"].lower()
    assert len(tasks_on_disk(tmp_path)) == 2


def test_replace_valido_aceita_e_grava(api, tmp_path):
    novo = [full_task(id="novo-1"), full_task(id="novo-2")]
    status, body = call(api, "/api/tasks", {"replace": True, "tasks": novo})

    assert status == 200
    assert body["count"] == 2
    assert sorted(t["id"] for t in tasks_on_disk(tmp_path)) == ["novo-1", "novo-2"]


def test_update_status_em_registro_sem_titulo_nao_quebra(api, tmp_path):
    """Regressão do KeyError: found["title"] num registro sem title."""
    srv.TASKS_PATH.write_text(
        json.dumps([{"id": "sem-title", "status": "todo", "updated_at": "2026-09-08T22:23:04Z"}]),
        encoding="utf-8",
    )

    status, body = call(api, "/api/tasks/update-status", {"id": "sem-title", "status": "done"})

    assert status == 200
    assert body["task"]["status"] == "done"


def test_update_status_de_id_inexistente_e_404(api):
    status, _ = call(api, "/api/tasks/update-status", {"id": "nao-existe", "status": "done"})

    assert status == 404
