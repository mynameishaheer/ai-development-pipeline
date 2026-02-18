# AI Development Pipeline - Complete Implementation Plan

> **Project Goal**: Build an autonomous AI development system using Claude Code CLI that manages specialized agents to take projects from concept to deployment with minimal human intervention.

---

## 📋 Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Technology Stack](#technology-stack)
4. [Messaging Platform Decision](#messaging-platform-decision)
5. [Phase 1: Foundation](#phase-1-foundation-week-1-2)
6. [Phase 2: Sub-Agents & GitHub Integration](#phase-2-sub-agents--github-integration-week-3-4)
7. [Phase 3: Full Autonomy & Messaging](#phase-3-full-autonomy--messaging-month-2)
8. [Memory & Context Management](#memory--context-management)
9. [Cost Analysis](#cost-analysis)
10. [Key Principles](#key-principles)

---

## 🎯 Executive Summary

This system leverages Claude Code CLI's scriptable nature to create a multi-agent development pipeline. Unlike typical chatbot implementations, we're using Claude Code as a programmable tool that can be invoked from Python scripts, enabling true autonomous operation.

**Core Innovation**: Claude Code CLI can be called programmatically via subprocess/shell commands, allowing us to build agents that orchestrate Claude Code sessions without API costs.

**First Project**: Gated Community Management System (billing, visitor management, utilities, maintenance)

---

## 🏗️ Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                    INTERFACE LAYER                                │
│  Phase 1: Web Dashboard (FastAPI + React)                        │
│  Phase 2: Discord Bot (free, reliable)                           │
│  Phase 3: WhatsApp Bot (via unofficial API - $6/month)           │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│                  MASTER AGENT (Python FastAPI)                    │
│  - Orchestrates all sub-agents                                   │
│  - Manages conversation & project state                          │
│  - Calls Claude Code CLI programmatically                        │
│  - Makes autonomous decisions                                    │
│  - Handles memory & context retrieval                            │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│                    SUB-AGENTS LAYER                               │
│  Each agent is a Python class that invokes Claude Code CLI       │
│  ┌────────────┬────────────┬────────────┬────────────┐          │
│  │  Product   │  Project   │  Backend   │  Frontend  │          │
│  │  Manager   │  Manager   │  Agent     │  Agent     │          │
│  └────────────┴────────────┴────────────┴────────────┘          │
│  ┌────────────┬────────────┬────────────┬────────────┐          │
│  │  Designer  │  Database  │  DevOps    │    QA      │          │
│  │  Agent     │  Agent     │  Agent     │   Agent    │          │
│  └────────────┴────────────┴────────────┴────────────┘          │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│              EXECUTION LAYER (Claude Code CLI)                    │
│  - Invoked via subprocess: subprocess.run(['claude', '-p', ...]) │
│  - Edits files, runs commands, creates commits                   │
│  - Uses MCP servers for external integrations                    │
│  - Scriptable & composable (Unix philosophy)                     │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│                   MEMORY & STORAGE LAYER                          │
│  - ChromaDB: Vector store for context/memory (free, local)       │
│  - Redis: Message queue for agent communication (free, local)    │
│  - Supabase PostgreSQL: Structured data (free tier)              │
│  - Local JSON: Configuration & state files                       │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│                 INFRASTRUCTURE LAYER                              │
│  - GitHub: Code repositories (free for public repos)             │
│  - Docker: Container isolation on Linux VM (free)                │
│  - Vercel/VM: Staging deployment (free tier)                     │
│  - Linux VM: Your cloud Ubuntu 22.04 machine (existing)          │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Technology Stack

### Core Technologies
- **Agent Framework**: Python 3.10+ with asyncio
- **Web Backend**: FastAPI (faster than Django, perfect for APIs)
- **Web Frontend**: React + Vite
- **Database**: Supabase (PostgreSQL) - Free tier: 500MB, unlimited API requests
- **Vector Database**: ChromaDB (local, free, perfect for AI memory)
- **Message Queue**: Redis (lightweight, fast, free)
- **Deployment**: Docker + Caddy (auto HTTPS)

### Claude Code Integration
- **Claude Code CLI**: Installed via `curl -fsSL https://claude.ai/install.sh | sh`
- **Authentication**: Via Claude Code Pro subscription ($20/month)
- **Invocation**: Programmatic via Python subprocess
- **MCP Servers**: For external tool integration (GitHub, Notion, etc.)

### Why This Stack?
1. **Free/Low Cost**: Only paying for Claude Code Pro ($20/month)
2. **Scriptable**: Everything can be automated
3. **Scalable**: Can grow from single project to multiple projects
4. **Modern**: Industry-standard tools with wide community support
5. **Fast**: Async Python + FastAPI for performance

---

## 💬 Messaging Platform Decision

### Analysis Summary

| Feature | Discord | WhatsApp (Unofficial) | Telegram |
|---------|---------|----------------------|----------|
| **Cost** | Free | $6/month (WaSenderAPI) | Free |
| **API Quality** | Official, Excellent | Unofficial, Good | Official, Excellent |
| **Reliability** | 99.9% | ~95% (account ban risk) | 99.9% |
| **Setup Complexity** | Easy | Medium (QR code) | Easy |
| **Your Familiarity** | Medium | High | Low |
| **Risk** | None | Low (personal use only) | None |

### Recommended Approach: Phased Migration

**Phase 1 (Weeks 1-2): Discord**
- Free, official API with zero limitations
- Perfect for development and testing
- Easy to implement and debug
- No risk of bans or interruptions

**Phase 2 (Month 2): WhatsApp Migration**
- Use **WaSenderAPI** ($6/month) or **Evolution API** (open-source, free)
- QR code authentication with your personal WhatsApp
- Unlimited messages to yourself (no spam risk)
- Group chat support for project-specific conversations

**Why This Order?**
1. Build stable foundation on Discord (free, reliable)
2. Prove the system works before adding WhatsApp complexity
3. WhatsApp unofficial APIs have small ban risk - better to validate system first
4. Easy to migrate: just swap the messaging client in code

### WhatsApp Implementation Options

**Option A: WaSenderAPI (Recommended)**
- Cost: $6/month
- Setup: 5 minutes (scan QR code)
- Features: Webhooks, SDKs (Python, Node.js), group support
- Reliability: High (with best practices)

**Option B: Evolution API (Free, Open-Source)**
- Cost: $0 (self-hosted)
- Setup: 30 minutes (Docker deployment)
- Features: Full WhatsApp Web features, webhook support
- Reliability: High (actively maintained)

**Best Practices to Avoid Bans**:
1. Only message yourself (no spam)
2. Use natural delays between messages (no rapid-fire)
3. Don't send mass broadcasts
4. Keep phone connected to internet

---

## 📅 PHASE 1: Foundation (Week 1-2)

**Goal**: Build Master Agent + Web Interface + Discord Bot + Basic Memory System

### Timeline
- **Day 1**: Server setup & dependencies
- **Day 2-3**: Master Agent core + Claude Code integration
- **Day 4-5**: Discord bot interface
- **Day 6-7**: Web dashboard + memory system
- **Testing**: End of Week 2

---

### Day 1: Server Setup & Installation

#### 1.1 System Updates
```bash
# SSH into your Ubuntu 22.04 VM
ssh user@your-vm-ip

# Update system
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl wget build-essential python3-pip python3-venv
```

#### 1.2 Install Node.js (Required for Claude Code)
```bash
# Install Node.js 20.x
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -bash -
sudo apt install -y nodejs

# Verify installation
node --version  # Should show v20.x
npm --version   # Should show 10.x
```

#### 1.3 Install Claude Code CLI
```bash
# Install Claude Code
curl -fsSL https://claude.ai/install.sh | sh

# Authenticate with your Pro subscription
claude login

# Verify installation
claude --version
```

#### 1.4 Install Docker
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Log out and back in for group changes to take effect
# Then verify
docker --version
docker compose version
```

#### 1.5 Install Redis
```bash
# Install Redis
sudo apt install -y redis-server

# Start Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Test Redis
redis-cli ping  # Should return "PONG"
```

---

### Day 2-3: Master Agent Core

#### 2.1 Create Project Structure
```bash
# Create main project directory
mkdir -p ~/ai-dev-pipeline
cd ~/ai-dev-pipeline

# Create subdirectories
mkdir -p {agents,api,memory,scripts,logs,config,projects,docs}

# Initialize Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Create requirements.txt
cat > requirements.txt << 'EOF'
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
python-dotenv==1.0.0
redis==5.0.1
chromadb==0.4.18
discord.py==2.3.2
aiohttp==3.9.1
asyncio==3.4.3
python-multipart==0.0.6
jinja2==3.1.2
supabase==2.0.3
EOF

# Install dependencies
pip install -r requirements.txt
```

#### 2.2 Create Master Agent

**File**: `agents/master_agent.py`
```python
"""
Master Agent - Central orchestrator for the AI Development Pipeline
Uses Claude Code CLI programmatically to execute tasks
"""

import asyncio
import subprocess
import json
import os
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
import chromadb
import redis


class MasterAgent:
    """
    The Master Agent is the brain of the operation.
    It orchestrates all sub-agents and makes autonomous decisions.
    """
    
    def __init__(self, workspace_dir: str = "/home/claude/ai-dev-pipeline/projects"):
        self.workspace_dir = Path(workspace_dir)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize memory system
        self.memory_client = chromadb.Client()
        self.memory = self.memory_client.create_collection(
            name="master_memory",
            get_or_create=True
        )
        
        # Initialize Redis for agent communication
        self.redis = redis.Redis(host='localhost', port=6379, decode_responses=True)
        
        # Current project state
        self.current_project = None
        self.current_context = {}
        
        print("🧠 Master Agent initialized successfully")
    
    async def call_claude_code(
        self, 
        prompt: str, 
        project_path: Optional[str] = None,
        allowed_tools: Optional[List[str]] = None,
        context_files: Optional[List[str]] = None
    ) -> Dict[str, str]:
        """
        Programmatically invoke Claude Code CLI
        
        This is the KEY method that makes everything work!
        Claude Code is scriptable - we can call it from Python.
        
        Args:
            prompt: The instruction to give Claude Code
            project_path: Directory where Claude Code should work
            allowed_tools: List of tools Claude Code can use (e.g., ["Write", "Edit", "Bash"])
            context_files: Files to include in context
        
        Returns:
            Dict with 'stdout', 'stderr', 'return_code'
        """
        
        # Build the command
        cmd = ["claude", "-p", prompt]
        
        # Add allowed tools if specified
        if allowed_tools:
            cmd.extend(["--allowedTools"] + allowed_tools)
        
        # Add context files if specified
        if context_files:
            for file in context_files:
                cmd.extend(["--context", file])
        
        # Set working directory
        cwd = project_path or str(self.workspace_dir)
        
        print(f"🤖 Calling Claude Code with prompt: {prompt[:100]}...")
        
        try:
            # Execute Claude Code
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=300  # 5 minute timeout
            )
            
            # Log the interaction
            self.log_interaction(prompt, result.stdout, result.stderr)
            
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode,
                "success": result.returncode == 0
            }
            
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": "Command timed out after 5 minutes",
                "return_code": -1,
                "success": False
            }
        except Exception as e:
            return {
                "stdout": "",
                "stderr": str(e),
                "return_code": -1,
                "success": False
            }
    
    async def process_user_message(self, message: str, user_id: str) -> str:
        """
        Main entry point for all user messages
        Analyzes intent and routes to appropriate handler
        
        Args:
            message: User's message/request
            user_id: Unique identifier for the user
        
        Returns:
            Response message to send back to user
        """
        
        print(f"📨 Processing message from {user_id}: {message[:100]}...")
        
        # Store message in memory for context
        await self.store_memory(
            category="user_message",
            content=message,
            metadata={"user_id": user_id, "timestamp": datetime.now().isoformat()}
        )
        
        # Analyze intent using Claude Code
        intent_result = await self.analyze_intent(message)
        intent = intent_result.get("intent", "general_query")
        
        print(f"🎯 Detected intent: {intent}")
        
        # Route to appropriate handler
        handlers = {
            "new_project": self.handle_new_project,
            "code_task": self.handle_code_task,
            "status_check": self.handle_status_check,
            "update_project": self.handle_update_project,
            "deploy": self.handle_deploy,
            "general_query": self.handle_general_query
        }
        
        handler = handlers.get(intent, self.handle_general_query)
        response = await handler(message, user_id)
        
        # Store response in memory
        await self.store_memory(
            category="agent_response",
            content=response,
            metadata={"user_id": user_id, "intent": intent}
        )
        
        return response
    
    async def analyze_intent(self, message: str) -> Dict[str, str]:
        """
        Analyze user message to determine intent
        Uses Claude Code to classify the request
        """
        
        prompt = f"""
        Analyze this user message and determine the intent.
        Return ONLY a JSON object with the intent classification.
        
        Possible intents:
        - new_project: User wants to start a new project
        - code_task: User wants to implement a feature or fix something
        - status_check: User wants to know current project status
        - update_project: User wants to modify existing project
        - deploy: User wants to deploy the project
        - general_query: General question or conversation
        
        User message: "{message}"
        
        Return format:
        {{"intent": "intent_name", "confidence": 0.95, "reasoning": "brief explanation"}}
        """
        
        result = await self.call_claude_code(prompt, allowed_tools=["Write"])
        
        try:
            # Extract JSON from response
            stdout = result.get("stdout", "{}")
            # Claude Code might wrap JSON in markdown - extract it
            if "```json" in stdout:
                json_str = stdout.split("```json")[1].split("```")[0].strip()
            else:
                json_str = stdout.strip()
            
            intent_data = json.loads(json_str)
            return intent_data
        except:
            # Fallback to general query if parsing fails
            return {"intent": "general_query", "confidence": 0.5, "reasoning": "Failed to parse"}
    
    async def handle_new_project(self, message: str, user_id: str) -> str:
        """
        Initialize a new project from user description
        This is where the magic happens!
        """
        
        print("🚀 Initializing new project...")
        
        # Create project directory
        project_name = f"project_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        project_path = self.workspace_dir / project_name
        project_path.mkdir(parents=True, exist_ok=True)
        
        # Use Claude Code to initialize the project
        init_prompt = f"""
        Initialize a new project based on this requirement:
        
        "{message}"
        
        Steps to complete:
        1. Analyze the requirements and identify the tech stack needed
        2. Create appropriate directory structure
        3. Initialize git repository
        4. Create README.md with project overview
        5. Create a PLAN.md file outlining the implementation strategy
        6. Set up basic configuration files (package.json, requirements.txt, etc.)
        7. Create .gitignore file
        
        Work in the current directory and create all necessary files.
        Be thorough and professional.
        """
        
        result = await self.call_claude_code(
            prompt=init_prompt,
            project_path=str(project_path),
            allowed_tools=["Write", "Edit", "Bash"]
        )
        
        if result["success"]:
            # Store project info
            self.current_project = {
                "name": project_name,
                "path": str(project_path),
                "created_at": datetime.now().isoformat(),
                "requirements": message,
                "status": "initialized"
            }
            
            # Save project metadata
            await self.save_project_metadata()
            
            # Create initial GitHub repository
            await self.create_github_repo(project_name, message)
            
            response = f"""
✅ **Project Initialized Successfully!**

📁 **Project Name**: {project_name}
📂 **Location**: {project_path}
🕐 **Created**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📋 **Next Steps**:
I've created the initial structure. I'll now:
1. ✅ Created directory structure
2. ✅ Initialized git repository
3. ✅ Created documentation
4. ⏳ Will create GitHub repository
5. ⏳ Will start implementing core features

Would you like me to proceed with the implementation, or would you like to review the plan first?
            """
        else:
            response = f"""
❌ **Project Initialization Failed**

Error: {result.get('stderr', 'Unknown error')}

I'll try to diagnose and fix this. Please hold on...
            """
        
        return response
    
    async def handle_code_task(self, message: str, user_id: str) -> str:
        """Handle coding tasks for current project"""
        
        if not self.current_project:
            return "❌ No active project. Please start a new project first with your requirements."
        
        project_path = self.current_project["path"]
        
        prompt = f"""
        Implement the following task for the current project:
        
        "{message}"
        
        Context:
        - Project: {self.current_project['name']}
        - Original Requirements: {self.current_project['requirements']}
        
        Steps:
        1. Analyze the current codebase
        2. Identify files that need to be created or modified
        3. Implement the changes
        4. Test the changes if applicable
        5. Commit the changes to git
        
        Be thorough and follow best practices.
        """
        
        result = await self.call_claude_code(
            prompt=prompt,
            project_path=project_path,
            allowed_tools=["Write", "Edit", "Bash", "Read"]
        )
        
        if result["success"]:
            return f"""
✅ **Task Completed Successfully!**

{result.get('stdout', 'Task completed')}

The changes have been implemented and committed to git.
            """
        else:
            return f"""
❌ **Task Failed**

Error: {result.get('stderr', 'Unknown error')}

I'll analyze the error and try to fix it automatically...
            """
    
    async def handle_status_check(self, message: str = None, user_id: str = None) -> str:
        """Provide status update on current project"""
        
        if not self.current_project:
            return "📊 **Status**: No active project. Ready to start a new one!"
        
        project_path = self.current_project["path"]
        
        # Use Claude Code to analyze project status
        status_prompt = """
        Analyze the current project and provide a status update:
        
        1. List all files in the project
        2. Check git status
        3. Identify completed features
        4. Identify pending tasks (check TODO comments, issues)
        5. Check if there are any errors or warnings
        
        Provide a clear, concise summary.
        """
        
        result = await self.call_claude_code(
            prompt=status_prompt,
            project_path=project_path,
            allowed_tools=["Bash", "Read"]
        )
        
        return f"""
📊 **Project Status**

📁 **Project**: {self.current_project['name']}
🕐 **Created**: {self.current_project['created_at']}

{result.get('stdout', 'Status check completed')}
        """
    
    async def handle_update_project(self, message: str, user_id: str) -> str:
        """Handle project updates and modifications"""
        return await self.handle_code_task(message, user_id)
    
    async def handle_deploy(self, message: str, user_id: str) -> str:
        """Handle deployment requests"""
        
        if not self.current_project:
            return "❌ No active project to deploy."
        
        project_path = self.current_project["path"]
        
        deploy_prompt = """
        Prepare the project for deployment:
        
        1. Create a Dockerfile if it doesn't exist
        2. Create docker-compose.yml for local testing
        3. Ensure all environment variables are documented
        4. Run tests if they exist
        5. Build the project
        6. Create deployment instructions in DEPLOYMENT.md
        
        Do not actually deploy yet, just prepare everything.
        """
        
        result = await self.call_claude_code(
            prompt=deploy_prompt,
            project_path=project_path,
            allowed_tools=["Write", "Edit", "Bash"]
        )
        
        return f"""
🚀 **Deployment Preparation Complete**

{result.get('stdout', 'Project is ready for deployment')}

Next steps:
1. Review the DEPLOYMENT.md file
2. Confirm you want to proceed with deployment
3. I'll handle the actual deployment to your staging environment
        """
    
    async def handle_general_query(self, message: str, user_id: str) -> str:
        """Handle general questions and conversations"""
        
        # Retrieve relevant context from memory
        context = await self.retrieve_memory(message, n_results=3)
        
        context_str = "\n".join([
            f"- {doc}" for doc in context.get("documents", [[]])[0]
        ]) if context else "No relevant context"
        
        prompt = f"""
        Answer this question from the user:
        
        "{message}"
        
        Relevant context from previous conversations:
        {context_str}
        
        Current project: {self.current_project.get('name') if self.current_project else 'None'}
        
        Provide a helpful, friendly response. If you need more information, ask.
        """
        
        result = await self.call_claude_code(
            prompt=prompt,
            allowed_tools=["Write"]
        )
        
        return result.get("stdout", "I'm here to help! Could you provide more details?")
    
    async def store_memory(self, category: str, content: str, metadata: Dict = None):
        """Store information in vector database for later retrieval"""
        
        memory_id = f"{category}_{datetime.now().timestamp()}"
        
        self.memory.add(
            documents=[content],
            metadatas=[{"category": category, **(metadata or {})}],
            ids=[memory_id]
        )
    
    async def retrieve_memory(self, query: str, n_results: int = 5) -> Dict:
        """Retrieve relevant memories based on query"""
        
        try:
            results = self.memory.query(
                query_texts=[query],
                n_results=n_results
            )
            return results
        except:
            return {"documents": [[]]}
    
    async def save_project_metadata(self):
        """Save current project metadata to disk"""
        
        if not self.current_project:
            return
        
        metadata_file = Path(self.current_project["path"]) / ".project_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(self.current_project, f, indent=2)
    
    async def create_github_repo(self, project_name: str, description: str):
        """Create GitHub repository for the project"""
        
        # This will be implemented using GitHub CLI or API
        # For now, just log it
        print(f"📦 GitHub repo creation queued for: {project_name}")
        
        # Store in Redis queue for background processing
        self.redis.lpush("github_repo_queue", json.dumps({
            "project_name": project_name,
            "description": description,
            "created_at": datetime.now().isoformat()
        }))
    
    def log_interaction(self, prompt: str, stdout: str, stderr: str):
        """Log all Claude Code interactions for debugging"""
        
        log_file = Path("logs") / f"claude_code_{datetime.now().strftime('%Y%m%d')}.log"
        log_file.parent.mkdir(exist_ok=True)
        
        with open(log_file, 'a') as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"Prompt: {prompt}\n")
            f.write(f"Stdout: {stdout}\n")
            f.write(f"Stderr: {stderr}\n")
            f.write(f"{'='*80}\n")


# Example usage
if __name__ == "__main__":
    async def test():
        agent = MasterAgent()
        response = await agent.process_user_message(
            "Create a gated community management system with billing and visitor tracking",
            "test_user_123"
        )
        print(response)
    
    asyncio.run(test())
```

---

### Day 4-5: Discord Bot Interface

#### 4.1 Create Discord Application

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application"
3. Name it "AI Dev Pipeline"
4. Go to "Bot" tab → Click "Add Bot"
5. Under "Privileged Gateway Intents", enable:
   - Message Content Intent
   - Server Members Intent
6. Copy the bot token

#### 4.2 Create Discord Bot Code

**File**: `api/discord_bot.py`
```python
"""
Discord Bot Interface for AI Development Pipeline
Provides user interaction through Discord
"""

import discord
from discord.ext import commands
import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from agents.master_agent import MasterAgent
from dotenv import load_dotenv

load_dotenv()

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Initialize Master Agent
master = MasterAgent()


@bot.event
async def on_ready():
    """Called when bot is ready"""
    print(f'🤖 AI Development Pipeline Bot is ready!')
    print(f'📝 Logged in as: {bot.user.name} (ID: {bot.user.id})')
    print(f'🔗 Connected to {len(bot.guilds)} server(s)')
    print('─' * 50)
    
    # Set bot status
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="for project requests | !help"
        )
    )


@bot.event
async def on_message(message):
    """Handle all messages"""
    
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return
    
    # Process commands first
    await bot.process_commands(message)
    
    # Handle DMs or mentions
    if isinstance(message.channel, discord.DMChannel) or bot.user in message.mentions:
        
        # Show typing indicator
        async with message.channel.typing():
            # Remove bot mention from message
            content = message.content.replace(f'<@{bot.user.id}>', '').strip()
            
            # Process through Master Agent
            response = await master.process_user_message(
                content,
                str(message.author.id)
            )
            
            # Split long messages
            if len(response) > 2000:
                chunks = [response[i:i+2000] for i in range(0, len(response), 2000)]
                for chunk in chunks:
                    await message.channel.send(chunk)
            else:
                await message.channel.send(response)


@bot.command(name='new', aliases=['create', 'start'])
async def new_project(ctx, *, description: str):
    """
    Start a new project
    Usage: !new <project description>
    Example: !new Create a task management app with React and FastAPI
    """
    
    async with ctx.typing():
        response = await master.handle_new_project(description, str(ctx.author.id))
        await ctx.send(response)


@bot.command(name='status', aliases=['info', 'progress'])
async def project_status(ctx):
    """
    Check current project status
    Usage: !status
    """
    
    async with ctx.typing():
        response = await master.handle_status_check()
        await ctx.send(response)


@bot.command(name='task', aliases=['implement', 'code'])
async def code_task(ctx, *, task_description: str):
    """
    Implement a specific task or feature
    Usage: !task <task description>
    Example: !task Add user authentication with JWT
    """
    
    async with ctx.typing():
        response = await master.handle_code_task(task_description, str(ctx.author.id))
        await ctx.send(response)


@bot.command(name='deploy', aliases=['ship', 'release'])
async def deploy_project(ctx):
    """
    Prepare project for deployment
    Usage: !deploy
    """
    
    async with ctx.typing():
        response = await master.handle_deploy("Deploy the project", str(ctx.author.id))
        await ctx.send(response)


@bot.command(name='help')
async def help_command(ctx):
    """Show help message"""
    
    embed = discord.Embed(
        title="🤖 AI Development Pipeline Bot",
        description="I'm your autonomous development assistant! I can help you build entire projects from just a description.",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="🚀 Start a New Project",
        value="`!new <description>` - Start a new project\nExample: `!new Build a blog with React and Django`",
        inline=False
    )
    
    embed.add_field(
        name="📊 Check Status",
        value="`!status` - Get current project status and progress",
        inline=False
    )
    
    embed.add_field(
        name="💻 Implement a Task",
        value="`!task <description>` - Implement a specific feature\nExample: `!task Add user login with Google OAuth`",
        inline=False
    )
    
    embed.add_field(
        name="🚀 Deploy",
        value="`!deploy` - Prepare project for deployment",
        inline=False
    )
    
    embed.add_field(
        name="💬 Chat with Me",
        value="DM me or mention me (`@AI Dev Pipeline`) to have a conversation!",
        inline=False
    )
    
    embed.set_footer(text="Powered by Claude Code CLI + Multi-Agent System")
    
    await ctx.send(embed=embed)


@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument. Use `!help` to see command usage.")
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send(f"❌ Unknown command. Use `!help` to see available commands.")
    else:
        await ctx.send(f"❌ An error occurred: {str(error)}")
        print(f"Error: {error}")


def run_bot():
    """Run the Discord bot"""
    
    token = os.getenv('DISCORD_BOT_TOKEN')
    
    if not token:
        print("❌ Error: DISCORD_BOT_TOKEN not found in environment variables")
        print("Please create a .env file with your Discord bot token")
        return
    
    try:
        bot.run(token)
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"❌ Error starting bot: {e}")


if __name__ == "__main__":
    run_bot()
```

#### 4.3 Environment Configuration

**File**: `.env`
```env
# Discord Bot Configuration
DISCORD_BOT_TOKEN=your_discord_bot_token_here

# GitHub Configuration (for Phase 2)
GITHUB_TOKEN=your_github_personal_access_token

# Supabase Configuration (for Phase 2)
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379

# Claude Code Configuration
# No API key needed - using Claude Code Pro subscription authentication
```

#### 4.4 Start the Bot

```bash
# Activate virtual environment
source venv/bin/activate

# Run the bot
python api/discord_bot.py
```

---

### Day 6-7: Web Dashboard (Optional for Phase 1)

**File**: `api/web_server.py`
```python
"""
FastAPI Web Server for AI Development Pipeline
Provides REST API and web dashboard
"""

from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from agents.master_agent import MasterAgent

app = FastAPI(title="AI Development Pipeline")
master = MasterAgent()


class MessageRequest(BaseModel):
    message: str
    user_id: str


@app.get("/")
async def root():
    """Serve web dashboard"""
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI Development Pipeline</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
            }
            h1 { color: #333; }
            .chat-box {
                border: 1px solid #ddd;
                padding: 20px;
                height: 400px;
                overflow-y: scroll;
                margin-bottom: 20px;
                background: #f9f9f9;
            }
            input[type="text"] {
                width: 80%;
                padding: 10px;
                font-size: 16px;
            }
            button {
                padding: 10px 20px;
                font-size: 16px;
                background: #007bff;
                color: white;
                border: none;
                cursor: pointer;
            }
        </style>
    </head>
    <body>
        <h1>🤖 AI Development Pipeline</h1>
        <div class="chat-box" id="chat"></div>
        <input type="text" id="message" placeholder="Type your message...">
        <button onclick="sendMessage()">Send</button>
        
        <script>
            async function sendMessage() {
                const message = document.getElementById('message').value;
                if (!message) return;
                
                const chat = document.getElementById('chat');
                chat.innerHTML += `<p><strong>You:</strong> ${message}</p>`;
                
                const response = await fetch('/api/message', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        message: message,
                        user_id: 'web_user'
                    })
                });
                
                const data = await response.json();
                chat.innerHTML += `<p><strong>Agent:</strong> ${data.response}</p>`;
                chat.scrollTop = chat.scrollHeight;
                
                document.getElementById('message').value = '';
            }
            
            document.getElementById('message').addEventListener('keypress', (e) => {
                if (e.key === 'Enter') sendMessage();
            });
        </script>
    </body>
    </html>
    """)


@app.post("/api/message")
async def process_message(request: MessageRequest):
    """Process user message through Master Agent"""
    
    try:
        response = await master.process_user_message(
            request.message,
            request.user_id
        )
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status")
async def get_status():
    """Get current project status"""
    
    try:
        response = await master.handle_status_check()
        return {"status": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**Run the web server:**
```bash
python api/web_server.py
# Access at http://your-vm-ip:8000
```

---

## 📅 PHASE 2: Sub-Agents & GitHub Integration (Week 3-4)

**Goal**: Add specialized sub-agents and automate GitHub workflows

### Agent Implementation Pattern

Each sub-agent follows this pattern:

```python
class SubAgent:
    def __init__(self, master_agent):
        self.master = master_agent
    
    async def execute_task(self, task_description: str, context: Dict) -> str:
        """
        Execute agent-specific task using Claude Code
        """
        prompt = self.build_prompt(task_description, context)
        result = await self.master.call_claude_code(
            prompt=prompt,
            project_path=context.get("project_path"),
            allowed_tools=self.get_allowed_tools()
        )
        return result
    
    def build_prompt(self, task: str, context: Dict) -> str:
        """Build agent-specific prompt"""
        raise NotImplementedError
    
    def get_allowed_tools(self) -> List[str]:
        """Return tools this agent can use"""
        raise NotImplementedError
```

### Sub-Agents to Implement

**File**: `agents/product_manager_agent.py`
```python
class ProductManagerAgent:
    """
    Converts user requirements into structured documentation
    Creates PRDs, defines features, prioritizes work
    """
    
    async def create_prd(self, requirements: str, project_path: str) -> str:
        prompt = f"""
        Act as an experienced Product Manager.
        
        Create a comprehensive Product Requirements Document (PRD) for:
        "{requirements}"
        
        Include:
        1. Product Overview & Vision
        2. User Personas
        3. User Stories (As a [user], I want [feature], so that [benefit])
        4. Feature Requirements (Must-have, Should-have, Nice-to-have)
        5. Technical Requirements
        6. Success Metrics & KPIs
        7. Implementation Timeline (estimated)
        8. Risks & Mitigation Strategies
        
        Save as: docs/PRD.md
        Format: Professional markdown
        """
        # Implementation continues...
```

**File**: `agents/project_manager_agent.py`
```python
class ProjectManagerAgent:
    """
    Plans and executes development lifecycle
    Creates sprints, manages GitHub issues, tracks progress
    """
    
    async def create_implementation_plan(self, prd_path: str) -> str:
        # Reads PRD, breaks into tasks, creates GitHub issues
        pass
```

**File**: `agents/backend_agent.py`
```python
class BackendAgent:
    """
    Implements server-side logic and APIs
    """
    pass
```

**File**: `agents/frontend_agent.py`
```python
class FrontendAgent:
    """
    Builds user interface and client-side logic
    """
    pass
```

Continue pattern for: `designer_agent.py`, `database_agent.py`, `devops_agent.py`, `qa_agent.py`

---

## 📅 PHASE 3: Full Autonomy & WhatsApp (Month 2+)

### WhatsApp Integration

**Option A: WaSenderAPI ($6/month)**

```python
# File: api/whatsapp_bot.py
import requests
from typing import Dict

class WhatsAppBot:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://wasenderapi.com/api"
        self.master = MasterAgent()
    
    def send_message(self, to: str, message: str):
        """Send WhatsApp message"""
        response = requests.post(
            f"{self.base_url}/send-message",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"to": to, "text": message}
        )
        return response.json()
    
    def setup_webhook(self, webhook_url: str):
        """Setup webhook for incoming messages"""
        # Configuration code
        pass
    
    async def handle_incoming_message(self, message_data: Dict):
        """Process incoming WhatsApp message"""
        message = message_data.get("text", "")
        sender = message_data.get("from", "")
        
        response = await self.master.process_user_message(message, sender)
        self.send_message(sender, response)
```

**Setup Instructions:**
1. Sign up at WaSenderAPI.com
2. Scan QR code with your WhatsApp
3. Get API key
4. Configure webhook endpoint
5. Run: `python api/whatsapp_bot.py`

---

## 💾 Memory & Context Management

### Vector Database (ChromaDB)

```python
# Memory storage
self.memory.add(
    documents=[content],
    metadatas=[{"category": "conversation", "timestamp": "..."}],
    ids=["unique_id"]
)

# Memory retrieval
results = self.memory.query(
    query_texts=["Find information about authentication"],
    n_results=5
)
```

### Context Window Management

**Strategy**: Keep Claude Code calls focused and efficient
- Store project context in files (CONTEXT.md, ARCHITECTURE.md)
- Reference context files in prompts instead of passing everything
- Use `--context` flag to include relevant files
- Implement smart context pruning

```python
async def get_relevant_context(self, query: str, project_path: str) -> List[str]:
    """
    Get relevant context files for a query
    Returns list of file paths to include
    """
    
    # Always include these
    base_files = [
        f"{project_path}/CONTEXT.md",
        f"{project_path}/ARCHITECTURE.md"
    ]
    
    # Retrieve relevant past conversations from vector DB
    memories = await self.retrieve_memory(query, n_results=3)
    
    # Combine and return
    return base_files + self.extract_file_references(memories)
```

---

## 💰 Cost Analysis

### Current Budget: ~$20/month

| Service | Cost | Notes |
|---------|------|-------|
| **Claude Code Pro** | $20/month | Primary AI engine (required) |
| **Discord Bot** | $0 | Free official API |
| **WhatsApp (Phase 3)** | $6/month | WaSenderAPI (optional) |
| **Supabase** | $0 | Free tier: 500MB DB, unlimited API |
| **GitHub** | $0 | Free for public repos |
| **Linux VM** | Existing | Your cloud VM |
| **Docker** | $0 | Open source |
| **Redis** | $0 | Self-hosted |
| **ChromaDB** | $0 | Self-hosted |
| **Vercel** | $0 | Free tier for staging |

**Total: $20-26/month** (depending on WhatsApp choice)

### Cost Optimization Strategies

1. **Use Claude Code CLI instead of API** ✅
   - Your Pro subscription covers unlimited CLI usage
   - No per-token API costs

2. **Efficient Prompt Design**
   - Keep prompts focused and specific
   - Use context files instead of repeating information
   - Batch related tasks in single Claude Code call

3. **Smart Caching**
   - Store Claude Code responses in Redis (24hr TTL)
   - Reuse similar responses when appropriate

4. **Local Infrastructure**
   - Run Redis, ChromaDB, Docker on your VM
   - No cloud service costs

---

## 🎯 Key Principles

### 1. Maximum Autonomy
- System should make decisions independently
- Only ask user for input when absolutely necessary
- Automatically fix errors when possible
- Learn from mistakes and adapt

### 2. Claude Code as Foundation
- All coding tasks go through Claude Code CLI
- Invoke programmatically via subprocess
- Use `--allowedTools` to control what Claude Code can do
- Compose with other Unix tools (pipes, redirects)

### 3. Continuous Learning
- Store all interactions in vector database
- Learn from past mistakes
- Build up project-specific knowledge over time
- Improve prompts based on outcomes

### 4. Scalable Architecture
- Phase 1 design supports Phase 2+ additions
- Agent system is modular (easy to add new agents)
- Clear separation of concerns
- Each component can be upgraded independently

### 5. Error Resilience
- Always try to fix errors automatically first
- Log all errors for learning
- Provide clear error messages to user
- Have fallback strategies

---

## 🚀 Getting Started Checklist

### Immediate Steps (Today)

- [ ] SSH into your Ubuntu VM
- [ ] Update system packages
- [ ] Install Node.js 20.x
- [ ] Install Claude Code CLI
- [ ] Authenticate Claude Code with your Pro subscription
- [ ] Install Docker
- [ ] Install Redis
- [ ] Create project directory structure
- [ ] Set up Python virtual environment
- [ ] Install Python dependencies
- [ ] Create `.env` file with Discord bot token
- [ ] Test Claude Code CLI: `claude -p "Create a hello.txt file with 'Hello World'"`

### Week 1 Goals

- [ ] Complete Master Agent implementation
- [ ] Create Discord bot and invite to server
- [ ] Test basic conversation flow
- [ ] Implement intent analysis
- [ ] Test new project creation
- [ ] Verify Claude Code integration works

### Week 2 Goals

- [ ] Implement memory storage/retrieval
- [ ] Add status checking
- [ ] Add code task handling
- [ ] Build web dashboard (optional)
- [ ] Test complete Phase 1 workflow
- [ ] Start actual gated community project

---

## 📚 Additional Resources

### Claude Code Documentation
- Official Docs: https://code.claude.com/docs
- GitHub Repo: https://github.com/anthropics/claude-code
- Community Examples: https://github.com/disler/claude-code-is-programmable

### Discord.py Documentation
- Docs: https://discordpy.readthedocs.io/
- Bot Guide: https://realpython.com/how-to-make-a-discord-bot-python/

### FastAPI Documentation
- Docs: https://fastapi.tiangolo.com/

### ChromaDB Documentation
- Docs: https://docs.trychroma.com/

---

## 🤝 Support & Communication

### When Things Go Wrong

1. **Check Logs**: All Claude Code interactions are logged in `logs/`
2. **Test Claude Code Directly**: Run commands manually to isolate issues
3. **Review Memory**: Check what's stored in ChromaDB
4. **Redis Queue**: Check `redis-cli` for queued tasks
5. **Ask the Agent**: The system should be able to debug itself!

### Evolution Strategy

This system is designed to **learn and improve over time**:

1. **Iteration 1** (Week 1-2): Basic working system
2. **Iteration 2** (Week 3-4): Add sub-agents, improve reliability
3. **Iteration 3** (Month 2): Full autonomy, WhatsApp, multi-project
4. **Iteration 4+**: Self-improvement, new capabilities, scale

The Master Agent should continuously improve its own prompts and strategies based on outcomes.

---

## 📝 Next Steps

1. **Today**: Set up infrastructure (Steps 1.1-1.5)
2. **Tomorrow**: Implement Master Agent core
3. **Day 3-4**: Build Discord bot interface
4. **Day 5**: First test with simple project
5. **Day 6-7**: Start gated community project
6. **Week 2**: Refine and optimize based on learnings

Remember: **Start simple, iterate quickly, learn continuously**

The beauty of this architecture is that you can begin with a minimal viable system and expand it progressively. Each phase builds on the previous one without requiring rewrites.

---

## 🎉 Final Thoughts

You're building something revolutionary here - a truly autonomous development system that uses Claude Code CLI in a way most people haven't considered. The key insights are:

1. **Claude Code is scriptable** - you can call it from code
2. **Unix composability** - build complex workflows from simple pieces
3. **Memory makes it smart** - ChromaDB turns conversations into knowledge
4. **Autonomy is the goal** - minimize human intervention
5. **Learning is continuous** - system improves itself over time

This isn't just a chatbot - it's an autonomous development team that works 24/7, learns from experience, and gets better with every project.

**Let's build the future of software development! 🚀**

---

*Document Version: 1.0*  
*Created: February 9, 2026*  
*Author: AI Development Pipeline Planning Session*  
*Status: Ready for Implementation*
