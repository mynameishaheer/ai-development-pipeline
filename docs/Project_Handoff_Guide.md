# AI Development Pipeline - Project Handoff Guide

> **Purpose**: This document ensures seamless continuity when switching between chat sessions while working on different phases of the project.

---

## 📋 Table of Contents

1. [Quick Project Overview](#quick-project-overview)
2. [Essential Files & Their Locations](#essential-files--their-locations)
3. [Phase Handoff Checklist](#phase-handoff-checklist)
4. [How to Brief a New Chat Session](#how-to-brief-a-new-chat-session)
5. [Common Issues & Solutions](#common-issues--solutions)
6. [Testing & Validation](#testing--validation)

---

## 🎯 Quick Project Overview

**What We're Building**: An autonomous AI development system that uses Claude Code CLI to manage specialized agents that take projects from concept to deployment.

**Key Innovation**: Using Claude Code CLI programmatically (via Python subprocess) to create a multi-agent system without API costs.

**First Real Project**: Gated Community Management System (billing, visitor management, utilities, maintenance)

**Tech Stack**: Python + FastAPI + React + Claude Code CLI + Discord Bot + ChromaDB + Redis + Supabase + Docker

**Cost**: ~$20/month (just Claude Code Pro subscription)

---

## 📂 Essential Files & Their Locations

### Project Root Structure
```
~/ai-dev-pipeline/
├── agents/                      # All agent implementations
│   ├── master_agent.py         # Core orchestrator
│   ├── product_manager_agent.py
│   ├── project_manager_agent.py
│   ├── backend_agent.py
│   └── ... (other agents)
├── api/                        # Interface layer
│   ├── discord_bot.py          # Discord interface
│   ├── whatsapp_bot.py         # WhatsApp interface (Phase 3)
│   └── web_server.py           # Web dashboard
├── memory/                     # Memory & context storage
│   ├── vector_store/           # ChromaDB data
│   └── redis_data/             # Redis persistence
├── projects/                   # All generated projects
│   └── project_YYYYMMDD_HHMMSS/
├── logs/                       # All interaction logs
│   └── claude_code_YYYYMMDD.log
├── config/                     # Configuration files
│   ├── .env                    # Environment variables
│   └── settings.json           # System settings
├── scripts/                    # Utility scripts
├── docs/                       # Documentation
│   ├── AI_Development_Pipeline_Concept.md
│   ├── AI_Development_Pipeline_Implementation_Plan.md
│   └── Project_Handoff_Guide.md (this file)
├── requirements.txt            # Python dependencies
├── docker-compose.yml          # Docker configuration
└── README.md                   # Project README
```

### Critical Files to Always Check

1. **`.env`** - Contains all secrets and configuration
2. **`agents/master_agent.py`** - Core system logic
3. **`logs/claude_code_YYYYMMDD.log`** - All Claude Code interactions
4. **Project metadata files** - `.project_metadata.json` in each project folder
5. **Redis queue** - Check with `redis-cli LRANGE github_repo_queue 0 -1`

---

## 🔄 Phase Handoff Checklist

### Before Starting a New Chat Session

**Step 1: Document Current State**
```bash
# Create a state snapshot
cd ~/ai-dev-pipeline

# What phase are we in?
echo "Current Phase: [Phase 1/2/3]" > CURRENT_STATE.md

# What's completed?
echo "## Completed Tasks" >> CURRENT_STATE.md
# List what works

# What's in progress?
echo "## In Progress" >> CURRENT_STATE.md
# List what's being worked on

# Any blockers?
echo "## Blockers" >> CURRENT_STATE.md
# List any issues
```

**Step 2: Test Everything That Should Work**
```bash
# Test Claude Code CLI
claude -p "Echo 'System check'"

# Test Discord bot (if Phase 1 complete)
python api/discord_bot.py  # Should start without errors

# Test Master Agent
python -c "from agents.master_agent import MasterAgent; agent = MasterAgent(); print('✅ Master Agent loads')"

# Check Redis
redis-cli ping  # Should return PONG

# Check logs
tail -n 50 logs/claude_code_$(date +%Y%m%d).log
```

**Step 3: Commit Everything to Git**
```bash
cd ~/ai-dev-pipeline
git add .
git commit -m "Phase [X] checkpoint - [brief description]"
git push origin main
```

**Step 4: Export Current Configuration**
```bash
# Backup .env (without secrets exposed)
cp .env .env.backup

# Export installed Python packages
pip freeze > requirements_frozen.txt

# Document system state
docker ps -a > docker_state.txt
systemctl status redis-server > redis_status.txt
```

---

## 💬 How to Brief a New Chat Session

### Template Message for Starting a New Chat

```markdown
Hi! I'm continuing work on the AI Development Pipeline project. Here's the context:

**Project**: Autonomous AI development system using Claude Code CLI
**Repository**: [Your GitHub repo link]
**Current Phase**: Phase [1/2/3]

**What's Been Completed**:
- [List completed tasks from CURRENT_STATE.md]

**What I'm Working On Now**:
- [Current objective]

**Project Files Available**:
- AI_Development_Pipeline_Concept.md (in project files)
- AI_Development_Pipeline_Implementation_Plan.md (in project files)
- Project_Handoff_Guide.md (in project files)

**Immediate Goal**: [What you want to accomplish in this session]

**Questions/Help Needed**: [Specific help you need]

Please read the project files to understand the full context, then let's continue where we left off.
```

### What to Upload to Each New Chat

**Always Upload These Files:**
1. `AI_Development_Pipeline_Implementation_Plan.md` - The master plan
2. `Project_Handoff_Guide.md` - This file
3. `CURRENT_STATE.md` - Current status snapshot

**Upload If Relevant:**
4. `agents/master_agent.py` - If working on agent logic
5. `api/discord_bot.py` - If working on Discord integration
6. Error logs from `logs/` - If debugging issues
7. Specific project files from `projects/` - If working on a specific project

---

## 🎯 Phase-Specific Handoff Notes

### Phase 1 → Phase 2 Handoff

**What Should Be Working:**
- ✅ Claude Code CLI installed and authenticated
- ✅ Master Agent can process messages
- ✅ Discord bot responds to commands
- ✅ Memory system (ChromaDB) stores and retrieves data
- ✅ Redis is running
- ✅ Basic project creation works

**What to Test Before Phase 2:**
```bash
# Test full workflow
!new Create a simple hello world web app
# Bot should respond and create project

!status
# Should show project status

!task Add a welcome message to the homepage
# Should implement the task

# Check project was created
ls -la ~/ai-dev-pipeline/projects/
```

**Phase 2 Prerequisites:**
- GitHub Personal Access Token ready
- Supabase account created (free tier)
- Understanding of which sub-agents to prioritize

---

### Phase 2 → Phase 3 Handoff

**What Should Be Working:**
- ✅ All Phase 1 functionality
- ✅ Product Manager Agent creates PRDs
- ✅ Project Manager Agent creates GitHub issues
- ✅ Backend Agent implements server logic
- ✅ Frontend Agent builds UI
- ✅ Automated GitHub integration
- ✅ Multi-agent coordination

**What to Test Before Phase 3:**
```bash
# Test full agent workflow
!new Build a task management system with user authentication

# Should trigger:
# 1. Product Manager creates PRD
# 2. Project Manager creates sprint plan
# 3. Backend Agent implements API
# 4. Frontend Agent builds UI
# 5. GitHub repo created with issues
```

**Phase 3 Prerequisites:**
- WhatsApp account ready (if using WhatsApp)
- WaSenderAPI account or Evolution API deployed
- Discord bot proven stable for 2+ weeks

---

## 🚨 Common Issues & Solutions

### Issue 1: Claude Code Not Found
```bash
# Solution: Verify installation
which claude
# If not found: curl -fsSL https://claude.ai/install.sh | sh
```

### Issue 2: Import Errors in Python
```bash
# Solution: Check virtual environment
source ~/ai-dev-pipeline/venv/bin/activate
pip list  # Verify packages installed
```

### Issue 3: Discord Bot Won't Start
```bash
# Solution 1: Check .env file
cat ~/ai-dev-pipeline/.env | grep DISCORD_BOT_TOKEN

# Solution 2: Test token manually
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('DISCORD_BOT_TOKEN'))"
```

### Issue 4: Redis Connection Failed
```bash
# Solution: Restart Redis
sudo systemctl restart redis-server
redis-cli ping  # Should return PONG
```

### Issue 5: ChromaDB Persistence Issues
```bash
# Solution: Check ChromaDB directory
ls -la ~/ai-dev-pipeline/memory/vector_store/

# If empty, memory isn't persisting - update master_agent.py:
# self.memory_client = chromadb.PersistentClient(path="./memory/vector_store")
```

### Issue 6: Projects Not Found
```bash
# Solution: Check workspace directory
ls -la ~/ai-dev-pipeline/projects/

# Verify master_agent.py has correct path
grep "workspace_dir" ~/ai-dev-pipeline/agents/master_agent.py
```

---

## ✅ Testing & Validation

### Quick Health Check Script

Create `scripts/health_check.sh`:
```bash
#!/bin/bash

echo "🔍 AI Development Pipeline Health Check"
echo "========================================"

# Check Claude Code
echo -n "Claude Code CLI: "
if command -v claude &> /dev/null; then
    echo "✅ Installed"
else
    echo "❌ Not found"
fi

# Check Python environment
echo -n "Python Virtual Env: "
if [ -d "venv" ]; then
    echo "✅ Exists"
else
    echo "❌ Not found"
fi

# Check Redis
echo -n "Redis: "
if redis-cli ping &> /dev/null; then
    echo "✅ Running"
else
    echo "❌ Not running"
fi

# Check required files
echo -n "Master Agent: "
if [ -f "agents/master_agent.py" ]; then
    echo "✅ Exists"
else
    echo "❌ Missing"
fi

echo -n "Discord Bot: "
if [ -f "api/discord_bot.py" ]; then
    echo "✅ Exists"
else
    echo "❌ Missing"
fi

# Check .env
echo -n "Environment Config: "
if [ -f ".env" ]; then
    echo "✅ Exists"
else
    echo "❌ Missing"
fi

# Check logs
echo -n "Logs Directory: "
if [ -d "logs" ]; then
    echo "✅ Exists ($(ls logs/ | wc -l) files)"
else
    echo "❌ Missing"
fi

# Check projects
echo -n "Projects Directory: "
if [ -d "projects" ]; then
    echo "✅ Exists ($(ls projects/ | wc -l) projects)"
else
    echo "❌ Missing"
fi

echo "========================================"
echo "Health check complete!"
```

Make it executable:
```bash
chmod +x scripts/health_check.sh
./scripts/health_check.sh
```

---

## 📊 Progress Tracking Template

### CURRENT_STATE.md Template

```markdown
# AI Development Pipeline - Current State

**Last Updated**: [Date and Time]
**Updated By**: [Your name or identifier]
**Current Phase**: Phase [1/2/3]

---

## ✅ Completed Components

### Phase 1
- [ ] Claude Code CLI installed and authenticated
- [ ] Master Agent core implementation
- [ ] Discord bot interface
- [ ] Memory system (ChromaDB)
- [ ] Redis message queue
- [ ] Web dashboard (optional)
- [ ] Basic project creation workflow
- [ ] Intent analysis system
- [ ] Status checking

### Phase 2
- [ ] Product Manager Agent
- [ ] Project Manager Agent
- [ ] Backend Agent
- [ ] Frontend Agent
- [ ] Designer Agent
- [ ] Database Agent
- [ ] DevOps Agent
- [ ] QA Agent
- [ ] GitHub integration
- [ ] Automated issue creation
- [ ] PR management

### Phase 3
- [ ] WhatsApp bot integration
- [ ] Full autonomy mode
- [ ] Multi-project support
- [ ] Self-improvement capabilities
- [ ] Advanced error recovery
- [ ] Comprehensive logging

---

## 🚧 In Progress

**Current Task**: [What you're working on]
**Started**: [Date]
**Expected Completion**: [Date]
**Blockers**: [Any issues]

**Recent Changes**:
- [List of recent commits or changes]

---

## 🐛 Known Issues

1. **Issue**: [Description]
   - **Impact**: [How it affects the system]
   - **Workaround**: [Temporary solution if any]
   - **Status**: [Open/In Progress/Blocked]

---

## 📝 Next Steps

1. [Next immediate task]
2. [Following task]
3. [Future task]

---

## 💡 Notes & Learnings

- [Important insights discovered]
- [Best practices identified]
- [Things to remember for next phase]

---

## 🔗 Related Files

- Implementation Plan: `docs/AI_Development_Pipeline_Implementation_Plan.md`
- Project Concept: `docs/AI_Development_Pipeline_Concept.md`
- Handoff Guide: `docs/Project_Handoff_Guide.md`
```

---

## 🎓 Best Practices for Multi-Chat Workflow

### 1. Always Start with Context
- Upload the 3 core documents to every new chat
- Provide CURRENT_STATE.md snapshot
- Explain what you're trying to accomplish

### 2. Keep Documentation Updated
- Update CURRENT_STATE.md after every session
- Commit changes to Git regularly
- Log important decisions and learnings

### 3. Test Before Switching
- Run health check script
- Verify critical functionality works
- Document any breaking changes

### 4. Use Git Religiously
- Commit after completing each feature
- Use descriptive commit messages
- Tag phase completions: `git tag phase1-complete`

### 5. Maintain Communication
- Leave notes for "future you" in CURRENT_STATE.md
- Document why decisions were made
- Keep a running log of issues encountered

---

## 🆘 Emergency Recovery

### If Everything Seems Broken

**Step 1: Check System State**
```bash
cd ~/ai-dev-pipeline
./scripts/health_check.sh
```

**Step 2: Review Recent Changes**
```bash
git log --oneline -10  # Last 10 commits
git diff HEAD~1  # Changes in last commit
```

**Step 3: Check Logs**
```bash
tail -n 100 logs/claude_code_$(date +%Y%m%d).log
```

**Step 4: Restart Services**
```bash
sudo systemctl restart redis-server
# If Discord bot is running: pkill -f discord_bot.py
# Then restart: python api/discord_bot.py
```

**Step 5: Restore from Backup (Last Resort)**
```bash
git checkout [last-known-good-commit]
git checkout -b recovery-branch
```

---

## 📞 Quick Reference Commands

### System Status
```bash
# Full health check
./scripts/health_check.sh

# Check running processes
ps aux | grep python
docker ps -a

# Check disk space
df -h

# Check logs
tail -f logs/claude_code_$(date +%Y%m%d).log
```

### Development
```bash
# Activate environment
source venv/bin/activate

# Run Discord bot
python api/discord_bot.py

# Run web server
python api/web_server.py

# Test Master Agent
python agents/master_agent.py
```

### Debugging
```bash
# Check Redis
redis-cli
> KEYS *
> LRANGE github_repo_queue 0 -1

# Test Claude Code directly
claude -p "Create a test.txt file with 'Hello World'"

# Python interactive testing
python
>>> from agents.master_agent import MasterAgent
>>> agent = MasterAgent()
>>> # Test methods here
```

---

## 🎯 Session Start Checklist

**Before Starting Work in a New Chat:**

- [ ] Upload 3 core documents (Implementation Plan, Handoff Guide, Current State)
- [ ] Brief the chat on current phase and objectives
- [ ] Run health check script
- [ ] Review last 10 git commits
- [ ] Check recent logs for errors
- [ ] Verify all services running (Redis, Discord bot if applicable)
- [ ] Activate Python virtual environment
- [ ] Confirm you're in correct directory (`~/ai-dev-pipeline`)

**After Completing Work in a Chat:**

- [ ] Update CURRENT_STATE.md
- [ ] Commit all changes to Git
- [ ] Run health check to verify nothing broke
- [ ] Document any learnings or issues
- [ ] Push to GitHub
- [ ] Create session summary note

---

## 📚 Additional Resources

### Commands Reference
- **Claude Code**: `claude --help`
- **Discord.py**: https://discordpy.readthedocs.io/
- **FastAPI**: https://fastapi.tiangolo.com/
- **ChromaDB**: https://docs.trychroma.com/
- **Redis**: https://redis.io/commands

### Troubleshooting Resources
- Claude Code Issues: https://github.com/anthropics/claude-code/issues
- Discord Bot Issues: Discord Developer Portal
- Python Issues: Stack Overflow

---

## 🎉 Final Notes

**Remember**: This project is designed to be worked on across multiple chat sessions. The key to success is:

1. **Documentation** - Keep everything documented
2. **Testing** - Test before and after each session
3. **Git** - Commit frequently, push regularly
4. **Communication** - Leave clear notes for future sessions

Each chat session should leave the project in a **better, more stable state** than it found it.

**Good luck, and happy building! 🚀**

---

*Document Version: 1.0*  
*Created: February 9, 2026*  
*Purpose: Enable seamless multi-chat project continuity*  
*Status: Active Reference Document*
