# AI Development Pipeline — Roadmap

**Last Updated**: February 19, 2026
**Current Status**: Phases 1–7 Complete ✅

---

## Summary of Upcoming Phases

| Phase | Name | Status |
|-------|------|--------|
| 8 | Production Hardening | Planned |
| 9 | Full Management Dashboard | Planned |
| 10 | MCP Server Integrations | Planned |
| 11 | New Specialized Agents | Planned |
| 12 | Team & Scale Features | Planned |

---

## Phase 8: Production Hardening

The system works end-to-end but has several rough edges that will cause failures in real use. This phase makes it reliable before adding new features.

### 8.1 Fix `requirements.txt`
Currently missing packages installed manually:
```
pyyaml
fastapi
uvicorn
httpx
jinja2
python-multipart
```
**Fix**: Add all to `requirements.txt`. Verify `pip install -r requirements.txt` works from a clean venv.

### 8.2 Project Name Sanitization
Cloudflare DNS subdomains cannot contain underscores. Auto-generated project names like `project_20260219_165036` will fail DNS routing.

**Fix in `agents/deployer.py`**:
```python
def _sanitize_subdomain(name: str) -> str:
    """Convert project_20260219 → project-20260219"""
    return name.replace("_", "-").lower()[:63]  # DNS label max 63 chars
```
Apply in all Cloudflare-facing calls. Store sanitized name in project metadata as `subdomain`.

### 8.3 Dockerfile Validation
The DevOps agent generates a Dockerfile via Claude Code but never validates it before deployment. A malformed Dockerfile causes a silent `docker build` failure.

**Fix**: After DevOps agent writes Dockerfile, run:
```bash
docker build --no-cache -t {name}-validate {path} 2>&1
```
If it fails, call Claude Code with the error output to fix it. Retry up to 3 times before marking the task as failed.

Add to `agents/devops_agent.py`:
```python
async def validate_dockerfile(self, project_path: str) -> bool:
    """Build and immediately remove the image to validate Dockerfile."""
```

### 8.4 Container Health Checks
After `docker run`, the deployer should wait a few seconds and verify the container is still running (not crashed on startup).

**Fix in `agents/deployer.py`**:
```python
async def _verify_container_running(self, container_name: str) -> bool:
    """Poll `docker inspect` for up to 10s to confirm container is Up."""
```

### 8.5 Graceful Worker Shutdown
Currently `!workers stop` sends a cancellation signal that can interrupt a task mid-execution, leaving a branch in a dirty state.

**Fix in `agents/worker_daemon.py`**:
- Add a `_shutdown_requested` flag.
- Workers check the flag after completing each task and exit cleanly at the end of the current task (not mid-task).
- Estimated extra delay: up to 2 minutes (one task completion cycle).

### 8.6 Better Error Reporting
When a worker fails a task, the Discord notification says "Task failed" with minimal context. Agents should include the first 500 characters of the Claude Code output in the GitHub comment.

**Fix**: Pass `stdout` from `call_claude_code()` back to the worker, include in `fail_task()` GitHub comment.

### 8.7 Systemd Auto-Start Units
Already documented in `RUNNING_THE_SYSTEM.md`. Phase 8 automates creation via a setup script:

```bash
scripts/install_services.sh
```

This script creates and enables `aip-discord.service` and `aip-dashboard.service` automatically.

**Files to create/modify**:
- `agents/deployer.py` — subdomain sanitization, health checks
- `agents/devops_agent.py` — Dockerfile validation
- `agents/worker_daemon.py` — graceful shutdown
- `requirements.txt` — add missing packages
- `scripts/install_services.sh` — new

---

## Phase 9: Full Management Dashboard

The Phase 7 dashboard is read-only. Phase 9 turns it into a full control interface — the user should rarely need Discord for anything except typing `!new`.

### 9.1 Project Creation from Web UI
A form on the dashboard that takes a project description and triggers the same flow as `!new`.

**New route**: `POST /projects/new`
**New template section**: `dashboard.html` — collapsible "New Project" form with textarea + submit button
**Backend**: calls `master.handle_new_project(description)` and streams progress via SSE

### 9.2 Live Log Streaming
Each agent task currently logs to `logs/claude_code_YYYYMMDD.log`. The dashboard should stream these in real time.

**Implementation**:
- Use Server-Sent Events (SSE): `GET /projects/{name}/logs/stream`
- FastAPI `StreamingResponse` with `EventSourceResponse` (via `sse-starlette` package)
- Frontend: `<div hx-ext="sse" sse-connect="/projects/{name}/logs/stream">` in project.html
- Log tail: tail the latest log file, emit each new line as an SSE event

### 9.3 Issue Management Interface
View and manage GitHub issues for the active project without leaving the browser.

**New route**: `GET /projects/{name}/issues` — fetches issues from GitHub API and renders table
**New route**: `POST /projects/{name}/issues/{number}/queue` — manually enqueue an issue to a specific agent type

**Template additions** in `project.html`:
- Issues table: number, title, labels, status, assigned agent
- "Queue to Agent" dropdown + button per issue
- Filter by label (backend / frontend / database / etc.)

### 9.4 PR Review Interface
View open pull requests, see the diff summary (from GitHub), and approve/reject from the dashboard.

**New route**: `GET /projects/{name}/prs` — lists open PRs
**New route**: `POST /projects/{name}/prs/{number}/merge` — triggers QA agent merge
**New route**: `POST /projects/{name}/prs/{number}/close` — closes PR

### 9.5 Worker Control Panel
Start, stop, and inspect workers per agent type from the dashboard.

**New route**: `POST /workers/{action}` (start / stop)
**New route**: `GET /workers/status` — JSON: per-agent state, current task, queue depth
**New template section**: worker grid with per-agent cards showing state + current task title

### 9.6 Task Queue Inspector
See what's in each Redis queue, reorder priorities, or remove stuck tasks.

**New route**: `GET /api/queues` — JSON dump of all queue contents
**New route**: `DELETE /api/queues/{agent_type}/{task_key}` — remove a task
**New route**: `PATCH /api/queues/{agent_type}/{task_key}/priority` — change priority score

### 9.7 CI Run History
Show the last N GitHub Actions runs for a project with status and a link to view logs.

**New route**: `GET /projects/{name}/ci` — calls `github_client.list_workflow_runs()`, renders timeline
**Template**: collapsible accordion, each run shows: status icon, trigger, commit SHA, duration

### 9.8 Terminal Access (Optional / Advanced)
An in-browser terminal (via `xterm.js` + WebSocket) that connects to the VM shell, scoped to the project directory.

This is the most complex addition — defer to a later iteration if needed.

**Files to create/modify**:
- `api/dashboard.py` — 8+ new routes
- `api/templates/dashboard.html` — project creation form
- `api/templates/project.html` — issues, PRs, CI, logs tabs
- `api/templates/workers.html` — new template
- `requirements.txt` — add `sse-starlette`

---

## Phase 10: MCP Server Integrations

MCP (Model Context Protocol) servers extend what Claude Code can do by giving it access to external APIs via standardized tools. The pipeline can use MCP servers to dramatically improve each agent's capabilities.

See `MCP_INTEGRATION_PLAN.md` for full implementation details.

### 10.1 Playwright MCP — Browser Testing
**What it enables**: QA agent runs real end-to-end browser tests against deployed apps (not just unit tests).

After a deploy, the QA agent instructs Claude Code (with Playwright MCP) to:
1. Navigate to `https://projectname.devbot.site`
2. Fill out forms, click buttons, verify UI state
3. Screenshot key pages
4. Report failures back to GitHub issues

### 10.2 Supabase MCP — Managed Database & Auth
**What it enables**: Instead of SQLite, generated apps use Supabase (hosted PostgreSQL + Auth + Storage).

The Database agent uses Supabase MCP to:
1. Create a Supabase project for each pipeline project
2. Apply the generated schema via SQL migrations
3. Set up Row Level Security policies
4. Generate connection strings for the app

### 10.3 Sentry MCP — Error Monitoring
**What it enables**: Deployed apps automatically report runtime errors to Sentry. PipelineMonitor reads Sentry instead of (or in addition to) CI logs.

New flow:
- DevOps agent injects Sentry DSN into the app's environment
- `PipelineMonitor` calls Sentry MCP to check for new errors every 5 minutes
- Auto-creates a GitHub issue for each new Sentry error
- Queues a `fix_bug` task for the backend/frontend worker

### 10.4 GitHub MCP — Deeper Integration
**What it enables**: More natural language-driven GitHub operations (PR creation, issue commenting, code review) without maintaining our own `github_client.py` wrapper.

Gradual migration: keep `github_client.py` for programmatic operations, use GitHub MCP inside Claude Code prompts for nuanced tasks like "review this PR for security issues."

### 10.5 Vercel MCP — Frontend Deployment (Alternative)
**What it enables**: For React/Next.js projects, deploy to Vercel instead of Docker + Cloudflare Tunnel. Vercel handles CDN, HTTPS, and preview deploys automatically.

The Deployer detects if a project is a pure frontend (no Dockerfile, has `package.json` with Next.js/Vite) and routes to Vercel deployment instead.

---

## Phase 11: New Specialized Agents

### 11.1 Security Agent
Reviews every PR for security vulnerabilities before the QA agent approves it.

**Trigger**: Queued automatically after backend/frontend worker opens a PR (before QA review).
**Claude Code prompt focus**:
- OWASP Top 10 check
- SQL injection / XSS in templates
- Hardcoded secrets / environment variable leakage
- Dependency audit (`pip audit` / `npm audit`)
- Authentication and authorization logic review

**Outputs**: GitHub PR comment with severity-rated findings. Blocks merge if HIGH severity found.

**New file**: `agents/security_agent.py`
**New queue**: `queue:agent:security`
**New worker loop** in `worker_daemon.py`

### 11.2 UX/Design Agent
Generates design specifications and reviews UI implementations against them.

**Capabilities**:
- Given a PRD, produces a component hierarchy and Tailwind class suggestions
- Reviews frontend PRs: checks for accessibility (alt text, ARIA labels, keyboard nav), responsiveness, and visual consistency
- Generates placeholder wireframe ASCII art embedded in GitHub issue comments

**New file**: `agents/ux_agent.py`

### 11.3 Documentation Agent
Keeps documentation in sync with code automatically.

**Trigger**: Runs after every merged PR.
**Actions**:
- Updates `README.md` with any new endpoints, environment variables, or installation steps
- Regenerates API docs from docstrings (`pdoc` or `mkdocs`)
- Updates `CHANGELOG.md` with the merged PR summary
- Commits directly to the `dev` branch

**New file**: `agents/docs_agent.py`

### 11.4 Performance Agent
Runs load tests and identifies bottlenecks after deploy.

**Trigger**: Automatically after successful deploy (or manually via `!perf test`).
**Tools**:
- `locust` for HTTP load testing
- `pytest-benchmark` for unit-level benchmarks
- Parses results and creates GitHub issues for endpoints that exceed a latency threshold

**New file**: `agents/performance_agent.py`

---

## Phase 12: Team & Scale Features

### 12.1 Multi-User Support
Currently a single Discord user owns all projects. Phase 12 adds user context to all operations.

**Changes**:
- Discord `ctx.author.id` passed to all `master.*` methods
- Projects tagged with `owner_id`
- `!projects` only shows your own projects (or all with an `--all` flag for admins)
- Dashboard adds simple OAuth (Discord OAuth2) to identify the logged-in user

### 12.2 Cost Tracking
Track Claude Code token usage per project to understand cost.

**Implementation**:
- `call_claude_code()` in `BaseAgent` captures stdout token usage metrics
- Stored per-project in `.project_metadata.json`
- Dashboard shows "Estimated cost" card per project (based on Claude Pro pricing)
- `!status` includes a cost line

### 12.3 Project Templates
Instead of starting every project from scratch, maintain a library of templates.

**Template types**: REST API (FastAPI), React dashboard, Discord bot, CLI tool, data pipeline
**How it works**: `!new --template rest-api Build a URL shortener` pre-seeds the PRD and skips the schema design step.

**New file**: `agents/template_library.py`
**New directory**: `templates/` with starter PRDs and Dockerfiles

### 12.4 Plugin System
Allow adding custom agents without modifying core files.

**Design**:
- Agents in `agents/plugins/` are auto-discovered at startup
- Each plugin defines: agent type name, `execute_task()` method, GitHub issue label patterns it handles
- `agent_factory.py` loads plugins dynamically

---

## Implementation Priority

Focus on phases in order. Don't start Phase 9 until Phase 8 is solid.

```
Phase 8 (hardening) → Phase 9 (dashboard) → Phase 10 (MCP) → Phase 11 (agents) → Phase 12 (scale)
```

Within each phase, prioritize items that fix real pain points (e.g., 8.1 requirements.txt, 8.2 name sanitization) before nice-to-haves (e.g., 8.7 systemd script).
