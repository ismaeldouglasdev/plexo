"""
plexo — TUI task manager with vim keys, dashboard, and activity logs.
"""
from __future__ import annotations

import time
from typing import Optional

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.reactive import reactive
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Button, DataTable, Footer, Header, Input, Label, RichLog, Static, TextArea,
)
from rich.style import Style
from rich.table import Table
from rich.text import Text
from rich.layout import Layout

from .storage import TaskStore, PRIO_COLORS, STATUS_ICONS, STATUS_CYCLE

# ═══════════════════════════════════════════════════════════════════════════════
# CSS — dark theme, amber accents, round borders
# ═══════════════════════════════════════════════════════════════════════════════

ROOT_CSS = """
Screen {
    background: #09090b;
}

TaskScreen, DashboardScreen, LogScreen {
    background: #09090b;
}

/* ── Header ── */
Header {
    background: #111113;
    color: #f59e0b;
    text-style: bold;
}

Header > HeaderTitle {
    text-style: bold;
}

/* ── DataTable ── */
#task-table {
    height: 1fr;
    margin: 0 1;
    border: round #27272a;
}

#task-table DataTable {
    height: 100%;
}

#task-table DataTable > .datatable--header {
    background: #18181b;
    color: #f59e0b;
    text-style: bold;
}

#task-table DataTable > .datatable--cursor {
    background: #1e1e30;
}

/* Status bar */
#status-line {
    dock: bottom;
    height: 1;
    padding: 0 1;
    background: #111113;
    color: #71717a;
}

/* ── Dashboard ── */
.stats-grid {
    layout: grid;
    grid-size: 4;
    grid-gutter: 1;
    padding: 0 1 0 1;
    height: 7;
}

.stat-card-total {
    background: #18181b;
    border-left: solid #a1a1aa;
    height: 5;
    padding: 0 1;
}

.stat-card-todo {
    background: #18181b;
    border-left: solid #52525b;
    height: 5;
    padding: 0 1;
}

.stat-card-doing {
    background: #18181b;
    border-left: solid #fbbf24;
    height: 5;
    padding: 0 1;
}

.stat-card-done {
    background: #18181b;
    border-left: solid #10b981;
    height: 5;
    padding: 0 1;
}

.stat-label {
    color: #71717a;
    text-style: bold;
    padding: 0 1;
}

.stat-value {
    text-style: bold;
    text-align: center;
}

.dash-section {
    border: round #27272a;
    margin: 0 1 1 1;
    padding: 1;
}

.dash-title {
    color: #f59e0b;
    text-style: bold;
    margin-bottom: 1;
}

/* ── Log View ── */
#log-view {
    margin: 0 1;
    border: round #27272a;
}

#log-view RichLog {
    height: 100%;
}

/* ── Footer ── */
Footer {
    background: #111113;
    color: #71717a;
}

Footer > FooterKey {
    color: #f59e0b;
}

/* ── Modals ── */
.modal-box {
    align: center middle;
    background: #00000080;
}

.modal-window {
    width: 50;
    padding: 1 2;
    background: #18181b;
    border: thick #f59e0b;
}

.modal-title {
    color: #f59e0b;
    text-style: bold;
    margin-bottom: 1;
    padding: 0 1;
}

.modal-hint {
    color: #52525b;
    padding: 0 1;
}

#form-title, #form-group {
    background: #27272a;
    border: solid #3f3f46;
    color: #e4e4e7;
    margin: 0 1;
}

#form-title:focus, #form-group:focus {
    border: solid #f59e0b;
}

#form-desc {
    background: #27272a;
    border: solid #3f3f46;
    color: #e4e4e7;
    margin: 0 1;
}

#form-desc:focus {
    border: solid #f59e0b;
}

#form-priority {
    background: #27272a;
    border: solid #3f3f46;
    color: #e4e4e7;
    margin: 0 1;
}

#form-priority:focus {
    border: solid #f59e0b;
}

#confirm-box {
    width: 40;
    padding: 1 2;
    background: #18181b;
    border: thick #ef4444;
}

Button {
    margin: 0 1;
}

/* ── Find/Help modals ── */
#search-input {
    background: #27272a;
    border: solid #3f3f46;
    color: #e4e4e7;
    margin: 0 1;
}

#search-input:focus {
    border: solid #f59e0b;
}

#search-results {
    padding: 0 1;
}
"""

# ═══════════════════════════════════════════════════════════════════════════════
# Shared helpers
# ═══════════════════════════════════════════════════════════════════════════════

def format_value(v: Optional[int]) -> Text:
    if v is None:
        return Text("   —  ", style="grey35")
    if v >= 1000:
        return Text(f"${v/1000:.1f}k".rjust(6), style="bold green")
    return Text(f"${v}".rjust(6), style="bold #10b981")

def format_task_row(task) -> list[Text]:
    icon = STATUS_ICONS.get(task.status, "○")
    prio_color = PRIO_COLORS.get(task.priority, "white")
    status_color = {
        "todo": "grey62", "in_progress": "yellow", "done": "green", "paused": "grey50",
    }.get(task.status, "grey62")
    title_style = "strike" if task.status == "done" else "none"
    title_color = "grey50" if task.status == "done" else "grey230"
    return [
        Text(icon, style=f"bold {status_color}"),
        format_value(task.value),
        Text(f" {task.title}", style=f"{title_style} {title_color}"),
        Text(f" {task.priority}", style=f"bold {prio_color}"),
        Text(f" #{task.group}", style="grey50"),
    ]

def format_time(iso: str) -> str:
    """Convert ISO timestamp to human relative time."""
    try:
        from datetime import datetime
        t = datetime.strptime(iso.replace("Z", ""), "%Y-%m-%dT%H:%M:%S")
        diff = time.time() - t.timestamp()
        if diff < 60: return "now"
        if diff < 3600: return f"{int(diff/60)}m"
        if diff < 86400: return f"{int(diff/3600)}h"
        return f"{int(diff/86400)}d"
    except: return ""

# ═══════════════════════════════════════════════════════════════════════════════
# Task List Screen
# ═══════════════════════════════════════════════════════════════════════════════

class TaskScreen(Screen):
    BINDINGS = [
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("a", "add_task", "Add", show=False),
        Binding("e", "edit_task", "Edit", show=False),
        Binding("d", "delete_task", "Delete", show=False),
        Binding("/", "focus_search", "Search", show=False),
        Binding("escape", "unfocus", "Cancel", show=False),
        Binding("1", "switch_tasks", "Tasks", show=False),
        Binding("2", "switch_dashboard", "Dash", show=False),
        Binding("3", "switch_logs", "Logs", show=False),
        Binding("q", "quit", "Quit", show=False),
        Binding("?", "show_help", "Help", show=False),
    ]

    def __init__(self, store: TaskStore):
        super().__init__()
        self.store = store
        self.filter_priority: Optional[str] = None
        self.filter_search: str = ""

    @property
    def filtered_tasks(self):
        tasks = self.store.tasks[:]
        if self.filter_priority:
            tasks = [t for t in tasks if t.priority == self.filter_priority]
        if self.filter_search:
            q = self.filter_search.lower()
            tasks = [t for t in tasks if q in t.title.lower() or q in t.description.lower() or q in t.group.lower()]
        return tasks

    def compose(self) -> ComposeResult:
        with Vertical(id="task-table"):
            yield DataTable()
        yield Static("", id="status-line")

    def on_mount(self):
        table = self.query_one(DataTable)
        table.add_columns("", "  $   ", "Title", "Prio", "Group")
        table.cursor_type = "row"
        self._refresh_table()
        self._update_status()

    def _refresh_table(self):
        table = self.query_one(DataTable)
        table.clear()
        for t in self.filtered_tasks:
            table.add_row(*format_task_row(t))
        if self.filtered_tasks:
            table.move_cursor(row=0)

    def _update_status(self):
        c = self.store.counts
        total = c["total"]
        shown = len(self.filtered_tasks)
        search_indicator = f' /🔍"{self.filter_search}"' if self.filter_search else ""
        prio_indicator = f' prio:{self.filter_priority}' if self.filter_priority else ""
        status = self.query_one("#status-line")
        status.update(
            f" tasks {shown}/{total}{search_indicator}{prio_indicator}"
            f"  •  jk:nav a:add e:edit d:del /:search ?:help  "
            f"  •  ⚫{c['todo']} ◔{c['in_progress']} ●{c['done']} ⊘{c['paused']}"
        )

    # ── Actions ──

    def action_cursor_down(self):
        table = self.query_one(DataTable)
        table.action_cursor_down()

    def action_cursor_up(self):
        table = self.query_one(DataTable)
        table.action_cursor_up()

    def _selected_task(self):
        table = self.query_one(DataTable)
        row = table.cursor_row
        if row is not None and row < len(self.filtered_tasks):
            return self.filtered_tasks[row]
        return None

    def action_add_task(self):
        self.app.push_screen(TaskForm(self.store, None))

    def action_edit_task(self):
        task = self._selected_task()
        if task:
            self.app.push_screen(TaskForm(self.store, task))

    def action_delete_task(self):
        task = self._selected_task()
        if task:
            self.app.push_screen(ConfirmDialog(self.store, task))

    def action_toggle_status(self):
        task = self._selected_task()
        if task:
            self.store.toggle_status(task.id)
            self._refresh_table()
            self._update_status()

    def on_data_table_row_selected(self, event: DataTable.RowSelected):
        """Enter key on a row — toggle task status (DataTable consumes 'enter' key)."""
        self.action_toggle_status()

    def action_focus_search(self):
        """Push find screen for search."""
        self.app.push_screen(FindScreen(self.store, self))

    def action_unfocus(self):
        self.filter_search = ""
        self.filter_priority = None
        self._refresh_table()
        self._update_status()

    def action_switch_tasks(self):
        self.app.switch_to_tasks()

    def action_switch_dashboard(self):
        self.app.switch_to_dashboard()

    def action_switch_logs(self):
        self.app.switch_to_logs()

    def action_quit(self):
        self.app.exit()

    def action_show_help(self):
        self.app.push_screen(HelpScreen())

# ═══════════════════════════════════════════════════════════════════════════════
# Dashboard Screen
# ═══════════════════════════════════════════════════════════════════════════════

class DashboardScreen(Screen):
    BINDINGS = [
        Binding("1", "switch_tasks", "Tasks", show=False),
        Binding("2", "switch_dashboard", "Dash", show=False),
        Binding("3", "switch_logs", "Logs", show=False),
        Binding("q", "quit", "Quit", show=False),
        Binding("/", "focus_search", "Search", show=False),
    ]

    def __init__(self, store: TaskStore):
        super().__init__()
        self.store = store

    def compose(self) -> ComposeResult:
        with Horizontal(classes="stats-grid"):
            for label, key, card_class, color in [
                ("Total", "total", "stat-card-total", "#e4e4e7"),
                ("Todo", "todo", "stat-card-todo", "#a1a1aa"),
                ("Doing", "in_progress", "stat-card-doing", "#fbbf24"),
                ("Done", "done", "stat-card-done", "#10b981"),
            ]:
                with Vertical(classes=card_class):
                    yield Static(label.upper(), classes="stat-label")
                    yield Static(f"[bold {color}]{self.store.counts[key]}[/]", classes="stat-value")

        # Priority chart
        with Vertical(classes="dash-section"):
            yield Static("PRIORITY DISTRIBUTION", classes="dash-title")
            yield PriorityChart(self.store)

        # Completion + Groups
        with Horizontal():
            with Vertical(classes="dash-section"):
                yield Static("COMPLETION", classes="dash-title")
                yield CompletionGauge(self.store)
            with Vertical(classes="dash-section"):
                yield Static("GROUPS", classes="dash-title")
                yield GroupsChart(self.store)

        # Recent activity
        with Vertical(classes="dash-section"):
            yield Static("RECENT ACTIVITY", classes="dash-title")
            yield RecentLog(self.store)

    def on_mount(self):
        pass  # fresh compose on each switch — no timer needed

    def action_switch_tasks(self):
        self.app.switch_to_tasks()

    def action_switch_dashboard(self):
        pass  # already here

    def action_switch_logs(self):
        self.app.switch_to_logs()

    def action_quit(self):
        self.app.exit()

    def action_focus_search(self):
        self.app.switch_to_tasks()

# ─── Dashboard sub-widgets ────────────────────────────────────────────────────

class PriorityChart(Static):
    def __init__(self, store: TaskStore):
        super().__init__()
        self.store = store

    def on_mount(self):
        self._refresh_chart()

    def _refresh_chart(self):
        c = self.store.counts
        total = c["total"] or 1
        bars = []
        for prio, color, label in [("high", "red", "HIGH"), ("medium", "yellow", "MED"), ("low", "green", "LOW")]:
            count = c[prio]
            pct = count / total * 100
            bar_len = max(1, int(pct / 5))
            bar = "█" * bar_len
            bars.append(f"[bold {color}]{label}: {bar} {count}[/] ({pct:.0f}%)")
        self.update("\n".join(bars))


class CompletionGauge(Static):
    def __init__(self, store: TaskStore):
        super().__init__()
        self.store = store

    def on_mount(self):
        self._refresh_gauge()

    def _refresh_gauge(self):
        rate = self.store.completion_rate
        c = self.store.counts
        bar_len = max(1, int(rate / 4))
        gauge = "█" * bar_len + "░" * (25 - bar_len)
        self.update(
            f"[bold green]{gauge}[/] {rate:.0f}%\n"
            f"[grey50]{c['done']} done of {c['total']} total[/]"
        )


class GroupsChart(Static):
    def __init__(self, store: TaskStore):
        super().__init__()
        self.store = store

    def on_mount(self):
        self._refresh_groups()

    def _refresh_groups(self):
        groups = self.store.group_counts
        if not groups:
            self.update("[grey50]no groups[/]")
            return
        lines = []
        for name, count in groups[:6]:
            bar = "▓" * count
            lines.append(f"[grey62]#{name:<10} {bar} {count}[/]")
        self.update("\n".join(lines))


class RecentLog(Static):
    def __init__(self, store: TaskStore):
        super().__init__()
        self.store = store

    def on_mount(self):
        self._refresh_log()

    def _refresh_log(self):
        logs = self.store.logs[:8]
        if not logs:
            self.update("[grey50]no activity yet[/]")
            return
        lines = []
        level_colors = {"info": "grey50", "success": "green", "warn": "yellow", "error": "red"}
        actions = {
            "TASK_CREATED": "CREATED", "TASK_DELETED": "DELETED",
            "TASK_UPDATED": "UPDATED", "TASK_STATUS_CHANGED": "STATUS",
            "APP_INIT": "INIT", "SYSTEM_ERROR": "ERROR", "STORAGE_WARNING": "WARN",
            "VIEW_CHANGED": "VIEW",
        }
        for log in logs:
            color = level_colors.get(log.level, "grey50")
            action = actions.get(log.action, log.action[:6])
            ago = format_time(log.timestamp)
            lines.append(f"[{color}]{action:<7}[/] {log.message:<45} [grey35]{ago}[/]")
        self.update("\n".join(lines[:6]))


# ═══════════════════════════════════════════════════════════════════════════════
# Log Viewer Screen
# ═══════════════════════════════════════════════════════════════════════════════

class LogScreen(Screen):
    BINDINGS = [
        Binding("1", "switch_tasks", "Tasks", show=False),
        Binding("2", "switch_dashboard", "Dash", show=False),
        Binding("3", "switch_logs", "Logs", show=False),
        Binding("q", "quit", "Quit", show=False),
        Binding("escape", "switch_tasks", "Back", show=False),
        Binding("d", "clear_logs", "Clear", show=False),
        Binding("c", "clear_logs", "Clear", show=False),
    ]

    def __init__(self, store: TaskStore):
        super().__init__()
        self.store = store

    def compose(self) -> ComposeResult:
        yield RichLog(id="log-view", highlight=True, wrap=True)

    def on_mount(self):
        self._refresh()

    def _refresh(self):
        log_widget = self.query_one(RichLog)
        log_widget.clear()
        level_colors = {"info": "grey50", "success": "green", "warn": "yellow", "error": "red"}
        for entry in self.store.logs[:200]:
            color = level_colors.get(entry.level, "grey50")
            log_widget.write(f"[{color}][{entry.action:<8}][/] {entry.message} [grey35]{format_time(entry.timestamp)}[/]")

    def action_switch_tasks(self):
        self.app.switch_to_tasks()

    def action_switch_dashboard(self):
        self.app.switch_to_dashboard()

    def action_switch_logs(self):
        pass  # already here

    def action_quit(self):
        self.app.exit()

    def action_clear_logs(self):
        self.store.logs.clear()
        self.store._save_logs()
        self._refresh()


# ═══════════════════════════════════════════════════════════════════════════════
# Find/Search Screen
# ═══════════════════════════════════════════════════════════════════════════════

class FindScreen(ModalScreen):
    def __init__(self, store: TaskStore, task_screen: TaskScreen):
        super().__init__()
        self.store = store
        self.task_screen = task_screen

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-box"):
            with Vertical(classes="modal-window"):
                yield Static("SEARCH / FILTER", classes="modal-title")
                yield Input(id="search-input", placeholder="search tasks...")
                yield Label("", id="search-results", classes="modal-hint")
                with Horizontal():
                    yield Button("All", id="btn-all", variant="default")
                    yield Button("High", id="btn-high", variant="error")
                    yield Button("Med", id="btn-med", variant="default")
                    yield Button("Low", id="btn-low", variant="success")

    def on_mount(self):
        self.query_one("#search-input").focus()
        self._update_count()

    def _update_count(self):
        label = self.query_one("#search-results")
        q = self.query_one("#search-input").value
        prio = getattr(self, "_prio_filter", None)
        tasks = self.store.tasks
        if q:
            ql = q.lower()
            tasks = [t for t in tasks if ql in t.title.lower() or ql in t.group.lower()]
        if prio:
            tasks = [t for t in tasks if t.priority == prio]
        label.update(f"{len(tasks)} tasks match")

    def on_input_changed(self, event: Input.Changed):
        self._update_count()

    def on_button_pressed(self, event: Button.Pressed):
        id_map = {"btn-all": None, "btn-high": "high", "btn-med": "medium", "btn-low": "low"}
        self._prio_filter = id_map.get(event.button.id)
        self._update_count()

    def key_enter(self):
        q = self.query_one("#search-input").value
        prio = getattr(self, "_prio_filter", None)
        self.task_screen.filter_search = q
        self.task_screen.filter_priority = prio
        self.task_screen._refresh_table()
        self.task_screen._update_status()
        self.dismiss()

    def key_escape(self):
        self.dismiss()


# ═══════════════════════════════════════════════════════════════════════════════
# Task Form (Modal)
# ═══════════════════════════════════════════════════════════════════════════════

class TaskForm(ModalScreen):
    def __init__(self, store: TaskStore, edit_task=None):
        super().__init__()
        self.store = store
        self.edit_task = edit_task

    def compose(self) -> ComposeResult:
        title = "EDIT TASK" if self.edit_task else "NEW TASK"
        with Vertical(classes="modal-box"):
            with Vertical(classes="modal-window"):
                yield Static(title, classes="modal-title")
                yield Label("Title", classes="modal-hint")
                yield Input(id="form-title", placeholder="task title",
                            value=self.edit_task.title if self.edit_task else "")
                yield Label("Description", classes="modal-hint")
                yield TextArea(id="form-desc", text=self.edit_task.description if self.edit_task else "")
                yield Label("Group", classes="modal-hint")
                yield Input(id="form-group", placeholder="group",
                            value=self.edit_task.group if self.edit_task else "")
                yield Label("Priority: high / medium / low", classes="modal-hint")
                yield Input(id="form-priority",
                            value=self.edit_task.priority if self.edit_task else "medium")
                yield Label("Est. value ($):", classes="modal-hint")
                yield Input(id="form-value", placeholder="e.g. 500",
                            value=f"{self.edit_task.value}" if self.edit_task and self.edit_task.value is not None else "")
                with Horizontal():
                    yield Button("Cancel", id="btn-cancel", variant="default")
                    yield Button("Save", id="btn-save", variant="primary")

    def on_mount(self):
        self.query_one("#form-title").focus()

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-cancel":
            self.dismiss()
        elif event.button.id == "btn-save":
            self._save()

    def key_escape(self):
        self.dismiss()

    def _save(self):
        title = self.query_one("#form-title").value.strip()
        if not title:
            return
        desc = self.query_one("#form-desc").text.strip()
        group = self.query_one("#form-group").value.strip()
        prio = self.query_one("#form-priority").value.strip().lower()
        if prio not in ("high", "medium", "low"):
            prio = "medium"
        val_raw = self.query_one("#form-value").value.strip()
        value: Optional[int] = None
        if val_raw:
            try:
                value = int(val_raw)
            except ValueError:
                pass
        if self.edit_task:
            self.store.update_task(self.edit_task.id, title=title, description=desc,
                                   group=group, priority=prio, value=value)
        else:
            self.store.add_task(title=title, description=desc, group=group, priority=prio, value=value)
        # Refresh parent task screen
        for s in self.app.screen_stack:
            if isinstance(s, TaskScreen):
                s._refresh_table()
                s._update_status()
        self.dismiss()


# ═══════════════════════════════════════════════════════════════════════════════
# Confirm Dialog (Modal)
# ═══════════════════════════════════════════════════════════════════════════════

class ConfirmDialog(ModalScreen):
    def __init__(self, store: TaskStore, task):
        super().__init__()
        self.store = store
        self._ctask = task  # _task conflicts with Textual's asyncio Task attribute

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-box"):
            with Vertical(id="confirm-box"):
                yield Static("DELETE TASK?", classes="modal-title")
                yield Label(f"[bold grey230]  {self._ctask.title}[/]")
                yield Label("", classes="modal-hint")
                with Horizontal():
                    yield Button("Cancel", id="btn-cancel", variant="default")
                    yield Button("Delete", id="btn-delete", variant="error")

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-delete":
            self.store.delete_task(self._ctask.id)
            self._refresh_parent()
            self.dismiss()
        else:
            self.dismiss()

    def key_escape(self):
        self.dismiss()

    def key_enter(self):
        self.store.delete_task(self._ctask.id)
        self._refresh_parent()
        self.dismiss()

    def _refresh_parent(self):
        for s in self.app.screen_stack:
            if isinstance(s, TaskScreen):
                s._refresh_table()
                s._update_status()


# ═══════════════════════════════════════════════════════════════════════════════
# Help Screen
# ═══════════════════════════════════════════════════════════════════════════════

class HelpScreen(ModalScreen):
    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-box"):
            with Vertical(classes="modal-window"):
                yield Static("KEYBINDINGS", classes="modal-title")
                keys = [
                    ("j / k", "Navigate up / down"),
                    ("a", "Add new task"),
                    ("e", "Edit selected task"),
                    ("d", "Delete selected task"),
                    ("Enter", "Toggle task status"),
                    ("/", "Search / filter"),
                    ("1 / 2 / 3", "Switch Tasks / Dash / Logs"),
                    ("Tab", "Next view"),
                    ("Esc", "Cancel / back"),
                    ("q", "Quit"),
                ]
                for key, desc in keys:
                    yield Label(f"  [bold #f59e0b]{key:<8}[/]  {desc}", classes="modal-hint")
                yield Label("")
                yield Label("[grey35]  Press any key to close[/]")

    def on_key(self, event):
        self.dismiss()


# ═══════════════════════════════════════════════════════════════════════════════
# Main App
# ═══════════════════════════════════════════════════════════════════════════════

class PlexoApp(App):
    """plexo — terminal task manager."""
    CSS = ROOT_CSS
    BINDINGS = [
        Binding("tab", "next_view", "Next view", show=True),
        Binding("q", "quit", "Quit", show=False),
        Binding("1", "switch_tasks", "Tasks", show=True),
        Binding("2", "switch_dashboard", "Dash", show=True),
        Binding("3", "switch_logs", "Logs", show=True),
    ]

    TITLE = "plexo"
    SUB_TITLE = "open tasks"

    def __init__(self):
        super().__init__()
        self.store = TaskStore()
        self._current_view = "tasks"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Footer()

    def on_mount(self):
        self.store._write_log("info", "APP_INIT", f"plexo started with {len(self.store.tasks)} tasks")
        # Push initial screen — do NOT compose it in compose(), so screen stack
        # management stays clean (root → screen, not mixed widget tree).
        self.push_screen(TaskScreen(self.store))

    # ── View switching ──

    def switch_to_tasks(self):
        self._switch_view("tasks")

    def switch_to_dashboard(self):
        self._switch_view("dashboard")

    def switch_to_logs(self):
        self._switch_view("logs")

    def _switch_view(self, name: str):
        """Switch to a named view, clearing any screens above root."""
        if self._current_view == name:
            return
        screens = {
            "tasks": TaskScreen(self.store),
            "dashboard": DashboardScreen(self.store),
            "logs": LogScreen(self.store),
        }
        # Pop everything above root — handles leftover modals too
        while len(self.screen_stack) > 1:
            self.pop_screen()
        self.push_screen(screens[name])
        self._current_view = name

    def action_next_view(self):
        order = ["tasks", "dashboard", "logs"]
        idx = order.index(self._current_view)
        next_idx = (idx + 1) % len(order)
        self._switch_view(order[next_idx])

    def action_quit(self):
        self.exit()


def main():
    app = PlexoApp()
    app.run()


if __name__ == "__main__":
    main()
