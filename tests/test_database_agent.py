"""
Tests for Database Agent (Phase 3.3)
Tests schema design task routing, migration setup, and seed data creation.
All tests use mocks — no Claude Code or file system writes required.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock, mock_open
from pathlib import Path

from agents.database_agent import DatabaseAgent
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
def db_agent(mock_redis):
    with patch("agents.messaging.redis.Redis", return_value=mock_redis):
        agent = DatabaseAgent(agent_id="db_test")
        return agent


# ==========================================
# SETUP TESTS
# ==========================================

class TestDatabaseAgentSetup:

    def test_agent_type_is_database(self, db_agent):
        assert db_agent.agent_type == AgentType.DATABASE

    def test_get_capabilities_returns_list(self, db_agent):
        caps = db_agent.get_capabilities()
        assert isinstance(caps, list)
        assert len(caps) > 0

    def test_capabilities_include_key_functions(self, db_agent):
        caps = db_agent.get_capabilities()
        caps_lower = [c.lower() for c in caps]
        assert any("schema" in c for c in caps_lower)
        assert any("migrat" in c for c in caps_lower)
        assert any("sqlalchemy" in c for c in caps_lower)


# ==========================================
# TASK ROUTING TESTS
# ==========================================

class TestTaskRouting:

    @pytest.mark.asyncio
    async def test_execute_unknown_task_raises(self, db_agent):
        with pytest.raises(ValueError, match="Unknown task type"):
            await db_agent.execute_task({"task_type": "unknown_operation"})

    @pytest.mark.asyncio
    async def test_execute_routes_design_schema(self, db_agent):
        db_agent.design_schema = AsyncMock(return_value={"success": True, "files_created": []})
        await db_agent.execute_task({"task_type": "design_schema", "project_path": "/tmp"})
        assert db_agent.design_schema.called

    @pytest.mark.asyncio
    async def test_execute_routes_create_migrations(self, db_agent):
        db_agent.create_migrations = AsyncMock(return_value={"success": True})
        await db_agent.execute_task({"task_type": "create_migrations", "project_path": "/tmp"})
        assert db_agent.create_migrations.called

    @pytest.mark.asyncio
    async def test_execute_routes_optimize_queries(self, db_agent):
        db_agent.optimize_queries = AsyncMock(return_value={"success": True})
        await db_agent.execute_task({"task_type": "optimize_queries", "project_path": "/tmp"})
        assert db_agent.optimize_queries.called

    @pytest.mark.asyncio
    async def test_execute_routes_create_seed_data(self, db_agent):
        db_agent.create_seed_data = AsyncMock(return_value={"success": True})
        await db_agent.execute_task({"task_type": "create_seed_data", "project_path": "/tmp"})
        assert db_agent.create_seed_data.called

    @pytest.mark.asyncio
    async def test_execute_routes_validate_integrity(self, db_agent):
        db_agent.validate_integrity = AsyncMock(return_value={"success": True})
        await db_agent.execute_task({"task_type": "validate_integrity", "project_path": "/tmp"})
        assert db_agent.validate_integrity.called


# ==========================================
# DESIGN SCHEMA TESTS
# ==========================================

class TestDesignSchema:

    @pytest.mark.asyncio
    async def test_design_schema_success(self, db_agent, tmp_path):
        # Mock call_claude_code to simulate file creation
        async def mock_claude(prompt, project_path=None, allowed_tools=None):
            # Actually create the files so path checks pass
            models_dir = tmp_path / "src" / "database"
            models_dir.mkdir(parents=True, exist_ok=True)
            (models_dir / "models.py").write_text("# models")

            docs_dir = tmp_path / "docs"
            docs_dir.mkdir(exist_ok=True)
            (docs_dir / "DATABASE_SCHEMA.md").write_text("# Schema")

            return {"success": True, "stdout": "Done", "stderr": "", "return_code": 0}

        db_agent.call_claude_code = mock_claude
        db_agent.log_action = AsyncMock()
        db_agent.send_status_update = AsyncMock()

        result = await db_agent.design_schema({
            "task_type": "design_schema",
            "project_path": str(tmp_path),
            "prd_path": "",
            "db_type": "postgresql",
        })

        assert result["success"] is True
        assert len(result["files_created"]) > 0
        assert result["db_type"] == "postgresql"

    @pytest.mark.asyncio
    async def test_design_schema_reads_prd(self, db_agent, tmp_path):
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD\n\nThis is a task management app with users and tasks.")

        prompts_received = []

        async def capture_prompt(prompt, project_path=None, allowed_tools=None):
            prompts_received.append(prompt)
            return {"success": True, "stdout": "", "stderr": "", "return_code": 0}

        db_agent.call_claude_code = capture_prompt
        db_agent.log_action = AsyncMock()
        db_agent.send_status_update = AsyncMock()

        await db_agent.design_schema({
            "task_type": "design_schema",
            "project_path": str(tmp_path),
            "prd_path": str(prd_file),
            "db_type": "postgresql",
        })

        assert len(prompts_received) == 1
        assert "task management" in prompts_received[0]

    @pytest.mark.asyncio
    async def test_design_schema_handles_missing_prd(self, db_agent, tmp_path):
        """Should still work when PRD file doesn't exist."""
        prompts_received = []

        async def capture_prompt(prompt, project_path=None, allowed_tools=None):
            prompts_received.append(prompt)
            return {"success": True, "stdout": "", "stderr": "", "return_code": 0}

        db_agent.call_claude_code = capture_prompt
        db_agent.log_action = AsyncMock()
        db_agent.send_status_update = AsyncMock()

        result = await db_agent.design_schema({
            "task_type": "design_schema",
            "project_path": str(tmp_path),
            "prd_path": "/nonexistent/PRD.md",
            "db_type": "sqlite",
        })

        assert result["success"] is True
        # Prompt should have fallback text
        assert "general-purpose" in prompts_received[0].lower() or \
               "project structure" in prompts_received[0].lower()


# ==========================================
# MIGRATION TESTS
# ==========================================

class TestCreateMigrations:

    @pytest.mark.asyncio
    async def test_create_migrations_calls_claude(self, db_agent, tmp_path):
        called = []

        async def mock_claude(prompt, project_path=None, allowed_tools=None):
            called.append(True)
            # Create alembic dir to simulate successful run
            (tmp_path / "alembic").mkdir(exist_ok=True)
            (tmp_path / "docs").mkdir(exist_ok=True)
            (tmp_path / "docs" / "MIGRATIONS.md").write_text("# Migrations")
            return {"success": True, "stdout": "Alembic initialized", "stderr": "", "return_code": 0}

        db_agent.call_claude_code = mock_claude
        db_agent.log_action = AsyncMock()

        result = await db_agent.create_migrations({
            "task_type": "create_migrations",
            "project_path": str(tmp_path),
        })

        assert result["success"] is True
        assert result["alembic_initialized"] is True
        assert len(called) == 1

    @pytest.mark.asyncio
    async def test_create_migrations_error_is_raised(self, db_agent, tmp_path):
        async def failing_claude(prompt, project_path=None, allowed_tools=None):
            raise RuntimeError("Claude Code unavailable")

        db_agent.call_claude_code = failing_claude
        db_agent.log_action = AsyncMock()

        with pytest.raises(RuntimeError, match="Claude Code unavailable"):
            await db_agent.create_migrations({
                "task_type": "create_migrations",
                "project_path": str(tmp_path),
            })


# ==========================================
# FULL WORKFLOW TESTS
# ==========================================

class TestFullDatabaseSetup:

    @pytest.mark.asyncio
    async def test_setup_database_runs_all_steps(self, db_agent, tmp_path):
        db_agent.design_schema = AsyncMock(return_value={"success": True, "files_created": []})
        db_agent.create_migrations = AsyncMock(return_value={"success": True})
        db_agent.create_seed_data = AsyncMock(return_value={"success": True, "seed_script": None})

        result = await db_agent.setup_database_for_project(
            project_path=str(tmp_path),
            prd_path="",
            db_type="postgresql",
        )

        assert result["success"] is True
        assert db_agent.design_schema.called
        assert db_agent.create_migrations.called
        assert db_agent.create_seed_data.called

    @pytest.mark.asyncio
    async def test_setup_database_result_contains_all_steps(self, db_agent, tmp_path):
        db_agent.design_schema = AsyncMock(return_value={"success": True, "files_created": []})
        db_agent.create_migrations = AsyncMock(return_value={"success": True})
        db_agent.create_seed_data = AsyncMock(return_value={"success": True, "seed_script": None})

        result = await db_agent.setup_database_for_project(str(tmp_path), "", "sqlite")

        assert "schema" in result["results"]
        assert "migrations" in result["results"]
        assert "seed_data" in result["results"]
