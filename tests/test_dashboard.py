"""
Tests for the FastAPI web dashboard (Phase 7).
Uses HTTPX async test client — no browser or real port required.
"""

import json
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from pathlib import Path


# ---------------------------------------------------------------------------
# Build a minimal MasterAgent mock that satisfies dashboard expectations
# ---------------------------------------------------------------------------

def _make_mock_master(projects=None, active=None, workers_running=False):
    master = MagicMock()
    master._active_project_name = active
    master._projects = projects or {}
    master.get_full_status = MagicMock(return_value={
        "projects": {
            name: {**proj, "active": name == active, "monitor_running": False}
            for name, proj in (projects or {}).items()
        },
        "active_project": active,
        "workers": {
            "running": workers_running,
            "queues": {"backend": 0, "frontend": 0},
            "worker_states": {"backend": "idle", "frontend": "idle"},
        },
    })
    master.handle_deploy_project = AsyncMock(
        return_value="🌐 **Deployed!**\n\nURL: https://proj.devbot.site"
    )
    return master


def _make_test_client(mock_master):
    """Create an HTTPX AsyncClient for the dashboard app with injected master."""
    pytest.importorskip("httpx")
    from httpx import AsyncClient, ASGITransport
    from api.dashboard import app, set_master
    set_master(mock_master)
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://testserver")


SAMPLE_PROJECTS = {
    "project_alpha": {
        "name": "project_alpha",
        "path": "/tmp/project_alpha",
        "repo_url": "https://github.com/user/project_alpha",
        "repo_name": "project_alpha",
        "status": "pipeline_complete",
        "created_at": "2026-01-01T10:00:00",
        "deploy_url": "https://project_alpha.devbot.site",
        "requirements": "Build a URL shortener",
    },
    "project_beta": {
        "name": "project_beta",
        "path": "/tmp/project_beta",
        "repo_url": "https://github.com/user/project_beta",
        "repo_name": "project_beta",
        "status": "ready_for_development",
        "created_at": "2026-01-02T08:00:00",
        "deploy_url": None,
        "requirements": "Build a blog",
    },
}


# ==========================================
# GET / — Dashboard
# ==========================================

class TestDashboardRoute:

    @pytest.mark.asyncio
    async def test_dashboard_returns_200(self):
        mock_master = _make_mock_master()
        async with _make_test_client(mock_master) as client:
            resp = await client.get("/")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_dashboard_contains_project_names(self):
        mock_master = _make_mock_master(
            projects=SAMPLE_PROJECTS, active="project_alpha"
        )
        async with _make_test_client(mock_master) as client:
            resp = await client.get("/")
        assert resp.status_code == 200
        assert "project_alpha" in resp.text
        assert "project_beta" in resp.text

    @pytest.mark.asyncio
    async def test_dashboard_shows_deploy_url(self):
        mock_master = _make_mock_master(
            projects=SAMPLE_PROJECTS, active="project_alpha"
        )
        async with _make_test_client(mock_master) as client:
            resp = await client.get("/")
        assert "devbot.site" in resp.text

    @pytest.mark.asyncio
    async def test_dashboard_no_projects_message(self):
        mock_master = _make_mock_master()
        async with _make_test_client(mock_master) as client:
            resp = await client.get("/")
        assert resp.status_code == 200
        # Should show some empty-state text
        assert "No projects" in resp.text or "!new" in resp.text


# ==========================================
# GET /api/status — JSON endpoint
# ==========================================

class TestApiStatusRoute:

    @pytest.mark.asyncio
    async def test_api_status_returns_200(self):
        mock_master = _make_mock_master()
        async with _make_test_client(mock_master) as client:
            resp = await client.get("/api/status")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_api_status_is_json(self):
        mock_master = _make_mock_master()
        async with _make_test_client(mock_master) as client:
            resp = await client.get("/api/status")
        data = resp.json()
        assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_api_status_contains_expected_keys(self):
        mock_master = _make_mock_master(
            projects=SAMPLE_PROJECTS, active="project_alpha"
        )
        async with _make_test_client(mock_master) as client:
            resp = await client.get("/api/status")
        data = resp.json()
        assert "projects" in data
        assert "workers" in data
        assert "active_project" in data

    @pytest.mark.asyncio
    async def test_api_status_includes_project_data(self):
        mock_master = _make_mock_master(
            projects=SAMPLE_PROJECTS, active="project_alpha"
        )
        async with _make_test_client(mock_master) as client:
            resp = await client.get("/api/status")
        data = resp.json()
        assert "project_alpha" in data["projects"]
        assert "project_beta" in data["projects"]


# ==========================================
# GET /api/status-fragment — HTML live fragment
# ==========================================

class TestStatusFragment:

    @pytest.mark.asyncio
    async def test_fragment_returns_200(self):
        mock_master = _make_mock_master()
        async with _make_test_client(mock_master) as client:
            resp = await client.get("/api/status-fragment")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_fragment_contains_worker_status(self):
        mock_master = _make_mock_master(workers_running=True)
        async with _make_test_client(mock_master) as client:
            resp = await client.get("/api/status-fragment")
        assert "Running" in resp.text or "running" in resp.text

    @pytest.mark.asyncio
    async def test_fragment_contains_pending_count(self):
        master = _make_mock_master()
        master.get_full_status.return_value["workers"]["queues"] = {
            "backend": 5, "frontend": 2
        }
        async with _make_test_client(master) as client:
            resp = await client.get("/api/status-fragment")
        assert "7" in resp.text or "backend" in resp.text


# ==========================================
# GET /projects/{name} — project detail
# ==========================================

class TestProjectDetailRoute:

    @pytest.mark.asyncio
    async def test_project_detail_returns_200(self):
        mock_master = _make_mock_master(
            projects=SAMPLE_PROJECTS, active="project_alpha"
        )
        async with _make_test_client(mock_master) as client:
            resp = await client.get("/projects/project_alpha")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_project_detail_contains_name(self):
        mock_master = _make_mock_master(
            projects=SAMPLE_PROJECTS, active="project_alpha"
        )
        async with _make_test_client(mock_master) as client:
            resp = await client.get("/projects/project_alpha")
        assert "project_alpha" in resp.text

    @pytest.mark.asyncio
    async def test_project_detail_shows_deploy_url(self):
        mock_master = _make_mock_master(
            projects=SAMPLE_PROJECTS, active="project_alpha"
        )
        async with _make_test_client(mock_master) as client:
            resp = await client.get("/projects/project_alpha")
        assert "devbot.site" in resp.text

    @pytest.mark.asyncio
    async def test_project_detail_404_for_unknown(self):
        mock_master = _make_mock_master(
            projects=SAMPLE_PROJECTS, active="project_alpha"
        )
        async with _make_test_client(mock_master) as client:
            resp = await client.get("/projects/nonexistent")
        assert resp.status_code == 404


# ==========================================
# POST /projects/{name}/deploy — trigger deploy
# ==========================================

class TestDeployRoute:

    @pytest.mark.asyncio
    async def test_deploy_redirects_to_project(self):
        mock_master = _make_mock_master(
            projects=SAMPLE_PROJECTS, active="project_alpha"
        )
        async with _make_test_client(mock_master) as client:
            resp = await client.post(
                "/projects/project_beta/deploy",
                follow_redirects=False,
            )
        # 303 redirect to /projects/project_beta
        assert resp.status_code == 303
        assert "/projects/project_beta" in resp.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_deploy_calls_handle_deploy_project(self):
        mock_master = _make_mock_master(
            projects=SAMPLE_PROJECTS, active="project_alpha"
        )
        async with _make_test_client(mock_master) as client:
            await client.post(
                "/projects/project_beta/deploy",
                follow_redirects=False,
            )
        mock_master.handle_deploy_project.assert_called_once()

    @pytest.mark.asyncio
    async def test_deploy_404_for_unknown_project(self):
        mock_master = _make_mock_master(
            projects=SAMPLE_PROJECTS, active="project_alpha"
        )
        async with _make_test_client(mock_master) as client:
            resp = await client.post("/projects/nonexistent/deploy")
        assert resp.status_code == 404
