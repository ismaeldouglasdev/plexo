"""Regressão: um registro com schema divergente não pode derrubar o tasks.json.

Bug de 2026-10-03: a task 1788884267-f43ad7 tinha só id/status/updated_at.
O dict-comprehension filtrava chave extra mas não preenchia chave faltando, e o
except de _load era (json.JSONDecodeError, KeyError) — TypeError passava direto
e matava a TUI inteira no startup.
"""

import json

from conftest import full_task
from tui.storage import SEED_TASKS, TaskStore


def test_record_com_schema_incompleto_nao_derruba_o_arquivo(write_tasks):
    """O caso exato que matou a TUI: 3 campos num registro de 8."""
    write_tasks([
        full_task(),
        {"id": "1788884267-f43ad7", "status": "done", "updated_at": "2026-09-08T22:23:04Z"},
    ])

    store = TaskStore()

    assert len(store.tasks) == 2
    legados = next(t for t in store.tasks if t.id == "1788884267-f43ad7")
    assert legados.status == "done"
    assert legados.priority == "medium"
    assert legados.group == "general"
    assert legados.title.strip()
    assert legados.created_at


def test_um_registro_ruim_nao_perde_os_bos(write_tasks):
    """O registro bom continua intacto ao lado do quebrado."""
    bom = full_task(id="bom", title="Não pode ser perdidos")
    write_tasks([bom, {"id": "ruim", "status": "todo"}])

    tasks = {t.id: t for t in TaskStore().tasks}

    assert tasks["bom"].title == "Não pode ser perdidos"
    assert tasks["bom"].description == "desc"
    assert tasks["bom"].created_at == "2026-01-01T00:00:00Z"


def test_enum_invalido_e_coerigido(write_tasks):
    write_tasks([
        full_task(id="a", status="banana"),
        full_task(id="b", priority="URGENTE"),
    ])

    tasks = {t.id: t for t in TaskStore().tasks}

    assert tasks["a"].status == "todo"
    assert tasks["b"].priority == "medium"


def test_campo_desconhecido_e_descartado(write_tasks):
    write_tasks([full_task(id="x", campo_inexistente="ignorado")])

    task = TaskStore().tasks[0]

    assert not hasattr(task, "campo_inexistente")
    assert task.id == "x"


def test_entrada_nao_dict_e_ignorada(write_tasks):
    write_tasks([full_task(), "isto nao e objeto", 42])

    tasks = TaskStore().tasks

    assert len(tasks) == 1
    assert tasks[0].title == "Tarefa completa"


def test_json_invalido_cai_para_seed(plexo_home):
    (plexo_home / "tasks.json").write_text("{ isso nao eh json", encoding="utf-8")

    tasks = TaskStore().tasks

    assert len(tasks) == len(SEED_TASKS)
    assert all(t.title for t in tasks)


def test_arquivo_ausente_cai_para_seed(plexo_home):
    assert not (plexo_home / "tasks.json").exists()

    assert len(TaskStore().tasks) == len(SEED_TASKS)


def test_todos_os_registros_carregam_com_title(write_tasks):
    write_tasks([
        full_task(id="1"),
        {"id": "2"},
        {"id": "3", "title": ""},
        full_task(id="4", priority="low", status="paused"),
    ])

    tasks = TaskStore().tasks

    assert len(tasks) == 4
    assert all(t.title.strip() for t in tasks), "title vazio quebraria a UI"


def test_reparo_e_registrado_no_log(write_tasks, plexo_home):
    write_tasks([full_task(), {"id": "ruim", "status": "todo"}])

    TaskStore()

    logs = json.loads((plexo_home / "logs.json").read_text(encoding="utf-8"))
    assert any("schema divergente" in entry.get("message", "") for entry in logs)


def test_reload_nao_duplica_nem_perde_tasks(write_tasks):
    write_tasks([full_task(id="a"), {"id": "b", "status": "todo"}])
    TaskStore()

    tasks = TaskStore().tasks

    assert sorted(t.id for t in tasks) == ["a", "b"]
