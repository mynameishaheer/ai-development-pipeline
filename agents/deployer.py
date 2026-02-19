"""
Deployer — Docker + Cloudflare Tunnel deployment for AI Dev Pipeline.

Per-project automation:
1. Build Docker image from project directory
2. Allocate a free port (tracked in ~/.ai-dev-pipeline/port_allocations.json)
3. Start Docker container mapping that port to :8000 inside
4. Update ~/.cloudflared/config.yml with new ingress entry
5. Add DNS record via `cloudflared tunnel route dns`
6. Reload cloudflared systemd service
7. Return https://{name}.devbot.site

Environment variables:
  CLOUDFLARE_TUNNEL_NAME  (default: devbot-pipeline)
  CLOUDFLARE_TUNNEL_ID    (used when creating config.yml from scratch)
  DEPLOY_DOMAIN           (default: devbot.site)
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Dict, Tuple

# ==========================================
# CONFIGURATION
# ==========================================

CLOUDFLARE_TUNNEL_NAME: str = os.getenv("CLOUDFLARE_TUNNEL_NAME", "devbot-pipeline")
DEPLOY_DOMAIN: str = os.getenv("DEPLOY_DOMAIN", "devbot.site")

PORT_ALLOCATIONS_FILE = Path.home() / ".ai-dev-pipeline" / "port_allocations.json"
CLOUDFLARED_CONFIG = Path.home() / ".cloudflared" / "config.yml"

PORT_START = 3000


# ==========================================
# PUBLIC API
# ==========================================


async def deploy_project(
    project_path: str,
    project_name: str,
    domain_suffix: str = None,
) -> Dict:
    """
    Build Docker image, run container, expose via Cloudflare Tunnel.

    Args:
        project_path: Absolute path to the project directory (must contain Dockerfile).
        project_name: Short identifier used as Docker image/container name and subdomain.
        domain_suffix: Domain to use (defaults to DEPLOY_DOMAIN env var).

    Returns:
        {
            "success": bool,
            "url": str,       # e.g. "https://my-project.devbot.site"
            "port": int,      # host port container is bound to
            "error": str,     # empty on full success
        }
    """
    domain_suffix = domain_suffix or DEPLOY_DOMAIN

    try:
        # Step 1: Build Docker image
        build_ok, build_err = await _build_docker_image(project_path, project_name)
        if not build_ok:
            return {
                "success": False,
                "url": "",
                "port": 0,
                "error": f"Docker build failed: {build_err}",
            }

        # Step 2: Find a free port
        port = _find_free_port()

        # Step 3: Start container
        run_ok, run_err = await _run_container(project_name, port)
        if not run_ok:
            return {
                "success": False,
                "url": "",
                "port": 0,
                "error": f"Docker run failed: {run_err}",
            }

        # Step 4: Cloudflare Tunnel route (non-fatal)
        url = f"https://{project_name}.{domain_suffix}"
        route_ok, route_err = await _add_cloudflare_route(
            project_name, port, domain_suffix
        )

        # Step 5: Persist port allocation
        _save_port_allocation(project_name, port)

        error_msg = "" if route_ok else (
            f"Container running on :{port} but Cloudflare route failed: {route_err}"
        )

        return {"success": True, "url": url, "port": port, "error": error_msg}

    except Exception as exc:
        return {"success": False, "url": "", "port": 0, "error": str(exc)}


# ==========================================
# DOCKER HELPERS
# ==========================================


async def _build_docker_image(project_path: str, name: str) -> Tuple[bool, str]:
    """Run `docker build -t {name} {project_path}`."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "build", "-t", name, project_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
        if proc.returncode == 0:
            return True, ""
        return False, stderr.decode(errors="replace")
    except asyncio.TimeoutError:
        return False, "Docker build timed out after 300s"
    except FileNotFoundError:
        return False, "docker binary not found — is Docker installed?"


async def _run_container(name: str, port: int) -> Tuple[bool, str]:
    """
    Remove any existing container with the same name, then start a fresh one.
    Maps host port → container :8000.
    """
    # Remove existing (ignore errors)
    rm_proc = await asyncio.create_subprocess_exec(
        "docker", "rm", "-f", name,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    await rm_proc.communicate()

    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "run", "-d",
            "-p", f"{port}:8000",
            "--name", name,
            "--restart", "unless-stopped",
            name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        if proc.returncode == 0:
            return True, ""
        return False, stderr.decode(errors="replace")
    except asyncio.TimeoutError:
        return False, "Docker run timed out after 60s"
    except FileNotFoundError:
        return False, "docker binary not found"


# ==========================================
# PORT ALLOCATION
# ==========================================


def _find_free_port(start: int = PORT_START) -> int:
    """Return the first port >= start not already in port_allocations.json."""
    used = set(_load_port_allocations().values())
    port = start
    while port in used:
        port += 1
    return port


def _load_port_allocations() -> Dict[str, int]:
    PORT_ALLOCATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if PORT_ALLOCATIONS_FILE.exists():
        try:
            with open(PORT_ALLOCATIONS_FILE, "r") as fh:
                return json.load(fh)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_port_allocation(name: str, port: int) -> None:
    allocations = _load_port_allocations()
    allocations[name] = port
    with open(PORT_ALLOCATIONS_FILE, "w") as fh:
        json.dump(allocations, fh, indent=2)


# ==========================================
# CLOUDFLARE TUNNEL
# ==========================================


async def _add_cloudflare_route(
    name: str, port: int, domain_suffix: str
) -> Tuple[bool, str]:
    """
    1. Update ~/.cloudflared/config.yml with new ingress entry.
    2. Run `cloudflared tunnel route dns <tunnel> <hostname>`.
    3. Reload cloudflared via systemctl.
    """
    hostname = f"{name}.{domain_suffix}"

    # Update config file
    try:
        _update_cloudflared_config(hostname, port)
    except Exception as exc:
        return False, f"config.yml update failed: {exc}"

    # Add DNS record
    dns_ok, dns_err = await _run_cloudflared_dns(hostname)
    if not dns_ok:
        return False, dns_err

    # Reload service
    reload_ok, reload_err = await _reload_cloudflared()
    if not reload_ok:
        return False, reload_err

    return True, ""


async def _run_cloudflared_dns(hostname: str) -> Tuple[bool, str]:
    """Run `cloudflared tunnel route dns <tunnel> <hostname>`."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "cloudflared", "tunnel", "route", "dns",
            CLOUDFLARE_TUNNEL_NAME, hostname,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        if proc.returncode != 0:
            err = stderr.decode(errors="replace")
            # "already exists" is not a real error
            if "already exists" in err.lower():
                return True, ""
            return False, f"cloudflared DNS route failed: {err}"
        return True, ""
    except asyncio.TimeoutError:
        return False, "cloudflared DNS route timed out"
    except FileNotFoundError:
        return False, "cloudflared binary not found — is cloudflared installed?"


async def _reload_cloudflared() -> Tuple[bool, str]:
    """Run `sudo systemctl reload cloudflared`."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "sudo", "systemctl", "reload", "cloudflared",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
        if proc.returncode != 0:
            return False, stderr.decode(errors="replace")
        return True, ""
    except asyncio.TimeoutError:
        return False, "systemctl reload timed out"
    except FileNotFoundError:
        return False, "sudo/systemctl not available"


def _update_cloudflared_config(hostname: str, port: int) -> None:
    """
    Parse ~/.cloudflared/config.yml, insert/update the ingress entry for
    this hostname, and write it back.  Creates the file from scratch if
    it does not exist yet (using CLOUDFLARE_TUNNEL_ID env var).
    """
    try:
        import yaml  # pyyaml — optional dep, only needed at deploy time
    except ImportError as exc:
        raise RuntimeError(
            "pyyaml is required for Cloudflare config management: pip install pyyaml"
        ) from exc

    CLOUDFLARED_CONFIG.parent.mkdir(parents=True, exist_ok=True)

    if CLOUDFLARED_CONFIG.exists():
        with open(CLOUDFLARED_CONFIG, "r") as fh:
            config = yaml.safe_load(fh) or {}
    else:
        tunnel_id = os.getenv("CLOUDFLARE_TUNNEL_ID", "")
        config = {
            "tunnel": tunnel_id,
            "credentials-file": str(
                Path.home() / ".cloudflared" / f"{tunnel_id}.json"
            ),
            "ingress": [],
        }

    ingress: list = config.get("ingress", [])

    # Remove stale entry for this hostname
    ingress = [e for e in ingress if e.get("hostname") != hostname]

    # New entry
    new_entry = {"hostname": hostname, "service": f"http://localhost:{port}"}

    # Insert before the catch-all (entry without a hostname key)
    catch_all_idx = next(
        (i for i, e in enumerate(ingress) if "hostname" not in e),
        len(ingress),
    )
    ingress.insert(catch_all_idx, new_entry)

    # Ensure a catch-all rule exists
    if not any("hostname" not in e for e in ingress):
        ingress.append({"service": "http_status:404"})

    config["ingress"] = ingress

    with open(CLOUDFLARED_CONFIG, "w") as fh:
        yaml.dump(config, fh, default_flow_style=False)
