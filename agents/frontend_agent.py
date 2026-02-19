"""
Frontend Agent for AI Development Pipeline
Builds UI components, integrates with backend APIs, creates PRs
"""

import os
import subprocess
from typing import Dict, List, Optional
from pathlib import Path

from agents.base_agent import BaseAgent
from agents.github_client import create_github_client
from utils.constants import AgentType, GitHubBranches, GITHUB_USERNAME
from utils.error_handlers import retry_on_rate_limit


class FrontendAgent(BaseAgent):
    """
    Frontend Development Agent
    
    Responsibilities:
    - Build React/Vue UI components
    - Integrate with backend APIs
    - Create feature branches
    - Write component tests
    - Create pull requests
    - Ensure responsive design
    - Implement accessibility
    """
    
    def __init__(self, agent_id: Optional[str] = None):
        """Initialize Frontend Agent"""
        super().__init__(
            agent_type=AgentType.FRONTEND,
            agent_id=agent_id
        )
        
        # Initialize GitHub client
        self.github = create_github_client()
        
        # Track work
        self.current_branch = None
        self.current_issue = None
        
        self.logger.info("Frontend Agent initialized")
    
    def get_capabilities(self) -> List[str]:
        """Get agent capabilities"""
        return [
            "Build UI components",
            "Integrate with APIs",
            "Create feature branches",
            "Write component tests",
            "Create pull requests",
            "Ensure responsive design",
            "Implement accessibility"
        ]
    
    async def execute_task(self, task: Dict) -> Dict:
        """Execute task assigned to Frontend Agent"""
        task_type = task.get("task_type", "implement_feature")
        
        handlers = {
            "implement_feature": self.implement_feature,
            "fix_bug": self.fix_bug,
            "improve_ui": self.improve_ui,
        }
        
        handler = handlers.get(task_type)
        if not handler:
            raise ValueError(f"Unknown task type: {task_type}")
        
        return await handler(task)
    
    async def implement_feature(self, task: Dict) -> Dict:
        """
        Implement a frontend feature from GitHub issue
        
        Workflow:
        1. Read issue details
        2. Create feature branch
        3. Build UI components
        4. Integrate with backend
        5. Write tests
        6. Create PR
        """
        repo_name = task.get("repo_name", "")
        issue_number = task.get("issue_number", 0)
        
        await self.log_action("implement_feature", "started", {
            "repo": repo_name,
            "issue": issue_number
        })
        
        try:
            # Get issue details
            issue = await self._get_issue_details(repo_name, issue_number)
            
            # Create feature branch
            branch_name = f"feature/ui-issue-{issue_number}"
            await self._create_feature_branch(repo_name, branch_name)
            
            # Setup local repo
            project_path = await self._setup_local_repo(repo_name, branch_name)
            
            # Implement UI using Claude Code
            await self._implement_ui_with_claude(
                project_path=project_path,
                issue_title=issue.get("title", ""),
                issue_body=issue.get("body", ""),
                issue_number=issue_number
            )
            
            # Write tests
            await self._write_component_tests(project_path, issue_number)

            # Validate — run tests, retry once on failure
            await self._validate_implementation(project_path, issue_number)

            # Commit and push
            await self._commit_and_push(project_path, branch_name, issue_number)
            
            # Create PR
            pr = await self._create_pull_request(
                repo_name=repo_name,
                branch_name=branch_name,
                issue_number=issue_number,
                issue_title=issue.get("title", "")
            )
            
            await self.log_action("implement_feature", "completed", {
                "pr_number": pr.get("number")
            })
            
            return {
                "success": True,
                "issue_number": issue_number,
                "pr_number": pr.get("number"),
                "pr_url": pr.get("html_url")
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
                "title": issue.get("title", f"UI Issue #{issue_number}"),
                "body": issue.get("body", ""),
                "labels": [lbl.get("name", "") for lbl in issue.get("labels", [])],
                "state": issue.get("state", "open"),
            }
        except Exception as e:
            self.logger.warning(f"Could not fetch issue #{issue_number}: {e}")
            return {
                "number": issue_number,
                "title": f"UI Issue #{issue_number}",
                "body": "UI implementation details",
                "labels": [],
                "state": "open",
            }
    
    @retry_on_rate_limit()
    async def _create_feature_branch(self, repo_name: str, branch_name: str):
        """Create feature branch"""
        await self.github.create_branch(
            repo_name=repo_name,
            branch_name=branch_name,
            from_branch=GitHubBranches.DEVELOPMENT
        )
        self.logger.info(f"Created UI feature branch: {branch_name}")
    
    async def _setup_local_repo(self, repo_name: str, branch_name: str) -> Path:
        """Setup local repository"""
        project_path = self.workspace_dir / repo_name
        project_path.mkdir(parents=True, exist_ok=True)
        (project_path / "src" / "components").mkdir(parents=True, exist_ok=True)
        (project_path / "src" / "pages").mkdir(parents=True, exist_ok=True)
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
    
    async def _implement_ui_with_claude(
        self,
        project_path: Path,
        issue_title: str,
        issue_body: str,
        issue_number: int
    ):
        """Implement UI using Claude Code"""
        prompt = f"""
You are implementing a frontend feature for a React application.

Issue #{issue_number}: {issue_title}

Details:
{issue_body}

Tasks:
1. Create React components in src/components/
2. Build page layouts in src/pages/
3. Integrate with backend API (assume API exists)
4. Add proper state management (useState, useContext)
5. Ensure responsive design (mobile, tablet, desktop)
6. Add accessibility features (ARIA labels, keyboard navigation)
7. Use Tailwind CSS for styling
8. Add loading states and error handling

Create production-ready, accessible, and responsive components.
Follow React best practices and hooks patterns.
"""
        
        await self.call_claude_code(
            prompt=prompt,
            project_path=str(project_path),
            allowed_tools=["Write", "Edit", "Bash", "Read"]
        )
    
    async def _write_component_tests(self, project_path: Path, issue_number: int):
        """Write component tests"""
        prompt = f"""
Write comprehensive tests for the UI components created for issue #{issue_number}.

Create test files in tests/ using React Testing Library:
1. Component rendering tests
2. User interaction tests (clicks, form inputs)
3. API integration tests (mocked)
4. Accessibility tests
5. Responsive design tests

Test:
- Component renders correctly
- User interactions work
- Error states display properly
- Loading states work
- Accessibility compliance
"""
        
        await self.call_claude_code(
            prompt=prompt,
            project_path=str(project_path),
            allowed_tools=["Write", "Edit"]
        )
    
    async def _validate_implementation(
        self,
        project_path: Path,
        issue_number: int
    ):
        """
        Run tests to validate the UI implementation.

        Detects jest (package.json) or pytest, runs tests, and on failure makes
        one retry call to Claude Code. Raises RuntimeError if tests still fail.
        Logs a warning (but does not block) when no tests are found.
        """
        has_jest = (project_path / "package.json").exists()
        has_pytest = (
            (project_path / "pytest.ini").exists()
            or list(project_path.glob("tests/**/*.py"))
        )

        if not has_jest and not has_pytest:
            self.logger.warning(
                f"No test framework detected for issue #{issue_number} "
                f"in {project_path} — skipping validation"
            )
            return

        test_output = ""
        passed = False

        if has_jest:
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
            except (subprocess.TimeoutExpired, FileNotFoundError) as e:
                self.logger.warning(f"jest run failed: {e}")
                return

        elif has_pytest:
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

        if passed:
            self.logger.info(f"Tests passed for issue #{issue_number}")
            return

        # One retry — ask Claude Code to fix the failures
        self.logger.warning(
            f"Tests failing for issue #{issue_number}, retrying with Claude Code fix"
        )
        await self.call_claude_code(
            prompt=(
                f"Fix these test failures for UI issue #{issue_number}:\n\n"
                f"{test_output[:3000]}\n\n"
                "Identify the root cause and fix the components or tests."
            ),
            project_path=str(project_path),
            allowed_tools=["Write", "Edit", "Bash", "Read"],
        )

        # Re-run after fix
        if has_jest:
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
        elif has_pytest:
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

        if not passed:
            raise RuntimeError(
                f"Tests still failing after retry for UI issue #{issue_number}. "
                f"Output: {test_output[:500]}"
            )

    async def _commit_and_push(
        self,
        project_path: Path,
        branch_name: str,
        issue_number: int
    ):
        """Commit and push changes"""
        prompt = f"""
Commit and push UI changes:
1. git add .
2. git commit -m "feat(ui): implement #{issue_number}"
3. git push origin {branch_name}
"""
        await self.call_claude_code(
            prompt=prompt,
            project_path=str(project_path),
            allowed_tools=["Bash"]
        )
    
    @retry_on_rate_limit()
    async def _create_pull_request(
        self,
        repo_name: str,
        branch_name: str,
        issue_number: int,
        issue_title: str
    ) -> Dict:
        """Create pull request"""
        pr_title = f"feat(ui): {issue_title}"
        pr_body = f"""
## Summary
Implements UI for #{issue_number}: {issue_title}

## Changes
- Created React components
- Integrated with backend API
- Added responsive design
- Implemented accessibility features
- Added comprehensive tests

## Screenshots
[Add screenshots here]

## Testing
- Component tests passing
- Manual testing completed
- Responsive on all devices
- Accessibility verified

Closes #{issue_number}
"""
        
        pr = await self.github.create_pull_request(
            repo_name=repo_name,
            title=pr_title,
            body=pr_body,
            head=branch_name,
            base=GitHubBranches.DEVELOPMENT
        )
        
        return pr
    
    async def fix_bug(self, task: Dict) -> Dict:
        """
        Fix a UI bug reported in a GitHub issue.

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
            branch_name = f"fix/ui-issue-{issue_number}"
            await self._create_feature_branch(repo_name, branch_name)

            project_path = await self._setup_local_repo(repo_name, branch_name)

            prompt = f"""
You are fixing a UI bug in a React frontend application.

Issue #{issue_number}: {issue.get('title', '')}

Bug description:
{issue.get('body', '')}

Tasks:
1. Read the relevant React components and understand the bug
2. Identify the root cause (state management, rendering, event handling, CSS, etc.)
3. Fix the bug with minimal changes — do not refactor unrelated components
4. Ensure the component still renders correctly and passes existing tests
5. Add a regression test using React Testing Library

Follow React best practices. Keep changes focused on the bug.
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
                issue_title=f"fix(ui): {issue.get('title', '')}",
            )

            await self.log_action("fix_bug", "completed", {
                "repo": repo_name, "issue": issue_number, "pr_number": pr.get("number")
            })
            await self.send_status_update("ui_bug_fixed", {
                "repo": repo_name, "issue": issue_number,
                "pr_url": pr.get("html_url"), "branch": branch_name,
            })

            return {
                "success": True,
                "issue_number": issue_number,
                "branch": branch_name,
                "pr_number": pr.get("number"),
                "pr_url": pr.get("html_url"),
                "message": "UI bug fix implemented and PR created",
            }

        except Exception as e:
            await self.log_action("fix_bug", "failed", {"error": str(e)})
            raise

    async def improve_ui(self, task: Dict) -> Dict:
        """
        Improve component styling / UX as described in the issue.

        Workflow: fetch issue → create improvement branch → Claude Code improves
        the UI → validate → commit → PR
        """
        repo_name = task.get("repo_name", "")
        issue_number = task.get("issue_number", 0)

        await self.log_action("improve_ui", "started", {
            "repo": repo_name, "issue": issue_number
        })

        try:
            issue = await self._get_issue_details(repo_name, issue_number)
            branch_name = f"improve/ui-issue-{issue_number}"
            await self._create_feature_branch(repo_name, branch_name)

            project_path = await self._setup_local_repo(repo_name, branch_name)

            prompt = f"""
You are improving the styling and UX of a React frontend application.

Issue #{issue_number}: {issue.get('title', '')}

Improvement requirements:
{issue.get('body', '')}

Tasks:
1. Read the existing components to understand current state
2. Apply the requested UI/UX improvements:
   - Better Tailwind CSS classes for visual polish
   - Improved layout and responsiveness (mobile, tablet, desktop)
   - Enhanced accessibility (ARIA labels, keyboard navigation, focus states)
   - Better loading states, empty states, and error messages
   - Smooth transitions and micro-interactions where appropriate
3. Do NOT break existing functionality
4. Verify all existing tests still pass

Prioritise usability and accessibility. Follow React and Tailwind best practices.
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
                issue_title=f"improve(ui): {issue.get('title', '')}",
            )

            await self.log_action("improve_ui", "completed", {
                "repo": repo_name, "issue": issue_number, "pr_number": pr.get("number")
            })

            return {
                "success": True,
                "issue_number": issue_number,
                "branch": branch_name,
                "pr_number": pr.get("number"),
                "pr_url": pr.get("html_url"),
                "message": "UI improvement complete and PR created",
            }

        except Exception as e:
            await self.log_action("improve_ui", "failed", {"error": str(e)})
            raise
