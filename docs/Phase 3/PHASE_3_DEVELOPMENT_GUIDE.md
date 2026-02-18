# Phase 3 - Development Guide (Claude Code Autonomous Mode)

**Development Method**: Claude Code CLI on VM (autonomous, self-coding)
**Human Role**: Review and approve milestones
**Automation Level**: Maximum

---

## 🎯 Phase 3 Objectives

### Primary Goals:
1. **Auto-Assignment System**: Issues automatically assigned to appropriate agents
2. **Code Implementation**: Backend/Frontend agents actually implement and test code
3. **QA Agent**: Automated testing and PR approval
4. **Database Agent**: Schema design, migrations, optimization
5. **DevOps Agent**: Deployment automation
6. **Complete Autonomy**: Zero human intervention from idea to deployed app

### Success Criteria:
- ✅ User types: "Build X"
- ✅ System autonomously creates PRD
- ✅ Creates GitHub repo with issues
- ✅ Assigns issues to agents
- ✅ Agents implement code
- ✅ QA tests and approves
- ✅ DevOps deploys
- ✅ User gets: Live application URL

---

## 🤖 Claude Code Autonomous Development Setup

### Prerequisites

1. **Claude Code Configuration**
```bash
# Ensure Claude Code has bypass permissions
export CLAUDE_CODE_BYPASS=true

# Allow all tools
export CLAUDE_CODE_ALLOWED_TOOLS="Write,Edit,Bash,Read"

# Disable interactive prompts
export CLAUDE_CODE_AUTO_APPROVE=true
```

2. **Package Installation Permissions**
```bash
# Allow pip to break system packages
export PIP_BREAK_SYSTEM_PACKAGES=1

# Allow npm global installs
npm config set prefix ~/.npm-global
export PATH=~/.npm-global/bin:$PATH
```

3. **MCP Server Configuration**
Create `~/.config/claude-code/mcp-config.json`:
```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      }
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem"],
      "env": {
        "ALLOWED_DIRECTORIES": "/home/shaheer/ai-dev-pipeline"
      }
    }
  }
}
```

---

## 📋 Claude Code Development Phases

### Phase 3.1: QA Agent (Week 1)
**Goal**: Automated testing and PR approval

**Tasks**:
1. Create `agents/qa_agent.py`
2. Implement test execution (pytest, jest)
3. PR review logic (check tests pass, coverage >80%)
4. Auto-approve or request changes
5. Integration with Project Manager for merging

**Deliverable**: QA agent that tests PRs and approves/rejects

### Phase 3.2: Auto-Assignment System (Week 1-2)
**Goal**: Issues automatically assigned to correct agents

**Tasks**:
1. Issue analyzer (read issue labels/description)
2. Agent selector (backend/frontend/database based on labels)
3. Assignment queue (Redis-based task distribution)
4. Coordinator in Master Agent
5. Status tracking

**Deliverable**: Issues auto-assigned after creation

### Phase 3.3: Database Agent (Week 2)
**Goal**: Schema design and migration management

**Tasks**:
1. Create `agents/database_agent.py`
2. Schema design from PRD requirements
3. Migration generation (Alembic/TypeORM)
4. Query optimization
5. Data integrity checks

**Deliverable**: Database agent creates schemas and migrations

### Phase 3.4: DevOps Agent (Week 3)
**Goal**: Automated deployment pipeline

**Tasks**:
1. Create `agents/devops_agent.py`
2. Docker container generation
3. CI/CD pipeline creation (GitHub Actions)
4. Deployment to staging
5. Health checks and monitoring

**Deliverable**: Auto-deployment to staging environment

### Phase 3.5: Complete Integration (Week 4)
**Goal**: Full end-to-end automation

**Tasks**:
1. Wire all agents together
2. Master Agent orchestration logic
3. Error recovery for entire pipeline
4. Status dashboard
5. E2E testing

**Deliverable**: Complete autonomous development pipeline

---

## 🚀 How to Use Claude Code for Development

### Method 1: Phase-by-Phase Development

**Step 1: Start Claude Code in project directory**
```bash
cd ~/ai-dev-pipeline
source venv/bin/activate
claude
```

**Step 2: Give Phase Instructions**
```
I am continuing development of the AI Development Pipeline.

Current Status: Phase 2 Complete (see docs/PHASE_2_COMPLETE.md)
Next Phase: Phase 3 - QA Agent and Auto-Assignment

Please read these files first:
- docs/PHASE_2_COMPLETE.md
- docs/PHASE_3_DEVELOPMENT_GUIDE.md
- agents/base_agent.py
- agents/product_manager_agent.py

Then:
1. Create agents/qa_agent.py following the BaseAgent pattern
2. Implement test execution (pytest for backend, jest for frontend)
3. Implement PR review logic
4. Create tests for the QA agent
5. Update agent_factory.py to include QA agent
6. Create test_qa_agent.py to verify it works

Follow all coding standards from existing agents.
Use structured logging from utils/structured_logger.py.
Include comprehensive error handling.

Begin with Phase 3.1: QA Agent.
```

### Method 2: Autonomous Multi-Phase Development

Create `claude_dev_instructions.md`:
```markdown
# Claude Code Autonomous Development Instructions

You are developing Phase 3 of the AI Development Pipeline.

## Context
- Read docs/PHASE_2_COMPLETE.md for current state
- Read docs/PHASE_3_DEVELOPMENT_GUIDE.md for Phase 3 plan
- Follow patterns from existing agents

## Development Plan
Execute these phases in order:

### Phase 3.1: QA Agent
1. Create agents/qa_agent.py
2. Implement test execution
3. Implement PR review
4. Write tests
5. Update factory

### Phase 3.2: Auto-Assignment
1. Create assignment logic in Master Agent
2. Implement issue analyzer
3. Create task queue system
4. Test assignment flow

### Phase 3.3: Database Agent
... (continue with all phases)

## Requirements
- Follow BaseAgent pattern
- Use structured logging
- Include error handling with retries
- Write comprehensive tests
- Update documentation
- Commit after each completed feature

## Verification
After each phase:
1. Run tests
2. Verify imports work
3. Test integration with existing agents
4. Update CURRENT_STATE.md

Begin with Phase 3.1.
```

Then run:
```bash
claude -p "$(cat claude_dev_instructions.md)"
```

### Method 3: Interactive Development with Checkpoints

```bash
# Start Claude Code
claude

# Give incremental instructions with verification
> Read docs/PHASE_3_DEVELOPMENT_GUIDE.md
> Create agents/qa_agent.py following the BaseAgent pattern
> [Claude Code creates it]
> Now test that it imports correctly
> [Claude Code tests]
> Now create comprehensive tests in tests/test_qa_agent.py
> [Claude Code creates tests]
> Run the tests
> [Claude Code runs tests]
> If all tests pass, commit the changes
```

---

## 🔧 Claude Code Configuration for Auto-Development

### Create `.clauderc` in project root:
```json
{
  "autoApprove": true,
  "allowedTools": ["Write", "Edit", "Bash", "Read"],
  "workspace": "/home/shaheer/ai-dev-pipeline",
  "pythonEnv": "venv",
  "testCommand": "pytest",
  "lintCommand": "ruff check .",
  "formatCommand": "black .",
  "autoCommit": false,
  "requireTests": true,
  "minCoverage": 80
}
```

### Create `claude_workflow.sh`:
```bash
#!/bin/bash

# Autonomous Claude Code development workflow

cd ~/ai-dev-pipeline
source venv/bin/activate

# Phase 3.1: QA Agent
claude -p "Create QA Agent following Phase 3.1 in docs/PHASE_3_DEVELOPMENT_GUIDE.md. Read existing agents first for patterns. Create agent, tests, and verify."

# Checkpoint: Verify QA Agent
python -c "from agents.qa_agent import QAAgent; print('✅ QA Agent imports')"
pytest tests/test_qa_agent.py

# Phase 3.2: Auto-Assignment
claude -p "Implement auto-assignment system following Phase 3.2. Update Master Agent, create assignment logic, test with mock issues."

# Continue for each phase...
```

---

## 📊 Development Standards for Claude Code

### Code Quality Requirements:
1. **Type Hints**: All functions must have type hints
2. **Docstrings**: Every class and public method
3. **Error Handling**: Use retry decorators from utils/error_handlers.py
4. **Logging**: Use structured logger from utils/structured_logger.py
5. **Tests**: Minimum 80% coverage
6. **Style**: Follow existing agent patterns

### File Organization:
```
agents/
├── qa_agent.py           # New in Phase 3.1
├── database_agent.py     # New in Phase 3.3
├── devops_agent.py       # New in Phase 3.4
└── ...

tests/
├── test_qa_agent.py
├── test_database_agent.py
├── test_devops_agent.py
└── test_integration.py   # E2E tests
```

### Commit Standards:
```
feat(qa): add QA agent with test execution
test(qa): add comprehensive QA agent tests
fix(assignment): handle edge case in issue analyzer
docs(phase3): update development guide
```

---

## 🧪 Testing Strategy

### Unit Tests (Required):
```bash
pytest tests/test_qa_agent.py -v --cov=agents.qa_agent
```

### Integration Tests:
```bash
pytest tests/test_integration.py -v
```

### E2E Test:
```bash
python test_complete_workflow.py
```

### Manual Verification:
```bash
# Test via Discord
python api/discord_bot.py
# !new Build a simple blog
```

---

## 📝 Documentation Requirements

After each phase, Claude Code should update:
1. `CURRENT_STATE.md` - Current progress
2. `docs/PHASE_3_CHECKPOINT_X.md` - Phase completion notes
3. Agent docstrings - Keep in sync with code
4. `README.md` - If user-facing features change

---

## 🎯 Success Milestones

### Milestone 1: QA Agent (Week 1)
- [ ] QA agent created
- [ ] Tests execute correctly
- [ ] PR review logic working
- [ ] Integration tested

### Milestone 2: Auto-Assignment (Week 2)
- [ ] Issues auto-assigned
- [ ] Task queue functional
- [ ] Status tracking working
- [ ] Integration tested

### Milestone 3: Database Agent (Week 2-3)
- [ ] Schema generation working
- [ ] Migrations created
- [ ] Integration tested

### Milestone 4: DevOps Agent (Week 3-4)
- [ ] Docker containers generated
- [ ] CI/CD pipelines created
- [ ] Deployment working
- [ ] Integration tested

### Milestone 5: Complete Integration (Week 4)
- [ ] All agents coordinated
- [ ] E2E test passing
- [ ] Zero human intervention needed
- [ ] Production ready

---

## 🚨 Critical Notes for Claude Code

1. **Always read existing code first** to understand patterns
2. **Use the same imports and structure** as existing agents
3. **Follow the BaseAgent pattern** - don't reinvent
4. **Test before committing** - run pytest
5. **Update docs** - keep CURRENT_STATE.md current
6. **Use structured logging** - never use print()
7. **Handle errors** - use retry decorators
8. **Git discipline** - commit after each feature

---

## 🎓 Learning Resources for Claude Code

Files to read before starting:
1. `agents/base_agent.py` - Base pattern
2. `agents/product_manager_agent.py` - Complete example
3. `agents/project_manager_agent.py` - GitHub integration example
4. `utils/error_handlers.py` - Error handling patterns
5. `utils/structured_logger.py` - Logging patterns

---

**Ready for Claude Code autonomous development!** 🚀
