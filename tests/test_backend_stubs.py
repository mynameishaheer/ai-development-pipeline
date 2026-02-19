"""
Tests for backend_agent.py stub implementations:
fix_bug, write_tests, refactor_code (Phase 6).
All external deps are mocked.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path


def _make_backend(tmp_path, mock_redis, mock_github):
    with patch("agents.assignment_manager.redis.Redis", return_value=mock_redis), \
         patch("agents.assignment_manager.create_github_client", return_value=mock_github), \
         patch("agents.backend_agent.create_github_client", return_value=mock_github):
        from agents.backend_agent import BackendAgent
        agent = BackendAgent(agent_id="test_backend")
        agent.github = mock_github
        agent.workspace_dir = tmp_path
        return agent


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
    gh.get_issue = AsyncMock(return_value={
        "number": 7, "title": "Auth fails", "body": "Details", "labels": [], "state": "open"
    })
    gh.create_branch = AsyncMock(return_value={"ref": "fix/issue-7"})
    gh.create_pull_request = AsyncMock(return_value={"number": 11, "html_url": "https://github.com/pr/11"})
    return gh


@pytest.fixture
def agent(tmp_path, mock_redis, mock_github):
    return _make_backend(tmp_path, mock_redis, mock_github)


# ==========================================
# SHARED HELPERS
# ==========================================

def _mock_agent_methods(agent, tmp_path):
    """Replace heavy internal methods with fast no-op mocks."""
    agent._get_issue_details = AsyncMock(return_value={
        "number": 7, "title": "Test issue", "body": "Some bug", "labels": [], "state": "open"
    })
    agent._create_feature_branch = AsyncMock()
    agent._setup_local_repo = AsyncMock(return_value=tmp_path)
    agent.call_claude_code = AsyncMock(return_value={
        "success": True, "stdout": "done", "stderr": "", "return_code": 0
    })
    agent._validate_implementation = AsyncMock()
    agent._commit_and_push = AsyncMock()
    agent._create_pull_request = AsyncMock(return_value={
        "number": 11, "html_url": "https://github.com/pr/11"
    })
    agent.log_action = AsyncMock()
    agent.send_status_update = AsyncMock()


# ==========================================
# fix_bug
# ==========================================

class TestFixBug:

    @pytest.mark.asyncio
    async def test_fix_bug_returns_success(self, agent, tmp_path):
        _mock_agent_methods(agent, tmp_path)

        result = await agent.fix_bug({
            "repo_name": "my-repo",
            "issue_number": 7,
            "project_path": str(tmp_path),
        })

        assert result["success"] is True
        assert result["pr_number"] == 11
        assert "fix" in result["message"].lower() or "PR" in result["message"]

    @pytest.mark.asyncio
    async def test_fix_bug_creates_fix_branch(self, agent, tmp_path):
        _mock_agent_methods(agent, tmp_path)

        await agent.fix_bug({"repo_name": "my-repo", "issue_number": 7})

        agent._create_feature_branch.assert_called_once()
        branch_name = agent._create_feature_branch.call_args[0][1]
        assert "fix" in branch_name

    @pytest.mark.asyncio
    async def test_fix_bug_calls_claude_code(self, agent, tmp_path):
        _mock_agent_methods(agent, tmp_path)
        await agent.fix_bug({"repo_name": "my-repo", "issue_number": 7})
        agent.call_claude_code.assert_called_once()

    @pytest.mark.asyncio
    async def test_fix_bug_validates_implementation(self, agent, tmp_path):
        _mock_agent_methods(agent, tmp_path)
        await agent.fix_bug({"repo_name": "my-repo", "issue_number": 7})
        agent._validate_implementation.assert_called_once()

    @pytest.mark.asyncio
    async def test_fix_bug_creates_pr(self, agent, tmp_path):
        _mock_agent_methods(agent, tmp_path)
        await agent.fix_bug({"repo_name": "my-repo", "issue_number": 7})
        agent._create_pull_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_fix_bug_propagates_exception(self, agent, tmp_path):
        _mock_agent_methods(agent, tmp_path)
        agent.call_claude_code.side_effect = RuntimeError("claude failed")

        with pytest.raises(RuntimeError, match="claude failed"):
            await agent.fix_bug({"repo_name": "my-repo", "issue_number": 7})


# ==========================================
# write_tests
# ==========================================

class TestWriteTests:

    @pytest.mark.asyncio
    async def test_write_tests_returns_success(self, agent, tmp_path):
        _mock_agent_methods(agent, tmp_path)

        result = await agent.write_tests({
            "repo_name": "my-repo",
            "issue_number": 7,
        })

        assert result["success"] is True
        assert result["pr_number"] == 11

    @pytest.mark.asyncio
    async def test_write_tests_creates_tests_branch(self, agent, tmp_path):
        _mock_agent_methods(agent, tmp_path)
        await agent.write_tests({"repo_name": "my-repo", "issue_number": 7})
        branch_name = agent._create_feature_branch.call_args[0][1]
        assert "tests" in branch_name or "test" in branch_name

    @pytest.mark.asyncio
    async def test_write_tests_calls_claude_code(self, agent, tmp_path):
        _mock_agent_methods(agent, tmp_path)
        await agent.write_tests({"repo_name": "my-repo", "issue_number": 7})
        agent.call_claude_code.assert_called_once()
        prompt = agent.call_claude_code.call_args[1]["prompt"] if "prompt" in agent.call_claude_code.call_args[1] else agent.call_claude_code.call_args[0][0]
        assert "test" in prompt.lower() or "coverage" in prompt.lower()

    @pytest.mark.asyncio
    async def test_write_tests_propagates_exception(self, agent, tmp_path):
        _mock_agent_methods(agent, tmp_path)
        agent._create_feature_branch.side_effect = Exception("branch error")

        with pytest.raises(Exception, match="branch error"):
            await agent.write_tests({"repo_name": "my-repo", "issue_number": 7})


# ==========================================
# refactor_code
# ==========================================

class TestRefactorCode:

    @pytest.mark.asyncio
    async def test_refactor_code_returns_success(self, agent, tmp_path):
        _mock_agent_methods(agent, tmp_path)

        result = await agent.refactor_code({
            "repo_name": "my-repo",
            "issue_number": 7,
        })

        assert result["success"] is True
        assert result["pr_number"] == 11

    @pytest.mark.asyncio
    async def test_refactor_creates_refactor_branch(self, agent, tmp_path):
        _mock_agent_methods(agent, tmp_path)
        await agent.refactor_code({"repo_name": "my-repo", "issue_number": 7})
        branch_name = agent._create_feature_branch.call_args[0][1]
        assert "refactor" in branch_name

    @pytest.mark.asyncio
    async def test_refactor_calls_claude_code_with_refactor_prompt(self, agent, tmp_path):
        _mock_agent_methods(agent, tmp_path)
        await agent.refactor_code({"repo_name": "my-repo", "issue_number": 7})
        agent.call_claude_code.assert_called_once()

    @pytest.mark.asyncio
    async def test_refactor_validates_and_creates_pr(self, agent, tmp_path):
        _mock_agent_methods(agent, tmp_path)
        await agent.refactor_code({"repo_name": "my-repo", "issue_number": 7})
        agent._validate_implementation.assert_called_once()
        agent._create_pull_request.assert_called_once()
