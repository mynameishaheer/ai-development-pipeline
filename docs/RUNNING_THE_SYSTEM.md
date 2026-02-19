# Running the AI Dev Pipeline

**Last Updated**: February 19, 2026

---

## Prerequisites (One-Time Setup)

### 1. Install system dependencies
```bash
# Python venv
cd ~/ai-dev-pipeline
python3 -m venv venv
venv/bin/pip install -r requirements.txt

# Missing packages (add these until requirements.txt is updated)
venv/bin/pip install pyyaml fastapi uvicorn httpx jinja2 python-multipart
```

### 2. Redis
```bash
sudo apt install -y redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server
redis-cli ping    # → PONG
```

### 3. Docker
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker shaheer   # allow running docker without sudo
newgrp docker                      # apply group change in current shell
docker --version                   # verify
```

### 4. Cloudflare Tunnel
```bash
# Install cloudflared
curl -L -o cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb

# Authenticate
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create devbot-pipeline
# Note the Tunnel ID printed

# Create config (replace TUNNEL_ID with yours)
TUNNEL_ID="your-tunnel-id-here"
cat > ~/.cloudflared/config.yml << EOF
tunnel: ${TUNNEL_ID}
credentials-file: /home/shaheer/.cloudflared/${TUNNEL_ID}.json

ingress:
  - hostname: dashboard.devbot.site
    service: http://localhost:8080
  - service: http_status:404
EOF

# Route dashboard subdomain
cloudflared tunnel route dns devbot-pipeline dashboard.devbot.site

# Install and start as system service
sudo cp ~/.cloudflared/config.yml /etc/cloudflared/config.yml
sudo cloudflared service install
sudo systemctl enable cloudflared
sudo systemctl start cloudflared
```

### 5. Configure `.env`
```bash
cp .env.example .env   # if it exists, or create fresh:
cat > .env << 'EOF'
GITHUB_TOKEN=ghp_your_token_here
GITHUB_USERNAME=your-github-username

DISCORD_BOT_TOKEN=your_discord_token

CLOUDFLARE_TUNNEL_NAME=devbot-pipeline
CLOUDFLARE_TUNNEL_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
DEPLOY_DOMAIN=devbot.site

REDIS_HOST=localhost
REDIS_PORT=6379

MIN_TEST_COVERAGE=80
WORKER_POLL_INTERVAL=10
WORKER_AGENTS=backend,frontend,database,devops,qa
EOF
```

---

## Daily Startup (3 Terminals / tmux panes)

### Recommended: tmux
```bash
# Create a new tmux session with 3 panes
tmux new-session -s pipeline -d
tmux split-window -h -t pipeline
tmux split-window -v -t pipeline:0.1

# Pane 0: Discord bot
tmux send-keys -t pipeline:0.0 'cd ~/ai-dev-pipeline && venv/bin/python api/discord_bot.py' Enter

# Pane 1: Dashboard
tmux send-keys -t pipeline:0.1 'cd ~/ai-dev-pipeline && venv/bin/python scripts/run_dashboard.py' Enter

# Pane 2: Free for commands
tmux send-keys -t pipeline:0.2 'cd ~/ai-dev-pipeline' Enter

tmux attach -t pipeline
```

### Or three separate terminals:

**Terminal 1 — Discord bot (required)**
```bash
cd ~/ai-dev-pipeline
venv/bin/python api/discord_bot.py
```

**Terminal 2 — Web dashboard (recommended)**
```bash
cd ~/ai-dev-pipeline
venv/bin/python scripts/run_dashboard.py
# Dashboard at: http://<vm-ip>:8080
# Public at:    https://dashboard.devbot.site
```

**Workers are started from Discord** (not a separate terminal):
```
!workers start
```

---

## Verify Everything is Working

```bash
# Redis
redis-cli ping                          # PONG

# Docker
docker ps                               # no error

# Cloudflare tunnel
sudo systemctl status cloudflared       # active (running)

# Dashboard
curl http://localhost:8080/api/status   # JSON response

# Tests
venv/bin/python -m pytest tests/ -v     # 266/266 passing
```

---

## First End-to-End Run

In Discord:
```
!new Build a URL shortener with FastAPI and SQLite — short links, click tracking, custom slugs
```

Wait ~2 minutes, then:
```
!run pipeline
```

Watch the bot work through all 4 stages. After it replies with the pipeline complete message:
```
!workers start
```

Workers will now claim and implement all the GitHub issues. Monitor progress:
```
!workers status
!status
```

When all tasks complete, the bot will automatically deploy and send:
> 🎉 All tasks complete! `project-xxx` has been deployed.
> 🌐 Live at: https://project-xxx.devbot.site

---

## Adding Aliases (Optional)

Add to `~/.bashrc`:
```bash
alias aip='cd ~/ai-dev-pipeline'
alias aipbot='cd ~/ai-dev-pipeline && venv/bin/python api/discord_bot.py'
alias aipdash='cd ~/ai-dev-pipeline && venv/bin/python scripts/run_dashboard.py'
alias aiptest='cd ~/ai-dev-pipeline && venv/bin/python -m pytest tests/ -v'
alias aiplog='tail -f ~/ai-dev-pipeline/logs/claude_code_$(date +%Y%m%d).log'
```

---

## Systemd Services (Recommended for Production)

To have the bot and dashboard auto-start on reboot:

```bash
# Discord bot service
sudo tee /etc/systemd/system/aip-discord.service << 'EOF'
[Unit]
Description=AI Dev Pipeline Discord Bot
After=network.target redis-server.service

[Service]
User=shaheer
WorkingDirectory=/home/shaheer/ai-dev-pipeline
ExecStart=/home/shaheer/ai-dev-pipeline/venv/bin/python api/discord_bot.py
Restart=always
RestartSec=10
EnvironmentFile=/home/shaheer/ai-dev-pipeline/.env

[Install]
WantedBy=multi-user.target
EOF

# Dashboard service
sudo tee /etc/systemd/system/aip-dashboard.service << 'EOF'
[Unit]
Description=AI Dev Pipeline Web Dashboard
After=network.target

[Service]
User=shaheer
WorkingDirectory=/home/shaheer/ai-dev-pipeline
ExecStart=/home/shaheer/ai-dev-pipeline/venv/bin/python scripts/run_dashboard.py
Restart=always
RestartSec=10
EnvironmentFile=/home/shaheer/ai-dev-pipeline/.env

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable aip-discord aip-dashboard
sudo systemctl start aip-discord aip-dashboard
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: fastapi` | `venv/bin/pip install fastapi uvicorn jinja2 python-multipart` |
| `ModuleNotFoundError: yaml` | `venv/bin/pip install pyyaml` |
| `redis.exceptions.ConnectionError` | `sudo systemctl start redis-server` |
| Discord bot not responding | Check `DISCORD_BOT_TOKEN` in `.env` |
| `docker: permission denied` | `sudo usermod -aG docker shaheer && newgrp docker` |
| `cloudflared: systemctl reload failed` | Check `/etc/cloudflared/config.yml` syntax: `cloudflared tunnel ingress validate` |
| Dashboard 404 on `/projects/x` | Project not in `_projects` dict — check `.project_metadata.json` exists in project dir |
| Workers claiming tasks but doing nothing | Redis queue has tasks but agent type mismatch — check `WORKER_AGENTS` env var |
