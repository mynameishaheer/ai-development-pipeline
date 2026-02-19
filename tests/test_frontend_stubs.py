"""
Tests for frontend_agent.py stub implementations:
fix_bug, improve_ui (Phase 6).
All external deps are mocked.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path


def _make_frontend(tmp_path, mock_redis, mock_github):
    with patch("agents.assignment_manager.redis.Redis", return_value=mock_redis), \
         patch("agents.assignment_manager.create_github_client", return_value=mock_github), \
         patch("agents.frontend_agent.create_github_client", return_value=mock_github):
        from agents.frontend_agent import FrontendAgent
        agent = FrontendAgent(agent_id="test_frontend")
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
        "number": 3, "title": "Button broken", "body": "Click does nothing",
        "labels": [], "state": "open",
    })
    gh.create_branch = AsyncMock(return_value={"ref": "fix/ui-issue-3"})
    gh.create_pull_request = AsyncMock(return_value={
        "number": 9, "html_url": "https://github.com/pr/9"
    })
    return gh


@pytest.fixture
def agent(tmp_path, mock_redis, mock_github):
    return _make_frontend(tmp_path, mock_redis, mock_github)


def _mock_agent_methods(agent, tmp_path):
    agent._get_issue_details = AsyncMock(return_value={
        "number": 3, "title": "Button broken", "body": "Click does nothing",
        "labels": [], "state": "open",
    })
    agent._create_feature_branch = AsyncMock()
    agent._setup_local_repo = AsyncMock(return_value=tmp_path)
    agent.call_claude_code = AsyncMock(return_value={
        "success": True, "stdout": "done", "stderr": "", "return_code": 0
    })
    agent._validate_implementation = AsyncMock()
    agent._commit_and_push = AsyncMock()
    agent._create_pull_request = AsyncMock(return_value={
        "number": 9, "html_url": "https://github.com/pr/9"
    })
    agent.log_action = AsyncMock()
    agent.send_status_update = AsyncMock()


# ==========================================
# fix_bug
# ==========================================

class TestFrontendFixBug:

    @pytest.mark.asyncio
    async def test_fix_bug_returns_success(self, agent, tmp_path):
        _mock_agent_methods(agent, tmp_path)
        result = await agent.fix_bug({
            "repo_name": "my-repo",
            "issue_number": 3,
        })
        assert result["success"] is True
        assert result["pr_number"] == 9

    @pytest.mark.asyncio
    async def test_fix_bug_creates_fix_branch(self, agent, tmp_path):
        _mock_agent_methods(agent, tmp_path)
        await agent.fix_bug({"repo_name": "my-repo", "issue_number": 3})
        branch_name = agent._create_feature_branch.call_args[0][1]
        assert "fix" in branch_name

    @pytest.mark.asyncio
    async def test_fix_bug_calls_claude_code(self, agent, tmp_path):
        _mock_agent_methods(agent, tmp_path)
        await agent.fix_bug({"repo_name": "my-repo", "issue_number": 3})
        agent.call_claude_code.assert_called_once()

    @pytest.mark.asyncio
    async def test_fix_bug_validates_implementation(self, agent, tmp_path):
        _mock_agent_methods(agent, tmp_path)
        await agent.fix_bug({"repo_name": "my-repo", "issue_number": 3})
        agent._validate_implementation.assert_called_once()

    @pytest.mark.asyncio
    async def test_fix_bug_creates_pr(self, agent, tmp_path):
        _mock_agent_methods(agent, tmp_path)
        await agent.fix_bug({"repo_name": "my-repo", "issue_number": 3})
        agent._create_pull_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_fix_bug_propagates_exception(self, agent, tmp_path):
        _mock_agent_methods(agent, tmp_path)
        agent.call_claude_code.side_effect = RuntimeError("claude error")
        with pytest.raises(RuntimeError, match="claude error"):
            await agent.fix_bug({"repo_name": "my-repo", "issue_number": 3})


# ==========================================
# improve_ui
# ==========================================

class TestImproveUI:

    @pytest.mark.asyncio
    async def test_improve_ui_returns_success(self, agent, tmp_path):
        _mock_agent_methods(agent, tmp_path)
        result = await agent.improve_ui({
            "repo_name": "my-repo",
            "issue_number": 3,
        })
        assert result["success"] is True
        assert result["pr_number"] == 9

    @pytest.mark.asyncio
    async def test_improve_ui_creates_improve_branch(self, agent, tmp_path):
        _mock_agent_methods(agent, tmp_path)
        await agent.improve_ui({"repo_name": "my-repo", "issue_number": 3})
        branch_name = agent._create_feature_branch.call_args[0][1]
        assert "improve" in branch_name

    @pytest.mark.asyncio
    async def test_improve_ui_calls_claude_code_with_ui_prompt(self, agent, tmp_path):
        _mock_agent_methods(agent, tmp_path)
        await agent.improve_ui({"repo_name": "my-repo", "issue_number": 3})
        agent.call_claude_code.assert_called_once()

    @pytest.mark.asyncio
    async def test_improve_ui_validates_and_creates_pr(self, agent, tmp_path):
        _mock_agent_methods(agent, tmp_path)
        await agent.improve_ui({"repo_name": "my-repo", "issue_number": 3})
        agent._validate_implementation.assert_called_once()
        agent._create_pull_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_improve_ui_propagates_exception(self, agent, tmp_path):
        _mock_agent_methods(agent, tmp_path)
        agent._validate_implementation.side_effect = RuntimeError("tests fail")
        with pytest.raises(RuntimeError, match="tests fail"):
            await agent.improve_ui({"repo_name": "my-repo", "issue_number": 3})
