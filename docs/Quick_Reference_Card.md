# AI Development Pipeline — Quick Reference

**Last Updated**: February 19, 2026

---

## Daily Startup

### Recommended: tmux (one command)
```bash
tmux new-session -s pipeline -d
tmux split-window -h -t pipeline
tmux split-window -v -t pipeline:0.1
tmux send-keys -t pipeline:0.0 'cd ~/ai-dev-pipeline && venv/bin/python api/discord_bot.py' Enter
tmux send-keys -t pipeline:0.1 'cd ~/ai-dev-pipeline && venv/bin/python scripts/run_dashboard.py' Enter
tmux attach -t pipeline
```

### Or two terminals
```bash
# Terminal 1 — Discord bot
cd ~/ai-dev-pipeline && venv/bin/python api/discord_bot.py

# Terminal 2 — Web dashboard (http://<vm-ip>:8080)
cd ~/ai-dev-pipeline && venv/bin/python scripts/run_dashboard.py
```

Workers are started from Discord, not a separate terminal:
```
!workers start
```

---

## Discord Commands

| Command | Description |
|---------|-------------|
| `!new <description>` | Create a new project (PRD + GitHub + CI + Deploy) |
| `!run pipeline` | Run full pipeline on the active project |
| `!status` | Active project status + queue sizes |
| `!projects` | List all projects with deploy URLs |
| `!switch <name>` | Switch the active project |
| `!deploy` | Deploy active project (Docker + Cloudflare) |
| `!deploy redeploy` | Rebuild and redeploy from scratch |
| `!workers start` | Start background worker agents |
| `!workers stop` | Stop workers (graceful — finishes current task) |
| `!workers status` | Queue sizes + per-agent worker states |
| `!monitor start` | Start CI/CD monitor for active project |
| `!monitor stop` | Stop CI/CD monitor |
| `!monitor status` | Show monitor state and last check time |
| `!task <description>` | Run an ad-hoc Claude Code task |
| `!help` | Show all commands in Discord |

---

## Web Dashboard Routes

| URL | Description |
|-----|-------------|
| `http://<vm-ip>:8080/` | Main dashboard — all projects |
| `http://<vm-ip>:8080/api/status` | JSON status snapshot |
| `http://<vm-ip>:8080/projects/<name>` | Project detail page |
| `POST /projects/<name>/deploy` | Trigger deploy (form submit) |
| `https://dashboard.devbot.site` | Public URL (via Cloudflare Tunnel) |

---

## Key File Locations

| Purpose | Path |
|---------|------|
| Orchestrator | `agents/master_agent.py` |
| Discord bot | `api/discord_bot.py` |
| Web dashboard | `api/dashboard.py` |
| Worker daemon | `agents/worker_daemon.py` |
| Task queues (Redis) | `agents/assignment_manager.py` |
| CI monitor | `agents/pipeline_monitor.py` |
| Docker deployer | `agents/deployer.py` |
| GitHub client | `agents/github_client.py` |
| Env config | `.env` |
| Logs | `logs/claude_code_YYYYMMDD.log` |
| Generated projects | `projects/` |
| Port allocations | `~/.ai-dev-pipeline/port_allocations.json` |
| Cloudflare config | `~/.cloudflared/config.yml` |

---

## Health Checks

```bash
redis-cli ping                        # PONG
docker ps                             # no error
sudo systemctl status cloudflared     # active (running)
curl http://localhost:8080/api/status # JSON response
venv/bin/python -m pytest tests/ -v   # 266/266 passing
```

---

## Environment Variables (`.env`)

```env
# Required
GITHUB_TOKEN=ghp_...
GITHUB_USERNAME=your-username
DISCORD_BOT_TOKEN=...

# Cloudflare Tunnel
CLOUDFLARE_TUNNEL_NAME=devbot-pipeline
CLOUDFLARE_TUNNEL_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
DEPLOY_DOMAIN=devbot.site

# Redis (defaults work for local)
REDIS_HOST=localhost
REDIS_PORT=6379

# Optional tuning
MIN_TEST_COVERAGE=80
WORKER_POLL_INTERVAL=10
WORKER_AGENTS=backend,frontend,database,devops,qa
```

---

## Common Troubleshooting

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: fastapi` | `venv/bin/pip install fastapi uvicorn jinja2 python-multipart` |
| `ModuleNotFoundError: yaml` | `venv/bin/pip install pyyaml` |
| `redis.exceptions.ConnectionError` | `sudo systemctl start redis-server` |
| Discord bot not responding | Check `DISCORD_BOT_TOKEN` in `.env` |
| `docker: permission denied` | `sudo usermod -aG docker shaheer && newgrp docker` |
| Cloudflare config not found | `sudo cp ~/.cloudflared/config.yml /etc/cloudflared/config.yml` |
| Cloudflare YAML parse error | Ensure no leading spaces — root keys (`tunnel:`, `ingress:`) must start at column 0 |
| Dashboard 404 on `/projects/x` | Project not loaded — check `.project_metadata.json` exists |
| Workers claiming tasks but idle | Agent type mismatch — check `WORKER_AGENTS` env var |

---

## Shell Aliases (add to `~/.bashrc`)

```bash
alias aip='cd ~/ai-dev-pipeline'
alias aipbot='cd ~/ai-dev-pipeline && venv/bin/python api/discord_bot.py'
alias aipdash='cd ~/ai-dev-pipeline && venv/bin/python scripts/run_dashboard.py'
alias aiptest='cd ~/ai-dev-pipeline && venv/bin/python -m pytest tests/ -v'
alias aiplog='tail -f ~/ai-dev-pipeline/logs/claude_code_$(date +%Y%m%d).log'
```

---

## Running Tests

```bash
# Full suite
venv/bin/python -m pytest tests/ -v

# Single file
venv/bin/python -m pytest tests/test_deployer.py -v

# Single test
venv/bin/python -m pytest tests/test_deployer.py::TestBuildDockerImage::test_build_success -v

# With output (shows print statements)
venv/bin/python -m pytest tests/ -v -s
```

---

## Redis Queue Inspection

```bash
# Queue sizes
redis-cli ZCARD queue:agent:backend
redis-cli ZCARD queue:agent:frontend
redis-cli ZCARD queue:agent:qa

# Peek at queue contents
redis-cli ZRANGE queue:agent:backend 0 -1 WITHSCORES

# Clear a stuck queue (use with care)
redis-cli DEL queue:agent:backend
```

---

## Docker / Container Management

```bash
# List running containers (deployed projects)
docker ps

# View logs for a project container
docker logs <project-name>

# Stop a container
docker stop <project-name>

# Remove container and image (full cleanup)
docker stop <project-name> && docker rm <project-name> && docker rmi <project-name>

# Check port allocations
cat ~/.ai-dev-pipeline/port_allocations.json
```

---

## Emergency Recovery

```bash
# Kill stuck Python processes
pkill -f discord_bot.py
pkill -f run_dashboard.py

# Restart Redis
sudo systemctl restart redis-server

# Restart Cloudflare Tunnel
sudo systemctl restart cloudflared

# Clear all Redis queues (drops all pending tasks)
redis-cli FLUSHDB   # WARNING: destructive
```
