"""
Web Dashboard for AI Development Pipeline
FastAPI app running on port 8080.

Routes:
  GET  /                         → project cards + worker status (Jinja2)
  GET  /api/status               → JSON snapshot (HTMX polling target)
  GET  /api/status-fragment      → HTML snippet for the live-status bar
  GET  /projects/{name}          → project detail page
  POST /projects/{name}/deploy   → trigger deploy for a project

Access: http://<vm-ip>:8080
"""

import sys
from pathlib import Path

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from agents.master_agent import MasterAgent

app = FastAPI(title="AI Dev Pipeline Dashboard", version="5.0.0")

# Templates directory sits next to this file
TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Singleton MasterAgent (shared with Discord bot when running together)
# When run standalone, this creates a fresh instance that reads from disk.
_master: MasterAgent = MasterAgent()


def get_master() -> MasterAgent:
    return _master


def set_master(master: MasterAgent) -> None:
    """Allow the Discord bot process to inject the shared MasterAgent."""
    global _master
    _master = master


# ==========================================
# ROUTES
# ==========================================


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard — list of all projects + live status bar."""
    master = get_master()
    status = master.get_full_status()
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "projects": status["projects"],
            "workers": status["workers"],
            "active_project": status["active_project"],
        },
    )


@app.get("/api/status")
async def api_status():
    """JSON status snapshot — consumed by HTMX polling and external tools."""
    master = get_master()
    return JSONResponse(master.get_full_status())


@app.get("/api/status-fragment", response_class=HTMLResponse)
async def status_fragment(request: Request):
    """Live-update HTML snippet rendered into the dashboard every 5s."""
    master = get_master()
    status = master.get_full_status()
    workers = status["workers"]
    running = workers.get("running", False)

    queues = workers.get("queues", {})
    total_pending = sum(queues.values())

    states = workers.get("worker_states", {})
    busy_count = sum(1 for s in states.values() if s == "working")

    active = status.get("active_project") or "none"

    color = "text-green-400" if running else "text-gray-500"
    worker_icon = "⚙️" if running else "⏹"

    queue_badges = " ".join(
        f'<span class="bg-gray-700 text-gray-300 text-xs px-2 py-0.5 rounded">'
        f"{agent}: {cnt}"
        f"</span>"
        for agent, cnt in queues.items()
    )

    html = f"""
<div class="bg-gray-800 border border-gray-700 rounded-xl px-5 py-3
            flex flex-wrap items-center gap-4 text-sm mb-6">
    <div>
        <span class="text-gray-500">Workers</span>
        <span class="{color} ml-2">{worker_icon} {'Running' if running else 'Stopped'}</span>
        {f'<span class="text-gray-400 ml-2">({busy_count} busy)</span>' if running else ''}
    </div>
    <div>
        <span class="text-gray-500">Pending tasks</span>
        <span class="text-indigo-400 ml-2">{total_pending}</span>
    </div>
    <div class="flex flex-wrap gap-1">{queue_badges}</div>
    <div class="ml-auto">
        <span class="text-gray-500">Active project</span>
        <a href="/projects/{active}" class="text-indigo-400 hover:underline ml-2 font-mono text-xs">{active}</a>
    </div>
</div>
"""
    return HTMLResponse(content=html)


@app.get("/projects/{name}", response_class=HTMLResponse)
async def project_detail(request: Request, name: str):
    """Project detail page."""
    master = get_master()
    status = master.get_full_status()
    projects = status["projects"]

    if name not in projects:
        raise HTTPException(status_code=404, detail=f"Project '{name}' not found")

    project = projects[name]
    project["name"] = name  # ensure name is available in template

    return templates.TemplateResponse(
        "project.html",
        {"request": request, "project": project},
    )


@app.post("/projects/{name}/deploy")
async def deploy_project_route(name: str, redeploy: str = Form(default="")):
    """Trigger (re-)deploy for a project."""
    master = get_master()
    status = master.get_full_status()

    if name not in status["projects"]:
        raise HTTPException(status_code=404, detail=f"Project '{name}' not found")

    # Switch to that project temporarily for the deploy call
    original_active = master._active_project_name
    master._active_project_name = name

    action = "redeploy" if redeploy else ""
    await master.handle_deploy_project(action)

    # Restore active project
    master._active_project_name = original_active

    return RedirectResponse(url=f"/projects/{name}", status_code=303)
