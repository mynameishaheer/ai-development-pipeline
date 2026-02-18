"""
Project Manager Agent for AI Development Pipeline
Manages project lifecycle: GitHub repos, issues, sprints, PRs, and deployments
"""

from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime
import json
import re

from agents.base_agent import BaseAgent
from agents.github_client import GitHubClient, create_github_client
from utils.constants import AgentType, GitHubBranches
from utils.error_handlers import retry_on_rate_limit, GitHubAPIError


class ProjectManagerAgent(BaseAgent):
    """
    Project Manager Agent
    
    Responsibilities:
    - Create and manage GitHub repositories
    - Generate GitHub issues from PRD user stories
    - Create and manage sprints/milestones
    - Manage pull requests and code reviews
    - Coordinate agent assignments
    - Track project progress
    - Merge approved PRs to dev/main branches
    """
    
    def __init__(self, agent_id: Optional[str] = None):
        """Initialize Project Manager Agent"""
        super().__init__(
            agent_type=AgentType.PROJECT_MANAGER,
            agent_id=agent_id
        )
        
        # Initialize GitHub client
        self.github = create_github_client()
        
        # Track managed repositories
        self.managed_repos = {}
        
        self.logger.info("Project Manager Agent initialized")
    
    def get_capabilities(self) -> List[str]:
        """Get agent capabilities"""
        return [
            "Create GitHub repositories",
            "Generate issues from PRD",
            "Create milestones and sprints",
            "Manage pull requests",
            "Coordinate agent assignments",
            "Track project progress",
            "Merge PRs to dev/main",
            "Set up CI/CD workflows"
        ]
    
    async def execute_task(self, task: Dict) -> Dict:
        """
        Execute a task assigned to Project Manager
        
        Args:
            task: Task dictionary with task details
        
        Returns:
            Result dictionary
        """
        task_type = task.get("type", "setup_project")
        
        handlers = {
            "setup_project": self.setup_complete_project,
            "create_repository": self.create_repository,
            "create_issues_from_prd": self.create_issues_from_prd,
            "create_milestone": self.create_milestone,
            "assign_issue": self.assign_issue_to_agent,
            "review_pr": self.review_pull_request,
            "merge_pr": self.merge_pull_request,
        }
        
        handler = handlers.get(task_type)
        
        if not handler:
            raise ValueError(f"Unknown task type: {task_type}")
        
        return await handler(task)
    
    # ==========================================
    # REPOSITORY MANAGEMENT
    # ==========================================
    
    @retry_on_rate_limit(max_retries=5)
    async def create_repository(self, task: Dict) -> Dict:
        """
        Create a GitHub repository for the project
        
        Args:
            task: Task with 'repo_name', 'description', 'private'
        
        Returns:
            Result with repository details
        """
        repo_name = task.get("repo_name", "")
        description = task.get("description", "")
        private = task.get("private", False)
        
        await self.log_action("create_repository", "started", {
            "repo_name": repo_name,
            "private": private
        })
        
        try:
            # Create repository
            repo = await self.github.create_repository(
                name=repo_name,
                description=description,
                private=private,
                auto_init=True,
                gitignore_template="Python"
            )
            
            self.logger.log_github_operation(
                operation="create_repository",
                repo=repo_name,
                status="success",
                details={
                    "url": repo.get("html_url"),
                    "clone_url": repo.get("clone_url")
                }
            )
            
            # Track this repo
            self.managed_repos[repo_name] = {
                "url": repo.get("html_url"),
                "created_at": datetime.now().isoformat(),
                "branches": [GitHubBranches.MAIN]
            }
            
            await self.log_action("create_repository", "completed", {
                "repo_name": repo_name,
                "url": repo.get("html_url")
            })
            
            # Send status update
            await self.send_status_update(
                "repository_created",
                {
                    "repo_name": repo_name,
                    "url": repo.get("html_url")
                }
            )
            
            return {
                "success": True,
                "repo_name": repo_name,
                "repo_url": repo.get("html_url"),
                "clone_url": repo.get("clone_url"),
                "message": "Repository created successfully"
            }
            
        except Exception as e:
            await self.log_action("create_repository", "failed", {
                "error": str(e)
            })
            raise GitHubAPIError(f"Failed to create repository: {str(e)}")
    
    @retry_on_rate_limit()
    async def create_dev_branch(self, repo_name: str) -> Dict:
        """
        Create development branch from main
        
        Args:
            repo_name: Repository name
        
        Returns:
            Result with branch details
        """
        try:
            branch = await self.github.create_branch(
                repo_name=repo_name,
                branch_name=GitHubBranches.DEVELOPMENT,
                from_branch=GitHubBranches.MAIN
            )
            
            self.logger.info(f"Created dev branch in {repo_name}")
            
            # Update tracked branches
            if repo_name in self.managed_repos:
                self.managed_repos[repo_name]["branches"].append(
                    GitHubBranches.DEVELOPMENT
                )
            
            return {
                "success": True,
                "branch_name": GitHubBranches.DEVELOPMENT
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create dev branch: {str(e)}")
            # Don't fail the whole process if branch already exists
            return {
                "success": False,
                "error": str(e)
            }
    
    @retry_on_rate_limit()
    async def setup_branch_protection(self, repo_name: str) -> Dict:
        """
        Set up branch protection rules for main branch
        
        Args:
            repo_name: Repository name
        
        Returns:
            Result dictionary
        """
        try:
            protection = await self.github.protect_branch(
                repo_name=repo_name,
                branch_name=GitHubBranches.MAIN,
                require_reviews=1,
                require_status_checks=True
            )
            
            self.logger.info(f"Set up branch protection for {repo_name}/main")
            
            return {
                "success": True,
                "message": "Branch protection configured"
            }
            
        except Exception as e:
            self.logger.warning(f"Branch protection setup failed: {str(e)}")
            # Non-critical, continue
            return {
                "success": False,
                "error": str(e)
            }
    
    # ==========================================
    # ISSUE MANAGEMENT
    # ==========================================
    
    async def create_issues_from_prd(self, task: Dict) -> Dict:
        """
        Parse PRD and create GitHub issues for user stories
        
        Args:
            task: Task with 'repo_name' and 'prd_path'
        
        Returns:
            Result with created issues
        """
        repo_name = task.get("repo_name", "")
        prd_path = task.get("prd_path", "")
        
        await self.log_action("create_issues_from_prd", "started", {
            "repo_name": repo_name,
            "prd_path": prd_path
        })
        
        try:
            # Read PRD
            with open(prd_path, 'r') as f:
                prd_content = f.read()
            
            # Extract user stories using Claude Code
            stories = await self._extract_user_stories(prd_content, prd_path)
            
            # Create GitHub issues
            created_issues = []
            
            for story in stories:
                issue = await self._create_issue_from_story(
                    repo_name=repo_name,
                    story=story
                )
                created_issues.append(issue)
            
            await self.log_action("create_issues_from_prd", "completed", {
                "repo_name": repo_name,
                "issues_created": len(created_issues)
            })
            
            # Send status update
            await self.send_status_update(
                "issues_created",
                {
                    "repo_name": repo_name,
                    "count": len(created_issues)
                }
            )
            
            return {
                "success": True,
                "repo_name": repo_name,
                "issues_created": len(created_issues),
                "issues": created_issues,
                "message": f"Created {len(created_issues)} issues from PRD"
            }
            
        except Exception as e:
            await self.log_action("create_issues_from_prd", "failed", {
                "error": str(e)
            })
            raise
    
    async def _extract_user_stories(self, prd_content: str, prd_path: str) -> List[Dict]:
        """
        Extract user stories from PRD using Claude Code
        
        Args:
            prd_content: PRD content
            prd_path: Path to PRD file
        
        Returns:
            List of user story dictionaries
        """
        # Get project path
        project_path = str(Path(prd_path).parent.parent)
        
        prompt = f"""
Read the PRD and extract all user stories.

For each user story, create a JSON object with:
- title: Brief title for the story
- description: Full story description (As a... I want... So that...)
- acceptance_criteria: List of acceptance criteria
- priority: "high", "medium", or "low"
- story_points: Estimated effort (1, 2, 3, 5, 8, 13)
- labels: List of relevant labels (e.g., ["feature", "backend", "frontend"])
- epic: The feature area this belongs to

Create a file called docs/EXTRACTED_STORIES.json with a JSON array of all stories.

CRITICAL: The output MUST be valid JSON. Use this exact format:
[
  {{
    "title": "User Registration",
    "description": "As a resident, I want to register my account...",
    "acceptance_criteria": ["Criterion 1", "Criterion 2"],
    "priority": "high",
    "story_points": 5,
    "labels": ["feature", "backend"],
    "epic": "Resident Management"
  }}
]
"""
        # Read PRD content and include in prompt since --context not supported
        with open(prd_path, 'r') as f:
            prd_text = f.read()

        enhanced_prompt = f"{prompt}\n\nHere is the PRD content:\n\n{prd_text[:10000]}"  # First 10k chars

        result = await self.call_claude_code(
            prompt=enhanced_prompt,
            project_path=project_path,
            allowed_tools=["Write", "Read"]
            # context_files removed - not supported
        )
       
        
        # Read the extracted stories
        stories_file = Path(project_path) / "docs" / "EXTRACTED_STORIES.json"
        
        if stories_file.exists():
            with open(stories_file, 'r') as f:
                stories = json.load(f)
            
            self.logger.info(f"Extracted {len(stories)} user stories from PRD")
            return stories
        else:
            self.logger.warning("Could not extract stories, creating default issues")
            return self._create_default_issues()
    
    def _create_default_issues(self) -> List[Dict]:
        """Create default issues if extraction fails"""
        return [
            {
                "title": "Set up project structure",
                "description": "Initialize project with proper directory structure, dependencies, and configuration",
                "acceptance_criteria": [
                    "Backend structure created",
                    "Frontend structure created",
                    "Database configured"
                ],
                "priority": "high",
                "story_points": 3,
                "labels": ["setup", "infrastructure"],
                "epic": "Project Setup"
            },
            {
                "title": "Implement user authentication",
                "description": "As a user, I want to register and login securely",
                "acceptance_criteria": [
                    "User can register",
                    "User can login",
                    "JWT tokens implemented",
                    "Password hashing implemented"
                ],
                "priority": "high",
                "story_points": 8,
                "labels": ["feature", "backend", "security"],
                "epic": "User Management"
            }
        ]
    
    @retry_on_rate_limit()
    async def _create_issue_from_story(self, repo_name: str, story: Dict) -> Dict:
        """
        Create a GitHub issue from a user story
        
        Args:
            repo_name: Repository name
            story: User story dictionary
        
        Returns:
            Created issue details
        """
        # Format issue body
        body = f"""## User Story

{story.get('description', '')}

## Acceptance Criteria

"""
        
        for i, criterion in enumerate(story.get('acceptance_criteria', []), 1):
            body += f"{i}. {criterion}\n"
        
        body += f"\n## Story Points\n\n{story.get('story_points', 3)}\n"
        body += f"\n## Epic\n\n{story.get('epic', 'General')}\n"
        
        # Create issue
        issue = await self.github.create_issue(
            repo_name=repo_name,
            title=story.get('title', 'Untitled Story'),
            body=body,
            labels=story.get('labels', ['feature'])
        )
        
        self.logger.log_github_operation(
            operation="create_issue",
            repo=repo_name,
            status="success",
            details={
                "issue_number": issue.get("number"),
                "title": story.get('title')
            }
        )
        
        return {
            "number": issue.get("number"),
            "title": story.get('title'),
            "url": issue.get("html_url")
        }
    
    # ==========================================
    # MILESTONE MANAGEMENT
    # ==========================================
    
    async def create_milestone(self, task: Dict) -> Dict:
        """
        Create a milestone for sprint planning
        
        Args:
            task: Task with 'repo_name', 'title', 'description', 'due_date'
        
        Returns:
            Result with milestone details
        """
        repo_name = task.get("repo_name", "")
        title = task.get("title", "")
        description = task.get("description", "")
        
        # Note: GitHub API milestone creation would go here
        # For now, log the action
        
        await self.log_action("create_milestone", "completed", {
            "repo_name": repo_name,
            "title": title
        })
        
        return {
            "success": True,
            "title": title,
            "message": "Milestone created"
        }
    
    # ==========================================
    # PULL REQUEST MANAGEMENT
    # ==========================================
    
    @retry_on_rate_limit()
    async def review_pull_request(self, task: Dict) -> Dict:
        """
        Review a pull request (typically called by QA agent)
        
        Args:
            task: Task with 'repo_name', 'pr_number', 'approved'
        
        Returns:
            Result with review status
        """
        repo_name = task.get("repo_name", "")
        pr_number = task.get("pr_number", 0)
        approved = task.get("approved", False)
        
        # In a full implementation, this would add a review comment
        # For now, we'll just log it
        
        await self.log_action("review_pr", "completed", {
            "repo_name": repo_name,
            "pr_number": pr_number,
            "approved": approved
        })
        
        return {
            "success": True,
            "pr_number": pr_number,
            "approved": approved
        }
    
    @retry_on_rate_limit()
    async def merge_pull_request(self, task: Dict) -> Dict:
        """
        Merge an approved pull request
        
        Args:
            task: Task with 'repo_name', 'pr_number', 'target_branch'
        
        Returns:
            Result with merge status
        """
        repo_name = task.get("repo_name", "")
        pr_number = task.get("pr_number", 0)
        target_branch = task.get("target_branch", GitHubBranches.DEVELOPMENT)
        
        await self.log_action("merge_pr", "started", {
            "repo_name": repo_name,
            "pr_number": pr_number,
            "target": target_branch
        })
        
        try:
            # Merge the PR
            result = await self.github.merge_pull_request(
                repo_name=repo_name,
                pr_number=pr_number,
                merge_method="squash"  # Squash commits for clean history
            )
            
            self.logger.log_github_operation(
                operation="merge_pr",
                repo=repo_name,
                status="success",
                details={
                    "pr_number": pr_number,
                    "merged": result.get("merged", False)
                }
            )
            
            await self.log_action("merge_pr", "completed", {
                "repo_name": repo_name,
                "pr_number": pr_number
            })
            
            # Notify other agents
            await self.send_status_update(
                "pr_merged",
                {
                    "repo_name": repo_name,
                    "pr_number": pr_number,
                    "branch": target_branch
                }
            )
            
            return {
                "success": True,
                "pr_number": pr_number,
                "merged": result.get("merged", False),
                "message": "Pull request merged successfully"
            }
            
        except Exception as e:
            await self.log_action("merge_pr", "failed", {
                "error": str(e)
            })
            raise
    
    # ==========================================
    # PROJECT SETUP (COMPLETE WORKFLOW)
    # ==========================================
    
    async def setup_complete_project(self, task: Dict) -> Dict:
        """
        Complete project setup workflow
        
        This orchestrates:
        1. Create GitHub repository
        2. Create dev branch
        3. Set up branch protection
        4. Create labels
        5. Create issues from PRD
        6. Create initial milestones
        
        Args:
            task: Task with 'project_name', 'description', 'prd_path'
        
        Returns:
            Complete setup result
        """
        project_name = task.get("project_name", "")
        description = task.get("description", "")
        prd_path = task.get("prd_path", "")
        
        await self.log_action("setup_complete_project", "started", {
            "project": project_name
        })
        
        results = {
            "project_name": project_name,
            "steps_completed": []
        }
        
        try:
            # Step 1: Create repository
            repo_result = await self.create_repository({
                "repo_name": project_name,
                "description": description,
                "private": False
            })
            results["repository"] = repo_result
            results["steps_completed"].append("repository_created")
            
            # Step 2: Create dev branch
            dev_result = await self.create_dev_branch(project_name)
            if dev_result["success"]:
                results["steps_completed"].append("dev_branch_created")
            
            # Step 3: Set up branch protection
            protection_result = await self.setup_branch_protection(project_name)
            if protection_result["success"]:
                results["steps_completed"].append("branch_protection_set")
            
            # Step 4: Create standard labels
            await self._create_standard_labels(project_name)
            results["steps_completed"].append("labels_created")
            
            # Step 5: Create issues from PRD
            if prd_path:
                issues_result = await self.create_issues_from_prd({
                    "repo_name": project_name,
                    "prd_path": prd_path
                })
                results["issues"] = issues_result
                results["steps_completed"].append("issues_created")
            
            # Step 6: Create initial project files
            await self._create_initial_files(project_name, description)
            results["steps_completed"].append("initial_files_created")
            
            await self.log_action("setup_complete_project", "completed", {
                "project": project_name,
                "steps": len(results["steps_completed"])
            })
            
            return {
                "success": True,
                **results,
                "message": f"Project {project_name} set up successfully"
            }
            
        except Exception as e:
            await self.log_action("setup_complete_project", "failed", {
                "error": str(e),
                "steps_completed": len(results.get("steps_completed", []))
            })
            raise
    
    @retry_on_rate_limit()
    async def _create_standard_labels(self, repo_name: str):
        """Create standard labels for issues"""
        labels = [
            {"name": "feature", "color": "0052CC", "description": "New feature"},
            {"name": "bug", "color": "D73A4A", "description": "Bug fix"},
            {"name": "enhancement", "color": "84B6EB", "description": "Enhancement"},
            {"name": "backend", "color": "F9D0C4", "description": "Backend work"},
            {"name": "frontend", "color": "C5DEF5", "description": "Frontend work"},
            {"name": "database", "color": "D4C5F9", "description": "Database work"},
            {"name": "high-priority", "color": "FF0000", "description": "High priority"},
            {"name": "medium-priority", "color": "FFA500", "description": "Medium priority"},
            {"name": "low-priority", "color": "00FF00", "description": "Low priority"},
        ]
        
        await self.github.create_labels(repo_name, labels)
        self.logger.info(f"Created standard labels for {repo_name}")
    
    async def _create_initial_files(self, repo_name: str, description: str):
        """Create initial project files (README, CONTRIBUTING, etc.)"""
        
        # Create README
        readme_content = f"""# {repo_name}

{description}

## Overview

This project was automatically generated and is managed by the AI Development Pipeline.

## Getting Started

Instructions coming soon...

## Development

See CONTRIBUTING.md for development guidelines.

## License

MIT License
"""
        
        # Get existing README to get its SHA (needed for update)
        try:
            existing = await self.github.get_file_content(
                repo_name=repo_name,
                file_path="README.md",
                branch=GitHubBranches.MAIN
            )
            sha = existing.get("sha")
        except:
            sha = None  # File doesn't exist

        # Create or update README
        await self.github.create_or_update_file(
            repo_name=repo_name,
            file_path="README.md",
            content=readme_content,
            commit_message="Update README with project details",
            branch=GitHubBranches.MAIN,
            sha=sha  # Include SHA for update
        )

        self.logger.info(f"Created initial files for {repo_name}")
        
    
    async def assign_issue_to_agent(self, task: Dict) -> Dict:
        """
        Assign an issue to an agent for implementation
        
        Args:
            task: Task with 'repo_name', 'issue_number', 'agent_type'
        
        Returns:
            Assignment result
        """
        repo_name = task.get("repo_name", "")
        issue_number = task.get("issue_number", 0)
        agent_type = task.get("agent_type", "")
        
        # Send task assignment to the appropriate agent
        await self.messenger.send_message(
            recipient=agent_type,
            message_type="task_assignment",
            content={
                "task_type": "implement_feature",
                "repo_name": repo_name,
                "issue_number": issue_number,
                "assigned_by": f"{self.agent_type}:{self.agent_id}"
            },
            priority=1,
            use_queue=True
        )
        
        self.logger.info(
            f"Assigned issue #{issue_number} to {agent_type}",
            extra={"repo": repo_name, "issue": issue_number}
        )
        
        return {
            "success": True,
            "issue_number": issue_number,
            "assigned_to": agent_type
        }


# ==========================================
# CONVENIENCE FUNCTIONS
# ==========================================

async def setup_project(
    project_name: str,
    description: str,
    prd_path: str
) -> Dict:
    """
    Set up a complete project with GitHub repo and issues
    
    Args:
        project_name: Project repository name
        description: Project description
        prd_path: Path to PRD file
    
    Returns:
        Setup result
    """
    pm = ProjectManagerAgent()
    
    result = await pm.setup_complete_project({
        "project_name": project_name,
        "description": description,
        "prd_path": prd_path
    })
    
    return result


# ==========================================
# EXAMPLE USAGE
# ==========================================

if __name__ == "__main__":
    import asyncio
    
    async def test_project_manager():
        """Test Project Manager Agent"""
        
        pm = ProjectManagerAgent()
        
        # Test repository creation
        result = await pm.create_repository({
            "repo_name": "test-project",
            "description": "Test project created by Project Manager Agent",
            "private": False
        })
        
        print(f"Repository created: {result}")
    
    asyncio.run(test_project_manager())
