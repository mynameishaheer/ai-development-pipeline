"""
Assignment Manager for AI Development Pipeline
Automatically assigns GitHub issues to the appropriate development agents
based on issue labels, titles, and content analysis.
"""

import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import redis

from agents.github_client import create_github_client
from utils.constants import AgentType, REDIS_HOST, REDIS_PORT, TaskStatus
from utils.structured_logger import get_logger


# Mapping from issue labels to agent types
LABEL_TO_AGENT: Dict[str, str] = {
    # Backend signals
    "backend": AgentType.BACKEND,
    "api": AgentType.BACKEND,
    "server": AgentType.BACKEND,
    "authentication": AgentType.BACKEND,
    "authorization": AgentType.BACKEND,
    "security": AgentType.BACKEND,
    "endpoint": AgentType.BACKEND,

    # Frontend signals
    "frontend": AgentType.FRONTEND,
    "ui": AgentType.FRONTEND,
    "ux": AgentType.FRONTEND,
    "component": AgentType.FRONTEND,
    "design": AgentType.FRONTEND,
    "css": AgentType.FRONTEND,
    "responsive": AgentType.FRONTEND,

    # Database signals
    "database": AgentType.DATABASE,
    "db": AgentType.DATABASE,
    "schema": AgentType.DATABASE,
    "migration": AgentType.DATABASE,
    "query": AgentType.DATABASE,
    "model": AgentType.DATABASE,

    # DevOps signals
    "devops": AgentType.DEVOPS,
    "deployment": AgentType.DEVOPS,
    "infrastructure": AgentType.DEVOPS,
    "ci/cd": AgentType.DEVOPS,
    "docker": AgentType.DEVOPS,
    "kubernetes": AgentType.DEVOPS,
    "monitoring": AgentType.DEVOPS,

    # QA signals
    "qa": AgentType.QA,
    "testing": AgentType.QA,
    "test": AgentType.QA,
    "bug": AgentType.QA,
}

# Keyword patterns in issue title/body for agent selection
KEYWORD_PATTERNS: Dict[str, List[str]] = {
    AgentType.BACKEND: [
        r"api\b", r"endpoint", r"route", r"service", r"backend",
        r"auth(entication|orization)?", r"server", r"rest", r"graphql",
        r"business logic", r"validation", r"middleware",
    ],
    AgentType.FRONTEND: [
        r"ui\b", r"ux\b", r"component", r"page", r"screen", r"button",
        r"form", r"modal", r"dashboard", r"menu", r"nav", r"layout",
        r"react", r"vue", r"angular", r"frontend", r"responsive",
    ],
    AgentType.DATABASE: [
        r"database", r"\bdb\b", r"schema", r"table", r"column", r"index",
        r"migration", r"query", r"model", r"relation", r"foreign key",
        r"postgres", r"mysql", r"sqlite", r"orm", r"alembic",
    ],
    AgentType.DEVOPS: [
        r"deploy", r"docker", r"kubernetes", r"container", r"ci/cd",
        r"pipeline", r"nginx", r"ssl", r"certificate", r"domain",
        r"server setup", r"infrastructure", r"scaling", r"monitoring",
    ],
    AgentType.QA: [
        r"test(ing)?", r"bug", r"fix", r"broken", r"error",
        r"coverage", r"assertion", r"jest", r"pytest", r"cypress",
        r"regression", r"quality",
    ],
}


class AssignmentManager:
    """
    Manages automatic assignment of GitHub issues to development agents.

    Uses label-based and keyword-based classification to determine
    which agent should handle each issue, then queues tasks via Redis.
    """

    def __init__(self):
        """Initialize Assignment Manager"""
        self.logger = get_logger("assignment_manager", agent_type="master")
        self.github = create_github_client()
        self.redis = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            decode_responses=True
        )
        self.logger.info("Assignment Manager initialized")

    # ==========================================
    # ISSUE CLASSIFICATION
    # ==========================================

    def classify_issue(self, issue: Dict) -> Tuple[str, float]:
        """
        Classify an issue and determine which agent should handle it.

        Uses a scoring system based on:
        1. Issue labels (highest weight)
        2. Keywords in title (medium weight)
        3. Keywords in body (lower weight)

        Args:
            issue: GitHub issue dictionary

        Returns:
            Tuple of (agent_type, confidence_score)
        """
        scores: Dict[str, float] = {
            AgentType.BACKEND: 0.0,
            AgentType.FRONTEND: 0.0,
            AgentType.DATABASE: 0.0,
            AgentType.DEVOPS: 0.0,
            AgentType.QA: 0.0,
        }

        # Score from labels (weight: 3.0)
        labels = [lbl.get("name", "").lower() for lbl in issue.get("labels", [])]
        for label in labels:
            agent = LABEL_TO_AGENT.get(label)
            if agent and agent in scores:
                scores[agent] += 3.0

        # Score from title (weight: 2.0)
        title = issue.get("title", "").lower()
        for agent_type, patterns in KEYWORD_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, title, re.IGNORECASE):
                    scores[agent_type] += 2.0

        # Score from body (weight: 1.0)
        body = issue.get("body", "").lower()
        for agent_type, patterns in KEYWORD_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, body, re.IGNORECASE):
                    scores[agent_type] += 1.0

        # Find the highest scoring agent
        best_agent = max(scores, key=scores.__getitem__)
        best_score = scores[best_agent]

        # Normalize confidence to 0-1
        total_score = sum(scores.values())
        confidence = (best_score / total_score) if total_score > 0 else 0.5

        self.logger.info(
            f"Classified issue #{issue.get('number')}: {best_agent} (confidence: {confidence:.2f})",
            extra={"scores": scores, "issue": issue.get("number")}
        )

        return best_agent, confidence

    def classify_issues(self, issues: List[Dict]) -> List[Dict]:
        """
        Classify multiple issues and return assignment plan.

        Args:
            issues: List of GitHub issue dictionaries

        Returns:
            List of assignment dictionaries
        """
        assignments = []

        for issue in issues:
            agent_type, confidence = self.classify_issue(issue)

            assignments.append({
                "issue_number": issue.get("number"),
                "issue_title": issue.get("title"),
                "assigned_agent": agent_type,
                "confidence": confidence,
                "labels": [lbl.get("name") for lbl in issue.get("labels", [])],
            })

        return assignments

    # ==========================================
    # ASSIGNMENT EXECUTION
    # ==========================================

    async def assign_issue(
        self,
        repo_name: str,
        issue_number: int,
        agent_type: str,
        project_path: str = ""
    ) -> Dict:
        """
        Assign a single issue to an agent by queuing it as a task.

        Args:
            repo_name: GitHub repository name
            issue_number: Issue number to assign
            agent_type: Agent type to assign to
            project_path: Local project path

        Returns:
            Assignment result
        """
        task = {
            "task_type": "implement_feature",
            "repo_name": repo_name,
            "issue_number": issue_number,
            "project_path": project_path,
            "assigned_at": datetime.now().isoformat(),
            "status": TaskStatus.PENDING,
            "assigned_agent": agent_type,
        }

        # Queue task in Redis for the appropriate agent
        queue_key = f"queue:agent:{agent_type}"
        task_json = json.dumps(task)

        # Use sorted set with priority (lower score = higher priority)
        priority = self._get_issue_priority(repo_name, issue_number)
        self.redis.zadd(queue_key, {task_json: priority})

        # Track assignment
        tracking_key = f"assignment:{repo_name}:{issue_number}"
        self.redis.hset(tracking_key, mapping={
            "agent": agent_type,
            "status": TaskStatus.PENDING,
            "assigned_at": datetime.now().isoformat(),
        })
        self.redis.expire(tracking_key, 86400 * 7)  # 7 days TTL

        self.logger.info(
            f"Assigned issue #{issue_number} to {agent_type}",
            extra={"repo": repo_name, "priority": priority}
        )

        # Add a comment on the GitHub issue
        try:
            comment = (
                f"🤖 **Auto-Assignment**: This issue has been assigned to the "
                f"**{agent_type.replace('_', ' ').title()} Agent** for implementation.\n\n"
                f"The agent will:\n"
                f"1. Create a feature branch\n"
                f"2. Implement the feature\n"
                f"3. Write tests\n"
                f"4. Submit a pull request for review\n\n"
                f"*Assigned automatically by the AI Development Pipeline*"
            )
            await self.github.add_issue_comment(repo_name, issue_number, comment)
        except Exception as e:
            self.logger.warning(f"Could not comment on issue: {e}")

        return {
            "success": True,
            "issue_number": issue_number,
            "assigned_to": agent_type,
            "queue_key": queue_key,
            "task": task,
        }

    async def assign_all_issues(
        self,
        repo_name: str,
        project_path: str = "",
        max_issues: int = 50
    ) -> Dict:
        """
        Fetch all open issues from a repo and assign them to appropriate agents.

        Args:
            repo_name: GitHub repository name
            project_path: Local project path
            max_issues: Maximum number of issues to assign

        Returns:
            Assignment summary
        """
        self.logger.info(f"Starting bulk assignment for {repo_name}")

        # Fetch open issues
        try:
            issues = await self.github.list_issues(repo_name, state="open")
        except Exception as e:
            return {"success": False, "error": f"Could not fetch issues: {e}"}

        # Limit
        issues = issues[:max_issues]

        if not issues:
            return {"success": True, "assigned": 0, "message": "No open issues found"}

        # Classify all issues
        assignments = self.classify_issues(issues)

        # Execute assignments
        assigned_count = 0
        assignment_results = []

        for assignment in assignments:
            try:
                result = await self.assign_issue(
                    repo_name=repo_name,
                    issue_number=assignment["issue_number"],
                    agent_type=assignment["assigned_agent"],
                    project_path=project_path
                )
                assignment_results.append({**assignment, "result": result})
                assigned_count += 1
            except Exception as e:
                self.logger.error(
                    f"Failed to assign issue #{assignment['issue_number']}: {e}"
                )
                assignment_results.append({**assignment, "error": str(e)})

        summary = self._generate_assignment_summary(assignment_results)

        return {
            "success": True,
            "total_issues": len(issues),
            "assigned": assigned_count,
            "assignments": assignment_results,
            "summary": summary,
        }

    # ==========================================
    # TASK QUEUE MANAGEMENT
    # ==========================================

    def get_pending_tasks(self, agent_type: str, count: int = 10) -> List[Dict]:
        """
        Get pending tasks for a specific agent from the queue.

        Args:
            agent_type: Agent type to get tasks for
            count: Maximum number of tasks to return

        Returns:
            List of pending task dictionaries
        """
        queue_key = f"queue:agent:{agent_type}"
        task_jsons = self.redis.zrange(queue_key, 0, count - 1)

        tasks = []
        for task_json in task_jsons:
            try:
                task = json.loads(task_json)
                tasks.append(task)
            except json.JSONDecodeError:
                continue

        return tasks

    def claim_next_task(self, agent_type: str) -> Optional[Dict]:
        """
        Atomically claim the next highest-priority task for an agent.

        Args:
            agent_type: Agent type claiming the task

        Returns:
            Task dictionary or None if queue is empty
        """
        queue_key = f"queue:agent:{agent_type}"

        # Get and remove the highest priority task (lowest score)
        tasks = self.redis.zpopmin(queue_key, 1)

        if not tasks:
            return None

        task_json, _priority = tasks[0]

        try:
            task = json.loads(task_json)

            # Update tracking
            tracking_key = f"assignment:{task.get('repo_name')}:{task.get('issue_number')}"
            self.redis.hset(tracking_key, mapping={
                "status": TaskStatus.IN_PROGRESS,
                "claimed_at": datetime.now().isoformat(),
            })

            return task
        except json.JSONDecodeError:
            return None

    def complete_task(self, repo_name: str, issue_number: int, result: Dict):
        """
        Mark a task as completed.

        Args:
            repo_name: Repository name
            issue_number: Issue number
            result: Completion result
        """
        tracking_key = f"assignment:{repo_name}:{issue_number}"
        self.redis.hset(tracking_key, mapping={
            "status": TaskStatus.COMPLETED,
            "completed_at": datetime.now().isoformat(),
            "result_summary": json.dumps(result)[:500],
        })

    def fail_task(self, repo_name: str, issue_number: int, error: str):
        """
        Mark a task as failed.

        Args:
            repo_name: Repository name
            issue_number: Issue number
            error: Error message
        """
        tracking_key = f"assignment:{repo_name}:{issue_number}"
        self.redis.hset(tracking_key, mapping={
            "status": TaskStatus.FAILED,
            "failed_at": datetime.now().isoformat(),
            "error": error[:500],
        })

    def get_queue_status(self) -> Dict:
        """
        Get status of all agent queues.

        Returns:
            Dictionary with queue sizes per agent
        """
        status = {}
        agent_types = [
            AgentType.BACKEND,
            AgentType.FRONTEND,
            AgentType.DATABASE,
            AgentType.DEVOPS,
            AgentType.QA,
        ]

        for agent_type in agent_types:
            queue_key = f"queue:agent:{agent_type}"
            count = self.redis.zcard(queue_key)
            status[agent_type] = {
                "pending_tasks": count,
                "queue_key": queue_key,
            }

        return status

    def clear_all_queues(self):
        """Clear all agent task queues (use with caution)"""
        agent_types = [
            AgentType.BACKEND, AgentType.FRONTEND,
            AgentType.DATABASE, AgentType.DEVOPS, AgentType.QA,
        ]
        for agent_type in agent_types:
            self.redis.delete(f"queue:agent:{agent_type}")
        self.logger.warning("All agent queues cleared")

    # ==========================================
    # UTILITIES
    # ==========================================

    def _get_issue_priority(self, repo_name: str, issue_number: int) -> float:
        """
        Determine task priority based on issue labels.
        Returns a score where lower = higher priority.
        """
        try:
            # We already have the issue data when we call this
            # Use issue number as a simple proxy (lower number = older = higher priority)
            return float(issue_number)
        except Exception:
            return 999.0

    def _generate_assignment_summary(self, assignments: List[Dict]) -> Dict:
        """Generate a summary of assignments by agent type"""
        summary: Dict[str, List[int]] = {}

        for assignment in assignments:
            agent = assignment.get("assigned_agent", "unknown")
            issue_num = assignment.get("issue_number", 0)

            if agent not in summary:
                summary[agent] = []
            summary[agent].append(issue_num)

        return {
            agent: {"count": len(issues), "issues": issues}
            for agent, issues in summary.items()
        }

    def get_assignment_status(self, repo_name: str, issue_number: int) -> Optional[Dict]:
        """
        Get the current assignment status for an issue.

        Args:
            repo_name: Repository name
            issue_number: Issue number

        Returns:
            Assignment status dictionary or None
        """
        tracking_key = f"assignment:{repo_name}:{issue_number}"
        data = self.redis.hgetall(tracking_key)

        if not data:
            return None

        return {
            "issue_number": issue_number,
            "repo_name": repo_name,
            **data
        }


# ==========================================
# CONVENIENCE FUNCTIONS
# ==========================================

async def assign_issues_for_repo(
    repo_name: str,
    project_path: str = ""
) -> Dict:
    """
    Assign all open issues in a repository to appropriate agents.

    Args:
        repo_name: GitHub repository name
        project_path: Local project path

    Returns:
        Assignment summary
    """
    manager = AssignmentManager()
    return await manager.assign_all_issues(
        repo_name=repo_name,
        project_path=project_path
    )


# ==========================================
# EXAMPLE USAGE
# ==========================================

if __name__ == "__main__":
    import asyncio

    async def test_assignment_manager():
        """Test the Assignment Manager"""
        manager = AssignmentManager()

        # Test classification with mock issues
        mock_issues = [
            {
                "number": 1,
                "title": "Add user authentication API endpoint",
                "body": "Implement JWT authentication for the REST API",
                "labels": [{"name": "backend"}, {"name": "feature"}]
            },
            {
                "number": 2,
                "title": "Create login page UI component",
                "body": "Build responsive login form with React",
                "labels": [{"name": "frontend"}, {"name": "ui"}]
            },
            {
                "number": 3,
                "title": "Design user database schema",
                "body": "Create SQLAlchemy models for users and profiles",
                "labels": [{"name": "database"}, {"name": "schema"}]
            },
        ]

        assignments = manager.classify_issues(mock_issues)
        print("\n📋 Issue Classifications:")
        for a in assignments:
            print(f"  Issue #{a['issue_number']}: {a['issue_title']}")
            print(f"  → {a['assigned_agent']} (confidence: {a['confidence']:.2f})")
            print()

        print("Queue Status:")
        status = manager.get_queue_status()
        for agent, info in status.items():
            print(f"  {agent}: {info['pending_tasks']} pending tasks")

    asyncio.run(test_assignment_manager())
