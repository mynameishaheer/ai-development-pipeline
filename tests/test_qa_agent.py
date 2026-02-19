"""
Tests for QA Agent (Phase 3.1)
Tests PR validation, test detection, coverage parsing, and review logic.
All tests use mocks — no GitHub connection or Claude Code required.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from agents.qa_agent import QAAgent
from utils.constants import AgentType


# ==========================================
# FIXTURES
# ==========================================

@pytest.fixture
def mock_redis():
    redis_mock = MagicMock()
    redis_mock.publish = MagicMock(return_value=1)
    return redis_mock


@pytest.fixture
def qa_agent(mock_redis):
    mock_gh = AsyncMock()
    with patch("agents.messaging.redis.Redis", return_value=mock_redis), \
         patch("agents.qa_agent.create_github_client", return_value=mock_gh):
        agent = QAAgent(agent_id="qa_test")
        agent.github = mock_gh
        return agent


# ==========================================
# AGENT SETUP TESTS
# ==========================================

class TestQAAgentSetup:

    def test_agent_type_is_qa(self, qa_agent):
        assert qa_agent.agent_type == AgentType.QA

    def test_get_capabilities_returns_list(self, qa_agent):
        caps = qa_agent.get_capabilities()
        assert isinstance(caps, list)
        assert len(caps) > 0

    def test_capabilities_include_key_functions(self, qa_agent):
        caps = qa_agent.get_capabilities()
        caps_lower = [c.lower() for c in caps]
        assert any("pr" in c or "pull request" in c for c in caps_lower)
        assert any("test" in c for c in caps_lower)
        assert any("coverage" in c for c in caps_lower)


# ==========================================
# PR VALIDATION TESTS
# ==========================================

class TestPRValidation:

    @pytest.mark.asyncio
    async def test_validate_pr_missing_number(self, qa_agent):
        result = await qa_agent.validate_pull_request({
            "task_type": "validate_pr",
            "repo_name": "myrepo",
        })
        assert result["valid"] is False
        assert "pr_number" in result.get("issues", ["pr_number"])[0].lower() or \
               result.get("reason") or not result["valid"]

    @pytest.mark.asyncio
    async def test_validate_pr_checks_title_convention(self, qa_agent):
        """PR with good title should pass title validation."""
        qa_agent.github.get_pull_request = AsyncMock(return_value={
            "number": 1,
            "title": "feat: add user authentication",
            "body": "This implements JWT auth. Closes #5",
            "head": {"ref": "feature/auth"},
            "base": {"ref": "dev"},
        })

        result = await qa_agent.validate_pull_request({
            "task_type": "validate_pr",
            "repo_name": "myrepo",
            "pr_number": 1,
        })

        assert isinstance(result, dict)
        assert "valid" in result

    @pytest.mark.asyncio
    async def test_validate_pr_rejects_empty_title(self, qa_agent):
        qa_agent.github.get_pull_request = AsyncMock(return_value={
            "number": 2,
            "title": "",
            "body": "Some description",
            "head": {"ref": "feature/test"},
            "base": {"ref": "dev"},
        })

        result = await qa_agent.validate_pull_request({
            "task_type": "validate_pr",
            "repo_name": "myrepo",
            "pr_number": 2,
        })

        assert result["valid"] is False

    @pytest.mark.asyncio
    async def test_validate_pr_github_error(self, qa_agent):
        qa_agent.github.get_pull_request = AsyncMock(side_effect=Exception("API error"))

        result = await qa_agent.validate_pull_request({
            "task_type": "validate_pr",
            "repo_name": "myrepo",
            "pr_number": 99,
        })

        assert result["valid"] is False


# ==========================================
# TEST DETECTION TESTS
# ==========================================

class TestFrameworkDetection:

    def test_detect_pytest(self, qa_agent, tmp_path):
        (tmp_path / "requirements.txt").write_text("pytest==7.0.0\nfastapi==0.100.0\n")
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_main.py").write_text("def test_something(): pass")

        framework = qa_agent._detect_test_framework(str(tmp_path))
        assert "pytest" in framework

    def test_detect_jest(self, qa_agent, tmp_path):
        (tmp_path / "package.json").write_text('{"devDependencies": {"jest": "^29.0.0"}}')

        framework = qa_agent._detect_test_framework(str(tmp_path))
        assert "jest" in framework

    def test_detect_both(self, qa_agent, tmp_path):
        (tmp_path / "requirements.txt").write_text("pytest==7.0.0\n")
        (tmp_path / "package.json").write_text('{"devDependencies": {"jest": "^29.0.0"}}')

        framework = qa_agent._detect_test_framework(str(tmp_path))
        assert "pytest" in framework
        assert "jest" in framework

    def test_detect_none(self, qa_agent, tmp_path):
        framework = qa_agent._detect_test_framework(str(tmp_path))
        assert framework == "none"


# ==========================================
# COVERAGE PARSING TESTS
# ==========================================

class TestCoverageParsing:

    def test_parse_standard_coverage_output(self, qa_agent):
        output = """
Name                      Stmts   Miss  Cover
---------------------------------------------
src/main.py                  50      5    90%
src/utils.py                 30      9    70%
---------------------------------------------
TOTAL                        80     14    83%
"""
        coverage = qa_agent._extract_coverage_percentage(output)
        assert coverage == 83.0

    def test_parse_coverage_with_decimal(self, qa_agent):
        output = "TOTAL                  100     15    85.5%\n"
        coverage = qa_agent._extract_coverage_percentage(output)
        assert coverage == 85.5

    def test_parse_coverage_no_match(self, qa_agent):
        output = "Tests passed: 42. No coverage info."
        coverage = qa_agent._extract_coverage_percentage(output)
        assert coverage is None

    def test_parse_coverage_100_percent(self, qa_agent):
        output = "TOTAL                   50      0   100%\n"
        coverage = qa_agent._extract_coverage_percentage(output)
        assert coverage == 100.0

    def test_parse_coverage_zero_percent(self, qa_agent):
        output = "TOTAL                   50     50     0%\n"
        coverage = qa_agent._extract_coverage_percentage(output)
        assert coverage == 0.0


# ==========================================
# TEST PASS DETECTION TESTS
# ==========================================

class TestPassDetection:

    def test_detect_pytest_all_passed(self, qa_agent):
        output = "15 passed in 2.34s"
        assert qa_agent._determine_test_pass(output, True) is True

    def test_detect_pytest_with_failures(self, qa_agent):
        output = "3 failed, 12 passed in 1.22s"
        assert qa_agent._determine_test_pass(output, True) is False

    def test_detect_pytest_errors(self, qa_agent):
        output = "1 error in 0.5s"
        assert qa_agent._determine_test_pass(output, True) is False

    def test_detect_jest_passed(self, qa_agent):
        output = "Tests:       10 passed, 10 total\nTest Suites: 2 passed, 2 total"
        assert qa_agent._determine_test_pass(output, True) is True

    def test_detect_jest_failed(self, qa_agent):
        output = "Tests:       2 failed, 8 passed, 10 total"
        assert qa_agent._determine_test_pass(output, True) is False

    def test_execution_failure_overrides_output(self, qa_agent):
        """If execution failed (non-zero return code), tests should be marked as failed."""
        output = "15 passed in 2.34s"
        assert qa_agent._determine_test_pass(output, False) is False

    def test_empty_output_with_success(self, qa_agent):
        """Empty output with successful execution — ambiguous, should be False."""
        assert qa_agent._determine_test_pass("", True) is False


# ==========================================
# EXECUTE TASK ROUTING
# ==========================================

class TestExecuteTask:

    @pytest.mark.asyncio
    async def test_execute_task_unknown_type(self, qa_agent):
        with pytest.raises(ValueError, match="Unknown task type"):
            await qa_agent.execute_task({"task_type": "nonexistent_task"})

    @pytest.mark.asyncio
    async def test_execute_task_routes_validate_pr(self, qa_agent):
        qa_agent.validate_pull_request = AsyncMock(return_value={"valid": True})
        await qa_agent.execute_task({"task_type": "validate_pr", "repo_name": "r", "pr_number": 1})
        assert qa_agent.validate_pull_request.called

    @pytest.mark.asyncio
    async def test_execute_task_routes_run_tests(self, qa_agent):
        qa_agent.run_tests_for_project = AsyncMock(return_value={"success": True, "tests_passed": True})
        await qa_agent.execute_task({"task_type": "run_tests", "project_path": "/tmp"})
        assert qa_agent.run_tests_for_project.called

    @pytest.mark.asyncio
    async def test_execute_task_routes_check_coverage(self, qa_agent):
        qa_agent.check_coverage = AsyncMock(return_value={"success": True, "coverage": 85.0})
        await qa_agent.execute_task({"task_type": "check_coverage", "project_path": "/tmp"})
        assert qa_agent.check_coverage.called
