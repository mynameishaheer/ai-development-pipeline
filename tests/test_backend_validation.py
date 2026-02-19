"""
Tests for BackendAgent._validate_implementation() (Phase 3 completion)
Tests validation pass / fail / retry logic using mocked subprocess.
All tests use mocks — no real test execution or Claude Code required.
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch, call

import pytest

from agents.backend_agent import BackendAgent
from utils.constants import AgentType


# ==========================================
# FIXTURES
# ==========================================

@pytest.fixture
def mock_redis():
    r = MagicMock()
    r.publish = MagicMock(return_value=1)
    return r


@pytest.fixture
def backend(mock_redis, tmp_path):
    """BackendAgent with all external deps mocked, pointing at tmp_path workspace."""
    mock_gh = AsyncMock()
    with patch("agents.messaging.redis.Redis", return_value=mock_redis), \
         patch("agents.backend_agent.create_github_client", return_value=mock_gh):
        agent = BackendAgent(agent_id="backend_test")
        agent.workspace_dir = tmp_path
        agent.github = mock_gh
        return agent


def _make_pytest_result(returncode: int) -> MagicMock:
    """Create a mock subprocess result for pytest."""
    result = MagicMock()
    result.returncode = returncode
    result.stdout = "1 passed" if returncode == 0 else "1 failed"
    result.stderr = ""
    return result


# ==========================================
# VALIDATION — NO TESTS FOUND
# ==========================================

class TestValidationNoTests:

    @pytest.mark.asyncio
    async def test_no_tests_skips_validation(self, backend, tmp_path):
        """When no test framework is detected, validation is skipped (no error)."""
        project_path = tmp_path / "myproject"
        project_path.mkdir()

        # No pytest.ini, no package.json, no test files → should skip
        with patch("subprocess.run") as mock_run:
            await backend._validate_implementation(project_path, issue_number=1)
            mock_run.assert_not_called()


# ==========================================
# VALIDATION — PYTEST DETECTED
# ==========================================

class TestValidationPytest:

    def _make_project_with_pytest(self, tmp_path) -> Path:
        """Create a project directory with a fake pytest.ini."""
        project_path = tmp_path / "pytest_project"
        project_path.mkdir()
        (project_path / "pytest.ini").write_text("[pytest]\n")
        return project_path

    @pytest.mark.asyncio
    async def test_passes_when_pytest_passes(self, backend, tmp_path):
        """No exception when pytest returns 0."""
        project_path = self._make_project_with_pytest(tmp_path)

        with patch("subprocess.run", return_value=_make_pytest_result(0)):
            await backend._validate_implementation(project_path, issue_number=1)

    @pytest.mark.asyncio
    async def test_retries_and_passes_on_second_run(self, backend, tmp_path):
        """First run fails → Claude Code called → second run passes → no exception."""
        project_path = self._make_project_with_pytest(tmp_path)

        results = [_make_pytest_result(1), _make_pytest_result(0)]
        backend.call_claude_code = AsyncMock(return_value={"success": True})

        with patch("subprocess.run", side_effect=results):
            await backend._validate_implementation(project_path, issue_number=2)

        backend.call_claude_code.assert_called_once()
        prompt_arg = backend.call_claude_code.call_args[1]["prompt"]
        assert "Fix these test failures" in prompt_arg

    @pytest.mark.asyncio
    async def test_raises_if_still_failing_after_retry(self, backend, tmp_path):
        """Two failures in a row → RuntimeError raised."""
        project_path = self._make_project_with_pytest(tmp_path)

        results = [_make_pytest_result(1), _make_pytest_result(1)]
        backend.call_claude_code = AsyncMock(return_value={"success": True})

        with patch("subprocess.run", side_effect=results):
            with pytest.raises(RuntimeError, match="Tests still failing"):
                await backend._validate_implementation(project_path, issue_number=3)

    @pytest.mark.asyncio
    async def test_does_not_call_claude_when_tests_pass_first_try(self, backend, tmp_path):
        """When tests pass immediately, Claude Code must NOT be called."""
        project_path = self._make_project_with_pytest(tmp_path)
        backend.call_claude_code = AsyncMock(return_value={"success": True})

        with patch("subprocess.run", return_value=_make_pytest_result(0)):
            await backend._validate_implementation(project_path, issue_number=4)

        backend.call_claude_code.assert_not_called()

    @pytest.mark.asyncio
    async def test_timeout_is_swallowed_gracefully(self, backend, tmp_path):
        """subprocess.TimeoutExpired must not crash validation — just skip."""
        project_path = self._make_project_with_pytest(tmp_path)

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("pytest", 120)):
            # Should NOT raise
            await backend._validate_implementation(project_path, issue_number=5)

    @pytest.mark.asyncio
    async def test_file_not_found_is_swallowed(self, backend, tmp_path):
        """FileNotFoundError (pytest not installed) must be swallowed."""
        project_path = self._make_project_with_pytest(tmp_path)

        with patch("subprocess.run", side_effect=FileNotFoundError("python not found")):
            await backend._validate_implementation(project_path, issue_number=6)


# ==========================================
# VALIDATION — JEST DETECTED
# ==========================================

class TestValidationJest:

    def _make_project_with_jest(self, tmp_path) -> Path:
        """Create a project directory with a fake package.json (no pytest.ini)."""
        project_path = tmp_path / "jest_project"
        project_path.mkdir()
        (project_path / "package.json").write_text('{"scripts": {"test": "jest"}}')
        return project_path

    def _jest_pass_result(self):
        r = MagicMock()
        r.returncode = 0
        r.stdout = "Tests: 3 passed, 3 total"
        r.stderr = ""
        return r

    def _jest_fail_result(self):
        r = MagicMock()
        r.returncode = 1
        r.stdout = "Tests: 1 failed, 1 total"
        r.stderr = ""
        return r

    @pytest.mark.asyncio
    async def test_passes_when_jest_passes(self, backend, tmp_path):
        project_path = self._make_project_with_jest(tmp_path)

        with patch("subprocess.run", return_value=self._jest_pass_result()):
            await backend._validate_implementation(project_path, issue_number=10)

    @pytest.mark.asyncio
    async def test_retries_jest_on_failure(self, backend, tmp_path):
        project_path = self._make_project_with_jest(tmp_path)

        results = [self._jest_fail_result(), self._jest_pass_result()]
        backend.call_claude_code = AsyncMock(return_value={"success": True})

        with patch("subprocess.run", side_effect=results):
            await backend._validate_implementation(project_path, issue_number=11)

        backend.call_claude_code.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_when_jest_fails_twice(self, backend, tmp_path):
        project_path = self._make_project_with_jest(tmp_path)

        backend.call_claude_code = AsyncMock(return_value={"success": True})

        with patch("subprocess.run", side_effect=[self._jest_fail_result(), self._jest_fail_result()]):
            with pytest.raises(RuntimeError, match="Tests still failing"):
                await backend._validate_implementation(project_path, issue_number=12)


# ==========================================
# IMPLEMENT FEATURE INTEGRATION SMOKE TEST
# ==========================================

class TestImplementFeatureCallsValidation:

    @pytest.mark.asyncio
    async def test_validate_called_before_commit(self, backend, tmp_path):
        """_validate_implementation must be called in the implement_feature flow."""
        call_order = []

        backend._get_issue_details = AsyncMock(return_value={
            "number": 1, "title": "Test", "body": "", "labels": [], "state": "open"
        })
        backend._create_feature_branch = AsyncMock()
        backend._setup_local_repo = AsyncMock(return_value=tmp_path)
        backend._implement_with_claude = AsyncMock(return_value={"success": True})

        async def record_write_tests(*args):
            call_order.append("write_tests")
        backend._write_tests = record_write_tests

        async def record_validate(*args):
            call_order.append("validate")
        backend._validate_implementation = record_validate

        async def record_commit(*args):
            call_order.append("commit")
        backend._commit_and_push = record_commit

        backend._create_pull_request = AsyncMock(return_value={"number": 1, "html_url": "http://x"})
        backend.send_status_update = AsyncMock()

        await backend.implement_feature({
            "repo_name": "my-repo",
            "issue_number": 1,
            "project_path": str(tmp_path),
        })

        assert "write_tests" in call_order
        assert "validate" in call_order
        assert "commit" in call_order

        validate_idx = call_order.index("validate")
        write_tests_idx = call_order.index("write_tests")
        commit_idx = call_order.index("commit")

        assert write_tests_idx < validate_idx < commit_idx
