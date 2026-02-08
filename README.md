# 🤖 AI Development Pipeline

> An autonomous AI development system using Claude Code CLI that manages specialized agents to take projects from concept to deployment with minimal human intervention.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Discord](https://img.shields.io/badge/Discord-Bot-7289da.svg)](https://discord.com/)

## 🌟 Overview

This project leverages Claude Code CLI's scriptable nature to create a multi-agent development pipeline. Unlike typical chatbot implementations, we use Claude Code as a programmable tool that can be invoked from Python scripts, enabling true autonomous operation.

**Key Innovation**: Claude Code CLI can be called programmatically via subprocess/shell commands, allowing us to build agents that orchestrate Claude Code sessions without API costs.

## ✨ Features

- 🧠 **Master Agent**: Central orchestrator that manages all sub-agents
- 💬 **Discord Bot Interface**: Chat with your AI development team via Discord
- 🗄️ **Memory System**: ChromaDB-powered context and conversation memory
- 🔄 **Async Processing**: Non-blocking Claude Code execution
- 📊 **Intent Analysis**: Automatically routes requests to appropriate handlers
- 🚀 **Project Initialization**: Create full project structures from descriptions
- 💾 **Redis Integration**: Message queue for agent communication

## 🏗️ Architecture
```
┌─────────────────────────────────────────────────┐
│           DISCORD BOT INTERFACE                 │
│        (User Interaction Layer)                 │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│           MASTER AGENT (Python)                 │
│   - Orchestrates sub-agents                     │
│   - Manages project state                       │
│   - Calls Claude Code CLI                       │
│   - Autonomous decision making                  │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│        CLAUDE CODE CLI (Execution)              │
│   - Edits files, runs commands                  │
│   - Creates commits                             │
│   - Scriptable & composable                     │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│         MEMORY & STORAGE LAYER                  │
│   - ChromaDB: Vector memory                     │
│   - Redis: Message queue                        │
│   - Local files: Project metadata               │
└─────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Ubuntu 22.04 (or similar Linux)
- Node.js 20.x
- Python 3.10+
- Claude Code Pro subscription ($20/month)
- Discord account

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/mynameishaheer/ai-development-pipeline.git
cd ai-development-pipeline
```

2. **Install Node.js 20.x**
```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

3. **Install Claude Code CLI**
```bash
curl -fsSL https://claude.ai/install.sh | sh
claude login
```

4. **Install Redis**
```bash
sudo apt install -y redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

5. **Install Docker (optional)**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
```

6. **Set up Python environment**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

7. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env and add your Discord bot token
```

8. **Configure Claude Code permissions**
```bash
# For bypass permissions mode (recommended for sandboxed environments)
cat > ~/.config/claude/settings.json << 'EOF'
{
  "permissionMode": "bypassPermissions"
}
EOF
```

9. **Run the Discord bot**
```bash
python api/discord_bot.py
```

## 💬 Discord Bot Commands

| Command | Description | Example |
|---------|-------------|---------|
| `!help` | Show help message | `!help` |
| `!new <description>` | Start a new project | `!new Create a task manager with React` |
| `!status` | Check current project status | `!status` |
| `!task <description>` | Implement a specific task | `!task Add user authentication` |
| `!deploy` | Prepare project for deployment | `!deploy` |
| **@mention** or **DM** | General conversation | `@AI Dev Pipeline how do I...` |

## 📁 Project Structure
```
ai-dev-pipeline/
├── agents/               # Agent implementations
│   └── master_agent.py   # Core orchestrator
├── api/                  # Interface layer
│   └── discord_bot.py    # Discord bot
├── memory/               # Persistent storage
│   └── vector_store/     # ChromaDB data
├── projects/             # Generated projects
├── logs/                 # All logs
├── config/               # Configuration
├── scripts/              # Utility scripts
├── docs/                 # Documentation
├── requirements.txt      # Python dependencies
├── .env                  # Environment variables (not in repo)
└── .gitignore           # Git ignore rules
```

## 🛠️ Technology Stack

- **Agent Framework**: Python 3.10+ with asyncio
- **AI Engine**: Claude Code CLI (via Claude Pro subscription)
- **Bot Interface**: Discord.py
- **Vector Database**: ChromaDB (local, for memory)
- **Message Queue**: Redis
- **Version Control**: Git + GitHub

## 💰 Cost Analysis

| Service | Cost | Notes |
|---------|------|-------|
| Claude Code Pro | $20/month | Primary AI engine (required) |
| Discord Bot | $0 | Free official API |
| GitHub | $0 | Free for public repos |
| Redis | $0 | Self-hosted |
| ChromaDB | $0 | Self-hosted |
| **Total** | **$20/month** | |

## 🎯 Current Status

**Phase 1: Complete** ✅
- Master Agent core implementation
- Discord bot interface
- Memory system (ChromaDB)
- Basic project creation workflow
- Intent analysis system
- Async Claude Code execution

**Phase 2: In Progress** 🚧
- Sub-agents (Product Manager, Project Manager, Backend, Frontend, etc.)
- GitHub integration (issues, PRs, branches)
- Automated testing and QA

**Phase 3: Planned** 📋
- WhatsApp bot integration
- Full autonomy mode
- Multi-project support
- Self-improvement capabilities

## 📊 Example Workflow

1. User types in Discord: `!new Create a blog with user authentication`
2. Master Agent analyzes intent → routes to `handle_new_project`
3. Claude Code CLI creates:
   - Project directory structure
   - Git repository
   - README.md, PLAN.md
   - Configuration files
   - Initial code files
4. User types: `!task Add Google OAuth login`
5. Master Agent → Claude Code implements the feature
6. User types: `!deploy`
7. Master Agent prepares deployment files (Dockerfile, etc.)

## 🤝 Contributing

Contributions are welcome! This is an experimental project exploring autonomous AI development.

## 📄 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- Built with [Claude Code CLI](https://code.claude.com)
- Powered by Anthropic's Claude AI
- Inspired by the vision of autonomous software development

## 🔗 Links

- [GitHub Repository](https://github.com/mynameishaheer/ai-development-pipeline)
- [Claude Code Documentation](https://code.claude.com/docs)
- [Discord.py Documentation](https://discordpy.readthedocs.io/)

---

**⚠️ Note**: This is an experimental project. Use in sandboxed environments only. The bypass permissions mode should only be used in VMs/containers with restricted internet access.

Built with ❤️ by the AI Development Pipeline Team
