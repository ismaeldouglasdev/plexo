# Plexo — Centralized Task Manager

Plexo is a lightweight, self-hosted task manager with **three interfaces**: a modern **Web UI** (React + Vite), a **Terminal UI** (Textual), and a **REST API** server.

> Your tasks live in `~/.plexo/tasks.json` — plain JSON, fully local, no database required.

---

## Screenshots

> _Screenshots coming soon — replace these placeholders after running the project._

| Web UI | Terminal UI |
|--------|-------------|
| ![Web UI screenshot](screenshots/web-ui.png) | ![TUI screenshot](screenshots/tui.png) |

---

## Features

- **Web UI** — Dashboard with task cards, filters, priority badges, stats
- **Terminal UI** — Full-featured TUI with keyboard shortcuts (`a` add, `e` edit, `d` delete, `/` search)
- **REST API** — CRUD endpoints for tasks + activity log
- **Real-time** — Web UI polls the API every 10s for live updates
- **Priority system** — High / Medium / Low with visual badges
- **Groups** — Organize tasks by project or context
- **Activity log** — Every creation, update, and completion is tracked
- **Server-side logging** — All operations logged to `~/.plexo/logs.json`

---

## Quick Start

```bash
# 1. Start the API server
./serve.sh 8082

# 2. Open the Web UI
xdg-open http://localhost:8082

# 3. Or launch the Terminal UI
./singularity
```

---

## Architecture

```
task-manager/
├── server.py          # Python API server (http.server)
├── serve.sh           # Server launcher
├── singularity        # TUI launcher script
├── src/               # React + Vite frontend
│   ├── components/    # UI components (shadcn/ui + Radix)
│   ├── hooks/         # Custom React hooks
│   ├── data/          # Data layer
│   └── lib/           # Utilities
├── tui/               # Terminal UI (Python Textual)
│   └── app.py         # TUI application
├── dist/              # Built frontend (served by server.py)
└── public/            # Static assets
```

### Data Flow

```
User ──► Web UI  ──┐
         TUI    ──┤──► API (server.py:8082) ──► ~/.plexo/tasks.json
         curl   ──┘                            ~/.plexo/logs.json
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/tasks` | List all tasks |
| `POST` | `/api/tasks/add` | Create a task |
| `POST` | `/api/tasks/update-status` | Change task status |
| `POST` | `/api/tasks/delete` | Delete a task |
| `GET` | `/api/logs` | Activity history |
| `GET` | `/api/stats` | Task counts (total, todo, done, etc.) |

All data is stored in plain JSON at `~/.plexo/` — no external dependencies.

---

## Development

```bash
# Install dependencies
pnpm install

# Start Vite dev server
pnpm dev

# Build frontend
pnpm build

# Rebuild and restart server
pnpm build && ./serve.sh 8082
```

Frontend is built with **React 19**, **TypeScript**, **Vite**, **Tailwind CSS**, and **shadcn/ui**. The TUI uses **Python Textual**.

---

## Keyboard Shortcuts (TUI)

| Key | Action |
|-----|--------|
| `a` | Add task |
| `e` | Edit task |
| `d` | Delete task |
| `Enter` | Toggle status (todo ↔ done) |
| `/` | Search |
| `1` | Tasks view |
| `2` | Dashboard view |
| `3` | Logs view |
| `q` | Quit |

---

## License

MIT
