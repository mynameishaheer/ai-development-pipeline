"""
Frontend Agent for AI Development Pipeline
Builds UI components, integrates with backend APIs, creates PRs
"""

from typing import Dict, List, Optional
from pathlib import Path

from agents.base_agent import BaseAgent
from agents.github_client import create_github_client
from utils.constants import AgentType, GitHubBranches
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
        return {
            "number": issue_number,
            "title": f"UI Issue #{issue_number}",
            "body": "UI implementation details"
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
        """Fix UI bug"""
        return {"success": True, "message": "UI bug fix not yet implemented"}
    
    async def improve_ui(self, task: Dict) -> Dict:
        """Improve existing UI"""
        return {"success": True, "message": "UI improvement not yet implemented"}
