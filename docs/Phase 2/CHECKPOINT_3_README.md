# Phase 2 - Checkpoint 3: Project Manager + GitHub Integration

## Overview

Checkpoint 3 adds the **Project Manager Agent** which automates the entire GitHub workflow:
- Creates repositories automatically
- Generates issues from PRD user stories
- Sets up branches, labels, and protection rules
- Manages pull requests and merging
- Coordinates development agent assignments

This completes the **planning phase** of the pipeline: Requirements → PRD → GitHub Repo with Issues

## 📦 Components Created

### 1. **Project Manager Agent** (`agents/project_manager_agent.py`)
Autonomous GitHub repository and project management.

**Core Capabilities:**
- ✅ Create GitHub repositories with proper structure
- ✅ Parse PRD and extract user stories
- ✅ Generate GitHub issues from user stories
- ✅ Create development branches
- ✅ Set up branch protection rules
- ✅ Create standard labels
- ✅ Manage pull requests
- ✅ Merge approved PRs
- ✅ Coordinate agent assignments

**Key Methods:**
- `setup_complete_project()` - Full project setup workflow
- `create_repository()` - Create GitHub repo
- `create_issues_from_prd()` - Generate issues from PRD
- `merge_pull_request()` - Merge approved PRs
- `assign_issue_to_agent()` - Assign work to agents

### 2. **Updated Agent Factory** (`agents/agent_factory.py`)
Now includes Project Manager.

### 3. **End-to-End Test** (`test_checkpoint3.py`)
Complete workflow demonstration.

## 📁 Installation Instructions

### Step 1: Transfer Files to VM

```bash
# From your local machine
scp project_manager_agent.py shaheer@vm.devbot.site:~/ai-dev-pipeline/agents/
scp agent_factory_updated.py shaheer@vm.devbot.site:~/ai-dev-pipeline/agents/agent_factory.py
scp test_checkpoint3.py shaheer@vm.devbot.site:~/ai-dev-pipeline/
```

### Step 2: Verify Installation

```bash
ssh shaheer@vm.devbot.site
cd ~/ai-dev-pipeline
source venv/bin/activate

# Test imports
python << 'EOF'
print("Testing Checkpoint 3 imports...")

from agents.project_manager_agent import ProjectManagerAgent
print("✅ ProjectManagerAgent imported")

from agents.agent_factory import create_project_manager
print("✅ create_project_manager imported")

print("\n🎉 All Checkpoint 3 components imported successfully!")
EOF
```

## 🧪 Testing Guide

### Test 1: Quick Agent Creation Test

```bash
python test_checkpoint3.py --quick
```

Expected output:
```
🧪 Quick Agent Creation Test
----------------------------------------------------------------------
✅ Product Manager: ProductManagerAgent(...)
   Status: {...}
✅ Project Manager: ProjectManagerAgent(...)
   Status: {...}

✅ Both agents created successfully!
```

### Test 2: Full End-to-End Workflow (THE BIG ONE!)

This will create a **REAL GitHub repository** with issues!

```bash
python test_checkpoint3.py
```

**What This Does:**
1. Creates Product Manager agent
2. Generates comprehensive PRD (2-3 minutes)
3. Creates Project Manager agent
4. Creates GitHub repository
5. Creates dev branch
6. Sets up branch protection
7. Creates standard labels
8. Extracts user stories from PRD
9. Creates GitHub issues for each story
10. Creates initial README

**Duration**: 5-8 minutes total

**Expected Output:**
```
======================================================================
🚀 CHECKPOINT 3: END-TO-END WORKFLOW TEST
======================================================================

📋 STEP 1: Creating Product Manager Agent
----------------------------------------------------------------------
✅ Created: ProductManagerAgent(pm_main)
   Capabilities: Create PRD from requirements, Define user stories, ...

📝 STEP 2: Generating PRD
----------------------------------------------------------------------
⏳ This will take 2-3 minutes...

✅ PRD Created Successfully!
   📄 Path: /home/shaheer/ai-dev-pipeline/projects/gated-community-system/docs/PRD.md
   📏 Size: 41.09 KB

🗂️  STEP 3: Creating Project Manager Agent
----------------------------------------------------------------------
✅ Created: ProjectManagerAgent(pm_github)
   Capabilities: Create GitHub repositories, Generate issues from PRD, ...

🐙 STEP 4: Setting up GitHub Repository
----------------------------------------------------------------------
⏳ Creating repository, branches, labels, and issues...
   This may take 2-3 minutes...

✅ GitHub Project Setup Complete!

📊 RESULTS:
----------------------------------------------------------------------
📦 Repository: https://github.com/mynameishaheer/gated-community-system
   Clone URL: https://github.com/mynameishaheer/gated-community-system.git

📋 Issues Created: 12

   First 5 issues:
   #1: Set up project structure
      URL: https://github.com/mynameishaheer/gated-community-system/issues/1
   #2: Implement user authentication
      URL: https://github.com/mynameishaheer/gated-community-system/issues/2
   ...

✅ Steps Completed: 6
   ✓ Repository Created
   ✓ Dev Branch Created
   ✓ Branch Protection Set
   ✓ Labels Created
   ✓ Issues Created
   ✓ Initial Files Created

======================================================================
🎉 WORKFLOW TEST COMPLETED SUCCESSFULLY!
======================================================================
```

### Test 3: Manual Repository Creation

```bash
python << 'EOF'
import asyncio
from agents.project_manager_agent import ProjectManagerAgent

async def test_repo_creation():
    pm = ProjectManagerAgent()
    
    result = await pm.create_repository({
        "repo_name": "test-project-checkpoint3",
        "description": "Test repository created in Checkpoint 3",
        "private": False
    })
    
    if result["success"]:
        print(f"✅ Repository created!")
        print(f"   URL: {result['repo_url']}")
        print(f"   Clone: {result['clone_url']}")
    else:
        print("❌ Failed:", result)

asyncio.run(test_repo_creation())
EOF
```

### Test 4: Issue Creation from Existing PRD

```bash
python << 'EOF'
import asyncio
from agents.project_manager_agent import ProjectManagerAgent

async def test_issue_creation():
    pm = ProjectManagerAgent()
    
    # Use the PRD we created in Checkpoint 2
    prd_path = "/home/shaheer/ai-dev-pipeline/projects/gated-community-mgmt/docs/PRD.md"
    
    result = await pm.create_issues_from_prd({
        "repo_name": "your-existing-repo",  # Replace with actual repo name
        "prd_path": prd_path
    })
    
    if result["success"]:
        print(f"✅ Created {result['issues_created']} issues")
        for issue in result.get('issues', [])[:5]:
            print(f"   #{issue['number']}: {issue['title']}")

asyncio.run(test_issue_creation())
EOF
```

## 📊 Validation Checklist

After installation and testing:

- [ ] Project Manager agent can be imported
- [ ] Agent Factory includes both PM and Project Manager
- [ ] GitHub client can authenticate
- [ ] Repository can be created
- [ ] Dev branch can be created
- [ ] Labels can be created
- [ ] Issues can be created from PRD
- [ ] Full end-to-end test completes successfully
- [ ] Real GitHub repository exists with issues

## 🎯 What This Enables

### Complete Planning Automation

**Before**: Manual project setup taking hours
```
1. Create GitHub repo manually
2. Create issues manually
3. Set up branches manually
4. Configure settings manually
5. Create labels manually
```

**Now**: Automated in 5-8 minutes
```
User: "Build a gated community system with billing and visitor management"
  ↓
Product Manager: Creates comprehensive PRD (3 mins)
  ↓
Project Manager: Sets up complete GitHub project (3 mins)
  ↓
Result: Production-ready repo with 10-20 issues ready for development
```

### The Workflow

```
┌─────────────────────┐
│   User Request      │
│ "Build X with Y"    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Product Manager    │
│  Creates PRD        │
│  • User stories     │
│  • Requirements     │
│  • Tech specs       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Project Manager    │
│  • Creates repo     │
│  • Creates issues   │
│  • Sets up branches │
│  • Creates labels   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Development Ready   │
│ • Repo: ✅          │
│ • Issues: ✅        │
│ • Branches: ✅      │
│ • Ready to code ✅  │
└─────────────────────┘
```

## 🔧 Integration with Master Agent

### Update `master_agent.py`

```python
from agents.product_manager_agent import ProductManagerAgent
from agents.project_manager_agent import ProjectManagerAgent

class MasterAgent:
    def __init__(self, ...):
        # ... existing code ...
        
        # Create agents
        self.pm_agent = ProductManagerAgent()
        self.project_mgr = ProjectManagerAgent()
    
    async def handle_new_project(self, message: str, user_id: str) -> str:
        """Complete autonomous project setup"""
        
        # Step 1: Create project directory
        project_name = f"project_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        project_path = self.workspace_dir / project_name
        project_path.mkdir(parents=True, exist_ok=True)
        (project_path / "docs").mkdir(exist_ok=True)
        
        # Step 2: Product Manager creates PRD
        prd_result = await self.pm_agent.create_prd_from_scratch(
            requirements=message,
            project_name=project_name,
            project_path=str(project_path)
        )
        
        if not prd_result["success"]:
            return "❌ Failed to create PRD"
        
        # Step 3: Project Manager sets up GitHub
        github_result = await self.project_mgr.setup_complete_project({
            "project_name": project_name,
            "description": f"Project created from user request",
            "prd_path": prd_result['prd_path']
        })
        
        if github_result["success"]:
            return f"""
✅ **Project Created Successfully!**

📁 **Project**: {project_name}
📄 **PRD**: {prd_result['prd_path']}
🐙 **GitHub**: {github_result['repository']['repo_url']}
📋 **Issues**: {github_result['issues']['issues_created']} created

**Next Steps**:
1. ✅ PRD created by Product Manager
2. ✅ GitHub repo and issues created by Project Manager
3. ⏳ Development agents will be assigned to implement features
4. ⏳ Each agent will create PRs for their work
5. ⏳ Project Manager will merge approved PRs

Your project is ready for development! 🚀
            """
        else:
            return "❌ GitHub setup failed"
```

## 📖 Usage Examples

### Example 1: Complete Project Setup

```python
from agents.product_manager_agent import ProductManagerAgent
from agents.project_manager_agent import ProjectManagerAgent

async def autonomous_project_setup(user_request: str):
    """
    Fully autonomous project setup from user request
    """
    
    # Create agents
    pm = ProductManagerAgent()
    project_mgr = ProjectManagerAgent()
    
    # Generate PRD
    prd_result = await pm.create_prd_from_scratch(
        requirements=user_request,
        project_name="my-project",
        project_path="/path/to/project"
    )
    
    # Set up GitHub
    github_result = await project_mgr.setup_complete_project({
        "project_name": "my-project",
        "description": "My awesome project",
        "prd_path": prd_result['prd_path']
    })
    
    return github_result
```

### Example 2: Just Create Repository

```python
from agents.project_manager_agent import ProjectManagerAgent

async def create_repo_only():
    pm = ProjectManagerAgent()
    
    result = await pm.create_repository({
        "repo_name": "my-new-repo",
        "description": "A new repository",
        "private": False
    })
    
    print(f"Repo URL: {result['repo_url']}")
```

### Example 3: Agent Coordination

```python
async def coordinate_development():
    """
    Example of how Project Manager coordinates with dev agents
    """
    
    pm = ProjectManagerAgent()
    
    # Get issues from repo
    # Assign to appropriate agents based on labels
    
    # Backend issue → Backend Agent
    await pm.assign_issue_to_agent({
        "repo_name": "my-project",
        "issue_number": 5,
        "agent_type": "backend"
    })
    
    # Frontend issue → Frontend Agent
    await pm.assign_issue_to_agent({
        "repo_name": "my-project",
        "issue_number": 6,
        "agent_type": "frontend"
    })
```

## 🎯 What's Next: Checkpoint 4

With planning automation complete, we'll create the **Development Agents**:

### **Checkpoint 4: Backend + Frontend + Database Agents**

These agents will:
1. **Backend Agent**
   - Receive assigned issues
   - Create feature branches
   - Implement APIs using Claude Code
   - Write tests
   - Create pull requests

2. **Frontend Agent**
   - Implement UI components
   - Integrate with APIs
   - Write tests
   - Create pull requests

3. **Database Agent**
   - Design schemas
   - Create migrations
   - Optimize queries

Then the complete workflow becomes:
```
User Request 
  → Product Manager (PRD) ✅
    → Project Manager (GitHub) ✅
      → Backend Agent (API implementation) ⏳ NEXT
      → Frontend Agent (UI implementation) ⏳ NEXT
      → Database Agent (schema) ⏳ NEXT
        → QA Agent (testing) ⏳ LATER
          → DevOps Agent (deployment) ⏳ LATER
```

## ⚠️ Common Issues

**Issue**: GitHub API authentication failed
**Fix**: Verify `GITHUB_TOKEN` in `.env` is valid

**Issue**: Repository already exists
**Fix**: GitHub prevents duplicate names - choose a different name or delete the existing repo

**Issue**: PRD extraction fails
**Fix**: The agent will fall back to creating default issues

**Issue**: Rate limit exceeded
**Fix**: The agent has retry logic with exponential backoff - just wait

## 🎉 Success Criteria

Checkpoint 3 is complete when:
- ✅ Project Manager Agent implemented
- ✅ Can create GitHub repositories
- ✅ Can extract stories from PRD
- ✅ Can create issues automatically
- ✅ Full end-to-end test passes
- ✅ Real GitHub repo created with issues
- ✅ Agent Factory updated
- ✅ Integration path clear

---

## 📚 Files Summary

| File | Lines | Purpose |
|------|-------|---------|
| `project_manager_agent.py` | 782 | Project Manager implementation |
| `agent_factory.py` | 137 | Updated factory with PM |
| `test_checkpoint3.py` | 238 | End-to-end workflow test |
| **Total** | **1,157** | **Checkpoint 3 code** |

**Phase 2 Total**: 6,304 lines of production code! 🚀

---

**Ready to run the full test? Let's see it create a real GitHub repository!** 🎉
