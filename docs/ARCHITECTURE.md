# AI Development Pipeline — Architecture

**Last Updated**: February 19, 2026

---

## High-Level Flow

```
User (Discord / Dashboard)
         │
         ▼
   MasterAgent          ← orchestrator, multi-project state
         │
   ┌─────┼─────────────────────────────────────────┐
   │     │                                         │
   ▼     ▼                                         ▼
 PM    ProjectMgr     AssignmentManager      PipelineMonitor
Agent  Agent          (Redis queues)          (CI watcher)
   │     │                  │
   │     │         ┌────────┴──────────┐
   │     │         ▼                   ▼
   │     │   WorkerDaemon         GitHub API
   │     │   ├─ backend worker
   │     │   ├─ frontend worker
   │     │   ├─ database worker
   │     │   ├─ devops worker
   │     │   └─ qa worker
   │     │         │
   │     │         ▼
   │     │    Deployer
   │     │    (Docker + Cloudflare Tunnel)
   │     │         │
   │     │         ▼
   │     │  https://name.devbot.site
   │     │
   └─────┘
    GitHub: repo, issues, branches, PRs, CI
```

---

## Component Roles

### MasterAgent (`agents/master_agent.py`)
The single orchestrator. Holds:
- `_projects: Dict[str, Dict]` — all known projects
- `_active_project_name` — which project is currently focused
- `_monitors: Dict[str, PipelineMonitor]` — one monitor per project
- `_worker_daemon` — the running AgentWorkerDaemon (if started)
- `_notify_channel` — Discord channel for proactive messages

Key public methods:
```
handle_new_project()         → PRD + GitHub setup
handle_run_full_pipeline()   → DB + CI/CD + issue assignment + deploy
handle_deploy_project()      → Docker + Cloudflare
handle_projects_list()       → list all _projects
handle_switch_project(name)  → switch active + restart monitor
get_full_status()            → snapshot for web dashboard
start_workers() / stop_workers()
```

### AgentWorkerDaemon (`agents/worker_daemon.py`)
Runs one asyncio loop per agent type. Each loop:
1. `claim_next_task()` from Redis sorted set
2. `agent.execute_task(task)` — delegates to correct agent
3. On success: `complete_task()` + GitHub comment + "in-review" label
4. On failure: `fail_task()` + GitHub comment + "needs-attention" label
5. If backend/frontend produced a PR → enqueue QA review task
6. After every task: `_check_and_trigger_deploy()` — if ALL queues empty
   and ALL workers idle → auto-deploy the active project

### AssignmentManager (`agents/assignment_manager.py`)
Redis interface for the task queue:
- Queue key: `queue:agent:{agent_type}` (sorted set, score = priority)
- Metadata key: `task:{repo}:{issue}` (hash)
- `assign_issue(issue)` → classifies by labels/title keywords → queues
- `claim_next_task(type)` → ZPOPMIN → returns task dict
- `complete_task()` / `fail_task()` → update metadata

### PipelineMonitor (`agents/pipeline_monitor.py`)
Polls GitHub Actions every 30 seconds for the active project's repo:
- On failed run → downloads logs via ZIP → Claude Code auto-fixes → push
- Detects stalled workers (task running > `WORKER_STALL_MINUTES`)
- Sends Discord notifications for CI failures and fixes

### Deployer (`agents/deployer.py`)
```
deploy_project(path, name) →
  1. docker build -t {name} {path}
  2. find free port (port_allocations.json)
  3. docker run -d -p {port}:8000 --restart unless-stopped {name}
  4. update ~/.cloudflared/config.yml (insert ingress entry)
  5. cloudflared tunnel route dns devbot-pipeline {name}.devbot.site
  6. sudo systemctl reload cloudflared
  7. return { success, url, port }
```

### Web Dashboard (`api/dashboard.py`)
FastAPI + Jinja2 + HTMX. No JS framework needed:
- `GET /` — project cards grid + live status bar (5s HTMX poll)
- `GET /api/status` — JSON snapshot
- `GET /api/status-fragment` — HTML snippet for live bar
- `GET /projects/{name}` — detail page
- `POST /projects/{name}/deploy` — trigger deploy

---

## Data Flow: New Project End-to-End

```
User: !new Build a URL shortener

1. discord_bot.py → master.handle_new_project(msg)
2. pm_agent.create_prd_from_scratch() → writes PRD to disk (40-50KB)
3. project_mgr.setup_complete_project() →
     GitHub API: create repo, dev branch, labels, protection
     GitHub API: create 15-30 issues from PRD
4. master saves project metadata to disk (.project_metadata.json)
5. Discord reply: "✅ Project created, 23 issues"

User: !run pipeline

6. master.run_full_pipeline() →
   a. database_agent.setup_database_for_project() → writes schema files
   b. devops_agent.setup_cicd_pipeline() → writes Dockerfile, .github/workflows
   c. assignment_manager.assign_all_issues() → classifies + queues each issue
   d. QA config saved (.qa_config.json)
7. github_pusher.push_project_to_github() → pushes all files
8. PipelineMonitor started → watching repo CI
9. deployer.deploy_project() → Docker + Cloudflare
10. Discord reply: "🎉 Pipeline complete. 🌐 https://project-xxx.devbot.site"

User: !workers start

11. AgentWorkerDaemon started (background task)
12. Workers poll Redis queues every 10s
13. backend worker claims issue → execute_task(implement_feature) →
     Claude Code implements → tests pass → PR opened → QA enqueued
14. qa worker claims PR review → approves → merges → issue closed
15. When ALL queues drain:
     _check_and_trigger_deploy() → _auto_deploy() → Discord notify
```

---

## Redis Schema

```
# Task queue (sorted set — lower score = higher priority)
queue:agent:backend     → [(task_json, priority_score), ...]
queue:agent:frontend    → [...]
queue:agent:database    → [...]
queue:agent:devops      → [...]
queue:agent:qa          → [...]

# Task metadata (hash)
task:{repo_name}:{issue_number} → {
    status: "queued|in_progress|completed|failed",
    agent_type: "backend",
    assigned_at: "ISO datetime",
    ...
}
```

---

## Disk Layout (Runtime)

```
~/.ai-dev-pipeline/
└── port_allocations.json    # { "project-name": 3001, ... }

~/.cloudflared/
├── cert.pem                 # Cloudflare auth cert
├── {TUNNEL_ID}.json         # Tunnel credentials
└── config.yml               # Ingress rules (auto-updated by deployer)

~/ai-dev-pipeline/
├── projects/
│   └── project_20260219_165036/
│       ├── .project_metadata.json   # MasterAgent state
│       ├── .qa_config.json          # QA settings
│       ├── docs/PRD.md              # Generated PRD
│       ├── src/                     # Generated code
│       ├── tests/                   # Generated tests
│       └── ...
├── memory/
│   └── vector_store/        # ChromaDB (conversation memory)
└── logs/
    └── claude_code_YYYYMMDD.log
```

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Claude Code CLI (subprocess) instead of API | No per-token cost for code generation — uses Claude Pro subscription |
| Redis sorted sets for queues | Priority ordering built-in; easy to inspect with redis-cli |
| Cloudflare Tunnel instead of open ports | Free, secure, no firewall rules, automatic HTTPS |
| HTMX instead of React for dashboard | No build step, no npm, minimal JS — works with Jinja2 |
| One worker loop per agent type | Simple to reason about; no race conditions on task claim |
| Per-project PipelineMonitor | Each project can be monitored independently when switching |
| `current_project` as property over dict | Backwards compatibility while enabling multi-project |
