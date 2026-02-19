"""
Tests for AgentWorkerDaemon (Phase 3 completion)
Tests task claim → execute → complete flow and GitHub sync.
All tests use mocks — no Redis, GitHub, or Claude Code required.
"""

import asyncio
import json
import pytest
from unittest.mock import MagicMock, AsyncMock, patch, call

from agents.worker_daemon import AgentWorkerDaemon
from utils.constants import AgentType


# ==========================================
# FIXTURES
# ==========================================

@pytest.fixture
def mock_redis():
    r = MagicMock()
    r.zadd = MagicMock(return_value=1)
    r.hset = MagicMock(return_value=1)
    r.expire = MagicMock(return_value=True)
    r.zcard = MagicMock(return_value=0)
    r.hgetall = MagicMock(return_value={})
    r.delete = MagicMock(return_value=1)
    r.zpopmin = MagicMock(return_value=[])
    return r


@pytest.fixture
def mock_github():
    gh = AsyncMock()
    gh.add_issue_comment = AsyncMock(return_value={"id": 1})
    gh.update_issue = AsyncMock(return_value={"number": 1})
    gh.merge_pull_request = AsyncMock(return_value={"merged": True})
    gh.close_issue = AsyncMock(return_value={"state": "closed"})
    return gh


@pytest.fixture
def daemon(mock_redis, mock_github):
    """Worker daemon with all external deps mocked."""
    with patch("agents.worker_daemon.create_github_client", return_value=mock_github), \
         patch("agents.assignment_manager.redis.Redis", return_value=mock_redis), \
         patch("agents.assignment_manager.create_github_client", return_value=mock_github):
        d = AgentWorkerDaemon(agent_types=["backend", "frontend", "qa"])
        d.assignment_manager.redis = mock_redis
        d.github = mock_github
        return d


# ==========================================
# INITIALISATION TESTS
# ==========================================

class TestDaemonInit:

    def test_default_agent_types_are_set(self, daemon):
        assert "backend" in daemon.agent_types
        assert "frontend" in daemon.agent_types
        assert "qa" in daemon.agent_types

    def test_initially_not_running(self, daemon):
        assert daemon._running is False

    def test_worker_states_initialised_idle(self, daemon):
        for agent_type in daemon.agent_types:
            assert daemon._worker_states[agent_type] == "idle"

    def test_no_agents_cached_initially(self, daemon):
        assert len(daemon._agents) == 0


# ==========================================
# GET STATUS TESTS
# ==========================================

class TestGetStatus:

    def test_get_status_returns_dict(self, daemon, mock_redis):
        mock_redis.zcard = MagicMock(return_value=3)
        status = daemon.get_status()
        assert isinstance(status, dict)
        assert "running" in status
        assert "queues" in status
        assert "worker_states" in status

    def test_get_status_running_false_initially(self, daemon, mock_redis):
        mock_redis.zcard = MagicMock(return_value=0)
        status = daemon.get_status()
        assert status["running"] is False


# ==========================================
# GITHUB SYNC TESTS
# ==========================================

class TestGitHubSync:

    @pytest.mark.asyncio
    async def test_sync_on_complete_posts_comment(self, daemon, mock_github):
        task = {"repo_name": "my-repo", "issue_number": 5}
        result = {"pr_number": 42}

        await daemon._sync_github_on_complete(task, result, "backend")

        mock_github.add_issue_comment.assert_called_once()
        comment_args = mock_github.add_issue_comment.call_args[0]
        assert "my-repo" in comment_args
        assert 5 in comment_args
        assert "backend" in comment_args[2]
        assert "PR: #42" in comment_args[2]

    @pytest.mark.asyncio
    async def test_sync_on_complete_adds_in_review_label(self, daemon, mock_github):
        task = {"repo_name": "my-repo", "issue_number": 7}
        result = {}

        await daemon._sync_github_on_complete(task, result, "frontend")

        mock_github.update_issue.assert_called_once_with(
            "my-repo", 7, labels=["in-review"]
        )

    @pytest.mark.asyncio
    async def test_sync_on_failure_posts_error_comment(self, daemon, mock_github):
        task = {"repo_name": "my-repo", "issue_number": 3}

        await daemon._sync_github_on_failure(task, "Something went wrong", "backend")

        mock_github.add_issue_comment.assert_called_once()
        comment_text = mock_github.add_issue_comment.call_args[0][2]
        assert "❌" in comment_text
        assert "Something went wrong" in comment_text

    @pytest.mark.asyncio
    async def test_sync_on_failure_adds_needs_attention_label(self, daemon, mock_github):
        task = {"repo_name": "my-repo", "issue_number": 3}

        await daemon._sync_github_on_failure(task, "error", "backend")

        mock_github.update_issue.assert_called_once_with(
            "my-repo", 3, labels=["needs-attention"]
        )

    @pytest.mark.asyncio
    async def test_sync_skips_when_no_repo_name(self, daemon, mock_github):
        """No GitHub calls if task has no repo_name."""
        task = {"repo_name": "", "issue_number": 1}
        await daemon._sync_github_on_complete(task, {}, "backend")
        mock_github.add_issue_comment.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_skips_when_no_issue_number(self, daemon, mock_github):
        task = {"repo_name": "my-repo", "issue_number": 0}
        await daemon._sync_github_on_failure(task, "error", "qa")
        mock_github.add_issue_comment.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_does_not_raise_on_github_error(self, daemon, mock_github):
        """GitHub failures must be swallowed — never crash the daemon."""
        mock_github.add_issue_comment.side_effect = Exception("network error")
        task = {"repo_name": "my-repo", "issue_number": 1}
        # Should not raise
        await daemon._sync_github_on_complete(task, {}, "backend")


# ==========================================
# QA REVIEW ENQUEUE TESTS
# ==========================================

class TestEnqueueQAReview:

    @pytest.mark.asyncio
    async def test_enqueue_qa_review_calls_assign_pr_review(self, daemon, mock_redis):
        daemon.assignment_manager.assign_pr_review = AsyncMock(return_value=True)

        await daemon._enqueue_qa_review(
            repo_name="my-repo",
            pr_number=10,
            issue_number=2,
            project_path="/tmp/project",
        )

        daemon.assignment_manager.assign_pr_review.assert_called_once_with(
            repo_name="my-repo",
            pr_number=10,
            issue_number=2,
            project_path="/tmp/project",
        )


# ==========================================
# WORKER LOOP TESTS (short-circuit)
# ==========================================

class TestWorkerLoop:

    @pytest.mark.asyncio
    async def test_worker_stops_when_not_running(self, daemon):
        """Worker should exit immediately when _running is False."""
        daemon._running = False

        # Should return almost immediately
        await asyncio.wait_for(
            daemon.run_worker("backend"),
            timeout=2.0
        )

    @pytest.mark.asyncio
    async def test_worker_claims_and_executes_task(self, daemon, mock_redis):
        """One task claimed, executed, then queue empty → worker exits."""
        task = {
            "task_type": "implement_feature",
            "repo_name": "my-repo",
            "issue_number": 1,
            "project_path": "",
        }
        task_json = json.dumps(task)

        # First poll: return one task; second poll: empty
        mock_redis.zpopmin.side_effect = [
            [(task_json, 1.0)],
            [],
        ]

        mock_agent = AsyncMock()
        mock_agent.execute_task = AsyncMock(return_value={"success": True})
        daemon._agents["backend"] = mock_agent

        # Stop daemon after first empty poll
        call_count = 0
        original_sleep = asyncio.sleep

        async def mock_sleep(seconds):
            nonlocal call_count
            call_count += 1
            daemon._running = False

        daemon._running = True

        with patch("asyncio.sleep", side_effect=mock_sleep):
            await daemon.run_worker("backend")

        mock_agent.execute_task.assert_called_once_with(task)

    @pytest.mark.asyncio
    async def test_worker_calls_fail_task_on_agent_error(self, daemon, mock_redis):
        """When execute_task raises, fail_task must be called."""
        task = {
            "task_type": "implement_feature",
            "repo_name": "my-repo",
            "issue_number": 99,
            "project_path": "",
        }
        task_json = json.dumps(task)

        mock_redis.zpopmin.side_effect = [
            [(task_json, 1.0)],
            [],
        ]

        mock_agent = AsyncMock()
        mock_agent.execute_task = AsyncMock(side_effect=RuntimeError("boom"))
        daemon._agents["backend"] = mock_agent

        daemon.assignment_manager.fail_task = MagicMock()

        daemon._running = True

        async def mock_sleep(_):
            daemon._running = False

        with patch("asyncio.sleep", side_effect=mock_sleep):
            await daemon.run_worker("backend")

        daemon.assignment_manager.fail_task.assert_called_once_with(
            repo_name="my-repo",
            issue_number=99,
            error="boom",
        )

    @pytest.mark.asyncio
    async def test_worker_enqueues_qa_review_for_backend_with_pr(self, daemon, mock_redis):
        """Backend task that produces a pr_number should enqueue QA review."""
        task = {
            "task_type": "implement_feature",
            "repo_name": "my-repo",
            "issue_number": 5,
            "project_path": "/tmp",
        }
        task_json = json.dumps(task)

        mock_redis.zpopmin.side_effect = [
            [(task_json, 1.0)],
            [],
        ]

        mock_agent = AsyncMock()
        mock_agent.execute_task = AsyncMock(
            return_value={"success": True, "pr_number": 7}
        )
        daemon._agents["backend"] = mock_agent

        daemon._enqueue_qa_review = AsyncMock()
        daemon._sync_github_on_complete = AsyncMock()

        daemon._running = True

        async def mock_sleep(_):
            daemon._running = False

        with patch("asyncio.sleep", side_effect=mock_sleep):
            await daemon.run_worker("backend")

        daemon._enqueue_qa_review.assert_called_once_with(
            repo_name="my-repo",
            pr_number=7,
            issue_number=5,
            project_path="/tmp",
        )


# ==========================================
# START / STOP TESTS
# ==========================================

class TestStartStop:

    @pytest.mark.asyncio
    async def test_stop_sets_running_false(self, daemon):
        daemon._running = True
        await daemon.stop()
        assert daemon._running is False

    @pytest.mark.asyncio
    async def test_stop_when_not_started_is_safe(self, daemon):
        """stop() with no running tasks should not raise."""
        assert not daemon._running
        await daemon.stop()  # Should not raise
