"""
Backend Agent for AI Development Pipeline
Implements server-side APIs, business logic, and creates pull requests
"""

import os
import subprocess
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime

from agents.base_agent import BaseAgent
from agents.github_client import create_github_client
from utils.constants import AgentType, GitHubBranches, GITHUB_USERNAME
from utils.error_handlers import retry_on_rate_limit


class BackendAgent(BaseAgent):
    """
    Backend Development Agent
    
    Responsibilities:
    - Implement REST APIs and business logic
    - Create feature branches for each issue
    - Write comprehensive tests
    - Create pull requests
    - Handle validation and error cases
    - Document API endpoints
    """
    
    def __init__(self, agent_id: Optional[str] = None):
        """Initialize Backend Agent"""
        super().__init__(
            agent_type=AgentType.BACKEND,
            agent_id=agent_id
        )
        
        # Initialize GitHub client
        self.github = create_github_client()
        
        # Track work
        self.current_branch = None
        self.current_issue = None
        
        self.logger.info("Backend Agent initialized")
    
    def get_capabilities(self) -> List[str]:
        """Get agent capabilities"""
        return [
            "Implement REST APIs",
            "Write business logic",
            "Create feature branches",
            "Write comprehensive tests",
            "Create pull requests",
            "Handle validation and errors",
            "Document endpoints"
        ]
    
    async def execute_task(self, task: Dict) -> Dict:
        """
        Execute a task assigned to Backend Agent
        
        Args:
            task: Task dictionary with task details
        
        Returns:
            Result dictionary
        """
        task_type = task.get("task_type", "implement_feature")
        
        handlers = {
            "implement_feature": self.implement_feature,
            "fix_bug": self.fix_bug,
            "write_tests": self.write_tests,
            "refactor": self.refactor_code,
        }
        
        handler = handlers.get(task_type)
        
        if not handler:
            raise ValueError(f"Unknown task type: {task_type}")
        
        return await handler(task)
    
    async def implement_feature(self, task: Dict) -> Dict:
        """
        Implement a feature from a GitHub issue
        
        Complete workflow:
        1. Read issue details
        2. Create feature branch
        3. Implement code using Claude Code
        4. Write tests
        5. Create pull request
        
        Args:
            task: Task with 'repo_name', 'issue_number'
        
        Returns:
            Result with PR details
        """
        repo_name = task.get("repo_name", "")
        issue_number = task.get("issue_number", 0)
        
        await self.log_action("implement_feature", "started", {
            "repo": repo_name,
            "issue": issue_number
        })
        
        try:
            # Step 1: Get issue details
            issue = await self._get_issue_details(repo_name, issue_number)
            
            # Step 2: Create feature branch
            branch_name = f"feature/issue-{issue_number}"
            await self._create_feature_branch(repo_name, branch_name)
            self.current_branch = branch_name
            self.current_issue = issue_number
            
            # Step 3: Clone repo and implement feature
            project_path = await self._setup_local_repo(repo_name, branch_name)
            
            # Step 4: Implement the feature using Claude Code
            implementation_result = await self._implement_with_claude(
                project_path=project_path,
                issue_title=issue.get("title", ""),
                issue_body=issue.get("body", ""),
                issue_number=issue_number
            )
            
            # Step 5: Write tests
            await self._write_tests(project_path, issue_number)

            # Step 5b: Validate — run tests, retry once on failure
            await self._validate_implementation(project_path, issue_number)

            # Step 6: Commit and push
            await self._commit_and_push(project_path, branch_name, issue_number)
            
            # Step 7: Create pull request
            pr = await self._create_pull_request(
                repo_name=repo_name,
                branch_name=branch_name,
                issue_number=issue_number,
                issue_title=issue.get("title", "")
            )
            
            await self.log_action("implement_feature", "completed", {
                "repo": repo_name,
                "issue": issue_number,
                "pr_number": pr.get("number")
            })
            
            # Notify completion
            await self.send_status_update(
                "feature_implemented",
                {
                    "repo": repo_name,
                    "issue": issue_number,
                    "pr_url": pr.get("html_url"),
                    "branch": branch_name
                }
            )
            
            return {
                "success": True,
                "issue_number": issue_number,
                "branch": branch_name,
                "pr_number": pr.get("number"),
                "pr_url": pr.get("html_url"),
                "message": f"Feature implemented and PR created"
            }
            
        except Exception as e:
            await self.log_action("implement_feature", "failed", {
                "error": str(e)
            })
            raise
    
    async def _get_issue_details(self, repo_name: str, issue_number: int) -> Dict:
        """Get issue details from GitHub"""
        try:
            issue = await self.github.get_issue(repo_name, issue_number)
            return {
                "number": issue.get("number", issue_number),
                "title": issue.get("title", f"Issue #{issue_number}"),
                "body": issue.get("body", ""),
                "labels": [lbl.get("name", "") for lbl in issue.get("labels", [])],
                "state": issue.get("state", "open"),
            }
        except Exception as e:
            self.logger.warning(f"Could not fetch issue #{issue_number}: {e}")
            return {
                "number": issue_number,
                "title": f"Issue #{issue_number}",
                "body": "Implementation details from issue",
                "labels": [],
                "state": "open",
            }
    
    @retry_on_rate_limit()
    async def _create_feature_branch(self, repo_name: str, branch_name: str):
        """Create a new feature branch from dev"""
        await self.github.create_branch(
            repo_name=repo_name,
            branch_name=branch_name,
            from_branch=GitHubBranches.DEVELOPMENT
        )
        
        self.logger.info(f"Created feature branch: {branch_name}")
    
    async def _setup_local_repo(self, repo_name: str, branch_name: str) -> Path:
        """Clone repo and checkout branch locally"""
        project_path = self.workspace_dir / repo_name
        project_path.mkdir(parents=True, exist_ok=True)

        (project_path / "src").mkdir(exist_ok=True)
        (project_path / "tests").mkdir(exist_ok=True)

        # Initialise git if not already a repo
        git_dir = project_path / ".git"
        if not git_dir.exists():
            username = GITHUB_USERNAME or os.getenv("GITHUB_USERNAME", "")
            await self.call_claude_code(
                prompt=(
                    f"Run: git init && git remote add origin "
                    f"https://github.com/{username}/{repo_name}.git"
                ),
                project_path=str(project_path),
                allowed_tools=["Bash"],
            )

        return project_path
    
    async def _implement_with_claude(
        self,
        project_path: Path,
        issue_title: str,
        issue_body: str,
        issue_number: int
    ) -> Dict:
        """
        Use Claude Code to implement the feature
        """
        prompt = f"""
You are implementing a backend feature for a FastAPI application.

Issue #{issue_number}: {issue_title}

Details:
{issue_body}

Tasks:
1. Analyze the requirements
2. Create the necessary API endpoints in src/api/
3. Implement business logic in src/services/
4. Add data models in src/models/
5. Handle validation and errors properly
6. Add proper type hints and docstrings
7. Follow FastAPI best practices

Create a well-structured, production-ready implementation.
Include proper error handling, validation, and documentation.
"""
        
        result = await self.call_claude_code(
            prompt=prompt,
            project_path=str(project_path),
            allowed_tools=["Write", "Edit", "Bash", "Read"]
        )
        
        return result
    
    async def _write_tests(self, project_path: Path, issue_number: int):
        """Write comprehensive tests for the feature"""
        prompt = f"""
Write comprehensive tests for the feature implemented for issue #{issue_number}.

Create test files in tests/ directory:
1. Unit tests for all functions
2. Integration tests for API endpoints
3. Test edge cases and error handling
4. Use pytest framework
5. Aim for 90%+ code coverage

Include:
- Positive test cases
- Negative test cases (error scenarios)
- Boundary conditions
- Mock external dependencies
"""
        
        result = await self.call_claude_code(
            prompt=prompt,
            project_path=str(project_path),
            allowed_tools=["Write", "Edit", "Bash"]
        )
        
        self.logger.info(f"Tests written for issue #{issue_number}")
    
    async def _validate_implementation(
        self,
        project_path: Path,
        issue_number: int
    ):
        """
        Run tests to validate the implementation.

        Detects pytest or jest, runs tests, and on failure makes one retry
        call to Claude Code to fix the failures. Raises RuntimeError if tests
        still fail after one retry. Logs a warning (but does not block) when
        no tests are found.
        """
        # Detect test framework
        has_pytest = (
            (project_path / "pytest.ini").exists()
            or (project_path / "pyproject.toml").exists()
            or (project_path / "setup.cfg").exists()
            or list(project_path.glob("tests/**/*.py"))
            or list(project_path.glob("test_*.py"))
        )
        has_jest = (project_path / "package.json").exists()

        if not has_pytest and not has_jest:
            self.logger.warning(
                f"No test framework detected for issue #{issue_number} "
                f"in {project_path} — skipping validation"
            )
            return

        test_output = ""
        passed = False

        if has_pytest:
            try:
                proc = subprocess.run(
                    ["python", "-m", "pytest", "-v", "--tb=short", "-x"],
                    cwd=str(project_path),
                    timeout=120,
                    capture_output=True,
                    text=True,
                )
                test_output = proc.stdout + proc.stderr
                passed = proc.returncode == 0
            except (subprocess.TimeoutExpired, FileNotFoundError) as e:
                self.logger.warning(f"pytest run failed: {e}")
                return

        elif has_jest:
            try:
                proc = subprocess.run(
                    ["npm", "test", "--", "--watchAll=false"],
                    cwd=str(project_path),
                    timeout=120,
                    capture_output=True,
                    text=True,
                )
                test_output = proc.stdout + proc.stderr
                output_lower = test_output.lower()
                passed = proc.returncode == 0 and "failed" not in output_lower

            except (subprocess.TimeoutExpired, FileNotFoundError) as e:
                self.logger.warning(f"jest run failed: {e}")
                return

        if passed:
            self.logger.info(f"Tests passed for issue #{issue_number}")
            return

        # One retry — ask Claude Code to fix the failures
        self.logger.warning(
            f"Tests failing for issue #{issue_number}, retrying with Claude Code fix"
        )
        await self.call_claude_code(
            prompt=(
                f"Fix these test failures for issue #{issue_number}:\n\n"
                f"{test_output[:3000]}\n\n"
                "Identify the root cause and fix the implementation or tests."
            ),
            project_path=str(project_path),
            allowed_tools=["Write", "Edit", "Bash", "Read"],
        )

        # Re-run after fix attempt
        if has_pytest:
            try:
                proc = subprocess.run(
                    ["python", "-m", "pytest", "-v", "--tb=short", "-x"],
                    cwd=str(project_path),
                    timeout=120,
                    capture_output=True,
                    text=True,
                )
                passed = proc.returncode == 0
                test_output = proc.stdout + proc.stderr
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
        elif has_jest:
            try:
                proc = subprocess.run(
                    ["npm", "test", "--", "--watchAll=false"],
                    cwd=str(project_path),
                    timeout=120,
                    capture_output=True,
                    text=True,
                )
                test_output = proc.stdout + proc.stderr
                passed = proc.returncode == 0 and "failed" not in test_output.lower()
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

        if not passed:
            raise RuntimeError(
                f"Tests still failing after retry for issue #{issue_number}. "
                f"Output: {test_output[:500]}"
            )

    async def _commit_and_push(
        self,
        project_path: Path,
        branch_name: str,
        issue_number: int
    ):
        """Commit changes and push to GitHub"""
        prompt = f"""
Commit and push the changes:

1. Stage all changes: git add .
2. Commit with message: "feat: implement #{issue_number} - [brief description]"
3. Push to origin/{branch_name}

Execute these git commands.
"""
        
        result = await self.call_claude_code(
            prompt=prompt,
            project_path=str(project_path),
            allowed_tools=["Bash"]
        )
        
        self.logger.info(f"Changes committed and pushed to {branch_name}")
    
    @retry_on_rate_limit()
    async def _create_pull_request(
        self,
        repo_name: str,
        branch_name: str,
        issue_number: int,
        issue_title: str
    ) -> Dict:
        """Create pull request for the feature"""
        
        pr_title = f"feat: {issue_title}"
        pr_body = f"""
## Summary
Implements #{issue_number}: {issue_title}

## Changes
- Implemented API endpoints
- Added business logic
- Created data models
- Added comprehensive tests
- Proper error handling

## Testing
- All tests passing
- Code coverage: 90%+

## Checklist
- [x] Code follows project style
- [x] Tests added and passing
- [x] Documentation updated
- [x] No breaking changes

Closes #{issue_number}
"""
        
        pr = await self.github.create_pull_request(
            repo_name=repo_name,
            title=pr_title,
            body=pr_body,
            head=branch_name,
            base=GitHubBranches.DEVELOPMENT
        )
        
        self.logger.log_github_operation(
            operation="create_pr",
            repo=repo_name,
            status="success",
            details={
                "pr_number": pr.get("number"),
                "branch": branch_name,
                "issue": issue_number
            }
        )
        
        return pr
    
    async def fix_bug(self, task: Dict) -> Dict:
        """
        Fix a bug reported in a GitHub issue.

        Workflow: fetch issue → create fix branch → Claude Code fixes it →
        validate → commit → PR
        """
        repo_name = task.get("repo_name", "")
        issue_number = task.get("issue_number", 0)

        await self.log_action("fix_bug", "started", {
            "repo": repo_name, "issue": issue_number
        })

        try:
            issue = await self._get_issue_details(repo_name, issue_number)
            branch_name = f"fix/issue-{issue_number}"
            await self._create_feature_branch(repo_name, branch_name)
            self.current_branch = branch_name
            self.current_issue = issue_number

            project_path = await self._setup_local_repo(repo_name, branch_name)

            prompt = f"""
You are fixing a bug in a FastAPI backend application.

Issue #{issue_number}: {issue.get('title', '')}

Bug description:
{issue.get('body', '')}

Tasks:
1. Read the existing code to understand the bug
2. Identify the root cause
3. Fix the bug with minimal changes — do not refactor unrelated code
4. Ensure existing tests still pass
5. Add a regression test that would catch this bug

Follow Python best practices and keep changes focused.
"""
            await self.call_claude_code(
                prompt=prompt,
                project_path=str(project_path),
                allowed_tools=["Write", "Edit", "Bash", "Read"],
            )

            await self._validate_implementation(project_path, issue_number)
            await self._commit_and_push(project_path, branch_name, issue_number)
            pr = await self._create_pull_request(
                repo_name=repo_name,
                branch_name=branch_name,
                issue_number=issue_number,
                issue_title=f"fix: {issue.get('title', '')}",
            )

            await self.log_action("fix_bug", "completed", {
                "repo": repo_name, "issue": issue_number, "pr_number": pr.get("number")
            })
            await self.send_status_update("bug_fixed", {
                "repo": repo_name, "issue": issue_number,
                "pr_url": pr.get("html_url"), "branch": branch_name,
            })

            return {
                "success": True,
                "issue_number": issue_number,
                "branch": branch_name,
                "pr_number": pr.get("number"),
                "pr_url": pr.get("html_url"),
                "message": "Bug fix implemented and PR created",
            }

        except Exception as e:
            await self.log_action("fix_bug", "failed", {"error": str(e)})
            raise

    async def write_tests(self, task: Dict) -> Dict:
        """
        Write missing test coverage for a module specified in the issue.

        Workflow: fetch issue → create tests branch → Claude Code writes tests →
        validate → commit → PR
        """
        repo_name = task.get("repo_name", "")
        issue_number = task.get("issue_number", 0)

        await self.log_action("write_tests", "started", {
            "repo": repo_name, "issue": issue_number
        })

        try:
            issue = await self._get_issue_details(repo_name, issue_number)
            branch_name = f"tests/issue-{issue_number}"
            await self._create_feature_branch(repo_name, branch_name)
            self.current_branch = branch_name
            self.current_issue = issue_number

            project_path = await self._setup_local_repo(repo_name, branch_name)

            prompt = f"""
You are writing missing test coverage for a FastAPI backend application.

Issue #{issue_number}: {issue.get('title', '')}

Details:
{issue.get('body', '')}

Tasks:
1. Identify which modules / functions have insufficient test coverage
2. Write pytest tests covering the missing cases
3. Include unit tests, edge cases, and error scenarios
4. Aim for 90%+ coverage on the targeted modules
5. Use pytest fixtures and mocking appropriately

Do NOT modify the production code — only add/edit test files.
"""
            await self.call_claude_code(
                prompt=prompt,
                project_path=str(project_path),
                allowed_tools=["Write", "Edit", "Bash", "Read"],
            )

            await self._validate_implementation(project_path, issue_number)
            await self._commit_and_push(project_path, branch_name, issue_number)
            pr = await self._create_pull_request(
                repo_name=repo_name,
                branch_name=branch_name,
                issue_number=issue_number,
                issue_title=f"tests: {issue.get('title', '')}",
            )

            await self.log_action("write_tests", "completed", {
                "repo": repo_name, "issue": issue_number, "pr_number": pr.get("number")
            })

            return {
                "success": True,
                "issue_number": issue_number,
                "branch": branch_name,
                "pr_number": pr.get("number"),
                "pr_url": pr.get("html_url"),
                "message": "Tests written and PR created",
            }

        except Exception as e:
            await self.log_action("write_tests", "failed", {"error": str(e)})
            raise

    async def refactor_code(self, task: Dict) -> Dict:
        """
        Refactor existing code as described in the issue.

        Workflow: fetch issue → create refactor branch → Claude Code refactors →
        validate → commit → PR
        """
        repo_name = task.get("repo_name", "")
        issue_number = task.get("issue_number", 0)

        await self.log_action("refactor_code", "started", {
            "repo": repo_name, "issue": issue_number
        })

        try:
            issue = await self._get_issue_details(repo_name, issue_number)
            branch_name = f"refactor/issue-{issue_number}"
            await self._create_feature_branch(repo_name, branch_name)
            self.current_branch = branch_name
            self.current_issue = issue_number

            project_path = await self._setup_local_repo(repo_name, branch_name)

            prompt = f"""
You are refactoring a FastAPI backend application.

Issue #{issue_number}: {issue.get('title', '')}

Refactoring requirements:
{issue.get('body', '')}

Tasks:
1. Read the existing code that needs to be refactored
2. Perform the refactoring as described in the issue
3. Ensure all existing tests still pass after refactoring
4. Do NOT add new features — only restructure/improve existing code
5. Update docstrings/comments as needed
6. Keep the public API unchanged (no breaking changes)

Follow Python best practices (SOLID, DRY, etc.).
"""
            await self.call_claude_code(
                prompt=prompt,
                project_path=str(project_path),
                allowed_tools=["Write", "Edit", "Bash", "Read"],
            )

            await self._validate_implementation(project_path, issue_number)
            await self._commit_and_push(project_path, branch_name, issue_number)
            pr = await self._create_pull_request(
                repo_name=repo_name,
                branch_name=branch_name,
                issue_number=issue_number,
                issue_title=f"refactor: {issue.get('title', '')}",
            )

            await self.log_action("refactor_code", "completed", {
                "repo": repo_name, "issue": issue_number, "pr_number": pr.get("number")
            })

            return {
                "success": True,
                "issue_number": issue_number,
                "branch": branch_name,
                "pr_number": pr.get("number"),
                "pr_url": pr.get("html_url"),
                "message": "Refactoring complete and PR created",
            }

        except Exception as e:
            await self.log_action("refactor_code", "failed", {"error": str(e)})
            raise


# ==========================================
# CONVENIENCE FUNCTIONS
# ==========================================

async def implement_backend_feature(
    repo_name: str,
    issue_number: int
) -> Dict:
    """
    Implement a backend feature
    
    Args:
        repo_name: Repository name
        issue_number: Issue number to implement
    
    Returns:
        Result with PR details
    """
    backend = BackendAgent()
    
    result = await backend.implement_feature({
        "task_type": "implement_feature",
        "repo_name": repo_name,
        "issue_number": issue_number
    })
    
    return result
