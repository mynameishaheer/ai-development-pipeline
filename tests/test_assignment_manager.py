"""
Tests for Assignment Manager (Phase 3.2)
Tests issue classification and task queue management.
All tests use mocks — no Redis or GitHub connection required.
"""

import json
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from agents.assignment_manager import AssignmentManager, LABEL_TO_AGENT, KEYWORD_PATTERNS
from utils.constants import AgentType, TaskStatus


# ==========================================
# FIXTURES
# ==========================================

@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis_mock = MagicMock()
    redis_mock.zadd = MagicMock(return_value=1)
    redis_mock.hset = MagicMock(return_value=1)
    redis_mock.expire = MagicMock(return_value=True)
    redis_mock.zrange = MagicMock(return_value=[])
    redis_mock.zpopmin = MagicMock(return_value=[])
    redis_mock.zcard = MagicMock(return_value=0)
    redis_mock.hgetall = MagicMock(return_value={})
    redis_mock.delete = MagicMock(return_value=1)
    return redis_mock


@pytest.fixture
def mock_github():
    """Mock GitHub client."""
    github_mock = AsyncMock()
    github_mock.list_issues = AsyncMock(return_value=[])
    github_mock.add_issue_comment = AsyncMock(return_value=True)
    return github_mock


@pytest.fixture
def manager(mock_redis, mock_github):
    """Assignment manager with mocked dependencies."""
    with patch("agents.assignment_manager.redis.Redis", return_value=mock_redis), \
         patch("agents.assignment_manager.create_github_client", return_value=mock_github):
        mgr = AssignmentManager()
        mgr.redis = mock_redis
        mgr.github = mock_github
        return mgr


# ==========================================
# ISSUE CLASSIFICATION TESTS
# ==========================================

class TestIssueClassification:

    def test_classify_backend_by_label(self, manager):
        issue = {
            "number": 1,
            "title": "New feature",
            "body": "Some description",
            "labels": [{"name": "backend"}],
        }
        agent_type, confidence = manager.classify_issue(issue)
        assert agent_type == AgentType.BACKEND
        assert confidence > 0.5

    def test_classify_frontend_by_label(self, manager):
        issue = {
            "number": 2,
            "title": "New page",
            "body": "",
            "labels": [{"name": "frontend"}, {"name": "ui"}],
        }
        agent_type, confidence = manager.classify_issue(issue)
        assert agent_type == AgentType.FRONTEND
        assert confidence > 0.5

    def test_classify_database_by_label(self, manager):
        issue = {
            "number": 3,
            "title": "Update models",
            "body": "",
            "labels": [{"name": "database"}, {"name": "schema"}],
        }
        agent_type, confidence = manager.classify_issue(issue)
        assert agent_type == AgentType.DATABASE

    def test_classify_devops_by_label(self, manager):
        issue = {
            "number": 4,
            "title": "Set up deployment",
            "body": "",
            "labels": [{"name": "devops"}, {"name": "docker"}],
        }
        agent_type, confidence = manager.classify_issue(issue)
        assert agent_type == AgentType.DEVOPS

    def test_classify_qa_by_label(self, manager):
        issue = {
            "number": 5,
            "title": "Fix failing tests",
            "body": "",
            "labels": [{"name": "qa"}, {"name": "bug"}],
        }
        agent_type, confidence = manager.classify_issue(issue)
        assert agent_type == AgentType.QA

    def test_classify_backend_by_title_keyword(self, manager):
        issue = {
            "number": 6,
            "title": "Implement REST API endpoint for user login",
            "body": "",
            "labels": [],
        }
        agent_type, confidence = manager.classify_issue(issue)
        assert agent_type == AgentType.BACKEND

    def test_classify_frontend_by_title_keyword(self, manager):
        issue = {
            "number": 7,
            "title": "Create login page React component",
            "body": "",
            "labels": [],
        }
        agent_type, confidence = manager.classify_issue(issue)
        assert agent_type == AgentType.FRONTEND

    def test_classify_database_by_title_keyword(self, manager):
        issue = {
            "number": 8,
            "title": "Add Alembic migration for users table",
            "body": "",
            "labels": [],
        }
        agent_type, confidence = manager.classify_issue(issue)
        assert agent_type == AgentType.DATABASE

    def test_classify_devops_by_title_keyword(self, manager):
        issue = {
            "number": 9,
            "title": "Set up Docker container and CI/CD pipeline",
            "body": "",
            "labels": [],
        }
        agent_type, confidence = manager.classify_issue(issue)
        assert agent_type == AgentType.DEVOPS

    def test_classify_from_body_keyword(self, manager):
        issue = {
            "number": 10,
            "title": "Improve system performance",
            "body": "We need to add database indexes and optimize postgres queries",
            "labels": [],
        }
        agent_type, confidence = manager.classify_issue(issue)
        assert agent_type == AgentType.DATABASE

    def test_label_beats_body_keyword(self, manager):
        """Label signal (3.0) should override conflicting body keyword (1.0)."""
        issue = {
            "number": 11,
            "title": "Feature",
            "body": "This relates to the React frontend components",
            "labels": [{"name": "backend"}, {"name": "backend"}, {"name": "backend"}],
        }
        agent_type, _ = manager.classify_issue(issue)
        assert agent_type == AgentType.BACKEND

    def test_classify_no_signals_returns_some_agent(self, manager):
        """Even with no signals, should return a valid agent type."""
        issue = {
            "number": 12,
            "title": "Random issue",
            "body": "Some random text with no keywords",
            "labels": [],
        }
        agent_type, confidence = manager.classify_issue(issue)
        valid_types = {
            AgentType.BACKEND, AgentType.FRONTEND, AgentType.DATABASE,
            AgentType.DEVOPS, AgentType.QA
        }
        assert agent_type in valid_types
        # With zero total score, confidence should be 0.5
        assert confidence == 0.5

    def test_confidence_sums_to_reasonable_range(self, manager):
        issue = {
            "number": 13,
            "title": "Implement REST API endpoint",
            "body": "Build server-side auth route for users",
            "labels": [{"name": "backend"}],
        }
        _, confidence = manager.classify_issue(issue)
        assert 0.0 <= confidence <= 1.0

    def test_classify_issues_batch(self, manager):
        issues = [
            {"number": 1, "title": "API endpoint", "body": "", "labels": [{"name": "backend"}]},
            {"number": 2, "title": "React component", "body": "", "labels": [{"name": "frontend"}]},
            {"number": 3, "title": "DB schema", "body": "", "labels": [{"name": "database"}]},
        ]
        assignments = manager.classify_issues(issues)
        assert len(assignments) == 3
        assert assignments[0]["assigned_agent"] == AgentType.BACKEND
        assert assignments[1]["assigned_agent"] == AgentType.FRONTEND
        assert assignments[2]["assigned_agent"] == AgentType.DATABASE


# ==========================================
# TASK QUEUE TESTS
# ==========================================

class TestTaskQueue:

    @pytest.mark.asyncio
    async def test_assign_issue_queues_task(self, manager, mock_redis):
        result = await manager.assign_issue(
            repo_name="myrepo",
            issue_number=1,
            agent_type=AgentType.BACKEND,
            project_path="/tmp/project",
        )

        assert result["success"] is True
        assert result["assigned_to"] == AgentType.BACKEND
        assert result["issue_number"] == 1
        assert mock_redis.zadd.called

    @pytest.mark.asyncio
    async def test_assign_issue_tracks_in_redis(self, manager, mock_redis):
        await manager.assign_issue("myrepo", 5, AgentType.QA, "/tmp/proj")

        # Verify tracking hash was set
        assert mock_redis.hset.called
        call_kwargs = mock_redis.hset.call_args
        assert call_kwargs is not None

    @pytest.mark.asyncio
    async def test_assign_issue_sets_ttl(self, manager, mock_redis):
        await manager.assign_issue("myrepo", 7, AgentType.DEVOPS, "")

        # Verify TTL was set
        assert mock_redis.expire.called
        ttl_call = mock_redis.expire.call_args[0]
        assert ttl_call[1] == 86400 * 7  # 7 days

    def test_get_pending_tasks_empty_queue(self, manager, mock_redis):
        mock_redis.zrange.return_value = []
        tasks = manager.get_pending_tasks(AgentType.BACKEND)
        assert tasks == []

    def test_get_pending_tasks_with_items(self, manager, mock_redis):
        task = {
            "task_type": "implement_feature",
            "repo_name": "myrepo",
            "issue_number": 42,
            "project_path": "/tmp",
            "assigned_agent": AgentType.BACKEND,
        }
        mock_redis.zrange.return_value = [json.dumps(task)]
        tasks = manager.get_pending_tasks(AgentType.BACKEND)
        assert len(tasks) == 1
        assert tasks[0]["issue_number"] == 42

    def test_claim_next_task_empty_queue(self, manager, mock_redis):
        mock_redis.zpopmin.return_value = []
        task = manager.claim_next_task(AgentType.FRONTEND)
        assert task is None

    def test_claim_next_task_returns_task(self, manager, mock_redis):
        task = {
            "task_type": "implement_feature",
            "repo_name": "myrepo",
            "issue_number": 10,
            "project_path": "/tmp",
        }
        mock_redis.zpopmin.return_value = [(json.dumps(task), 10.0)]
        result = manager.claim_next_task(AgentType.BACKEND)
        assert result is not None
        assert result["issue_number"] == 10

    def test_claim_next_task_updates_status(self, manager, mock_redis):
        task = {
            "task_type": "implement_feature",
            "repo_name": "myrepo",
            "issue_number": 10,
            "project_path": "/tmp",
        }
        mock_redis.zpopmin.return_value = [(json.dumps(task), 10.0)]
        manager.claim_next_task(AgentType.BACKEND)

        # Should update tracking to IN_PROGRESS
        hset_calls = mock_redis.hset.call_args_list
        statuses = [
            c[1].get("mapping", {}).get("status")
            for c in hset_calls
            if isinstance(c[1].get("mapping"), dict)
        ]
        assert TaskStatus.IN_PROGRESS in statuses

    def test_complete_task_sets_completed(self, manager, mock_redis):
        manager.complete_task("myrepo", 1, {"pr_url": "https://github.com/pr/1"})

        call_mapping = mock_redis.hset.call_args[1].get("mapping", {})
        assert call_mapping.get("status") == TaskStatus.COMPLETED

    def test_fail_task_sets_failed(self, manager, mock_redis):
        manager.fail_task("myrepo", 2, "Compilation error")

        call_mapping = mock_redis.hset.call_args[1].get("mapping", {})
        assert call_mapping.get("status") == TaskStatus.FAILED
        assert "Compilation error" in call_mapping.get("error", "")

    def test_get_queue_status_all_agents(self, manager, mock_redis):
        mock_redis.zcard.return_value = 3
        status = manager.get_queue_status()

        expected_agents = {
            AgentType.BACKEND, AgentType.FRONTEND, AgentType.DATABASE,
            AgentType.DEVOPS, AgentType.QA
        }
        assert set(status.keys()) == expected_agents
        for agent_type in expected_agents:
            assert status[agent_type]["pending_tasks"] == 3

    def test_clear_all_queues(self, manager, mock_redis):
        manager.clear_all_queues()
        assert mock_redis.delete.call_count == 5  # One per agent type

    def test_get_assignment_status_missing(self, manager, mock_redis):
        mock_redis.hgetall.return_value = {}
        result = manager.get_assignment_status("myrepo", 999)
        assert result is None

    def test_get_assignment_status_found(self, manager, mock_redis):
        mock_redis.hgetall.return_value = {
            "agent": AgentType.BACKEND,
            "status": TaskStatus.IN_PROGRESS,
            "assigned_at": "2024-01-01T00:00:00",
        }
        result = manager.get_assignment_status("myrepo", 1)
        assert result is not None
        assert result["status"] == TaskStatus.IN_PROGRESS


# ==========================================
# BULK ASSIGNMENT TESTS
# ==========================================

class TestBulkAssignment:

    @pytest.mark.asyncio
    async def test_assign_all_no_issues(self, manager, mock_github):
        mock_github.list_issues.return_value = []
        result = await manager.assign_all_issues("myrepo")

        assert result["success"] is True
        assert result["assigned"] == 0

    @pytest.mark.asyncio
    async def test_assign_all_issues_creates_assignments(self, manager, mock_github, mock_redis):
        mock_github.list_issues.return_value = [
            {"number": 1, "title": "API endpoint", "body": "", "labels": [{"name": "backend"}]},
            {"number": 2, "title": "UI component", "body": "", "labels": [{"name": "frontend"}]},
        ]
        result = await manager.assign_all_issues("myrepo", "/tmp/proj")

        assert result["success"] is True
        assert result["assigned"] == 2
        assert result["total_issues"] == 2

    @pytest.mark.asyncio
    async def test_assign_all_github_error(self, manager, mock_github):
        mock_github.list_issues.side_effect = Exception("GitHub API error")
        result = await manager.assign_all_issues("myrepo")

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_assign_all_respects_max_issues(self, manager, mock_github, mock_redis):
        mock_github.list_issues.return_value = [
            {"number": i, "title": f"Issue {i}", "body": "", "labels": [{"name": "backend"}]}
            for i in range(100)
        ]
        result = await manager.assign_all_issues("myrepo", max_issues=5)

        assert result["total_issues"] == 5


# ==========================================
# CONSTANT TESTS
# ==========================================

class TestConstants:

    def test_label_to_agent_has_all_agent_types(self):
        agent_types = set(LABEL_TO_AGENT.values())
        expected = {AgentType.BACKEND, AgentType.FRONTEND, AgentType.DATABASE, AgentType.DEVOPS, AgentType.QA}
        assert expected.issubset(agent_types)

    def test_keyword_patterns_has_all_agent_types(self):
        expected = {AgentType.BACKEND, AgentType.FRONTEND, AgentType.DATABASE, AgentType.DEVOPS, AgentType.QA}
        assert set(KEYWORD_PATTERNS.keys()) == expected

    def test_all_keyword_patterns_are_valid_regex(self):
        import re
        for agent_type, patterns in KEYWORD_PATTERNS.items():
            for pattern in patterns:
                try:
                    re.compile(pattern)
                except re.error as e:
                    pytest.fail(f"Invalid regex '{pattern}' for {agent_type}: {e}")
