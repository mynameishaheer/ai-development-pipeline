"""
Agent Worker Daemon for AI Development Pipeline
Pulls tasks from Redis queues and dispatches them to the appropriate agents.
Handles GitHub sync on completion/failure and routes QA review tasks.
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Dict, List, Optional

from agents.assignment_manager import AssignmentManager
from agents.agent_factory import AgentFactory
from agents.github_client import create_github_client
from utils.constants import AgentType, REDIS_HOST, REDIS_PORT
from utils.structured_logger import get_logger

# ==========================================
# ENVIRONMENT CONFIG
# ==========================================

WORKER_POLL_INTERVAL = int(os.getenv("WORKER_POLL_INTERVAL", "10"))
WORKER_MAX_CONCURRENT = int(os.getenv("WORKER_MAX_CONCURRENT", "1"))
WORKER_AGENTS = os.getenv(
    "WORKER_AGENTS", "backend,frontend,database,devops,qa"
).split(",")


class AgentWorkerDaemon:
    """
    Runs one async worker loop per agent type.

    Each loop:
    1. Claims the next highest-priority task from Redis
    2. Calls agent.execute_task(task)
    3. On success → complete_task() + GitHub sync
    4. On failure → fail_task() + GitHub sync

    After backend/frontend complete with a PR, automatically enqueues
    a QA review task. QA worker handles merge + close on approval.

    When ALL queues across all agent types drain to 0 simultaneously,
    triggers auto-deploy via deployer.deploy_project() and notifies Discord.
    """

    def __init__(self, agent_types: Optional[List[str]] = None, master=None):
        self.logger = get_logger("worker_daemon", agent_type="master")
        self.assignment_manager = AssignmentManager()
        self.github = create_github_client()

        # Which agent types to run workers for
        self.agent_types = agent_types or WORKER_AGENTS

        # Lazily-created agent instances (one per type)
        self._agents: Dict[str, object] = {}

        # Worker state tracking
        self._running = False
        self._worker_tasks: List[asyncio.Task] = []
        self._worker_states: Dict[str, str] = {
            agent_type: "idle" for agent_type in self.agent_types
        }

        # ISO-format start time for the current task per worker (used for stall detection)
        self._task_start_times: Dict[str, str] = {}

        # Phase 6: all-tasks-done detection
        # Holds a reference to MasterAgent so we can trigger deploy + notify
        self._master = master
        self._all_tasks_done_notified: bool = False

        self.logger.info(
            "AgentWorkerDaemon initialized",
            extra={"agent_types": self.agent_types}
        )

    # ==========================================
    # AGENT ACCESS
    # ==========================================

    def _get_agent(self, agent_type: str):
        """Return a cached agent instance, creating it lazily."""
        if agent_type not in self._agents:
            self._agents[agent_type] = AgentFactory.create_agent(
                agent_type, agent_id=f"worker_{agent_type}"
            )
        return self._agents[agent_type]

    # ==========================================
    # WORKER LOOP
    # ==========================================

    async def run_worker(self, agent_type: str):
        """
        Single worker loop for one agent type.
        Runs indefinitely until self._running is False.
        """
        self.logger.info(f"Worker loop started for agent: {agent_type}")

        while self._running:
            self._worker_states[agent_type] = "polling"

            try:
                task = self.assignment_manager.claim_next_task(agent_type)

                if task is None:
                    # Queue empty — wait before polling again
                    self._worker_states[agent_type] = "idle"
                    await asyncio.sleep(WORKER_POLL_INTERVAL)
                    continue

                self._worker_states[agent_type] = "working"
                self._task_start_times[agent_type] = datetime.utcnow().isoformat()
                self.logger.info(
                    f"[{agent_type}] Claimed task: {task.get('task_type')} "
                    f"for issue #{task.get('issue_number')} in {task.get('repo_name')}"
                )

                agent = self._get_agent(agent_type)

                try:
                    result = await agent.execute_task(task)

                    # Mark complete in Redis
                    self.assignment_manager.complete_task(
                        repo_name=task.get("repo_name", ""),
                        issue_number=task.get("issue_number", 0),
                        result=result,
                    )

                    # GitHub sync
                    await self._sync_github_on_complete(task, result, agent_type)

                    # If backend/frontend produced a PR, enqueue QA review
                    if agent_type in (AgentType.BACKEND, AgentType.FRONTEND):
                        pr_number = result.get("pr_number")
                        if pr_number:
                            await self._enqueue_qa_review(
                                repo_name=task.get("repo_name", ""),
                                pr_number=pr_number,
                                issue_number=task.get("issue_number", 0),
                                project_path=task.get("project_path", ""),
                            )

                except Exception as task_error:
                    error_msg = str(task_error)
                    self.logger.error(
                        f"[{agent_type}] Task failed: {error_msg}",
                        exc_info=True
                    )

                    # Mark failed in Redis
                    self.assignment_manager.fail_task(
                        repo_name=task.get("repo_name", ""),
                        issue_number=task.get("issue_number", 0),
                        error=error_msg,
                    )

                    # Get diagnosis then sync GitHub with enriched comment
                    diagnosis = await self._get_task_failure_diagnosis(task, error_msg)
                    await self._sync_github_on_failure(
                        task, error_msg, agent_type, diagnosis=diagnosis
                    )

                self._worker_states[agent_type] = "idle"
                self._task_start_times.pop(agent_type, None)
                await self._check_and_trigger_deploy()

            except Exception as loop_error:
                # Loop-level error (e.g., Redis connection issue) — back off
                self.logger.error(
                    f"[{agent_type}] Worker loop error: {loop_error}",
                    exc_info=True
                )
                self._worker_states[agent_type] = "error"
                await asyncio.sleep(WORKER_POLL_INTERVAL * 2)

        self.logger.info(f"Worker loop stopped for agent: {agent_type}")
        self._worker_states[agent_type] = "stopped"

    # ==========================================
    # QA WORKER — handles review_pr tasks
    # ==========================================

    async def run_qa_worker(self):
        """
        QA worker loop — extends run_worker with post-review merge/close.
        """
        self.logger.info("QA worker loop started")

        while self._running:
            self._worker_states[AgentType.QA] = "polling"

            try:
                task = self.assignment_manager.claim_next_task(AgentType.QA)

                if task is None:
                    self._worker_states[AgentType.QA] = "idle"
                    await asyncio.sleep(WORKER_POLL_INTERVAL)
                    continue

                self._worker_states[AgentType.QA] = "working"
                self._task_start_times[AgentType.QA] = datetime.utcnow().isoformat()
                self.logger.info(
                    f"[qa] Claimed QA task: {task.get('task_type')} "
                    f"PR #{task.get('pr_number')} in {task.get('repo_name')}"
                )

                agent = self._get_agent(AgentType.QA)

                try:
                    result = await agent.execute_task(task)

                    approved = result.get("approved", False)
                    repo_name = task.get("repo_name", "")
                    pr_number = task.get("pr_number", 0)
                    issue_number = task.get("issue_number", 0)

                    if approved:
                        # Merge PR and close issue
                        try:
                            await self.github.merge_pull_request(repo_name, pr_number)
                            self.logger.info(
                                f"[qa] Merged PR #{pr_number} in {repo_name}"
                            )
                        except Exception as merge_err:
                            self.logger.warning(
                                f"[qa] Could not merge PR #{pr_number}: {merge_err}"
                            )

                        try:
                            await self.github.close_issue(repo_name, issue_number)
                            self.logger.info(
                                f"[qa] Closed issue #{issue_number} in {repo_name}"
                            )
                        except Exception as close_err:
                            self.logger.warning(
                                f"[qa] Could not close issue #{issue_number}: {close_err}"
                            )

                        self.assignment_manager.complete_task(
                            repo_name=repo_name,
                            issue_number=issue_number,
                            result=result,
                        )
                    else:
                        # QA rejected — add label and mark failed
                        try:
                            await self.github.add_issue_comment(
                                repo_name,
                                issue_number,
                                f"🔁 QA review requested changes on PR #{pr_number}. "
                                f"Issues: {', '.join(result.get('issues', []))}",
                            )
                            await self.github.update_issue(
                                repo_name,
                                issue_number,
                                labels=["needs-revision"],
                            )
                        except Exception as gh_err:
                            self.logger.warning(
                                f"[qa] GitHub update after rejection failed: {gh_err}"
                            )

                        self.assignment_manager.fail_task(
                            repo_name=repo_name,
                            issue_number=issue_number,
                            error="QA review: changes requested",
                        )

                except Exception as task_error:
                    error_msg = str(task_error)
                    self.logger.error(
                        f"[qa] QA task failed: {error_msg}", exc_info=True
                    )
                    self.assignment_manager.fail_task(
                        repo_name=task.get("repo_name", ""),
                        issue_number=task.get("issue_number", 0),
                        error=error_msg,
                    )
                    diagnosis = await self._get_task_failure_diagnosis(task, error_msg)
                    await self._sync_github_on_failure(
                        task, error_msg, AgentType.QA, diagnosis=diagnosis
                    )

                self._worker_states[AgentType.QA] = "idle"
                self._task_start_times.pop(AgentType.QA, None)
                await self._check_and_trigger_deploy()

            except Exception as loop_error:
                self.logger.error(
                    f"[qa] Worker loop error: {loop_error}", exc_info=True
                )
                self._worker_states[AgentType.QA] = "error"
                await asyncio.sleep(WORKER_POLL_INTERVAL * 2)

        self.logger.info("QA worker loop stopped")
        self._worker_states[AgentType.QA] = "stopped"

    # ==========================================
    # START / STOP
    # ==========================================

    async def start(self):
        """Launch all worker loops as concurrent asyncio tasks."""
        self._running = True
        self._worker_tasks = []

        for agent_type in self.agent_types:
            if agent_type == AgentType.QA:
                task = asyncio.create_task(self.run_qa_worker())
            else:
                task = asyncio.create_task(self.run_worker(agent_type))
            self._worker_tasks.append(task)

        self.logger.info(
            f"Started {len(self._worker_tasks)} worker(s) for: "
            f"{', '.join(self.agent_types)}"
        )

        try:
            await asyncio.gather(*self._worker_tasks)
        except asyncio.CancelledError:
            self.logger.info("Worker daemon cancelled")
        except Exception as e:
            self.logger.error(f"Worker daemon error: {e}", exc_info=True)

    async def stop(self):
        """Gracefully stop all worker loops."""
        self.logger.info("Stopping worker daemon...")
        self._running = False

        for task in self._worker_tasks:
            if not task.done():
                task.cancel()

        if self._worker_tasks:
            await asyncio.gather(*self._worker_tasks, return_exceptions=True)

        self._worker_tasks = []
        self.logger.info("Worker daemon stopped")

    # ==========================================
    # GITHUB SYNC
    # ==========================================

    async def _sync_github_on_complete(
        self, task: Dict, result: Dict, agent_type: str
    ):
        """Add completion comment + in-review label to the GitHub issue."""
        repo_name = task.get("repo_name", "")
        issue_number = task.get("issue_number", 0)

        if not repo_name or not issue_number:
            return

        pr_number = result.get("pr_number")
        pr_ref = f" PR: #{pr_number}" if pr_number else ""

        comment = (
            f"✅ Implemented by **{agent_type}** agent.{pr_ref}\n\n"
            f"*{datetime.now().strftime('%Y-%m-%d %H:%M UTC')}*"
        )

        try:
            await self.github.add_issue_comment(repo_name, issue_number, comment)
            await self.github.update_issue(
                repo_name, issue_number, labels=["in-review"]
            )
        except Exception as e:
            self.logger.warning(
                f"GitHub sync on complete failed for issue #{issue_number}: {e}"
            )

    async def _get_task_failure_diagnosis(self, task: Dict, error: str) -> str:
        """
        Call Claude Code to generate a human-readable diagnosis of why a task failed.
        Returns a 2-3 sentence summary, or a fallback string on failure.
        """
        agent_type = task.get("agent_type", "backend")
        try:
            agent = self._get_agent(agent_type)
            result = await agent.call_claude_code(
                prompt=(
                    f"A development task failed with this error:\n\n"
                    f"Task type: {task.get('task_type')}\n"
                    f"Repository: {task.get('repo_name')}\n"
                    f"Issue: #{task.get('issue_number')}\n"
                    f"Error: {error}\n\n"
                    f"In 2-3 sentences, diagnose: what went wrong and what a "
                    f"developer should do to fix it."
                ),
                allowed_tools=["Read"],
                timeout=60,
            )
            diagnosis = result.get("stdout", "").strip()
            return diagnosis or "Unable to generate diagnosis."
        except Exception as exc:
            self.logger.warning(f"Diagnosis call failed: {exc}")
            return "Diagnosis failed — see logs for details."

    async def _sync_github_on_failure(
        self, task: Dict, error: str, agent_type: str, diagnosis: str = None
    ):
        """Add enriched failure comment + needs-attention label to the GitHub issue."""
        repo_name = task.get("repo_name", "")
        issue_number = task.get("issue_number", 0)

        if not repo_name or not issue_number:
            return

        diagnosis_section = (
            f"\n\n**Diagnosis:** {diagnosis}" if diagnosis else ""
        )
        comment = (
            f"❌ **{agent_type}** agent failed after 3 attempts."
            f"{diagnosis_section}\n\n"
            f"**Error:** {error[:500]}\n\n"
            f"Task moved to `needs-attention` label.\n\n"
            f"*{datetime.now().strftime('%Y-%m-%d %H:%M UTC')}*"
        )

        try:
            await self.github.add_issue_comment(repo_name, issue_number, comment)
            await self.github.update_issue(
                repo_name, issue_number, labels=["needs-attention"]
            )
        except Exception as e:
            self.logger.warning(
                f"GitHub sync on failure failed for issue #{issue_number}: {e}"
            )

    # ==========================================
    # ALL-TASKS-DONE DETECTION (Phase 6)
    # ==========================================

    def _all_queues_empty(self) -> bool:
        """Return True when every agent queue has 0 pending tasks."""
        try:
            queue_status = self.assignment_manager.get_queue_status()
            return all(
                info.get("pending_tasks", 0) == 0
                for info in queue_status.values()
            )
        except Exception:
            return False

    def _all_workers_idle(self) -> bool:
        """Return True when every worker is idle (not currently processing a task)."""
        return all(
            state in ("idle", "polling", "stopped")
            for state in self._worker_states.values()
        )

    async def _check_and_trigger_deploy(self):
        """
        If all queues are empty and all workers are idle, trigger auto-deploy once.
        Resets the flag when new tasks appear so the next drain re-triggers.
        """
        if self._all_queues_empty() and self._all_workers_idle():
            if not self._all_tasks_done_notified:
                self._all_tasks_done_notified = True
                self.logger.info("All queues empty — triggering auto-deploy")
                await self._auto_deploy()
        else:
            # New tasks arrived — allow another notification later
            self._all_tasks_done_notified = False

    async def _auto_deploy(self):
        """Trigger deploy_project() for the active project and notify Discord."""
        if not self._master:
            return

        project = self._master.current_project
        if not project:
            return

        project_path = project.get("path", "")
        project_name = project.get("name", "")
        if not project_path or not project_name:
            return

        try:
            from agents.deployer import deploy_project
            deploy_result = await deploy_project(
                project_path=project_path,
                project_name=project_name,
            )

            if deploy_result["success"]:
                url = deploy_result["url"]
                project["deploy_url"] = url
                await self._master.save_project_metadata()
                msg = (
                    f"🎉 **All tasks complete!** `{project_name}` has been deployed.\n"
                    f"🌐 Live at: {url}"
                )
                self.logger.info(f"Auto-deploy succeeded: {url}")
            else:
                err = deploy_result.get("error", "unknown error")
                msg = (
                    f"✅ **All tasks complete** for `{project_name}`, "
                    f"but auto-deploy failed: {err[:200]}"
                )
                self.logger.warning(f"Auto-deploy failed: {err}")

            await self._master._notify(msg)

        except Exception as exc:
            self.logger.error(f"Auto-deploy exception: {exc}", exc_info=True)
            await self._master._notify(
                f"✅ **All tasks complete** for `{project_name}`, "
                f"but auto-deploy raised an error: {str(exc)[:200]}"
            )

    # ==========================================
    # QA TASK ENQUEUE
    # ==========================================

    async def _enqueue_qa_review(
        self,
        repo_name: str,
        pr_number: int,
        issue_number: int,
        project_path: str = "",
    ):
        """Push a QA review task onto queue:agent:qa."""
        await self.assignment_manager.assign_pr_review(
            repo_name=repo_name,
            pr_number=pr_number,
            issue_number=issue_number,
            project_path=project_path,
        )
        self.logger.info(
            f"Enqueued QA review for PR #{pr_number} "
            f"(issue #{issue_number}) in {repo_name}"
        )

    # ==========================================
    # STATUS
    # ==========================================

    def get_status(self) -> Dict:
        """Return queue sizes, worker states, and per-worker task start times."""
        queue_status = self.assignment_manager.get_queue_status()
        return {
            "running": self._running,
            "agent_types": self.agent_types,
            "worker_states": dict(self._worker_states),
            "task_start_times": dict(self._task_start_times),
            "queues": {
                agent_type: info.get("pending_tasks", 0)
                for agent_type, info in queue_status.items()
            },
        }
