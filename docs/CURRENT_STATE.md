# AI Development Pipeline — Current State

**Last Updated**: February 19, 2026
**Active Phase**: Phases 1–7 COMPLETE ✅ | Phase 8 planning in progress
**Test Suite**: 266/266 passing ✅

---

## What This System Does

You describe an idea in Discord (or the web dashboard). The pipeline autonomously:

1. Writes a full PRD
2. Creates a GitHub repository with issues, labels, branch protection
3. Designs a database schema
4. Sets up CI/CD and Docker
5. Assigns issues to specialized agents (backend, frontend, QA, etc.)
6. Worker agents implement each issue, write tests, validate, and open PRs
7. QA agent reviews PRs, merges approved ones, closes issues
8. Monitors CI — auto-fixes failing runs via Claude Code
9. When all tasks complete, Docker-builds the app and deploys it
10. Exposes the app at `https://projectname.devbot.site` via Cloudflare Tunnel

Zero human intervention after the initial `!new` command.

---

## Completed Phases

| Phase | What Was Built | Tests |
|-------|---------------|-------|
| 1 | Foundation: error handling, logging, Redis pub/sub, base agent | — |
| 2 | All core agents: PM, Project Manager, Backend, Frontend, Database, DevOps, QA | 100% |
| 3 | Worker daemon, Redis task queues, QA auto-review, full E2E pipeline | 109/109 |
| 4 | CI/CD monitor, auto-fix failing runs, worker stall detection, Discord notifications | 154/154 |
| 5 | Multi-project management (`_projects` dict, `!projects`, `!switch`) | 266/266 |
| 6 | All agent stubs implemented: `fix_bug`, `write_tests`, `refactor_code`, `improve_ui` | 266/266 |
| 7 | Docker + Cloudflare Tunnel deployment, FastAPI web dashboard on :8080 | 266/266 |

---

## Current File Structure

```
ai-dev-pipeline/
├── agents/
│   ├── base_agent.py              ✅ Abstract base, call_claude_code()
│   ├── master_agent.py            ✅ Orchestrator, multi-project, deploy
│   ├── product_manager_agent.py   ✅ PRD generation
│   ├── project_manager_agent.py   ✅ GitHub repo/issues/branches
│   ├── backend_agent.py           ✅ implement_feature, fix_bug, write_tests, refactor
│   ├── frontend_agent.py          ✅ implement_feature, fix_bug, improve_ui
│   ├── database_agent.py          ✅ Schema design, migrations
│   ├── devops_agent.py            ✅ CI/CD, Dockerfile
│   ├── qa_agent.py                ✅ PR review, test running, coverage
│   ├── assignment_manager.py      ✅ Redis queues, issue routing
│   ├── worker_daemon.py           ✅ Worker loops, all-done detection, auto-deploy
│   ├── github_client.py           ✅ Full GitHub API wrapper
│   ├── github_pusher.py           ✅ Clone → rsync → commit → push
│   ├── pipeline_monitor.py        ✅ CI polling, auto-fix, stall detection
│   ├── deployer.py                ✅ Docker build → port alloc → CF Tunnel
│   └── agent_factory.py           ✅ Agent creation by type
├── api/
│   ├── discord_bot.py             ✅ All commands wired
│   ├── dashboard.py               ✅ FastAPI on :8080
│   └── templates/                 ✅ Jinja2 + Tailwind + HTMX
├── utils/
│   ├── constants.py               ✅
│   ├── error_handlers.py          ✅ Retry, backoff
│   └── structured_logger.py       ✅ JSON logs
├── scripts/
│   ├── run_workers.py             ✅ Standalone worker launcher
│   ├── run_dashboard.py           ✅ uvicorn :8080
│   └── health_check.sh            ✅
├── tests/                         ✅ 266 tests, all passing
├── docs/                          ✅ This folder
└── .env                           ✅ Secrets
```

---

## Discord Commands

| Command | What It Does |
|---------|-------------|
| `!new <description>` | Start a new project end-to-end |
| `!run pipeline` | Run full pipeline on active project |
| `!status` | Active project status + queue sizes |
| `!projects` | List all projects with deploy URLs |
| `!switch <name>` | Switch active project |
| `!deploy` | Deploy active project (Docker + Cloudflare) |
| `!deploy redeploy` | Rebuild and redeploy |
| `!workers start` | Start background worker agents |
| `!workers stop` | Stop workers |
| `!workers status` | Queue sizes + worker states |
| `!monitor start/stop/status` | CI/CD monitor control |
| `!task <description>` | Ad-hoc code task |
| `!help` | Show all commands |

---

## Required `.env` Variables

```env
# GitHub
GITHUB_TOKEN=ghp_...
GITHUB_USERNAME=your-username

# Discord
DISCORD_BOT_TOKEN=...

# Cloudflare
CLOUDFLARE_TUNNEL_NAME=devbot-pipeline
CLOUDFLARE_TUNNEL_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
DEPLOY_DOMAIN=devbot.site

# Redis (defaults fine for local)
REDIS_HOST=localhost
REDIS_PORT=6379

# Optional
MIN_TEST_COVERAGE=80
WORKER_POLL_INTERVAL=10
```

---

## How to Run the System

See `docs/RUNNING_THE_SYSTEM.md` for the complete startup guide.

**TL;DR:**
```bash
# Terminal 1 — Discord bot
cd ~/ai-dev-pipeline && venv/bin/python api/discord_bot.py

# Terminal 2 — Web dashboard
cd ~/ai-dev-pipeline && venv/bin/python scripts/run_dashboard.py

# Workers are started from Discord with: !workers start
```

---

## Known Issues / Immediate Gaps

1. **Project names contain underscores** — Cloudflare DNS requires dashes. `deployer.py` should sanitize `project_20260219` → `project-20260219` before using as subdomain. Tracked in Phase 8 (8.2).

2. **No Dockerfile guarantee** — The DevOps agent generates a Dockerfile via Claude Code, but if it's malformed, `docker build` fails silently. Tracked in Phase 8 (8.3).

3. **Dashboard is read-only** — Current Phase 7 dashboard shows status and has a deploy button but can't create projects, manage issues, or view logs. Tracked in Phase 9.

---

## Metrics

- **Total Python files**: ~25
- **Total lines of code**: ~15,000+
- **Test files**: 13
- **Test count**: 266
- **Agents**: 9 specialized + 1 master
- **Discord commands**: 11
- **Dashboard routes**: 5
