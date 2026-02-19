"""
Tests for agents/github_pusher.py (Phase 4)
All subprocess calls are mocked — no git, rsync, or GitHub access required.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call

from agents.github_pusher import push_project_to_github, _run_subprocess


# ==========================================
# _run_subprocess UNIT TESTS
# ==========================================

class TestRunSubprocess:

    @pytest.mark.asyncio
    async def test_returns_true_on_exit_zero(self):
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"output", b""))

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await _run_subprocess(["git", "status"], cwd="/tmp")

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_on_nonzero_exit(self):
        mock_proc = AsyncMock()
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock(return_value=(b"", b"error"))

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await _run_subprocess(["git", "push"], cwd="/tmp")

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_timeout(self):
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError())

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await _run_subprocess(["rsync", "-a", "."], cwd="/tmp")

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_exception(self):
        with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError("git not found")):
            result = await _run_subprocess(["git", "clone", "url"], cwd="/tmp")

        assert result is False


# ==========================================
# push_project_to_github INTEGRATION TESTS
# ==========================================

def _make_proc(returncode=0, stdout=b"", stderr=b""):
    """Helper: create a mock async process."""
    proc = AsyncMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    return proc


class TestPushProjectToGitHub:

    @pytest.mark.asyncio
    async def test_successful_push(self, tmp_path):
        """Happy path: clone → rsync → diff shows changes → add → commit → push."""
        # Sequence of subprocess calls:
        # 1. git clone       → success
        # 2. rsync           → success
        # 3. git status      → has changes (b"M file.py\n")
        # 4. git config email → success
        # 5. git config name  → success
        # 6. git add -A       → success
        # 7. git commit       → success
        # 8. git push         → success
        procs = [
            _make_proc(0),                     # clone
            _make_proc(0),                     # rsync
            _make_proc(0, stdout=b"M app.py"), # git status --porcelain
            _make_proc(0),                     # git config email
            _make_proc(0),                     # git config name
            _make_proc(0),                     # git add
            _make_proc(0),                     # git commit
            _make_proc(0),                     # git push
        ]

        with patch("asyncio.create_subprocess_exec", side_effect=procs):
            result = await push_project_to_github(
                project_path=str(tmp_path),
                repo_name="my-repo",
                github_token="tok",
                github_username="user",
            )

        assert result is True

    @pytest.mark.asyncio
    async def test_nothing_to_commit(self, tmp_path):
        """If git status --porcelain returns empty, return True without committing."""
        procs = [
            _make_proc(0),          # clone
            _make_proc(0),          # rsync
            _make_proc(0, stdout=b""),  # git status --porcelain → nothing
        ]

        with patch("asyncio.create_subprocess_exec", side_effect=procs):
            result = await push_project_to_github(
                project_path=str(tmp_path),
                repo_name="my-repo",
                github_token="tok",
                github_username="user",
            )

        assert result is True

    @pytest.mark.asyncio
    async def test_clone_failure_returns_false(self, tmp_path):
        """If both clone attempts fail, return False immediately."""
        procs = [
            _make_proc(1),  # clone with --branch fails
            _make_proc(1),  # clone without --branch also fails
        ]

        with patch("asyncio.create_subprocess_exec", side_effect=procs):
            result = await push_project_to_github(
                project_path=str(tmp_path),
                repo_name="my-repo",
                github_token="tok",
                github_username="user",
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_rsync_failure_returns_false(self, tmp_path):
        procs = [
            _make_proc(0),  # clone succeeds
            _make_proc(1),  # rsync fails
        ]

        with patch("asyncio.create_subprocess_exec", side_effect=procs):
            result = await push_project_to_github(
                project_path=str(tmp_path),
                repo_name="my-repo",
                github_token="tok",
                github_username="user",
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_push_failure_returns_false(self, tmp_path):
        """If git push fails, return False."""
        procs = [
            _make_proc(0),                     # clone
            _make_proc(0),                     # rsync
            _make_proc(0, stdout=b"M app.py"), # git status
            _make_proc(0),                     # git config email
            _make_proc(0),                     # git config name
            _make_proc(0),                     # git add
            _make_proc(0),                     # git commit
            _make_proc(1),                     # git push ← FAILS
        ]

        with patch("asyncio.create_subprocess_exec", side_effect=procs):
            result = await push_project_to_github(
                project_path=str(tmp_path),
                repo_name="my-repo",
                github_token="tok",
                github_username="user",
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_uses_authenticated_url(self, tmp_path):
        """Token must be embedded in the clone URL."""
        captured = []

        async def fake_exec(*cmd, **kwargs):
            captured.append(cmd)
            return _make_proc(0, stdout=b"" if "status" in cmd else b"")

        procs = [
            _make_proc(0),          # clone
            _make_proc(0),          # rsync
            _make_proc(0, stdout=b""), # git status → empty
        ]

        with patch("asyncio.create_subprocess_exec", side_effect=procs) as mock_exec:
            await push_project_to_github(
                project_path=str(tmp_path),
                repo_name="my-repo",
                github_token="secret-token",
                github_username="myuser",
            )
            first_call_args = mock_exec.call_args_list[0][0]

        # The clone URL should contain the token
        clone_url = next(
            arg for arg in first_call_args if "github.com" in str(arg)
        )
        assert "secret-token" in clone_url
        assert "myuser/my-repo" in clone_url

    @pytest.mark.asyncio
    async def test_custom_commit_message(self, tmp_path):
        """Custom commit message should be passed to git commit."""
        procs = [
            _make_proc(0),                     # clone
            _make_proc(0),                     # rsync
            _make_proc(0, stdout=b"M app.py"), # git status
            _make_proc(0),                     # git config email
            _make_proc(0),                     # git config name
            _make_proc(0),                     # git add
            _make_proc(0),                     # git commit
            _make_proc(0),                     # git push
        ]

        with patch("asyncio.create_subprocess_exec", side_effect=procs) as mock_exec:
            await push_project_to_github(
                project_path=str(tmp_path),
                repo_name="my-repo",
                github_token="tok",
                github_username="user",
                commit_message="feat: my custom message",
            )
            # git commit call is the 7th call (index 6)
            commit_call = mock_exec.call_args_list[6][0]

        assert "feat: my custom message" in commit_call
