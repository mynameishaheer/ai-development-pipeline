"""
GitHub Pusher for AI Development Pipeline (Phase 4)

Pushes a local project directory to its GitHub repository.
Called after run_full_pipeline() completes so generated code lands on GitHub.
"""

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Optional

from utils.structured_logger import get_logger

logger = get_logger("github_pusher", agent_type="master")

# Files/dirs to exclude when rsyncing into the cloned repo
RSYNC_EXCLUDES = [
    ".git",
    "app.db",
    "*.pyc",
    "__pycache__",
    ".project_metadata.json",
    ".qa_config.json",
    "*.egg-info",
    ".env",
    "node_modules",
    "venv",
    ".venv",
]


async def push_project_to_github(
    project_path: str,
    repo_name: str,
    github_token: str,
    github_username: str,
    branch: str = "main",
    commit_message: Optional[str] = None,
) -> bool:
    """
    Push a local project directory to its GitHub repository.

    Steps:
    1. Clone the repo into a temp directory
    2. rsync project files into the clone (excluding .git, .db, cache, etc.)
    3. git add + commit + push

    Args:
        project_path: Local directory with generated project files
        repo_name: GitHub repository name (e.g., "project_20260219_165036")
        github_token: GitHub Personal Access Token
        github_username: GitHub username (for repo URL construction)
        branch: Branch to push to (default: "main")
        commit_message: Commit message (auto-generated if not provided)

    Returns:
        True if push succeeded, False otherwise
    """
    if commit_message is None:
        from datetime import datetime
        commit_message = (
            f"chore: automated code push from pipeline "
            f"({datetime.now().strftime('%Y-%m-%d %H:%M')})"
        )

    project_path = str(Path(project_path).resolve())
    repo_url = f"https://{github_token}@github.com/{github_username}/{repo_name}.git"

    with tempfile.TemporaryDirectory() as tmpdir:
        clone_dir = os.path.join(tmpdir, repo_name)

        # --- Step 1: Clone ---
        logger.info(f"Cloning {repo_name} to temp dir...")
        ok = await _run_subprocess(
            ["git", "clone", "--depth=1", f"--branch={branch}", repo_url, clone_dir],
            cwd=tmpdir,
        )
        if not ok:
            # Repo might be empty (no commits yet) — try without --branch
            logger.warning("Clone with --branch failed, retrying without --branch")
            ok = await _run_subprocess(
                ["git", "clone", "--depth=1", repo_url, clone_dir],
                cwd=tmpdir,
            )
            if not ok:
                logger.error(f"Failed to clone {repo_name}")
                return False

        # --- Step 2: rsync project files ---
        logger.info(f"Syncing {project_path} → {clone_dir}...")
        exclude_args: list = []
        for excl in RSYNC_EXCLUDES:
            exclude_args.extend(["--exclude", excl])

        rsync_cmd = [
            "rsync", "-a", "--delete",
            *exclude_args,
            project_path.rstrip("/") + "/",
            clone_dir.rstrip("/") + "/",
        ]
        ok = await _run_subprocess(rsync_cmd, cwd=tmpdir)
        if not ok:
            logger.error("rsync failed")
            return False

        # --- Step 3: Check if there's anything to commit ---
        diff_proc = await asyncio.create_subprocess_exec(
            "git", "status", "--porcelain",
            cwd=clone_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await diff_proc.communicate()
        if not stdout.strip():
            logger.info("Nothing to commit — repo is already up to date")
            return True

        # --- Step 4: Configure git identity ---
        await _run_subprocess(
            ["git", "config", "user.email", "pipeline@ai-dev-pipeline"],
            cwd=clone_dir,
        )
        await _run_subprocess(
            ["git", "config", "user.name", "AI Dev Pipeline"],
            cwd=clone_dir,
        )

        # --- Step 5: Stage all changes ---
        ok = await _run_subprocess(["git", "add", "-A"], cwd=clone_dir)
        if not ok:
            logger.error("git add failed")
            return False

        # --- Step 6: Commit ---
        ok = await _run_subprocess(
            ["git", "commit", "-m", commit_message],
            cwd=clone_dir,
        )
        if not ok:
            logger.error("git commit failed")
            return False

        # --- Step 7: Push ---
        logger.info(f"Pushing to origin/{branch}...")
        ok = await _run_subprocess(
            ["git", "push", "origin", branch],
            cwd=clone_dir,
        )
        if not ok:
            logger.error("git push failed")
            return False

        logger.info(f"Successfully pushed {repo_name} to GitHub ({branch})")
        return True


async def _run_subprocess(cmd: list, cwd: str) -> bool:
    """
    Run an external command non-blockingly.

    Returns True if the process exits with code 0, False otherwise.
    Times out after 120 seconds.
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        if proc.returncode != 0:
            logger.warning(
                f"Command failed [{' '.join(str(c) for c in cmd[:3])}] "
                f"exit={proc.returncode}: {stderr.decode('utf-8', errors='replace')[:500]}"
            )
            return False
        return True
    except asyncio.TimeoutError:
        logger.error(f"Command timed out: {' '.join(str(c) for c in cmd[:3])}")
        return False
    except Exception as e:
        logger.error(f"Command error ({cmd[0]}): {e}")
        return False
