# Phase 2 - Checkpoint 2: Base Agent + Product Manager

## Overview

Checkpoint 2 builds upon the foundation layer to create the first working agent: the **Product Manager Agent**. This agent can autonomously convert user requirements into comprehensive Product Requirements Documents (PRDs).

## 📦 Components Created

### 1. **Base Agent** (`agents/base_agent.py`)
Abstract base class that all agents inherit from.

**Key Features:**
- Claude Code execution with retry logic
- Structured logging integration
- Agent-to-agent messaging via Redis
- Task assignment handling
- Status management
- Common utility methods

**Core Methods:**
- `call_claude_code()` - Execute Claude Code with error handling
- `execute_task()` - Abstract method for task execution
- `get_capabilities()` - List agent capabilities
- `send_status_update()` - Broadcast status
- `request_help()` - Request assistance from other agents

### 2. **Product Manager Agent** (`agents/product_manager_agent.py`)
First concrete agent implementation.

**Capabilities:**
- Create comprehensive PRDs from requirements
- Define user stories with acceptance criteria
- Prioritize features using MoSCoW method
- Clarify ambiguous requirements
- Create technical specifications
- Define success metrics and KPIs

**Key Methods:**
- `create_prd()` - Generate complete PRD
- `create_user_stories()` - Extract and detail user stories
- `prioritize_features()` - Apply MoSCoW prioritization
- `clarify_requirements()` - Generate clarification questions

### 3. **Agent Factory** (`agents/agent_factory.py`)
Factory pattern for creating agents.

**Features:**
- Registry of available agents
- Easy agent instantiation
- Extensible for new agent types
- Convenience functions

## 📁 Installation Instructions

### Step 1: Transfer Files to VM

```bash
# From your local machine
scp base_agent.py shaheer@vm.devbot.site:~/ai-dev-pipeline/agents/
scp product_manager_agent.py shaheer@vm.devbot.site:~/ai-dev-pipeline/agents/
scp agent_factory.py shaheer@vm.devbot.site:~/ai-dev-pipeline/agents/
```

### Step 2: Verify Installation

```bash
ssh shaheer@vm.devbot.site
cd ~/ai-dev-pipeline
source venv/bin/activate

# Test imports
python << 'EOF'
print("Testing Checkpoint 2 imports...")

from agents.base_agent import BaseAgent
print("✅ BaseAgent imported")

from agents.product_manager_agent import ProductManagerAgent
print("✅ ProductManagerAgent imported")

from agents.agent_factory import AgentFactory, create_product_manager
print("✅ AgentFactory imported")

print("\n🎉 All Checkpoint 2 components imported successfully!")
EOF
```

## 🧪 Testing Guide

### Test 1: Create Product Manager Agent

```bash
python << 'EOF'
from agents.agent_factory import create_product_manager

# Create Product Manager
pm = create_product_manager()

print(f"Created: {pm}")
print(f"Agent Type: {pm.agent_type}")
print(f"Agent ID: {pm.agent_id}")
print(f"Capabilities: {pm.get_capabilities()}")
print(f"Status: {pm.get_status()}")

print("\n✅ Product Manager Agent created successfully!")
EOF
```

### Test 2: Create PRD for Gated Community System

```bash
python << 'EOF'
import asyncio
from agents.product_manager_agent import ProductManagerAgent
from pathlib import Path

async def test_prd_creation():
    # Create Product Manager
    pm = ProductManagerAgent()
    
    # Define requirements
    requirements = """
    Build a gated community management system with the following features:
    
    1. Resident Management
       - Register and manage resident information
       - Track unit ownership and occupancy
       - Maintain contact details
    
    2. Billing System
       - Generate monthly maintenance bills
       - Track payments and dues
       - Send payment reminders
       - Generate billing reports
    
    3. Visitor Management
       - Pre-register visitors
       - Track visitor entry and exit
       - Generate visitor passes
       - Maintain visitor logs
    
    4. Facility Booking
       - Book community facilities (clubhouse, gym, pool)
       - Manage booking calendar
       - Handle booking conflicts
    
    5. Complaint Management
       - Submit and track complaints
       - Assign to relevant staff
       - Track resolution status
    
    Target Users: Residents, Admin staff, Security guards
    Technology: Web-based application, mobile-friendly
    Platform: FastAPI backend + React frontend
    """
    
    # Create project directory
    project_path = Path.home() / "ai-dev-pipeline" / "projects" / "gated-community-mgmt"
    project_path.mkdir(parents=True, exist_ok=True)
    (project_path / "docs").mkdir(exist_ok=True)
    
    print(f"📁 Created project directory: {project_path}")
    
    # Create PRD
    print("\n🔨 Creating PRD...")
    print("This may take 1-2 minutes...\n")
    
    result = await pm.create_prd_from_scratch(
        requirements=requirements,
        project_name="Gated Community Management System",
        project_path=str(project_path)
    )
    
    if result["success"]:
        print(f"✅ PRD created successfully!")
        print(f"📄 PRD Path: {result['prd_path']}")
        print(f"📊 Project: {result['project_name']}")
        
        # Check file exists and show size
        prd_file = Path(result['prd_path'])
        if prd_file.exists():
            size_kb = prd_file.stat().st_size / 1024
            print(f"📏 PRD Size: {size_kb:.2f} KB")
            
            # Show first few lines
            with open(prd_file, 'r') as f:
                lines = f.readlines()[:20]
                print(f"\n📖 First 20 lines of PRD:")
                print("".join(lines))
    else:
        print("❌ PRD creation failed")
        print(result)

# Run test
asyncio.run(test_prd_creation())
EOF
```

### Test 3: Test Agent Messaging

```bash
python << 'EOF'
import asyncio
from agents.product_manager_agent import ProductManagerAgent

async def test_messaging():
    # Create two Product Manager agents
    pm1 = ProductManagerAgent(agent_id="pm1")
    pm2 = ProductManagerAgent(agent_id="pm2")
    
    # Agent 1 sends status update
    await pm1.send_status_update(
        status="ready",
        details={"message": "Product Manager 1 is ready"}
    )
    
    # Agent 2 requests help
    await pm2.request_help(
        from_agent="product_manager",
        problem="Need help clarifying requirements",
        context={"project": "test-project"}
    )
    
    print("✅ Messaging test completed")
    print(f"Agent 1: {pm1}")
    print(f"Agent 2: {pm2}")

asyncio.run(test_messaging())
EOF
```

### Test 4: Test Claude Code Integration

```bash
python << 'EOF'
import asyncio
from agents.product_manager_agent import ProductManagerAgent
from pathlib import Path
import tempfile

async def test_claude_code():
    pm = ProductManagerAgent()
    
    # Create temporary project directory
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)
        (project_path / "docs").mkdir(exist_ok=True)
        
        print(f"Testing Claude Code execution...")
        
        # Simple test: create a file
        result = await pm.call_claude_code(
            prompt="Create a file called docs/test.txt with the text 'Hello from Product Manager Agent'",
            project_path=str(project_path),
            allowed_tools=["Write"]
        )
        
        if result["success"]:
            print("✅ Claude Code execution successful")
            print(f"Return code: {result['return_code']}")
            print(f"Duration: {result['duration']:.2f}s")
            
            # Verify file was created
            test_file = project_path / "docs" / "test.txt"
            if test_file.exists():
                content = test_file.read_text()
                print(f"✅ File created with content: {content}")
            else:
                print("❌ File was not created")
        else:
            print("❌ Claude Code execution failed")
            print(f"Error: {result['stderr']}")

asyncio.run(test_claude_code())
EOF
```

## 📊 Validation Checklist

After installation and testing:

- [ ] All 3 files transferred to VM
- [ ] All imports work without errors
- [ ] Product Manager agent can be created
- [ ] PRD can be generated for test project
- [ ] Agent messaging works
- [ ] Claude Code integration works
- [ ] Logs are being created in `logs/` directory
- [ ] PRD file exists and is comprehensive

## 📖 Usage Examples

### Example 1: Create PRD in Master Agent

```python
from agents.product_manager_agent import ProductManagerAgent

async def create_prd_for_user_request(user_message: str):
    """Integrate PM agent into Master Agent workflow"""
    
    # Create Product Manager
    pm = ProductManagerAgent()
    
    # Determine project details
    project_name = "user-project"
    project_path = f"/home/claude/ai-dev-pipeline/projects/{project_name}"
    
    # Create PRD
    result = await pm.create_prd_from_scratch(
        requirements=user_message,
        project_name=project_name,
        project_path=project_path
    )
    
    return result
```

### Example 2: Agent Communication Pattern

```python
from agents.product_manager_agent import ProductManagerAgent
from agents.messaging import AgentMessage

async def agent_workflow():
    """Example of agent-to-agent communication"""
    
    pm = ProductManagerAgent()
    
    # Register custom handler for project updates
    async def handle_project_update(message: AgentMessage):
        print(f"Received update: {message.content}")
        
        # PM might need to update PRD based on changes
        if message.content.get("update_type") == "feature_change":
            # Update PRD accordingly
            pass
    
    pm.messenger.register_handler("project_update", handle_project_update)
    
    # Start listening for messages
    await pm.start_listening()
```

### Example 3: Using Agent Factory

```python
from agents.agent_factory import AgentFactory, create_product_manager

# Method 1: Use factory
pm1 = AgentFactory.create_agent("product_manager", agent_id="pm1")

# Method 2: Use convenience function
pm2 = create_product_manager(agent_id="pm2")

# Check available agents
available = AgentFactory.get_available_agents()
print(f"Available: {available}")
```

## 🔧 Integration with Master Agent

To integrate the Product Manager Agent into the existing Master Agent:

### Update `master_agent.py`

```python
# Add import at top
from agents.product_manager_agent import ProductManagerAgent

class MasterAgent:
    def __init__(self, ...):
        # ... existing code ...
        
        # Create Product Manager agent
        self.pm_agent = ProductManagerAgent()
    
    async def handle_new_project(self, message: str, user_id: str) -> str:
        """Modified to use PM agent"""
        
        # Create project directory
        project_name = f"project_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        project_path = self.workspace_dir / project_name
        project_path.mkdir(parents=True, exist_ok=True)
        (project_path / "docs").mkdir(exist_ok=True)
        
        # Use PM agent to create PRD
        prd_result = await self.pm_agent.create_prd_from_scratch(
            requirements=message,
            project_name=project_name,
            project_path=str(project_path)
        )
        
        if prd_result["success"]:
            # Continue with project setup...
            # - Initialize git
            # - Create README
            # - Next: Project Manager will create GitHub repo and issues
            
            return f"""
✅ **Project Initialized Successfully!**

📁 **Project Name**: {project_name}
📄 **PRD Created**: {prd_result['prd_path']}

Next steps:
1. ✅ PRD created by Product Manager
2. ⏳ Project Manager will create GitHub repo
3. ⏳ Project Manager will create issues from PRD
4. ⏳ Development agents will implement features

Would you like to review the PRD before proceeding?
            """
```

## 🎯 What's Next: Checkpoint 3

With the Product Manager agent complete, we'll move to **Checkpoint 3: Project Manager Agent + GitHub Integration**:

1. **Project Manager Agent** - Reads PRD, creates GitHub repo, generates issues
2. **GitHub Integration** - Automatic repo creation, issue generation, sprint planning
3. **Workflow Integration** - PM → Project Manager → Dev agents

## 📝 Key Learnings

### Agent Design Patterns

1. **Inheritance**: All agents inherit from `BaseAgent`
2. **Factory Pattern**: Use `AgentFactory` for creation
3. **Async/Await**: All agent operations are async
4. **Messaging**: Agents communicate via Redis pub/sub
5. **Logging**: Structured JSON logs for debugging

### Claude Code Best Practices

1. **Detailed Prompts**: More detail = better results
2. **Context Files**: Use `--context` to include relevant files
3. **Tool Restrictions**: Limit tools to what's needed
4. **Error Handling**: Always use retry logic
5. **Verification**: Check output files exist and are valid

## ⚠️ Common Issues

**Issue**: Agent creation fails with import error
**Fix**: Ensure all foundation files (Checkpoint 1) are installed

**Issue**: Claude Code timeout
**Fix**: Increase timeout or simplify prompt

**Issue**: PRD file not created
**Fix**: Ensure docs/ directory exists in project path

**Issue**: Messaging not working
**Fix**: Verify Redis is running: `redis-cli ping`

## 🎉 Success Criteria

Checkpoint 2 is complete when:
- ✅ Base Agent class implemented
- ✅ Product Manager Agent working
- ✅ PRD can be generated for test project
- ✅ Agent Factory functional
- ✅ All tests pass
- ✅ Integration path clear for Master Agent

---

**Ready for Checkpoint 3!** 🚀

## 📚 Files Summary

| File | Lines | Purpose |
|------|-------|---------|
| `base_agent.py` | 518 | Abstract base class for all agents |
| `product_manager_agent.py` | 442 | Product Manager implementation |
| `agent_factory.py` | 127 | Factory for agent creation |
| **Total** | **1,087** | **Checkpoint 2 code** |

Combined with Checkpoint 1: **4,558 lines of production code!**
