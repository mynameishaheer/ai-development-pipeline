# AI Development Pipeline — System Concept

**Last Updated**: February 19, 2026

---

## What This Is

An autonomous AI development team running on a single VM. You describe a project idea in Discord (or the web dashboard), and the pipeline takes it from concept to a running, publicly accessible web app — with zero human intervention after the initial `!new` command.

The system is built on Claude Code CLI (subprocess calls) which means all code generation runs against your Claude Pro subscription with no additional API costs.

---

## Core Idea

Real software teams have specialized roles that work in parallel: product managers write requirements, engineers implement features, QA validates the work, DevOps deploys it, and a manager coordinates everyone. This pipeline recreates that structure with AI agents.

Each agent has a single job. The MasterAgent coordinates them. Redis queues decouple task assignment from execution. GitHub is the shared workspace (issues, branches, PRs, CI).

---

## Agent Roles

### MasterAgent (`agents/master_agent.py`)
The single orchestrator. Every Discord command and dashboard action goes through it.

Responsibilities:
- Manages `_projects` dict — knows about all projects, which is active
- Routes user requests to the right sub-agent
- Holds one `PipelineMonitor` per project (watches CI)
- Controls the `AgentWorkerDaemon` (start/stop workers)
- Sends proactive Discord notifications when things happen autonomously
- Exposes a `get_full_status()` snapshot for the web dashboard

### Product Manager Agent (`agents/product_manager_agent.py`)
Converts a plain-English description into a structured PRD.

Output: a `docs/PRD.md` file (40–50KB) with features, acceptance criteria, technical constraints, and issue breakdown.

### Project Manager Agent (`agents/project_manager_agent.py`)
Turns the PRD into a GitHub repository with everything set up for development.

Output: GitHub repo with dev branch, labels (backend/frontend/database/devops/qa/bug/enhancement), branch protection, and 15–30 issues.

### Backend Agent (`agents/backend_agent.py`)
Implements server-side features via Claude Code.

Task types: `implement_feature`, `fix_bug`, `write_tests`, `refactor_code`

Each task: fetch issue → create branch → Claude Code makes changes → validate (pytest) → commit → open PR

### Frontend Agent (`agents/frontend_agent.py`)
Implements client-side features and UI.

Task types: `implement_feature`, `fix_bug`, `improve_ui`

Specialization: React/Tailwind focused prompts, accessibility checks, responsive design.

### Database Agent (`agents/database_agent.py`)
Designs the data model and manages migrations.

Output: schema files, SQLAlchemy models, Alembic migration scripts — all in the project directory.

### DevOps Agent (`agents/devops_agent.py`)
Sets up deployment infrastructure.

Output: `Dockerfile`, `.github/workflows/ci.yml` (runs tests on push), environment configuration.

### QA Agent (`agents/qa_agent.py`)
Reviews every PR opened by backend/frontend workers.

Process: fetch PR diff → Claude Code reviews for correctness, test coverage, and code quality → approve + merge or request changes → close linked issue → auto-enqueue another QA review if needed.

### Assignment Manager (`agents/assignment_manager.py`)
The Redis interface. Not an "agent" but the queue system that connects everything.

- Classifies each GitHub issue by labels/title keywords → assigns to the right agent queue
- Queue key: `queue:agent:{agent_type}` (sorted set, lower score = higher priority)
- Task metadata: `task:{repo}:{issue}` (hash with status, timestamps, agent type)

### AgentWorkerDaemon (`agents/worker_daemon.py`)
Runs one asyncio loop per agent type. Each loop polls Redis every 10 seconds.

Process per task: claim → `agent.execute_task()` → on success: GitHub comment + "in-review" label + enqueue QA → on failure: GitHub comment + "needs-attention" label.

After every task: checks if all queues are empty and all workers idle → if so, triggers `_auto_deploy()`.

### PipelineMonitor (`agents/pipeline_monitor.py`)
Watches GitHub Actions CI every 30 seconds for the active project's repo.

On failed run: downloads logs (ZIP) → Claude Code auto-fixes → pushes fix → notifies Discord.
Also detects stalled workers (task running > `WORKER_STALL_MINUTES`) and alerts via Discord.

### Deployer (`agents/deployer.py`)
Turns a project directory into a live URL.

Process:
1. `docker build` the image
2. Find a free port (tracked in `~/.ai-dev-pipeline/port_allocations.json`)
3. `docker run -d` the container
4. Update `~/.cloudflared/config.yml` with new ingress rule
5. `cloudflared tunnel route dns` to create the DNS record
6. `sudo systemctl reload cloudflared`
7. Return `https://{name}.devbot.site`

---

## Data Flow

```
User: !new Build a URL shortener

1.  discord_bot → master.handle_new_project()
2.  pm_agent.create_prd_from_scratch() → PRD.md (40–50KB)
3.  project_mgr.setup_complete_project() → GitHub repo + 15–30 issues
4.  Master saves .project_metadata.json
5.  Discord: "✅ Project created — 23 issues"

User: !run pipeline

6.  master.handle_run_full_pipeline()
    a. database_agent.setup_database_for_project() → schema files
    b. devops_agent.setup_cicd_pipeline() → Dockerfile + CI workflow
    c. assignment_manager.assign_all_issues() → all issues queued to Redis
    d. github_pusher.push_project_to_github() → files committed and pushed
    e. PipelineMonitor started → CI being watched
    f. deployer.deploy_project() → Docker + Cloudflare
7.  Discord: "🎉 Pipeline complete. 🌐 https://project-xxx.devbot.site"

User: !workers start

8.  AgentWorkerDaemon started (background asyncio tasks)
9.  Workers poll Redis every 10s
10. backend worker: claim issue → Claude Code implements → tests pass → PR opened → QA enqueued
11. qa worker: claim PR review → approve + merge → issue closed
12. When all queues drain → _auto_deploy() → Discord "All tasks complete, redeployed"
```

---

## Infrastructure

| Component | Technology | Why |
|-----------|-----------|-----|
| Code generation | Claude Code CLI (subprocess) | No per-token cost — uses Claude Pro subscription |
| Task queues | Redis sorted sets | Priority ordering built-in, easy to inspect |
| Deployment | Docker + Cloudflare Tunnel | Free, secure, HTTPS, no firewall rules |
| Dashboard | FastAPI + Jinja2 + HTMX | No build step, no npm, works with Python |
| GitHub integration | REST API (`github_client.py`) | Issues, PRs, branches, CI runs |
| CI/CD | GitHub Actions | Runs tests on every push |
| Persistent state | JSON files on disk | `.project_metadata.json` per project |

---

## What's Planned Next

The system is complete through Phase 7. The next phases (documented in `ROADMAP.md`):

- **Phase 8** — Production hardening (Dockerfile validation, name sanitization, graceful shutdown, `requirements.txt` fix)
- **Phase 9** — Full management dashboard (project creation from UI, live logs, issue management, PR review, worker controls)
- **Phase 10** — MCP server integrations (Playwright browser testing, Supabase managed DB, Sentry error monitoring, Vercel frontend deploy)
- **Phase 11** — New agents: Security Agent (OWASP scanning), UX/Design Agent, Documentation Agent, Performance Agent
- **Phase 12** — Team features: multi-user support, cost tracking, project templates, plugin system

---

## Design Principles

- **Zero intervention** — the pipeline should complete a full project without the user doing anything after `!new`
- **No API cost** — use Claude Code CLI (Claude Pro subscription) not the Anthropic API, so code generation is free
- **Observable** — everything is visible in Discord, the web dashboard, GitHub, and logs
- **Resilient** — CI failures are auto-fixed, worker failures create "needs-attention" labels so nothing is silently dropped
- **Composable** — each agent has a single job and communicates through GitHub + Redis, not direct function calls
