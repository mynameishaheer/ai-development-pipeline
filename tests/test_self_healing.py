"""
Tests for Phase 8: Self-Healing Agent Architecture

Tests error classification, diagnose-and-fix logic, recursion guard,
and enriched GitHub failure comments.
All external dependencies are mocked — no subprocess, Redis, or GitHub required.
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from utils.error_handlers import classify_claude_error, ClaudeCodeError
from agents.worker_daemon import AgentWorkerDaemon


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


@pytest.fixture
def agent():
    """Minimal BaseAgent subclass with all external deps patched."""
    with patch("agents.base_agent.get_logger") as mock_logger_factory, \
         patch("agents.base_agent.AgentMessenger") as mock_messenger_cls:

        mock_log = MagicMock()
        mock_log.log_agent_action = MagicMock()
        mock_log.log_claude_code_call = MagicMock()
        mock_log.warning = MagicMock()
        mock_log.info = MagicMock()
        mock_log.error = MagicMock()
        mock_logger_factory.return_value = mock_log

        mock_messenger_cls.return_value = MagicMock()

        from agents.base_agent import BaseAgent

        class ConcreteAgent(BaseAgent):
            async def execute_task(self, task):
                return {}

            def get_capabilities(self):
                return ["test"]

        a = ConcreteAgent(agent_type="backend", workspace_dir=Path("/tmp"))
        return a


# ==========================================
# ERROR CLASSIFICATION TESTS
# ==========================================

class TestClassifyClaudeError:

    def test_rate_limit_from_429(self):
        assert classify_claude_error("Error 429 too many requests") == "rate_limit"

    def test_rate_limit_from_text(self):
        assert classify_claude_error("You have exceeded the rate limit") == "rate_limit"

    def test_import_error_modulenotfounderror(self):
        assert classify_claude_error(
            "ModuleNotFoundError: No module named 'foo'"
        ) == "import_error"

    def test_import_error_importerror(self):
        assert classify_claude_error(
            "ImportError: cannot import name 'bar' from 'baz'"
        ) == "import_error"

    def test_auth_error_from_401(self):
        assert classify_claude_error("401 not authenticated") == "auth_error"

    def test_auth_error_from_text(self):
        assert classify_claude_error("Invalid API key provided") == "auth_error"

    def test_file_not_found(self):
        assert classify_claude_error(
            "FileNotFoundError: No such file or directory: '/tmp/missing.py'"
        ) == "file_not_found"

    def test_permission_denied(self):
        assert classify_claude_error("permission denied: /etc/passwd") == "permission"

    def test_generic_random_message(self):
        assert classify_claude_error("Something went terribly wrong") == "generic"

    def test_generic_empty_string(self):
        assert classify_claude_error("") == "generic"


# ==========================================
# _diagnose_and_fix TESTS
# ==========================================

class TestDiagnoseAndFix:

    @pytest.mark.asyncio
    async def test_diagnose_and_fix_called_on_failure(self, agent):
        """
        When _run_claude_subprocess fails once then succeeds,
        _diagnose_and_fix should be called before the retry.
        """
        call_count = 0

        async def mock_subprocess(prompt, cwd, allowed_tools=None, timeout=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ClaudeCodeError("Claude Code failed: modulenotfounderror: no module named 'requests'")
            return {
                "stdout": "done", "stderr": "", "return_code": 0,
                "success": True, "duration": 0.1,
            }

        agent._run_claude_subprocess = mock_subprocess

        diagnose_calls = []

        async def mock_diagnose(error_output, project_path):
            diagnose_calls.append(error_output)

        agent._diagnose_and_fix = mock_diagnose

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await agent.call_claude_code("do something", project_path="/tmp")

        assert result["success"] is True
        assert len(diagnose_calls) == 1
        assert "modulenotfounderror" in diagnose_calls[0].lower()

    @pytest.mark.asyncio
    async def test_no_healing_on_auth_error(self, agent):
        """
        When classify returns 'auth_error', _diagnose_and_fix should
        return immediately without calling _run_claude_subprocess.
        """
        subprocess_calls = []

        async def mock_subprocess(prompt, cwd, allowed_tools=None, timeout=None):
            subprocess_calls.append(prompt)
            return {
                "stdout": "ok", "stderr": "", "return_code": 0,
                "success": True, "duration": 0.1,
            }

        agent._run_claude_subprocess = mock_subprocess

        with patch("utils.error_handlers.classify_claude_error", return_value="auth_error"):
            await agent._diagnose_and_fix("401 authentication failed", "/tmp")

        # _run_claude_subprocess should NOT have been called during healing
        assert len(subprocess_calls) == 0

    @pytest.mark.asyncio
    async def test_is_healing_guard_prevents_recursion(self, agent):
        """
        If _is_healing is already True, _diagnose_and_fix returns
        immediately without calling _run_claude_subprocess.
        """
        subprocess_calls = []

        async def mock_subprocess(prompt, cwd, allowed_tools=None, timeout=None):
            subprocess_calls.append(prompt)
            return {
                "stdout": "ok", "stderr": "", "return_code": 0,
                "success": True, "duration": 0.1,
            }

        agent._run_claude_subprocess = mock_subprocess
        agent._is_healing = True  # simulate already healing

        await agent._diagnose_and_fix("some error", "/tmp")

        # Guard should have prevented any subprocess call
        assert len(subprocess_calls) == 0

    @pytest.mark.asyncio
    async def test_healing_guard_reset_after_completion(self, agent):
        """After _diagnose_and_fix completes, _is_healing is reset to False."""
        async def mock_subprocess(prompt, cwd, allowed_tools=None, timeout=None):
            return {
                "stdout": "fixed", "stderr": "", "return_code": 0,
                "success": True, "duration": 0.1,
            }

        agent._run_claude_subprocess = mock_subprocess

        assert agent._is_healing is False
        await agent._diagnose_and_fix("some generic error", "/tmp")
        assert agent._is_healing is False

    @pytest.mark.asyncio
    async def test_healing_guard_reset_even_on_failure(self, agent):
        """_is_healing is reset to False even if the healing subprocess raises."""
        async def mock_subprocess(prompt, cwd, allowed_tools=None, timeout=None):
            raise ClaudeCodeError("healing also failed")

        agent._run_claude_subprocess = mock_subprocess

        assert agent._is_healing is False
        await agent._diagnose_and_fix("some generic error", "/tmp")
        assert agent._is_healing is False


# ==========================================
# WORKER DAEMON GITHUB COMMENT TESTS
# ==========================================

class TestWorkerGitHubDiagnosis:

    @pytest.mark.asyncio
    async def test_github_comment_includes_diagnosis_section(self, daemon, mock_github):
        """
        _sync_github_on_failure with a diagnosis string must include
        'Diagnosis:' in the posted GitHub comment.
        """
        task = {"repo_name": "my-repo", "issue_number": 42}
        diagnosis = "The requests package was not installed in the project virtualenv."

        await daemon._sync_github_on_failure(
            task, "ModuleNotFoundError: requests", "backend", diagnosis=diagnosis
        )

        mock_github.add_issue_comment.assert_called_once()
        comment_text = mock_github.add_issue_comment.call_args[0][2]
        assert "Diagnosis:" in comment_text
        assert diagnosis in comment_text
        assert "❌" in comment_text
        assert "ModuleNotFoundError" in comment_text

    @pytest.mark.asyncio
    async def test_github_comment_without_diagnosis_still_works(self, daemon, mock_github):
        """
        _sync_github_on_failure called without diagnosis (backwards compatible)
        should still post a comment without crashing.
        """
        task = {"repo_name": "my-repo", "issue_number": 5}

        await daemon._sync_github_on_failure(
            task, "Some error occurred", "frontend"
        )

        mock_github.add_issue_comment.assert_called_once()
        comment_text = mock_github.add_issue_comment.call_args[0][2]
        assert "❌" in comment_text
        assert "Some error occurred" in comment_text
