# Phase 2 - Foundation Layer (Checkpoint 1)

## Overview

This checkpoint establishes the foundational infrastructure for Phase 2 of the AI Development Pipeline. All sub-agents will build upon these core components.

## 📦 Components Created

### 1. **Error Handlers** (`utils/error_handlers.py`)
- Retry logic with exponential backoff
- Error recovery strategies
- Custom exception classes
- Global error recovery manager

**Key Features:**
- `@retry_with_backoff` decorator for resilient operations
- `@retry_on_rate_limit` for GitHub API calls
- `ErrorRecoveryManager` for intelligent error handling
- Automatic recovery attempts for common failures

### 2. **Constants** (`utils/constants.py`)
- Centralized configuration
- Agent types and priorities
- Redis channels and queues
- GitHub branch conventions
- File patterns and templates

**Key Features:**
- All agent types defined
- Standard messaging channels
- GitHub workflow configurations
- Default project structures
- Validation utilities

### 3. **Structured Logger** (`utils/structured_logger.py`)
- JSON-formatted logging
- Agent-specific log files
- Specialized logging methods
- Log analysis utilities

**Key Features:**
- `StructuredLogger` class
- Agent action logging
- Claude Code call logging
- GitHub operation logging
- Log parsing and filtering

### 4. **Agent Messaging** (`agents/messaging.py`)
- Redis pub/sub communication
- Priority-based message queues
- Message handlers
- Broadcast capabilities

**Key Features:**
- `AgentMessenger` for individual agents
- `MessageBus` for central monitoring
- Typed messages with `AgentMessage` class
- Queue and pub/sub hybrid approach

### 5. **GitHub Client** (`agents/github_client.py`)
- Complete GitHub API integration
- Repository management
- Issue and PR automation
- Branch operations
- Workflow/CI/CD support

**Key Features:**
- Repository creation and deletion
- Branch creation and protection
- Issue creation and management
- PR creation and merging
- File content manipulation
- GitHub Actions integration

## 📁 Installation Instructions

### Step 1: Create Directories
```bash
cd ~/ai-dev-pipeline

# Create new directories
mkdir -p utils
mkdir -p agents/messaging  # Not actually needed, just for clarity
```

### Step 2: Install Files

Transfer each file to your VM:

```bash
# From your local machine (where you downloaded the files)
scp error_handlers.py shaheer@vm.devbot.site:~/ai-dev-pipeline/utils/
scp constants.py shaheer@vm.devbot.site:~/ai-dev-pipeline/utils/
scp structured_logger.py shaheer@vm.devbot.site:~/ai-dev-pipeline/utils/
scp messaging.py shaheer@vm.devbot.site:~/ai-dev-pipeline/agents/
scp github_client.py shaheer@vm.devbot.site:~/ai-dev-pipeline/agents/
```

**OR** create each file directly on VM using `nano`:

```bash
# SSH into VM
ssh shaheer@vm.devbot.site
cd ~/ai-dev-pipeline

# Create utils directory
mkdir -p utils

# Create each file
nano utils/error_handlers.py  # Paste content, Ctrl+X, Y, Enter
nano utils/constants.py
nano utils/structured_logger.py
nano agents/messaging.py
nano agents/github_client.py
```

### Step 3: Create `__init__.py` Files

```bash
cd ~/ai-dev-pipeline

# Make utils a package
touch utils/__init__.py

# Update agents __init__.py if needed
touch agents/__init__.py
```

### Step 4: Install Missing Dependencies

```bash
source venv/bin/activate

# Install requests (for GitHub client)
pip install requests

# Update requirements.txt
cat >> requirements.txt << 'EOF'
requests==2.31.0
EOF
```

## 🧪 Testing the Foundation

### Test 1: Import All Modules

```bash
cd ~/ai-dev-pipeline
source venv/bin/activate

python << 'EOF'
print("Testing imports...")

# Test error handlers
from utils.error_handlers import retry_with_backoff, ErrorRecoveryManager
print("✅ Error handlers imported")

# Test constants
from utils.constants import AgentType, RedisChannels, GITHUB_TOKEN
print("✅ Constants imported")

# Test logger
from utils.structured_logger import get_logger
print("✅ Logger imported")

# Test messaging
from agents.messaging import AgentMessenger, AgentMessage
print("✅ Messaging imported")

# Test GitHub client
from agents.github_client import GitHubClient
print("✅ GitHub client imported")

print("\n🎉 All foundation modules imported successfully!")
EOF
```

### Test 2: Logger Functionality

```bash
python << 'EOF'
from utils.structured_logger import get_logger

# Create a logger
logger = get_logger("test_agent", agent_type="test")

# Test logging
logger.info("Testing structured logger", extra={"test": "value"})
logger.log_agent_action(
    agent_type="test",
    action="test_action",
    status="completed",
    details={"result": "success"}
)

print("✅ Logger test completed - check logs/test_YYYYMMDD.log")
EOF
```

### Test 3: Messaging System

```bash
python << 'EOF'
import asyncio
from agents.messaging import create_messenger, AgentMessage

async def test_messaging():
    # Create two messengers
    agent1 = create_messenger("backend", "test1")
    agent2 = create_messenger("frontend", "test2")
    
    # Send a message
    msg_id = await agent1.send_message(
        recipient="frontend:test2",
        message_type="task_assignment",
        content={"task": "Build UI"},
        priority=1
    )
    
    print(f"✅ Sent message: {msg_id}")
    
    # Receive message
    message = await agent2.receive_message(timeout=2)
    
    if message:
        print(f"✅ Received message: {message.message_type}")
        print(f"   Content: {message.content}")
    else:
        print("⚠️  No message received (expected in test)")
    
    print("✅ Messaging test completed")

asyncio.run(test_messaging())
EOF
```

### Test 4: GitHub Client (Verify Only - Don't Create)

```bash
python << 'EOF'
import asyncio
from agents.github_client import create_github_client

async def test_github():
    # Create client
    client = create_github_client()
    
    # Check authentication
    user = await client.get_authenticated_user()
    print(f"✅ Authenticated as: {user['login']}")
    
    # Check rate limit
    rate_limit = await client.check_rate_limit()
    remaining = rate_limit['rate']['remaining']
    print(f"✅ API calls remaining: {remaining}")
    
    print("✅ GitHub client test completed")

asyncio.run(test_github())
EOF
```

### Test 5: Error Handling

```bash
python << 'EOF'
import asyncio
from utils.error_handlers import retry_with_backoff

@retry_with_backoff(max_retries=3, base_delay=0.5)
async def flaky_function():
    import random
    if random.random() < 0.7:  # 70% chance of failure
        raise Exception("Simulated failure")
    return "Success!"

async def test_retry():
    try:
        result = await flaky_function()
        print(f"✅ Function succeeded: {result}")
    except Exception as e:
        print(f"❌ Function failed after retries: {e}")

asyncio.run(test_retry())
print("✅ Error handling test completed")
EOF
```

## 📊 Validation Checklist

After installation, verify:

- [ ] All 5 files created in correct locations
- [ ] `__init__.py` files created
- [ ] All imports work without errors
- [ ] Logger creates log files in `logs/` directory
- [ ] Messaging can send/receive via Redis
- [ ] GitHub client can authenticate
- [ ] Error handlers work with retries
- [ ] No import errors or missing dependencies

## 🔧 Configuration Required

### Update `.env` file

Ensure these are set:

```env
GITHUB_TOKEN=your_github_token
GITHUB_USERNAME=mynameishaheer
GITHUB_ORG=  # Optional

REDIS_HOST=localhost
REDIS_PORT=6379

LOG_LEVEL=INFO
```

### Validate Configuration

```bash
python << 'EOF'
from utils.constants import validate_config

if validate_config():
    print("✅ Configuration valid")
else:
    print("❌ Configuration errors detected")
EOF
```

## 📖 Usage Examples

### Example 1: Using Structured Logger in Agents

```python
from utils.structured_logger import get_logger

class MyAgent:
    def __init__(self):
        self.logger = get_logger("my_agent", agent_type="backend")
    
    async def do_work(self):
        self.logger.log_agent_action(
            agent_type="backend",
            action="implement_feature",
            status="started",
            details={"feature": "user_auth"}
        )
        
        # ... do work ...
        
        self.logger.log_agent_action(
            agent_type="backend",
            action="implement_feature",
            status="completed",
            details={"feature": "user_auth", "files_created": 3}
        )
```

### Example 2: Using Messaging Between Agents

```python
from agents.messaging import create_messenger

class BackendAgent:
    def __init__(self):
        self.messenger = create_messenger("backend", "backend_1")
        
        # Register message handler
        self.messenger.register_handler(
            "task_assignment",
            self.handle_task
        )
    
    async def handle_task(self, message):
        print(f"Received task: {message.content}")
        
        # Do work...
        
        # Notify completion
        await self.messenger.notify_completion(
            task_id=message.content.get("task_id"),
            result={"status": "success"},
            notify_agent="project_manager"
        )
    
    async def start(self):
        # Start listening for messages
        await self.messenger.start_listening()
```

### Example 3: Using GitHub Client

```python
from agents.github_client import create_github_client

async def create_project_repo():
    client = create_github_client()
    
    # Create repository
    repo = await client.create_repository(
        name="my-new-project",
        description="Automated project",
        private=False
    )
    
    # Create initial issues
    await client.create_issue(
        repo_name="my-new-project",
        title="Set up project structure",
        body="Initialize project with basic structure",
        labels=["setup"]
    )
    
    # Create feature branch
    await client.create_branch(
        repo_name="my-new-project",
        branch_name="feature/initial-setup",
        from_branch="main"
    )
    
    return repo
```

### Example 4: Using Error Handlers

```python
from utils.error_handlers import retry_with_backoff, ClaudeCodeError

@retry_with_backoff(max_retries=3, base_delay=2.0)
async def call_claude_code(prompt: str):
    # Your Claude Code call logic
    result = subprocess.run(["claude", "-p", prompt], ...)
    
    if result.returncode != 0:
        raise ClaudeCodeError("Claude Code execution failed")
    
    return result
```

## 🎯 Next Steps

With the foundation layer complete, we're ready for **Checkpoint 2**:

1. ✅ **Base Agent Class** - Abstract class using all foundation components
2. ✅ **Product Manager Agent** - First concrete agent implementation
3. ✅ **Test PRD Generation** - Validate the agent works end-to-end

## 📝 Notes

- **Logging**: All logs are JSON-formatted for easy parsing
- **Messaging**: Uses hybrid pub/sub + queue approach
- **Error Handling**: Automatic retries with exponential backoff
- **GitHub**: Full API coverage for automation needs
- **Constants**: Single source of truth for all config

## ⚠️ Common Issues

**Issue**: Import errors for `utils` module
**Fix**: Ensure `utils/__init__.py` exists

**Issue**: Redis connection failed
**Fix**: Verify Redis is running: `redis-cli ping`

**Issue**: GitHub authentication failed
**Fix**: Check `GITHUB_TOKEN` in `.env` file

**Issue**: Permission denied for log files
**Fix**: Ensure `logs/` directory is writable

## 🎉 Success Criteria

Checkpoint 1 is complete when:
- ✅ All files installed and imports work
- ✅ Tests pass without errors  
- ✅ Logger creates JSON log files
- ✅ Redis messaging works
- ✅ GitHub client authenticates
- ✅ Configuration validates

---

**Ready for Checkpoint 2!** 🚀
