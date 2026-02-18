# AI Development Pipeline - Quick Reference Card

> **Keep This Handy**: Essential commands, file locations, and troubleshooting steps for quick access during development.

---

## 🚀 Quick Start Commands

### System Setup (First Time Only)
```bash
# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -bash -
sudo apt install -y nodejs

# Install Claude Code
curl -fsSL https://claude.ai/install.sh | sh
claude login

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Redis
sudo apt install -y redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

### Daily Development Workflow
```bash
# 1. Navigate to project
cd ~/ai-dev-pipeline

# 2. Activate Python environment
source venv/bin/activate

# 3. Health check
./scripts/health_check.sh

# 4. Start Discord bot
python api/discord_bot.py

# 5. (Optional) Start web server
python api/web_server.py
```

---

## 📂 Critical File Locations

| File | Location | Purpose |
|------|----------|---------|
| Master Agent | `agents/master_agent.py` | Core orchestration logic |
| Discord Bot | `api/discord_bot.py` | User interface |
| Environment Config | `.env` | Secrets & configuration |
| Current State | `CURRENT_STATE.md` | Project status snapshot |
| Logs | `logs/claude_code_YYYYMMDD.log` | All interactions |
| Projects | `projects/` | Generated projects |
| Requirements | `requirements.txt` | Python dependencies |

---

## 🎯 Claude Code CLI Essentials

### Basic Usage
```bash
# Simple prompt
claude -p "Your instruction here"

# With specific tools
claude -p "Your instruction" --allowedTools "Write" "Edit" "Bash"

# With context files
claude -p "Your instruction" --context file1.txt --context file2.md

# In specific directory
cd /path/to/project && claude -p "Your instruction"
```

### Example Commands
```bash
# Create a file
claude -p "Create a hello.py that prints Hello World"

# Fix code
claude -p "Fix any bugs in app.py"

# Add feature
claude -p "Add user authentication to the existing Flask app"

# Create documentation
claude -p "Generate API documentation for all endpoints"
```

---

## 🤖 Discord Bot Commands

| Command | Usage | Description |
|---------|-------|-------------|
| `!new` | `!new <description>` | Start new project |
| `!status` | `!status` | Check project status |
| `!task` | `!task <description>` | Implement a feature |
| `!deploy` | `!deploy` | Prepare deployment |
| `!help` | `!help` | Show help message |
| DM / @mention | Message the bot | General conversation |

### Example Discord Interactions
```
!new Create a REST API for a todo app with FastAPI

!task Add user authentication with JWT tokens

!status

!deploy
```

---

## 🔧 Troubleshooting Quick Fixes

### Claude Code Issues
```bash
# Not found
which claude
# If missing: curl -fsSL https://claude.ai/install.sh | sh

# Authentication expired
claude login
```

### Python Issues
```bash
# Virtual environment not activated
source venv/bin/activate

# Missing packages
pip install -r requirements.txt

# Import errors
python -c "from agents.master_agent import MasterAgent; print('OK')"
```

### Redis Issues
```bash
# Check if running
redis-cli ping  # Should return PONG

# Restart
sudo systemctl restart redis-server

# Check status
sudo systemctl status redis-server
```

### Discord Bot Issues
```bash
# Check token
cat .env | grep DISCORD_BOT_TOKEN

# Kill stuck process
pkill -f discord_bot.py

# Restart bot
python api/discord_bot.py
```

### ChromaDB Issues
```bash
# Check if data persists
ls -la memory/vector_store/

# Test in Python
python -c "import chromadb; client = chromadb.Client(); print('OK')"
```

---

## 📊 System Health Check

### Quick Status
```bash
# All-in-one check
./scripts/health_check.sh

# Individual checks
claude --version           # Claude Code
python --version          # Python
docker --version          # Docker
redis-cli ping            # Redis
node --version            # Node.js
```

### Check Running Services
```bash
# Python processes
ps aux | grep python

# Docker containers
docker ps -a

# System resources
df -h                     # Disk space
free -h                   # Memory
top                       # CPU usage
```

---

## 🗂️ Project Structure

```
ai-dev-pipeline/
├── agents/               # Agent implementations
│   ├── master_agent.py
│   ├── product_manager_agent.py
│   └── ...
├── api/                  # Interface layer
│   ├── discord_bot.py
│   ├── whatsapp_bot.py
│   └── web_server.py
├── memory/               # Persistent storage
│   └── vector_store/
├── projects/             # Generated projects
├── logs/                 # All logs
├── config/               # Configuration
│   └── .env
├── scripts/              # Utility scripts
│   └── health_check.sh
├── docs/                 # Documentation
├── venv/                 # Python virtual env
└── requirements.txt      # Dependencies
```

---

## 🔑 Environment Variables (.env)

```env
# Discord
DISCORD_BOT_TOKEN=your_token_here

# GitHub
GITHUB_TOKEN=your_github_token

# Supabase
SUPABASE_URL=your_url
SUPABASE_KEY=your_key

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
```

---

## 📝 Git Workflow

### Daily Commands
```bash
# Check status
git status

# Add changes
git add .

# Commit
git commit -m "Description of changes"

# Push
git push origin main

# View history
git log --oneline -10
```

### Phase Completion
```bash
# Tag a phase
git tag -a phase1-complete -m "Phase 1 complete"
git push origin phase1-complete

# Create checkpoint
git commit -m "Phase 1 checkpoint - all core features working"
```

---

## 🐛 Common Error Messages & Fixes

| Error | Fix |
|-------|-----|
| `claude: command not found` | `curl -fsSL https://claude.ai/install.sh \| sh` |
| `ModuleNotFoundError` | `source venv/bin/activate && pip install -r requirements.txt` |
| `Redis connection refused` | `sudo systemctl restart redis-server` |
| `Discord login failed` | Check `DISCORD_BOT_TOKEN` in `.env` |
| `Permission denied` | `chmod +x script.sh` or use `sudo` |
| `Port already in use` | `lsof -i :8000` then `kill <PID>` |

---

## 🎨 Master Agent API

### Process User Message
```python
from agents.master_agent import MasterAgent

agent = MasterAgent()
response = await agent.process_user_message(
    message="Your request here",
    user_id="user_123"
)
```

### Call Claude Code Directly
```python
result = await agent.call_claude_code(
    prompt="Your instruction",
    project_path="/path/to/project",
    allowed_tools=["Write", "Edit", "Bash"]
)
```

### Store & Retrieve Memory
```python
# Store
await agent.store_memory(
    category="user_message",
    content="Message content",
    metadata={"user_id": "123"}
)

# Retrieve
results = await agent.retrieve_memory(
    query="Find authentication info",
    n_results=5
)
```

---

## 📞 Support & Resources

### Documentation
- **Implementation Plan**: `docs/AI_Development_Pipeline_Implementation_Plan.md`
- **Handoff Guide**: `docs/Project_Handoff_Guide.md`
- **This Reference**: `docs/Quick_Reference_Card.md`

### External Resources
- Claude Code: https://code.claude.com/docs
- Discord.py: https://discordpy.readthedocs.io/
- FastAPI: https://fastapi.tiangolo.com/
- ChromaDB: https://docs.trychroma.com/

### Logs Location
```bash
# Claude Code interactions
tail -f logs/claude_code_$(date +%Y%m%d).log

# Discord bot (if redirected)
tail -f logs/discord_bot.log

# System logs
journalctl -u redis-server -f
```

---

## ⚡ Performance Tips

1. **Keep prompts concise** - Claude Code works best with focused instructions
2. **Use context files** - Instead of repeating info in prompts
3. **Batch related tasks** - Combine similar operations in one call
4. **Monitor logs** - Watch for patterns and optimize
5. **Clean up projects** - Archive old projects to save space

---

## 🎯 Testing Checklist

### Before Committing Changes
- [ ] Run health check script
- [ ] Test Discord bot responds
- [ ] Verify Master Agent imports
- [ ] Check Redis connection
- [ ] Run quick functionality test
- [ ] Review error logs
- [ ] Update CURRENT_STATE.md

### Before Starting New Phase
- [ ] All previous phase tests passing
- [ ] Documentation updated
- [ ] Git committed and pushed
- [ ] No blocking issues
- [ ] Dependencies installed
- [ ] Services running

---

## 💡 Pro Tips

1. **Use aliases** in your `.bashrc`:
   ```bash
   alias aip='cd ~/ai-dev-pipeline && source venv/bin/activate'
   alias aiph='./scripts/health_check.sh'
   alias aiplog='tail -f logs/claude_code_$(date +%Y%m%d).log'
   ```

2. **Create tmux sessions** for long-running processes:
   ```bash
   tmux new -s discord-bot
   python api/discord_bot.py
   # Ctrl+B, D to detach
   tmux attach -t discord-bot  # To reattach
   ```

3. **Monitor with watch**:
   ```bash
   watch -n 2 'ps aux | grep python'
   ```

4. **Quick backup**:
   ```bash
   tar -czf backup_$(date +%Y%m%d).tar.gz ~/ai-dev-pipeline
   ```

---

## 🚨 Emergency Commands

### System Unresponsive
```bash
# Kill all Python processes
pkill -9 python

# Restart all services
sudo systemctl restart redis-server
cd ~/ai-dev-pipeline && source venv/bin/activate
python api/discord_bot.py &
```

### Disk Space Full
```bash
# Find large files
du -sh ~/ai-dev-pipeline/* | sort -h

# Clean up logs
find logs/ -name "*.log" -mtime +7 -delete

# Clean up old projects
# (Manually review first!)
ls -lat projects/
```

### Git Issues
```bash
# Undo last commit (keep changes)
git reset --soft HEAD~1

# Discard all changes
git reset --hard HEAD

# Create recovery branch
git checkout -b recovery-$(date +%Y%m%d)
```

---

*Quick Reference v1.0 - Keep this handy! 🚀*
