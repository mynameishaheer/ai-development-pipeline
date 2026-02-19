"""
Tests for agents/pipeline_monitor.py (Phase 4)
All external dependencies are mocked — no GitHub API, Redis, or Discord required.
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

from agents.pipeline_monitor import PipelineMonitor, WORKER_STALL_MINUTES


# ==========================================
# FIXTURES
# ==========================================

def _make_master(repo_name="test-repo", project_path="/tmp/project"):
    """Build a minimal MasterAgent mock."""
    master = MagicMock()
    master.current_project = {
        "repo_name": repo_name,
        "path": project_path,
        "repo_url": f"https://github.com/user/{repo_name}",
    }
    master._notify_channel = None
    master._worker_daemon = None
    master.call_claude_code = AsyncMock(return_value={"success": True, "stdout": "fixed", "stderr": ""})
    return master


def _make_github():
    gh = AsyncMock()
    gh.get_workflow_runs = AsyncMock(return_value=[])
    gh.get_workflow_run_logs = AsyncMock(return_value="ERROR: test failed")
    return gh


@pytest.fixture
def master():
    return _make_master()


@pytest.fixture
def github():
    return _make_github()


@pytest.fixture
def monitor(master, github):
    return PipelineMonitor(master=master, github=github)


# ==========================================
# INITIALISATION
# ==========================================

class TestInit:

    def test_not_running_initially(self, monitor):
        assert monitor.is_running() is False

    def test_fix_attempts_empty(self, monitor):
        assert monitor._fix_attempts == {}

    def test_handled_runs_empty(self, monitor):
        assert len(monitor._handled_runs) == 0

    def test_get_status_returns_dict(self, monitor):
        status = monitor.get_status()
        assert "running" in status
        assert "repo" in status
        assert status["repo"] == "test-repo"


# ==========================================
# START / STOP
# ==========================================

class TestStartStop:

    @pytest.mark.asyncio
    async def test_start_sets_running(self, monitor):
        await monitor.start()
        assert monitor.is_running() is True
        await monitor.stop()

    @pytest.mark.asyncio
    async def test_stop_clears_running(self, monitor):
        await monitor.start()
        await monitor.stop()
        assert monitor.is_running() is False

    @pytest.mark.asyncio
    async def test_start_idempotent(self, monitor):
        """Calling start() twice should not create a second task."""
        await monitor.start()
        task1 = monitor._task
        await monitor.start()
        task2 = monitor._task
        assert task1 is task2
        await monitor.stop()

    @pytest.mark.asyncio
    async def test_stop_when_not_started_is_safe(self, monitor):
        """stop() before start() should not raise."""
        await monitor.stop()  # Should not raise


# ==========================================
# CI STATUS CHECKING
# ==========================================

class TestCheckCIStatus:

    @pytest.mark.asyncio
    async def test_no_project_returns_early(self, monitor, master):
        master.current_project = None
        # Should return without calling GitHub
        await monitor._check_ci_status()
        monitor.github.get_workflow_runs.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_repo_name_returns_early(self, monitor, master):
        master.current_project = {"repo_name": "", "path": "/tmp"}
        await monitor._check_ci_status()
        monitor.github.get_workflow_runs.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_runs_returns_early(self, monitor, github):
        github.get_workflow_runs = AsyncMock(return_value=[])
        await monitor._check_ci_status()
        # No failure handling triggered
        assert len(monitor._handled_runs) == 0

    @pytest.mark.asyncio
    async def test_successful_run_marked_handled(self, monitor, github):
        github.get_workflow_runs = AsyncMock(return_value=[
            {"id": 100, "status": "completed", "conclusion": "success", "name": "CI"}
        ])
        await monitor._check_ci_status()
        assert 100 in monitor._handled_runs

    @pytest.mark.asyncio
    async def test_successful_run_after_fix_notifies(self, monitor, github):
        """If we attempted a fix for this run_id, notify on success."""
        monitor._fix_attempts[100] = 1  # We previously attempted a fix

        channel = AsyncMock()
        monitor.master._notify_channel = channel

        github.get_workflow_runs = AsyncMock(return_value=[
            {"id": 100, "status": "completed", "conclusion": "success", "name": "CI"}
        ])
        await monitor._check_ci_status()
        channel.send.assert_called_once()
        assert "✅" in channel.send.call_args[0][0]

    @pytest.mark.asyncio
    async def test_failed_run_triggers_handle_ci_failure(self, monitor, github):
        github.get_workflow_runs = AsyncMock(return_value=[
            {"id": 200, "status": "completed", "conclusion": "failure", "name": "Tests"}
        ])
        monitor._handle_ci_failure = AsyncMock()
        await monitor._check_ci_status()
        monitor._handle_ci_failure.assert_called_once()

    @pytest.mark.asyncio
    async def test_already_handled_run_skipped(self, monitor, github):
        monitor._handled_runs.add(300)
        github.get_workflow_runs = AsyncMock(return_value=[
            {"id": 300, "status": "completed", "conclusion": "failure", "name": "CI"}
        ])
        monitor._handle_ci_failure = AsyncMock()
        await monitor._check_ci_status()
        monitor._handle_ci_failure.assert_not_called()

    @pytest.mark.asyncio
    async def test_in_progress_run_not_handled(self, monitor, github):
        github.get_workflow_runs = AsyncMock(return_value=[
            {"id": 400, "status": "in_progress", "conclusion": None, "name": "CI"}
        ])
        monitor._handle_ci_failure = AsyncMock()
        await monitor._check_ci_status()
        monitor._handle_ci_failure.assert_not_called()

    @pytest.mark.asyncio
    async def test_max_fix_attempts_gives_up(self, monitor, github):
        """After MAX_FIX_ATTEMPTS, stop trying and notify user."""
        run_id = 500
        monitor._fix_attempts[run_id] = 3  # Already at max

        channel = AsyncMock()
        monitor.master._notify_channel = channel

        github.get_workflow_runs = AsyncMock(return_value=[
            {"id": run_id, "status": "completed", "conclusion": "failure", "name": "CI"}
        ])
        monitor._handle_ci_failure = AsyncMock()

        await monitor._check_ci_status()

        monitor._handle_ci_failure.assert_not_called()
        channel.send.assert_called_once()
        assert "❌" in channel.send.call_args[0][0]
        assert run_id in monitor._handled_runs

    @pytest.mark.asyncio
    async def test_github_error_is_swallowed(self, monitor, github):
        """GitHub API errors must not crash the monitor."""
        github.get_workflow_runs = AsyncMock(side_effect=Exception("network error"))
        # Should not raise
        await monitor._check_ci_status()


# ==========================================
# CI FAILURE HANDLER
# ==========================================

class TestHandleCIFailure:

    @pytest.mark.asyncio
    async def test_increments_fix_attempt_counter(self, monitor, master):
        run = {"id": 10, "name": "Tests"}
        master.call_claude_code = AsyncMock(return_value={"success": False, "stderr": "no"})
        with patch.dict("os.environ", {"GITHUB_TOKEN": "", "GITHUB_USERNAME": ""}):
            await monitor._handle_ci_failure(run)
        assert monitor._fix_attempts[10] == 1

    @pytest.mark.asyncio
    async def test_calls_claude_code_with_logs(self, monitor, master, github):
        run = {"id": 20, "name": "CI"}
        github.get_workflow_run_logs = AsyncMock(return_value="FAIL: assertion error")
        master.call_claude_code = AsyncMock(return_value={"success": True, "stdout": "fixed import"})

        with patch("agents.github_pusher.push_project_to_github", AsyncMock(return_value=True)), \
             patch.dict("os.environ", {"GITHUB_TOKEN": "tok", "GITHUB_USERNAME": "user"}):
            await monitor._handle_ci_failure(run)

        master.call_claude_code.assert_called_once()
        prompt = master.call_claude_code.call_args[1]["prompt"]
        assert "FAIL: assertion error" in prompt

    @pytest.mark.asyncio
    async def test_push_called_when_fix_succeeds(self, monitor, master, github):
        run = {"id": 30, "name": "CI"}
        github.get_workflow_run_logs = AsyncMock(return_value="error log")
        master.call_claude_code = AsyncMock(return_value={"success": True, "stdout": "added fix"})

        with patch("agents.github_pusher.push_project_to_github", AsyncMock(return_value=True)) as mock_push, \
             patch.dict("os.environ", {"GITHUB_TOKEN": "tok", "GITHUB_USERNAME": "user"}):
            await monitor._handle_ci_failure(run)

        mock_push.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_marked_handled_after_successful_push(self, monitor, master, github):
        run = {"id": 40, "name": "CI"}
        github.get_workflow_run_logs = AsyncMock(return_value="error")
        master.call_claude_code = AsyncMock(return_value={"success": True, "stdout": "fix"})

        with patch("agents.github_pusher.push_project_to_github", AsyncMock(return_value=True)), \
             patch.dict("os.environ", {"GITHUB_TOKEN": "tok", "GITHUB_USERNAME": "user"}):
            await monitor._handle_ci_failure(run)

        assert 40 in monitor._handled_runs

    @pytest.mark.asyncio
    async def test_no_push_when_token_missing(self, monitor, master, github):
        run = {"id": 50, "name": "CI"}
        github.get_workflow_run_logs = AsyncMock(return_value="error")
        master.call_claude_code = AsyncMock(return_value={"success": True, "stdout": "fix"})

        channel = AsyncMock()
        monitor.master._notify_channel = channel

        with patch("agents.github_pusher.push_project_to_github", AsyncMock()) as mock_push, \
             patch.dict("os.environ", {"GITHUB_TOKEN": "", "GITHUB_USERNAME": ""}):
            await monitor._handle_ci_failure(run)

        mock_push.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_project_returns_early(self, monitor, master):
        master.current_project = None
        run = {"id": 60, "name": "CI"}
        master.call_claude_code = AsyncMock()
        await monitor._handle_ci_failure(run)
        master.call_claude_code.assert_not_called()


# ==========================================
# WORKER HEALTH CHECKING
# ==========================================

class TestCheckWorkerHealth:

    @pytest.mark.asyncio
    async def test_no_daemon_returns_early(self, monitor, master):
        master._worker_daemon = None
        # Should not raise
        await monitor._check_worker_health()

    @pytest.mark.asyncio
    async def test_idle_worker_not_flagged(self, monitor, master):
        daemon = MagicMock()
        daemon.get_status = MagicMock(return_value={
            "worker_states": {"backend": "idle"},
            "task_start_times": {},
        })
        master._worker_daemon = daemon

        channel = AsyncMock()
        monitor.master._notify_channel = channel

        await monitor._check_worker_health()
        channel.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_fresh_working_worker_not_flagged(self, monitor, master):
        """Worker that's been working for <WORKER_STALL_MINUTES should not be flagged."""
        daemon = MagicMock()
        recent = (datetime.utcnow() - timedelta(minutes=2)).isoformat()
        daemon.get_status = MagicMock(return_value={
            "worker_states": {"backend": "working"},
            "task_start_times": {"backend": recent},
        })
        daemon._worker_states = {"backend": "working"}
        daemon._task_start_times = {"backend": recent}
        master._worker_daemon = daemon

        channel = AsyncMock()
        monitor.master._notify_channel = channel

        await monitor._check_worker_health()
        channel.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_stalled_worker_triggers_notify(self, monitor, master):
        """Worker stuck for >WORKER_STALL_MINUTES should trigger a notification."""
        daemon = MagicMock()
        old_start = (
            datetime.utcnow() - timedelta(minutes=WORKER_STALL_MINUTES + 5)
        ).isoformat()
        daemon.get_status = MagicMock(return_value={
            "worker_states": {"backend": "working"},
            "task_start_times": {"backend": old_start},
        })
        daemon._worker_states = {"backend": "working"}
        daemon._task_start_times = {"backend": old_start}
        master._worker_daemon = daemon

        channel = AsyncMock()
        monitor.master._notify_channel = channel

        await monitor._check_worker_health()

        channel.send.assert_called_once()
        assert "⚠️" in channel.send.call_args[0][0]
        assert "backend" in channel.send.call_args[0][0]

    @pytest.mark.asyncio
    async def test_stalled_worker_state_reset_to_idle(self, monitor, master):
        """Stalled worker should have its state reset to 'idle'."""
        daemon = MagicMock()
        old_start = (
            datetime.utcnow() - timedelta(minutes=WORKER_STALL_MINUTES + 5)
        ).isoformat()
        daemon.get_status = MagicMock(return_value={
            "worker_states": {"frontend": "working"},
            "task_start_times": {"frontend": old_start},
        })
        daemon._worker_states = {"frontend": "working"}
        daemon._task_start_times = {"frontend": old_start}
        master._worker_daemon = daemon

        monitor.master._notify_channel = AsyncMock()
        await monitor._check_worker_health()

        assert daemon._worker_states["frontend"] == "idle"

    @pytest.mark.asyncio
    async def test_invalid_start_time_skipped(self, monitor, master):
        """Bad ISO timestamp should be silently skipped."""
        daemon = MagicMock()
        daemon.get_status = MagicMock(return_value={
            "worker_states": {"backend": "working"},
            "task_start_times": {"backend": "not-a-timestamp"},
        })
        master._worker_daemon = daemon
        channel = AsyncMock()
        monitor.master._notify_channel = channel

        # Should not raise
        await monitor._check_worker_health()
        channel.send.assert_not_called()


# ==========================================
# DISCORD NOTIFICATION
# ==========================================

class TestNotify:

    @pytest.mark.asyncio
    async def test_notify_sends_to_channel(self, monitor, master):
        channel = AsyncMock()
        master._notify_channel = channel
        await monitor._notify("Hello from monitor")
        channel.send.assert_called_once_with("Hello from monitor")

    @pytest.mark.asyncio
    async def test_notify_no_channel_does_not_raise(self, monitor, master):
        master._notify_channel = None
        await monitor._notify("message")  # Should not raise

    @pytest.mark.asyncio
    async def test_notify_truncates_long_messages(self, monitor, master):
        channel = AsyncMock()
        master._notify_channel = channel
        long_msg = "x" * 3000
        await monitor._notify(long_msg)
        sent = channel.send.call_args[0][0]
        assert len(sent) <= 2000

    @pytest.mark.asyncio
    async def test_notify_swallows_send_errors(self, monitor, master):
        channel = AsyncMock()
        channel.send = AsyncMock(side_effect=Exception("Discord down"))
        master._notify_channel = channel
        await monitor._notify("test")  # Should not raise
