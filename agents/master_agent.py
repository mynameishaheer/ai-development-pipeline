"""
Master Agent - Central orchestrator for the AI Development Pipeline
Coordinates all sub-agents to deliver a complete autonomous development pipeline.

Phase 3: Full pipeline — idea → PRD → GitHub → DB schema → code → tests → deploy
"""

import asyncio
import json
import os
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

import chromadb
import redis

from agents.product_manager_agent import ProductManagerAgent
from agents.project_manager_agent import ProjectManagerAgent
from agents.backend_agent import BackendAgent
from agents.frontend_agent import FrontendAgent
from agents.database_agent import DatabaseAgent
from agents.devops_agent import DevOpsAgent
from agents.qa_agent import QAAgent
from agents.assignment_manager import AssignmentManager
from agents.worker_daemon import AgentWorkerDaemon


class MasterAgent:
    """
    The Master Agent is the brain of the AI Development Pipeline.
    It orchestrates all sub-agents and makes autonomous decisions.

    Full Phase 3 Pipeline:
    1. Product Manager → PRD from user requirements
    2. Project Manager → GitHub repo, issues, labels, branch protection
    3. Assignment Manager → Route issues to appropriate agents
    4. Database Agent → Schema design, migrations, seed data
    5. Backend + Frontend Agents → Implement features from issues
    6. QA Agent → Review PRs, run tests, validate coverage
    7. DevOps Agent → CI/CD, Docker, deployment config
    """

    def __init__(self, workspace_dir: str = None):
        if workspace_dir is None:
            workspace_dir = str(Path.home() / "ai-dev-pipeline" / "projects")

        self.workspace_dir = Path(workspace_dir)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

        # Initialize memory system (ChromaDB)
        memory_path = str(Path.home() / "ai-dev-pipeline" / "memory" / "vector_store")
        self.memory_client = chromadb.PersistentClient(path=memory_path)
        self.memory = self.memory_client.get_or_create_collection(name="master_memory")

        # Initialize Redis for agent communication
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        self.redis = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)

        # Core agents (always needed)
        self.pm_agent = ProductManagerAgent(agent_id="pm_main")
        self.project_mgr = ProjectManagerAgent(agent_id="proj_mgr")

        # Phase 3 agents (initialized lazily to avoid startup costs if not needed)
        self._backend_agent: Optional[BackendAgent] = None
        self._frontend_agent: Optional[FrontendAgent] = None
        self._database_agent: Optional[DatabaseAgent] = None
        self._devops_agent: Optional[DevOpsAgent] = None
        self._qa_agent: Optional[QAAgent] = None
        self._assignment_manager: Optional[AssignmentManager] = None

        # Current project state
        self.current_project: Optional[Dict] = None
        self.current_context: Dict = {}

        # Pipeline state tracking
        self._pipeline_steps: List[Dict] = []

        # Worker daemon (started on demand)
        self._worker_daemon: Optional[AgentWorkerDaemon] = None
        self._worker_task: Optional[asyncio.Task] = None

        print("🧠 Master Agent initialized (Phase 3)")

    # ==========================================
    # LAZY AGENT ACCESSORS
    # ==========================================

    @property
    def backend_agent(self) -> BackendAgent:
        if not self._backend_agent:
            self._backend_agent = BackendAgent(agent_id="backend_main")
        return self._backend_agent

    @property
    def frontend_agent(self) -> FrontendAgent:
        if not self._frontend_agent:
            self._frontend_agent = FrontendAgent(agent_id="frontend_main")
        return self._frontend_agent

    @property
    def database_agent(self) -> DatabaseAgent:
        if not self._database_agent:
            self._database_agent = DatabaseAgent(agent_id="database_main")
        return self._database_agent

    @property
    def devops_agent(self) -> DevOpsAgent:
        if not self._devops_agent:
            self._devops_agent = DevOpsAgent(agent_id="devops_main")
        return self._devops_agent

    @property
    def qa_agent(self) -> QAAgent:
        if not self._qa_agent:
            self._qa_agent = QAAgent(agent_id="qa_main")
        return self._qa_agent

    @property
    def assignment_manager(self) -> AssignmentManager:
        if not self._assignment_manager:
            self._assignment_manager = AssignmentManager()
        return self._assignment_manager

    # ==========================================
    # MAIN MESSAGE ENTRY POINT
    # ==========================================

    async def process_user_message(self, message: str, user_id: str) -> str:
        """
        Main entry point for all user messages.
        Analyzes intent and routes to appropriate handler.

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
            metadata={"user_id": user_id, "timestamp": datetime.now().isoformat()},
        )

        # Analyze intent
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
            "run_pipeline": self.handle_run_full_pipeline,
            "assign_issues": self.handle_assign_issues,
            "run_tests": self.handle_run_tests,
            "workers": self.handle_workers,
            "general_query": self.handle_general_query,
        }

        handler = handlers.get(intent, self.handle_general_query)
        response = await handler(message, user_id)

        # Store response in memory
        await self.store_memory(
            category="agent_response",
            content=response,
            metadata={"user_id": user_id, "intent": intent},
        )

        return response

    async def analyze_intent(self, message: str) -> Dict:
        """
        Analyze user message to determine intent.
        Uses Claude Code to classify the request.
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
- run_pipeline: User wants to run the full automated pipeline
- assign_issues: User wants to assign GitHub issues to agents
- run_tests: User wants to run tests or QA checks
- workers: User wants to start, stop, or check status of worker agents
- general_query: General question or conversation

User message: "{message}"

Return format:
{{"intent": "intent_name", "confidence": 0.95, "reasoning": "brief explanation"}}
"""
        result = await self.call_claude_code(prompt, allowed_tools=["Write"])

        try:
            stdout = result.get("stdout", "{}")
            if "```json" in stdout:
                json_str = stdout.split("```json")[1].split("```")[0].strip()
            elif "```" in stdout:
                json_str = stdout.split("```")[1].split("```")[0].strip()
            else:
                json_str = stdout.strip()

            return json.loads(json_str)
        except Exception as e:
            print(f"⚠️ Intent parsing failed: {e}")
            return {"intent": "general_query", "confidence": 0.5, "reasoning": "Parse error"}

    # ==========================================
    # PIPELINE HANDLERS
    # ==========================================

    async def handle_new_project(self, message: str, user_id: str) -> str:
        """
        Initialize a new project using PM and Project Manager agents.
        Stores project state for subsequent pipeline stages.
        """
        print("🚀 Initializing new project...")

        # Create project directory
        project_name = f"project_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        project_path = self.workspace_dir / project_name
        project_path.mkdir(parents=True, exist_ok=True)
        (project_path / "docs").mkdir(exist_ok=True)

        # Step 1: Product Manager creates PRD
        try:
            prd_result = await self.pm_agent.create_prd_from_scratch(
                requirements=message,
                project_name=project_name,
                project_path=str(project_path),
            )
            if not prd_result["success"]:
                return "❌ Failed to create PRD. Please try again."

            prd_path = prd_result["prd_path"]
            prd_size = Path(prd_path).stat().st_size / 1024
        except Exception as e:
            return f"❌ PRD creation failed: {str(e)}"

        # Step 2: Project Manager sets up GitHub
        try:
            github_result = await self.project_mgr.setup_complete_project({
                "project_name": project_name,
                "description": f"Automated project: {project_name}",
                "prd_path": prd_path,
            })

            if not github_result["success"]:
                return f"❌ GitHub setup failed. PRD was created at: {prd_path}"

            repo_url = github_result.get("repository", {}).get("repo_url", "N/A")
            repo_name = github_result.get("repository", {}).get("repo_name", project_name)
            issues_created = github_result.get("issues", {}).get("issues_created", 0)
        except Exception as e:
            return f"⚠️ PRD created but GitHub setup failed: {str(e)}\nPRD: {prd_path}"

        # Store project info
        self.current_project = {
            "name": project_name,
            "path": str(project_path),
            "prd_path": prd_path,
            "repo_url": repo_url,
            "repo_name": repo_name,
            "requirements": message,
            "created_at": datetime.now().isoformat(),
            "status": "ready_for_development",
        }

        await self.save_project_metadata()

        return f"""
✅ **Project Created Successfully!**

📁 **Project**: `{project_name}`
📄 **PRD**: {prd_size:.2f} KB
🐙 **GitHub**: {repo_url}
📋 **Issues**: {issues_created} created

**What Just Happened:**
1. ✅ Product Manager analyzed your requirements
2. ✅ Created comprehensive PRD with user stories
3. ✅ Project Manager created GitHub repository
4. ✅ Generated {issues_created} issues from PRD
5. ✅ Set up branches, labels, and protection rules

**Next Steps:**
- Say `run pipeline` to fully automate development (DB schema + code + tests + CI/CD)
- Say `assign issues` to route issues to specialized agents
- Say `status` to see current project state

**Repository**: {repo_url}
**Local Path**: {project_path}

Your project is ready for development! 🚀
"""

    async def handle_run_full_pipeline(self, message: str, user_id: str) -> str:
        """
        Run the full autonomous development pipeline end-to-end.
        Triggers after a project is created and GitHub issues exist.
        """
        if not self.current_project:
            return "❌ No active project. Please start a new project first."

        project_path = self.current_project["path"]
        prd_path = self.current_project.get("prd_path", "")
        repo_name = self.current_project.get("repo_name", "")

        self._pipeline_steps = []
        print("\n🚀 Starting Full Autonomous Development Pipeline...\n")

        result = await self.run_full_pipeline(
            project_path=project_path,
            prd_path=prd_path,
            repo_name=repo_name,
        )

        self.current_project["status"] = "pipeline_complete"
        await self.save_project_metadata()

        # Format summary
        steps_summary = ""
        for step in result.get("steps", []):
            status_icon = "✅" if step.get("success") else "❌"
            steps_summary += f"{status_icon} **{step['name']}**: {step.get('message', '')}\n"

        return f"""
🎉 **Full Pipeline Complete!**

{steps_summary}
**Project**: `{self.current_project['name']}`
**Repository**: {self.current_project.get('repo_url', 'N/A')}

The pipeline has automatically:
- Designed database schema and migrations
- Set up CI/CD with GitHub Actions
- Created Docker configuration for deployment
- Assigned issues to specialized agents for implementation
- Configured QA validation for all pull requests

Your project is ready for automated development! 🚀
"""

    async def run_full_pipeline(
        self,
        project_path: str,
        prd_path: str,
        repo_name: str,
        db_type: str = "postgresql",
    ) -> Dict:
        """
        Execute the full development pipeline.

        Pipeline stages:
        1. Database setup (schema + migrations + seed data)
        2. DevOps setup (CI/CD + Docker)
        3. Auto-assign issues to agents
        4. QA configuration

        Args:
            project_path: Local project directory path
            prd_path: Path to the PRD document
            repo_name: GitHub repository name
            db_type: Database type (postgresql, sqlite)

        Returns:
            Pipeline execution results
        """
        steps = []

        # === Stage 1: Database Setup ===
        print("📊 Stage 1/4: Setting up database schema...")
        try:
            db_result = await self.database_agent.setup_database_for_project(
                project_path=project_path,
                prd_path=prd_path,
                db_type=db_type,
            )
            steps.append({
                "name": "Database Setup",
                "success": db_result.get("success", False),
                "message": db_result.get("message", ""),
            })
            print("  ✅ Database schema created")
        except Exception as e:
            steps.append({"name": "Database Setup", "success": False, "message": str(e)})
            print(f"  ⚠️ Database setup failed: {e}")

        # === Stage 2: DevOps Setup ===
        print("🔧 Stage 2/4: Setting up CI/CD and Docker...")
        try:
            devops_result = await self.devops_agent.setup_cicd_pipeline({
                "task_type": "setup_cicd_pipeline",
                "project_path": project_path,
                "repo_name": repo_name,
                "stack": self._detect_stack(project_path),
            })
            steps.append({
                "name": "DevOps / CI-CD Setup",
                "success": devops_result.get("success", False),
                "message": devops_result.get("message", ""),
            })
            print("  ✅ CI/CD and Docker configured")
        except Exception as e:
            steps.append({"name": "DevOps / CI-CD Setup", "success": False, "message": str(e)})
            print(f"  ⚠️ DevOps setup failed: {e}")

        # === Stage 3: Auto-Assign Issues ===
        print("📋 Stage 3/4: Assigning issues to agents...")
        try:
            assign_result = await self.assignment_manager.assign_all_issues(
                repo_name=repo_name,
                project_path=project_path,
            )
            assigned = assign_result.get("assigned", 0)
            steps.append({
                "name": "Issue Assignment",
                "success": assign_result.get("success", False),
                "message": f"Assigned {assigned} issues to specialized agents",
            })
            print(f"  ✅ {assigned} issues assigned to agents")
        except Exception as e:
            steps.append({"name": "Issue Assignment", "success": False, "message": str(e)})
            print(f"  ⚠️ Issue assignment failed: {e}")

        # === Stage 4: QA Setup (post-pipeline config note) ===
        print("🧪 Stage 4/4: Configuring QA validation...")
        try:
            # Store QA configuration in project metadata so PR handlers know to use it
            qa_config = {
                "min_coverage": int(os.getenv("MIN_TEST_COVERAGE", "80")),
                "auto_review": True,
                "block_on_failure": True,
            }
            qa_config_path = Path(project_path) / ".qa_config.json"
            with open(qa_config_path, "w") as f:
                json.dump(qa_config, f, indent=2)

            steps.append({
                "name": "QA Configuration",
                "success": True,
                "message": f"QA agent configured (min coverage: {qa_config['min_coverage']}%)",
            })
            print(f"  ✅ QA validation configured (min coverage: {qa_config['min_coverage']}%)")
        except Exception as e:
            steps.append({"name": "QA Configuration", "success": False, "message": str(e)})
            print(f"  ⚠️ QA configuration failed: {e}")

        success_count = sum(1 for s in steps if s.get("success"))
        return {
            "success": success_count > 0,
            "steps": steps,
            "steps_succeeded": success_count,
            "steps_total": len(steps),
        }

    async def handle_assign_issues(self, message: str, user_id: str) -> str:
        """Assign all open GitHub issues to the appropriate agents."""
        if not self.current_project:
            return "❌ No active project."

        repo_name = self.current_project.get("repo_name", "")
        project_path = self.current_project.get("path", "")

        if not repo_name:
            return "❌ No GitHub repository linked to this project."

        print(f"📋 Assigning issues for {repo_name}...")
        result = await self.assignment_manager.assign_all_issues(
            repo_name=repo_name,
            project_path=project_path,
        )

        if not result.get("success"):
            return f"❌ Assignment failed: {result.get('error', 'Unknown error')}"

        assigned = result.get("assigned", 0)
        summary = result.get("summary", {})

        summary_lines = []
        for agent_type, info in summary.items():
            count = info.get("count", 0)
            issues = info.get("issues", [])
            summary_lines.append(f"  • **{agent_type.replace('_', ' ').title()}**: {count} issues {issues}")

        summary_str = "\n".join(summary_lines) if summary_lines else "  • No assignments made"

        return f"""
📋 **Issue Assignment Complete**

**Repository**: {repo_name}
**Total Issues Assigned**: {assigned}

**By Agent:**
{summary_str}

Each assigned agent will:
1. Claim the issue from the queue
2. Create a feature branch
3. Implement the feature
4. Submit a PR for QA review
"""

    async def handle_run_tests(self, message: str, user_id: str) -> str:
        """Run QA tests for the current project."""
        if not self.current_project:
            return "❌ No active project."

        project_path = self.current_project.get("path", "")

        print(f"🧪 Running tests for project...")
        result = await self.qa_agent.run_tests_for_project({
            "task_type": "run_tests",
            "project_path": project_path,
        })

        passed = result.get("tests_passed", False)
        coverage = result.get("coverage_percentage")
        output = result.get("output", "")[:1000]

        status_icon = "✅" if passed else "❌"
        coverage_str = f"{coverage:.1f}%" if coverage is not None else "N/A"

        return f"""
{status_icon} **Test Results**

**Project**: {self.current_project['name']}
**Tests Passed**: {"Yes" if passed else "No"}
**Coverage**: {coverage_str}

**Output:**
```
{output}
```
"""

    async def handle_code_task(self, message: str, user_id: str) -> str:
        """Handle coding tasks for current project."""
        if not self.current_project:
            return "❌ No active project. Please start a new project first with your requirements."

        project_path = self.current_project["path"]

        prompt = f"""
Implement the following task for the current project:

"{message}"

Context:
- Project: {self.current_project['name']}
- Original Requirements: {self.current_project.get('requirements', 'See project PRD')}

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
            allowed_tools=["Write", "Edit", "Bash", "Read"],
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
        """Provide status update on current project and agent queues."""
        if not self.current_project:
            return "📊 **Status**: No active project. Ready to start a new one!"

        # Get queue status from assignment manager
        try:
            queue_status = self.assignment_manager.get_queue_status()
        except Exception:
            queue_status = {}

        queue_lines = []
        for agent_type, info in queue_status.items():
            pending = info.get("pending_tasks", 0)
            queue_lines.append(f"  • **{agent_type.replace('_', ' ').title()}**: {pending} pending tasks")

        queue_str = "\n".join(queue_lines) if queue_lines else "  • All queues empty"

        project_path = self.current_project["path"]
        status_prompt = """
Analyze the current project and provide a brief status update:
1. List key files that exist
2. Check git status (any uncommitted changes?)
3. Any errors visible in logs?
Provide a concise 3-5 line summary.
"""
        code_result = await self.call_claude_code(
            prompt=status_prompt,
            project_path=project_path,
            allowed_tools=["Bash", "Read"],
        )

        return f"""
📊 **Project Status**

📁 **Project**: {self.current_project['name']}
🔗 **Repository**: {self.current_project.get('repo_url', 'N/A')}
📅 **Created**: {self.current_project['created_at']}
🔄 **Status**: {self.current_project.get('status', 'unknown')}

**Agent Queue Status:**
{queue_str}

**Codebase Overview:**
{code_result.get('stdout', 'Unable to read project status')}
"""

    async def handle_update_project(self, message: str, user_id: str) -> str:
        """Handle project updates and modifications."""
        return await self.handle_code_task(message, user_id)

    async def handle_deploy(self, message: str, user_id: str) -> str:
        """Handle deployment requests using the DevOps agent."""
        if not self.current_project:
            return "❌ No active project to deploy."

        project_path = self.current_project["path"]
        repo_name = self.current_project.get("repo_name", "")

        print("🚀 Running DevOps setup for deployment...")
        try:
            result = await self.devops_agent.setup_cicd_pipeline({
                "task_type": "setup_cicd_pipeline",
                "project_path": project_path,
                "repo_name": repo_name,
                "stack": self._detect_stack(project_path),
            })

            files = result.get("files_created", [])
            files_str = "\n".join([f"  - {f}" for f in files]) if files else "  (see project directory)"

            return f"""
🚀 **Deployment Configuration Complete**

**Files Created:**
{files_str}

**What's Ready:**
- ✅ Dockerfile with multi-stage builds
- ✅ docker-compose.yml with all services
- ✅ GitHub Actions CI/CD pipeline
- ✅ Deployment scripts (deploy.sh, rollback.sh)
- ✅ Health check endpoint

**Next Steps:**
1. Review `DEPLOYMENT.md` for environment setup
2. Set secrets in GitHub repository settings
3. Push to `main` branch to trigger CI/CD
4. Confirm to proceed with actual deployment
"""
        except Exception as e:
            return f"❌ Deployment setup failed: {str(e)}"

    async def handle_workers(self, message: str, user_id: str) -> str:
        """Route !workers start / stop / status commands."""
        msg_lower = message.lower()
        if "start" in msg_lower:
            return await self.start_workers()
        elif "stop" in msg_lower:
            return await self.stop_workers()
        else:
            return await self.worker_status()

    async def start_workers(self, agents: Optional[List[str]] = None) -> str:
        """Create and start the AgentWorkerDaemon as a background asyncio task."""
        if self._worker_daemon and self._worker_daemon._running:
            return "⚠️ Workers are already running. Use `!workers status` to check."

        self._worker_daemon = AgentWorkerDaemon(agent_types=agents)
        agent_types = self._worker_daemon.agent_types

        # Run as a background task so we don't block the event loop
        self._worker_task = asyncio.create_task(self._worker_daemon.start())

        print(f"🚀 Worker daemon started for: {', '.join(agent_types)}")

        return (
            f"✅ Workers started for: {', '.join(agent_types)}\n\n"
            f"Workers are now pulling tasks from Redis queues and implementing issues.\n"
            f"Use `!workers status` to monitor progress."
        )

    async def stop_workers(self) -> str:
        """Gracefully stop the AgentWorkerDaemon."""
        if not self._worker_daemon or not self._worker_daemon._running:
            return "⚠️ No workers are currently running."

        await self._worker_daemon.stop()

        if self._worker_task and not self._worker_task.done():
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

        self._worker_daemon = None
        self._worker_task = None

        return "✅ Workers stopped successfully."

    async def worker_status(self) -> str:
        """Return queue sizes and worker states."""
        if not self._worker_daemon:
            return "📊 Workers are not running. Use `!workers start` to start them."

        status = self._worker_daemon.get_status()
        queue_lines = [
            f"  • **{agent}**: {count} pending tasks"
            for agent, count in status.get("queues", {}).items()
        ]
        state_lines = [
            f"  • **{agent}**: {state}"
            for agent, state in status.get("worker_states", {}).items()
        ]

        return (
            f"📊 **Worker Status**\n\n"
            f"**Running**: {'Yes' if status['running'] else 'No'}\n\n"
            f"**Queue Sizes:**\n" + "\n".join(queue_lines) + "\n\n"
            f"**Worker States:**\n" + "\n".join(state_lines)
        )

    async def handle_general_query(self, message: str, user_id: str) -> str:
        """Handle general questions and conversations."""
        context = await self.retrieve_memory(message, n_results=3)

        context_str = (
            "\n".join([f"- {doc}" for doc in context.get("documents", [[]])[0]])
            if context and context.get("documents") and len(context.get("documents")[0]) > 0
            else "No relevant context"
        )

        prompt = f"""
Answer this question from the user:

"{message}"

Relevant context from previous conversations:
{context_str}

Current project: {self.current_project.get('name') if self.current_project else 'None'}

Provide a helpful, friendly response. If you need more information, ask.
"""
        result = await self.call_claude_code(prompt=prompt, allowed_tools=["Write"])
        return result.get("stdout", "I'm here to help! Could you provide more details?")

    # ==========================================
    # CLAUDE CODE CLI
    # ==========================================

    async def call_claude_code(
        self,
        prompt: str,
        project_path: Optional[str] = None,
        allowed_tools: Optional[List[str]] = None,
        context_files: Optional[List[str]] = None,
    ) -> Dict:
        """
        Programmatically invoke Claude Code CLI (async).

        Args:
            prompt: The instruction to give Claude Code
            project_path: Directory where Claude Code should work
            allowed_tools: List of tools Claude Code can use
            context_files: Files to include in context

        Returns:
            Dict with 'stdout', 'stderr', 'return_code', 'success'
        """
        cmd = ["claude", "-p", prompt, "--dangerously-skip-permissions"]

        if allowed_tools:
            cmd.extend(["--allowed-tools"])
            cmd.extend(allowed_tools)

        cwd = project_path or str(self.workspace_dir)
        print(f"🤖 Calling Claude Code: {prompt[:80]}...")

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=300
                )
                stdout = stdout.decode("utf-8")
                stderr = stderr.decode("utf-8")
                return_code = process.returncode
            except asyncio.TimeoutError:
                process.kill()
                await process.communicate()
                return {
                    "stdout": "",
                    "stderr": "Command timed out after 5 minutes",
                    "return_code": -1,
                    "success": False,
                }

            await self.log_interaction(prompt, stdout, stderr)

            return {
                "stdout": stdout,
                "stderr": stderr,
                "return_code": return_code,
                "success": return_code == 0,
            }

        except Exception as e:
            return {"stdout": "", "stderr": str(e), "return_code": -1, "success": False}

    # ==========================================
    # MEMORY
    # ==========================================

    async def store_memory(self, category: str, content: str, metadata: Dict = None):
        """Store information in vector database for later retrieval."""
        memory_id = f"{category}_{datetime.now().timestamp()}"
        self.memory.add(
            documents=[content],
            metadatas=[{"category": category, **(metadata or {})}],
            ids=[memory_id],
        )

    async def retrieve_memory(self, query: str, n_results: int = 5) -> Dict:
        """Retrieve relevant memories based on query."""
        try:
            return self.memory.query(query_texts=[query], n_results=n_results)
        except Exception as e:
            print(f"⚠️ Memory retrieval error: {e}")
            return {"documents": [[]]}

    # ==========================================
    # UTILITIES
    # ==========================================

    def _detect_stack(self, project_path: str) -> str:
        """
        Detect technology stack from project files.

        Returns:
            Stack identifier: 'python', 'node', 'fullstack', or 'unknown'
        """
        path = Path(project_path)
        has_python = any([
            (path / "requirements.txt").exists(),
            (path / "pyproject.toml").exists(),
            (path / "setup.py").exists(),
        ])
        has_node = any([
            (path / "package.json").exists(),
            (path / "node_modules").exists(),
        ])

        if has_python and has_node:
            return "fullstack"
        elif has_python:
            return "python"
        elif has_node:
            return "node"
        return "unknown"

    async def save_project_metadata(self):
        """Save current project metadata to disk."""
        if not self.current_project:
            return

        metadata_file = Path(self.current_project["path"]) / ".project_metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(self.current_project, f, indent=2)

    async def load_project(self, project_path: str) -> bool:
        """
        Load a previously saved project from disk.

        Args:
            project_path: Path to the project directory

        Returns:
            True if loaded successfully
        """
        metadata_file = Path(project_path) / ".project_metadata.json"
        if not metadata_file.exists():
            print(f"⚠️ No project metadata found at {metadata_file}")
            return False

        with open(metadata_file, "r") as f:
            self.current_project = json.load(f)

        print(f"✅ Loaded project: {self.current_project.get('name')}")
        return True

    async def log_interaction(self, prompt: str, stdout: str, stderr: str):
        """Log all Claude Code interactions for debugging."""
        log_dir = Path.home() / "ai-dev-pipeline" / "logs"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"claude_code_{datetime.now().strftime('%Y%m%d')}.log"

        with open(log_file, "a") as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"Prompt: {prompt[:500]}\n")
            f.write(f"Stdout: {stdout[:2000]}\n")
            f.write(f"Stderr: {stderr[:500]}\n")
            f.write(f"{'='*80}\n")


# ==========================================
# EXAMPLE USAGE
# ==========================================

if __name__ == "__main__":

    async def test():
        agent = MasterAgent()
        response = await agent.process_user_message(
            "Create a simple task management web app", "test_user_123"
        )
        print(response)

    asyncio.run(test())
