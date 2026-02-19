"""
Tests for the all-tasks-done detection in AgentWorkerDaemon (Phase 6).
Tests _all_queues_empty(), _all_workers_idle(), _check_and_trigger_deploy(),
and _auto_deploy().
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_daemon(mock_redis, mock_github, master=None):
    with patch("agents.worker_daemon.create_github_client", return_value=mock_github), \
         patch("agents.assignment_manager.redis.Redis", return_value=mock_redis), \
         patch("agents.assignment_manager.create_github_client", return_value=mock_github):
        from agents.worker_daemon import AgentWorkerDaemon
        d = AgentWorkerDaemon(agent_types=["backend", "frontend"], master=master)
        d.assignment_manager.redis = mock_redis
        d.github = mock_github
        return d


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
    return gh


@pytest.fixture
def mock_master():
    master = MagicMock()
    master.current_project = {
        "name": "my-project",
        "path": "/tmp/my-project",
        "deploy_url": None,
    }
    master._notify = AsyncMock()
    master.save_project_metadata = AsyncMock()
    return master


@pytest.fixture
def daemon(mock_redis, mock_github, mock_master):
    return _make_daemon(mock_redis, mock_github, master=mock_master)


# ==========================================
# _all_queues_empty
# ==========================================

class TestAllQueuesEmpty:

    def test_empty_when_all_zero(self, daemon, mock_redis):
        mock_redis.zcard.return_value = 0
        assert daemon._all_queues_empty() is True

    def test_not_empty_when_tasks_pending(self, daemon, mock_redis):
        mock_redis.zcard.side_effect = [3, 0]
        assert daemon._all_queues_empty() is False

    def test_returns_true_on_redis_error(self, daemon, mock_redis):
        daemon.assignment_manager.get_queue_status = MagicMock(
            side_effect=Exception("redis error")
        )
        # Should not raise, returns False
        assert daemon._all_queues_empty() is False


# ==========================================
# _all_workers_idle
# ==========================================

class TestAllWorkersIdle:

    def test_idle_when_all_polling(self, daemon):
        daemon._worker_states = {"backend": "polling", "frontend": "idle"}
        assert daemon._all_workers_idle() is True

    def test_not_idle_when_one_working(self, daemon):
        daemon._worker_states = {"backend": "working", "frontend": "idle"}
        assert daemon._all_workers_idle() is False

    def test_idle_when_all_stopped(self, daemon):
        daemon._worker_states = {"backend": "stopped", "frontend": "stopped"}
        assert daemon._all_workers_idle() is True


# ==========================================
# _check_and_trigger_deploy
# ==========================================

class TestCheckAndTriggerDeploy:

    @pytest.mark.asyncio
    async def test_triggers_when_all_empty_and_idle(self, daemon):
        daemon._all_queues_empty = MagicMock(return_value=True)
        daemon._all_workers_idle = MagicMock(return_value=True)
        daemon._auto_deploy = AsyncMock()
        daemon._all_tasks_done_notified = False

        await daemon._check_and_trigger_deploy()

        daemon._auto_deploy.assert_called_once()
        assert daemon._all_tasks_done_notified is True

    @pytest.mark.asyncio
    async def test_does_not_trigger_twice(self, daemon):
        daemon._all_queues_empty = MagicMock(return_value=True)
        daemon._all_workers_idle = MagicMock(return_value=True)
        daemon._auto_deploy = AsyncMock()
        daemon._all_tasks_done_notified = True  # already notified

        await daemon._check_and_trigger_deploy()

        daemon._auto_deploy.assert_not_called()

    @pytest.mark.asyncio
    async def test_resets_flag_when_tasks_arrive(self, daemon):
        daemon._all_queues_empty = MagicMock(return_value=False)
        daemon._all_workers_idle = MagicMock(return_value=True)
        daemon._auto_deploy = AsyncMock()
        daemon._all_tasks_done_notified = True  # was notified before

        await daemon._check_and_trigger_deploy()

        # Flag reset so next drain will trigger again
        assert daemon._all_tasks_done_notified is False
        daemon._auto_deploy.assert_not_called()

    @pytest.mark.asyncio
    async def test_does_not_trigger_when_workers_busy(self, daemon):
        daemon._all_queues_empty = MagicMock(return_value=True)
        daemon._all_workers_idle = MagicMock(return_value=False)
        daemon._auto_deploy = AsyncMock()
        daemon._all_tasks_done_notified = False

        await daemon._check_and_trigger_deploy()

        daemon._auto_deploy.assert_not_called()


# ==========================================
# _auto_deploy
# ==========================================

class TestAutoDeploy:

    @pytest.mark.asyncio
    async def test_deploys_active_project(self, daemon, mock_master):
        mock_deploy_result = {
            "success": True,
            "url": "https://my-project.devbot.site",
            "port": 3000,
            "error": "",
        }

        with patch("agents.deployer.deploy_project", return_value=mock_deploy_result):
            # Simulate the import inside _auto_deploy
            import agents.deployer as dep_mod
            dep_mod.deploy_project = AsyncMock(return_value=mock_deploy_result)

            # Directly patch the function used inside _auto_deploy
            async def fake_deploy(project_path, project_name):
                return mock_deploy_result

            with patch("agents.deployer.deploy_project", fake_deploy):
                await daemon._auto_deploy()

        # MasterAgent should be notified
        mock_master._notify.assert_called_once()
        call_arg = mock_master._notify.call_args[0][0]
        assert "devbot.site" in call_arg or "deployed" in call_arg.lower()

    @pytest.mark.asyncio
    async def test_notify_on_deploy_failure(self, daemon, mock_master):
        async def fake_deploy(project_path, project_name):
            return {"success": False, "url": "", "port": 0, "error": "docker not found"}

        with patch("agents.deployer.deploy_project", fake_deploy):
            await daemon._auto_deploy()

        mock_master._notify.assert_called_once()
        call_arg = mock_master._notify.call_args[0][0]
        assert "failed" in call_arg.lower() or "error" in call_arg.lower()

    @pytest.mark.asyncio
    async def test_no_deploy_when_no_master(self, daemon, mock_master):
        daemon._master = None
        # Should not raise
        await daemon._auto_deploy()

    @pytest.mark.asyncio
    async def test_no_deploy_when_no_project(self, daemon, mock_master):
        mock_master.current_project = None
        await daemon._auto_deploy()
        mock_master._notify.assert_not_called()

    @pytest.mark.asyncio
    async def test_saves_project_metadata_on_success(self, daemon, mock_master):
        async def fake_deploy(project_path, project_name):
            return {
                "success": True,
                "url": "https://my-project.devbot.site",
                "port": 3000,
                "error": "",
            }

        with patch("agents.deployer.deploy_project", fake_deploy):
            await daemon._auto_deploy()

        mock_master.save_project_metadata.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_exception_gracefully(self, daemon, mock_master):
        async def boom(project_path, project_name):
            raise RuntimeError("unexpected!")

        with patch("agents.deployer.deploy_project", boom):
            # Should not propagate the exception
            await daemon._auto_deploy()

        mock_master._notify.assert_called_once()


# ==========================================
# master reference in daemon
# ==========================================

class TestDaemonMasterRef:

    def test_master_stored(self, daemon, mock_master):
        assert daemon._master is mock_master

    def test_no_master_when_not_provided(self, mock_redis, mock_github):
        d = _make_daemon(mock_redis, mock_github, master=None)
        assert d._master is None

    def test_all_tasks_done_flag_initially_false(self, daemon):
        assert daemon._all_tasks_done_notified is False
