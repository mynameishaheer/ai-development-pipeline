"""
Tests for agents/deployer.py (Phase 5)
All external deps (docker, cloudflared, systemctl) are mocked.
No Docker daemon, Cloudflare account, or network required.
"""

import asyncio
import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, mock_open

from agents.deployer import (
    deploy_project,
    _find_free_port,
    _load_port_allocations,
    _save_port_allocation,
    _update_cloudflared_config,
    _build_docker_image,
    _run_container,
    _run_cloudflared_dns,
    _reload_cloudflared,
    PORT_ALLOCATIONS_FILE,
)


# ==========================================
# HELPERS
# ==========================================

def _mock_proc(returncode=0, stdout=b"", stderr=b""):
    proc = AsyncMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    return proc


# ==========================================
# PORT ALLOCATION
# ==========================================

class TestPortAllocation:

    def test_find_free_port_returns_start_when_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr("agents.deployer.PORT_ALLOCATIONS_FILE", tmp_path / "ports.json")
        port = _find_free_port(start=3000)
        assert port == 3000

    def test_find_free_port_skips_used_ports(self, tmp_path, monkeypatch):
        alloc_file = tmp_path / "ports.json"
        alloc_file.write_text(json.dumps({"existing": 3000, "another": 3001}))
        monkeypatch.setattr("agents.deployer.PORT_ALLOCATIONS_FILE", alloc_file)
        port = _find_free_port(start=3000)
        assert port == 3002

    def test_save_and_load_roundtrip(self, tmp_path, monkeypatch):
        alloc_file = tmp_path / "ports.json"
        monkeypatch.setattr("agents.deployer.PORT_ALLOCATIONS_FILE", alloc_file)
        _save_port_allocation("my-project", 4000)
        allocations = _load_port_allocations()
        assert allocations["my-project"] == 4000

    def test_load_returns_empty_when_file_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "agents.deployer.PORT_ALLOCATIONS_FILE", tmp_path / "nonexistent.json"
        )
        assert _load_port_allocations() == {}

    def test_load_returns_empty_on_bad_json(self, tmp_path, monkeypatch):
        alloc_file = tmp_path / "ports.json"
        alloc_file.write_text("not-json")
        monkeypatch.setattr("agents.deployer.PORT_ALLOCATIONS_FILE", alloc_file)
        assert _load_port_allocations() == {}


# ==========================================
# DOCKER BUILD
# ==========================================

class TestBuildDockerImage:

    @pytest.mark.asyncio
    async def test_build_success(self):
        proc = _mock_proc(returncode=0)
        with patch("asyncio.create_subprocess_exec", return_value=proc):
            ok, err = await _build_docker_image("/tmp/project", "my-app")
        assert ok is True
        assert err == ""

    @pytest.mark.asyncio
    async def test_build_failure_returns_stderr(self):
        proc = _mock_proc(returncode=1, stderr=b"build failed: no dockerfile")
        with patch("asyncio.create_subprocess_exec", return_value=proc):
            ok, err = await _build_docker_image("/tmp/project", "my-app")
        assert ok is False
        assert "build failed" in err

    @pytest.mark.asyncio
    async def test_build_docker_not_found(self):
        with patch(
            "asyncio.create_subprocess_exec", side_effect=FileNotFoundError("docker not found")
        ):
            ok, err = await _build_docker_image("/tmp/project", "my-app")
        assert ok is False
        assert "not found" in err

    @pytest.mark.asyncio
    async def test_build_timeout(self):
        async def slow_communicate():
            await asyncio.sleep(999)
            return b"", b""

        proc = AsyncMock()
        proc.communicate = slow_communicate
        with patch("asyncio.create_subprocess_exec", return_value=proc), \
             patch("asyncio.wait_for", side_effect=asyncio.TimeoutError):
            ok, err = await _build_docker_image("/tmp/project", "my-app")
        assert ok is False
        assert "timed out" in err.lower()


# ==========================================
# DOCKER RUN
# ==========================================

class TestRunContainer:

    @pytest.mark.asyncio
    async def test_run_success(self):
        rm_proc = _mock_proc(returncode=0)
        run_proc = _mock_proc(returncode=0, stdout=b"abc123\n")
        call_count = 0

        async def fake_exec(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return rm_proc if call_count == 1 else run_proc

        with patch("asyncio.create_subprocess_exec", side_effect=fake_exec):
            ok, err = await _run_container("my-app", 3000)
        assert ok is True
        assert err == ""

    @pytest.mark.asyncio
    async def test_run_failure_returns_stderr(self):
        rm_proc = _mock_proc(returncode=0)
        run_proc = _mock_proc(returncode=1, stderr=b"port already in use")
        call_count = 0

        async def fake_exec(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return rm_proc if call_count == 1 else run_proc

        with patch("asyncio.create_subprocess_exec", side_effect=fake_exec):
            ok, err = await _run_container("my-app", 3000)
        assert ok is False
        assert "port" in err


# ==========================================
# CLOUDFLARE DNS
# ==========================================

class TestCloudflaredDNS:

    @pytest.mark.asyncio
    async def test_dns_success(self):
        proc = _mock_proc(returncode=0)
        with patch("asyncio.create_subprocess_exec", return_value=proc):
            ok, err = await _run_cloudflared_dns("my-app.devbot.site")
        assert ok is True

    @pytest.mark.asyncio
    async def test_dns_already_exists_is_not_error(self):
        proc = _mock_proc(returncode=1, stderr=b"already exists")
        with patch("asyncio.create_subprocess_exec", return_value=proc):
            ok, err = await _run_cloudflared_dns("my-app.devbot.site")
        assert ok is True

    @pytest.mark.asyncio
    async def test_dns_failure_returned(self):
        proc = _mock_proc(returncode=1, stderr=b"auth error")
        with patch("asyncio.create_subprocess_exec", return_value=proc):
            ok, err = await _run_cloudflared_dns("my-app.devbot.site")
        assert ok is False
        assert "auth error" in err

    @pytest.mark.asyncio
    async def test_cloudflared_not_installed(self):
        with patch(
            "asyncio.create_subprocess_exec", side_effect=FileNotFoundError("cloudflared")
        ):
            ok, err = await _run_cloudflared_dns("my-app.devbot.site")
        assert ok is False
        assert "not found" in err


# ==========================================
# RELOAD CLOUDFLARED
# ==========================================

class TestReloadCloudflared:

    @pytest.mark.asyncio
    async def test_reload_success(self):
        proc = _mock_proc(returncode=0)
        with patch("asyncio.create_subprocess_exec", return_value=proc):
            ok, err = await _reload_cloudflared()
        assert ok is True

    @pytest.mark.asyncio
    async def test_reload_failure(self):
        proc = _mock_proc(returncode=1, stderr=b"unit not found")
        with patch("asyncio.create_subprocess_exec", return_value=proc):
            ok, err = await _reload_cloudflared()
        assert ok is False
        assert "unit not found" in err


# ==========================================
# CLOUDFLARE CONFIG UPDATE
# ==========================================

class TestUpdateCloudflaredConfig:

    def test_creates_config_with_new_entry(self, tmp_path, monkeypatch):
        yaml = pytest.importorskip("yaml")
        config_path = tmp_path / "config.yml"
        monkeypatch.setattr("agents.deployer.CLOUDFLARED_CONFIG", config_path)
        monkeypatch.setenv("CLOUDFLARE_TUNNEL_ID", "test-tunnel-id")

        _update_cloudflared_config("my-app.devbot.site", 3000)

        with open(config_path) as f:
            config = yaml.safe_load(f)

        ingress = config["ingress"]
        hostnames = [e.get("hostname") for e in ingress]
        assert "my-app.devbot.site" in hostnames

        # Find the new entry
        entry = next(e for e in ingress if e.get("hostname") == "my-app.devbot.site")
        assert entry["service"] == "http://localhost:3000"

    def test_adds_catch_all_when_missing(self, tmp_path, monkeypatch):
        yaml = pytest.importorskip("yaml")
        config_path = tmp_path / "config.yml"
        monkeypatch.setattr("agents.deployer.CLOUDFLARED_CONFIG", config_path)
        monkeypatch.setenv("CLOUDFLARE_TUNNEL_ID", "tid")

        _update_cloudflared_config("app.devbot.site", 3001)

        with open(config_path) as f:
            config = yaml.safe_load(f)

        ingress = config["ingress"]
        catch_all = [e for e in ingress if "hostname" not in e]
        assert len(catch_all) >= 1

    def test_replaces_existing_entry_for_same_hostname(self, tmp_path, monkeypatch):
        yaml = pytest.importorskip("yaml")
        config_path = tmp_path / "config.yml"
        monkeypatch.setattr("agents.deployer.CLOUDFLARED_CONFIG", config_path)
        monkeypatch.setenv("CLOUDFLARE_TUNNEL_ID", "tid")

        # First write
        _update_cloudflared_config("app.devbot.site", 3001)
        # Update port
        _update_cloudflared_config("app.devbot.site", 3999)

        with open(config_path) as f:
            config = yaml.safe_load(f)

        entries = [e for e in config["ingress"] if e.get("hostname") == "app.devbot.site"]
        assert len(entries) == 1
        assert entries[0]["service"] == "http://localhost:3999"


# ==========================================
# FULL DEPLOY FLOW
# ==========================================

class TestDeployProject:

    @pytest.mark.asyncio
    async def test_deploy_success(self, tmp_path, monkeypatch):
        alloc_file = tmp_path / "ports.json"
        monkeypatch.setattr("agents.deployer.PORT_ALLOCATIONS_FILE", alloc_file)

        with patch("agents.deployer._build_docker_image", return_value=(True, "")), \
             patch("agents.deployer._run_container", return_value=(True, "")), \
             patch("agents.deployer._add_cloudflare_route", return_value=(True, "")):

            result = await deploy_project(
                project_path="/tmp/proj",
                project_name="my-app",
                domain_suffix="devbot.site",
            )

        assert result["success"] is True
        assert result["url"] == "https://my-app.devbot.site"
        assert result["port"] >= 3000
        assert result["error"] == ""

    @pytest.mark.asyncio
    async def test_deploy_fails_on_build_error(self, tmp_path, monkeypatch):
        alloc_file = tmp_path / "ports.json"
        monkeypatch.setattr("agents.deployer.PORT_ALLOCATIONS_FILE", alloc_file)

        with patch("agents.deployer._build_docker_image", return_value=(False, "no dockerfile")):
            result = await deploy_project("/tmp/proj", "my-app")

        assert result["success"] is False
        assert "no dockerfile" in result["error"]
        assert result["url"] == ""

    @pytest.mark.asyncio
    async def test_deploy_fails_on_run_error(self, tmp_path, monkeypatch):
        alloc_file = tmp_path / "ports.json"
        monkeypatch.setattr("agents.deployer.PORT_ALLOCATIONS_FILE", alloc_file)

        with patch("agents.deployer._build_docker_image", return_value=(True, "")), \
             patch("agents.deployer._run_container", return_value=(False, "port in use")):
            result = await deploy_project("/tmp/proj", "my-app")

        assert result["success"] is False
        assert "port in use" in result["error"]

    @pytest.mark.asyncio
    async def test_deploy_succeeds_even_if_cloudflare_fails(self, tmp_path, monkeypatch):
        """Cloudflare route failure is non-fatal — container is running."""
        alloc_file = tmp_path / "ports.json"
        monkeypatch.setattr("agents.deployer.PORT_ALLOCATIONS_FILE", alloc_file)

        with patch("agents.deployer._build_docker_image", return_value=(True, "")), \
             patch("agents.deployer._run_container", return_value=(True, "")), \
             patch(
                 "agents.deployer._add_cloudflare_route",
                 return_value=(False, "cloudflared not installed"),
             ):
            result = await deploy_project("/tmp/proj", "my-app")

        assert result["success"] is True
        assert "cloudflared not installed" in result["error"]

    @pytest.mark.asyncio
    async def test_deploy_saves_port_allocation(self, tmp_path, monkeypatch):
        alloc_file = tmp_path / "ports.json"
        monkeypatch.setattr("agents.deployer.PORT_ALLOCATIONS_FILE", alloc_file)

        with patch("agents.deployer._build_docker_image", return_value=(True, "")), \
             patch("agents.deployer._run_container", return_value=(True, "")), \
             patch("agents.deployer._add_cloudflare_route", return_value=(True, "")):
            result = await deploy_project("/tmp/proj", "my-app")

        allocations = _load_port_allocations()
        assert "my-app" in allocations
        assert allocations["my-app"] == result["port"]

    @pytest.mark.asyncio
    async def test_deploy_handles_unexpected_exception(self, tmp_path, monkeypatch):
        alloc_file = tmp_path / "ports.json"
        monkeypatch.setattr("agents.deployer.PORT_ALLOCATIONS_FILE", alloc_file)

        with patch(
            "agents.deployer._build_docker_image", side_effect=RuntimeError("unexpected")
        ):
            result = await deploy_project("/tmp/proj", "my-app")

        assert result["success"] is False
        assert "unexpected" in result["error"]
