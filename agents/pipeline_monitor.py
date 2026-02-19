"""
Pipeline Monitor for AI Development Pipeline (Phase 4)

Runs as a background asyncio task that:
1. Polls GitHub Actions every 30 seconds for CI/CD failures
2. Diagnoses failures with Claude Code, pushes fixes, re-checks
3. Detects stalled workers (stuck in 'working' for >10 min)
4. Sends proactive Discord notifications via master._notify_channel
"""

import asyncio
import os
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Dict, Optional, Set

from agents.github_client import GitHubClient
from utils.structured_logger import get_logger

if TYPE_CHECKING:
    from agents.master_agent import MasterAgent

logger = get_logger("pipeline_monitor", agent_type="master")

# Configurable via environment
MONITOR_POLL_INTERVAL = int(os.getenv("MONITOR_POLL_INTERVAL", "30"))
MAX_FIX_ATTEMPTS = 3
WORKER_STALL_MINUTES = 10


class PipelineMonitor:
    """
    Background CI/CD watcher and worker health monitor.

    Lifecycle:
        monitor = PipelineMonitor(master, github)
        await monitor.start()   # begins background loop
        await monitor.stop()    # cancels loop cleanly
    """

    def __init__(self, master: "MasterAgent", github: GitHubClient):
        self.master = master
        self.github = github
        self._running = False
        self._task: Optional[asyncio.Task] = None

        # run_id → number of fix attempts made
        self._fix_attempts: Dict[int, int] = {}

        # run_ids already fully handled (no re-processing)
        self._handled_runs: Set[int] = set()

        logger.info("PipelineMonitor initialized")

    # ==========================================
    # PUBLIC API
    # ==========================================

    async def start(self):
        """Start the background monitoring loop (idempotent)."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("PipelineMonitor started")

    async def stop(self):
        """Stop the monitoring loop cleanly."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("PipelineMonitor stopped")

    def is_running(self) -> bool:
        """Return True if the monitor loop is active."""
        return self._running and self._task is not None and not self._task.done()

    def get_status(self) -> Dict:
        """Return current monitor state for the !monitor status command."""
        project = self.master.current_project
        return {
            "running": self.is_running(),
            "repo": project.get("repo_name", "") if project else "",
            "fix_attempts": dict(self._fix_attempts),
            "handled_runs": len(self._handled_runs),
        }

    # ==========================================
    # MAIN LOOP
    # ==========================================

    async def _monitor_loop(self):
        """30-second polling loop — runs until stop() is called."""
        project = self.master.current_project
        if project:
            repo_name = project.get("repo_name", "")
            if repo_name:
                await self._notify(f"🔍 Monitoring CI for {repo_name}...")

        try:
            while self._running:
                try:
                    await self._check_ci_status()
                    await self._check_worker_health()
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.error(f"Monitor loop iteration error: {e}", exc_info=True)

                await asyncio.sleep(MONITOR_POLL_INTERVAL)
        except asyncio.CancelledError:
            pass
        finally:
            self._running = False

    # ==========================================
    # CI/CD WATCHER
    # ==========================================

    async def _check_ci_status(self):
        """Fetch latest GitHub Actions run and act on failure/success."""
        project = self.master.current_project
        if not project:
            return

        repo_name = project.get("repo_name", "")
        if not repo_name:
            return

        try:
            runs = await self.github.get_workflow_runs(repo_name, branch="main")
        except Exception as e:
            logger.warning(f"Could not fetch workflow runs for {repo_name}: {e}")
            return

        if not runs:
            return

        latest_run = runs[0]
        run_id = latest_run.get("id")
        status = latest_run.get("status")       # queued, in_progress, completed
        conclusion = latest_run.get("conclusion")  # success, failure, cancelled, None

        if run_id in self._handled_runs:
            return

        if status != "completed":
            return  # Still running — check again next poll

        if conclusion == "failure":
            attempts = self._fix_attempts.get(run_id, 0)
            if attempts >= MAX_FIX_ATTEMPTS:
                self._handled_runs.add(run_id)
                await self._notify(
                    f"❌ CI still failing after {MAX_FIX_ATTEMPTS} auto-fix attempts — "
                    f"needs your attention. Run ID: {run_id}"
                )
                return
            await self._handle_ci_failure(latest_run)

        elif conclusion == "success":
            self._handled_runs.add(run_id)
            # Only notify if we were the ones who attempted a fix
            if run_id in self._fix_attempts:
                await self._notify("✅ CI passing — all checks green")

    async def _handle_ci_failure(self, run: Dict):
        """
        Diagnose a CI failure, apply a Claude Code fix, push the fix.

        Flow:
            fetch logs → Claude Code diagnose+fix → push → notify → wait for next run
        """
        run_id = run.get("id")
        run_name = run.get("name", "CI")

        project = self.master.current_project
        if not project:
            return

        repo_name = project.get("repo_name", "")
        project_path = project.get("path", "")

        # Increment attempt counter
        self._fix_attempts[run_id] = self._fix_attempts.get(run_id, 0) + 1
        attempt = self._fix_attempts[run_id]

        await self._notify(
            f"❌ CI failed on `{run_name}` "
            f"(attempt {attempt}/{MAX_FIX_ATTEMPTS}) — diagnosing now..."
        )

        # Fetch failure logs
        logs = await self.github.get_workflow_run_logs(repo_name, run_id)

        prompt = f"""
The GitHub Actions CI pipeline failed. Analyze the error logs and fix the issue.

Repository: {repo_name}
Project path: {project_path}

CI Failure Logs:
```
{logs[:5000]}
```

Instructions:
1. Identify the root cause of the CI failure from the logs above
2. Fix the relevant files in the project directory at {project_path}
3. Make minimal, targeted changes — only touch what causes the failure
4. Do not create new test files unless the fix absolutely requires it
5. Focus on the actual error, not style issues or unrelated improvements

Fix the code so CI will pass on the next run.
"""

        logger.info(f"Calling Claude Code to diagnose CI failure for run {run_id}")
        result = await self.master.call_claude_code(
            prompt=prompt,
            project_path=project_path,
            allowed_tools=["Read", "Edit", "Write", "Bash"],
        )

        if not result.get("success"):
            await self._notify(
                f"⚠️ Auto-diagnosis failed. "
                f"Error: {result.get('stderr', '')[:200]}"
            )
            return

        fix_summary = result.get("stdout", "")[:300].strip()

        # Push fix to GitHub
        github_token = os.getenv("GITHUB_TOKEN", "")
        github_username = os.getenv("GITHUB_USERNAME", "")

        if not (github_token and github_username and project_path):
            await self._notify(
                "🔧 Fix applied locally but GITHUB_TOKEN/GITHUB_USERNAME not set — "
                "cannot push automatically."
            )
            return

        from agents.github_pusher import push_project_to_github

        pushed = await push_project_to_github(
            project_path=project_path,
            repo_name=repo_name,
            github_token=github_token,
            github_username=github_username,
            commit_message=f"fix: auto-fix CI failure (run {run_id}, attempt {attempt})",
        )

        if pushed:
            self._handled_runs.add(run_id)
            await self._notify(
                f"🔧 Fix pushed: {fix_summary or 'see commit for details'}\n"
                f"Waiting for CI to re-run..."
            )
        else:
            await self._notify(
                "⚠️ Fix was generated but push to GitHub failed. Manual review needed."
            )

    # ==========================================
    # WORKER HEALTH WATCHER
    # ==========================================

    async def _check_worker_health(self):
        """Detect workers stuck in 'working' for longer than WORKER_STALL_MINUTES."""
        daemon = self.master._worker_daemon
        if not daemon:
            return

        status = daemon.get_status()
        now = datetime.utcnow()
        stall_threshold = timedelta(minutes=WORKER_STALL_MINUTES)

        task_start_times: Dict[str, str] = status.get("task_start_times", {})
        worker_states: Dict[str, str] = status.get("worker_states", {})

        for agent_type, state in worker_states.items():
            if state != "working":
                continue

            start_time_str = task_start_times.get(agent_type)
            if not start_time_str:
                continue

            try:
                start_time = datetime.fromisoformat(start_time_str)
            except ValueError:
                continue

            duration = now - start_time
            if duration <= stall_threshold:
                continue

            minutes_stuck = int(duration.total_seconds() / 60)
            logger.warning(
                f"Worker {agent_type} has been in 'working' state for "
                f"{minutes_stuck} minutes — treating as stalled"
            )
            await self._notify(
                f"⚠️ Worker `{agent_type}` has been stuck for {minutes_stuck} minutes — requeuing task"
            )

            # Reset worker state so it can claim new tasks on next poll
            daemon._worker_states[agent_type] = "idle"
            if hasattr(daemon, "_task_start_times"):
                daemon._task_start_times.pop(agent_type, None)

    # ==========================================
    # DISCORD NOTIFICATION
    # ==========================================

    async def _notify(self, message: str):
        """Send a proactive message to the last-used Discord channel."""
        logger.info(f"[notify] {message}")

        channel = getattr(self.master, "_notify_channel", None)
        if channel is None:
            return

        try:
            if len(message) > 2000:
                message = message[:1997] + "..."
            await channel.send(message)
        except Exception as e:
            logger.warning(f"Discord notification failed: {e}")
