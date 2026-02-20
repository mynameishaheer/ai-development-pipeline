"""
Base Agent Class for AI Development Pipeline
Abstract base class that all sub-agents inherit from
Provides common functionality for Claude Code execution, messaging, logging, and error handling
"""

import os
import subprocess
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import time
import uuid

from utils.error_handlers import handle_error, ClaudeCodeError
from utils.structured_logger import get_logger
from utils.constants import (
    AgentType,
    CLAUDE_CODE_TIMEOUT,
    CLAUDE_CODE_TOOLS,
    WORKSPACE_DIR
)
from agents.messaging import AgentMessenger, AgentMessage


class BaseAgent(ABC):
    """
    Abstract base class for all AI agents
    
    Provides:
    - Claude Code CLI execution with error handling
    - Structured logging
    - Agent-to-agent messaging
    - Common utility methods
    """
    
    def __init__(
        self,
        agent_type: str,
        agent_id: Optional[str] = None,
        workspace_dir: Optional[Path] = None
    ):
        """
        Initialize base agent
        
        Args:
            agent_type: Type of agent (from AgentType constants)
            agent_id: Optional unique agent ID (auto-generated if not provided)
            workspace_dir: Optional workspace directory (defaults to WORKSPACE_DIR)
        """
        self.agent_type = agent_type
        self.agent_id = agent_id or str(uuid.uuid4())[:8]
        self.workspace_dir = workspace_dir or WORKSPACE_DIR
        
        # Initialize logger
        self.logger = get_logger(
            name=f"{agent_type}_{self.agent_id}",
            agent_type=agent_type
        )
        
        # Initialize messenger
        self.messenger = AgentMessenger(
            agent_id=self.agent_id,
            agent_type=agent_type
        )
        
        # Register message handlers
        self._register_message_handlers()
        
        # Current state
        self.current_project = None
        self.current_task = None
        self.is_busy = False
        self._is_healing = False  # recursion guard for self-healing
        
        self.logger.info(
            f"Agent initialized: {agent_type} ({self.agent_id})",
            extra={
                "agent_type": agent_type,
                "agent_id": self.agent_id,
                "workspace": str(self.workspace_dir)
            }
        )
    
    # ==========================================
    # ABSTRACT METHODS (must be implemented by subclasses)
    # ==========================================
    
    @abstractmethod
    async def execute_task(self, task: Dict) -> Dict:
        """
        Execute a specific task
        
        Args:
            task: Task dictionary with task details
        
        Returns:
            Result dictionary
        """
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """
        Get list of agent capabilities
        
        Returns:
            List of capability strings
        """
        pass
    
    # ==========================================
    # CLAUDE CODE EXECUTION
    # ==========================================
    
    async def _run_claude_subprocess(
        self,
        prompt: str,
        cwd: str,
        allowed_tools: Optional[List[str]] = None,
        timeout: int = CLAUDE_CODE_TIMEOUT,
    ) -> Dict[str, Any]:
        """
        Low-level subprocess executor for Claude Code.
        Raises ClaudeCodeError on failure or timeout.

        Returns:
            Dictionary with stdout, stderr, return_code, success, duration
        """
        start_time = time.time()

        # Build command
        cmd = ["claude", "-p", prompt]

        # Add allowed tools
        if allowed_tools:
            cmd.extend(["--allowedTools"] + allowed_tools)

        # Build subprocess env — strip CLAUDECODE so nested claude
        # sessions are not blocked by the parent session guard
        env = os.environ.copy()
        env.pop("CLAUDECODE", None)

        try:
            # Execute in a thread pool so the asyncio event loop stays free
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    cwd=cwd,
                    timeout=timeout,
                    env=env,
                ),
            )

            duration = time.time() - start_time
            result_dict = {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode,
                "success": result.returncode == 0,
                "duration": duration,
            }

            if not result_dict["success"]:
                error_output = result.stderr or result.stdout or "no output"
                raise ClaudeCodeError(f"Claude Code failed: {error_output}")

            return result_dict

        except subprocess.TimeoutExpired:
            raise ClaudeCodeError(f"Claude Code timeout after {timeout}s")

    async def _diagnose_and_fix(self, error_output: str, project_path: str):
        """
        Attempt to diagnose and fix a Claude Code failure before retrying.
        Calls Claude Code with a diagnosis prompt and applies the suggested fix.
        Skips healing for auth/permission errors and if already healing (guard).
        """
        if self._is_healing:
            return  # recursion guard — never heal a heal

        from utils.error_handlers import classify_claude_error
        error_type = classify_claude_error(error_output)

        # Don't try to heal auth or permission errors programmatically
        if error_type in ("auth_error", "permission"):
            return

        self._is_healing = True
        try:
            diagnosis_prompt = f"""
A Claude Code call failed with this error:
{error_output}

Error type: {error_type}

Diagnose what went wrong and fix it. Common fixes:
- import_error: run `pip install <package>` in the project directory
- file_not_found: create the missing file or directory
- generic: read the error carefully and apply the minimal fix needed

Apply the fix now. Do not explain — just fix it.
"""
            await self._run_claude_subprocess(
                prompt=diagnosis_prompt,
                cwd=project_path,
                allowed_tools=["Bash", "Write", "Edit", "Read"],
                timeout=120,
            )
            self.logger.info(
                f"Self-healing attempt completed for error type: {error_type}"
            )
        except Exception as e:
            self.logger.warning(f"Self-healing failed: {e}")
        finally:
            self._is_healing = False

    async def call_claude_code(
        self,
        prompt: str,
        project_path: Optional[str] = None,
        allowed_tools: Optional[List[str]] = None,
        context_files: Optional[List[str]] = None,
        timeout: int = CLAUDE_CODE_TIMEOUT
    ) -> Dict[str, Any]:
        """
        Execute Claude Code CLI with self-healing retry logic.

        On failure:
        1. Classify the error
        2. Attempt self-diagnosis and fix (unless already healing)
        3. Retry up to max_retries times with exponential backoff
        4. Raise ClaudeCodeError if all retries exhausted

        Args:
            prompt: Instruction for Claude Code
            project_path: Directory to execute in
            allowed_tools: Tools Claude Code can use
            context_files: Files to include in context
            timeout: Execution timeout in seconds

        Returns:
            Dictionary with stdout, stderr, return_code, success, duration
        """
        # Use agent-specific tools if not specified
        if allowed_tools is None:
            allowed_tools = CLAUDE_CODE_TOOLS.get(
                self.agent_type,
                ["Write", "Edit", "Read", "Bash"]
            )

        # Set working directory
        cwd = project_path or str(self.workspace_dir)

        self.logger.log_agent_action(
            agent_type=self.agent_type,
            action="claude_code_call",
            status="started",
            details={
                "prompt_preview": prompt[:200],
                "project_path": cwd,
                "allowed_tools": allowed_tools
            }
        )

        max_retries = 3
        last_error = None

        for attempt in range(max_retries):
            try:
                result = await self._run_claude_subprocess(
                    prompt=prompt,
                    cwd=cwd,
                    allowed_tools=allowed_tools,
                    timeout=timeout,
                )

                # Log success
                self.logger.log_claude_code_call(
                    prompt=prompt,
                    result=result,
                    duration=result["duration"],
                )
                self.logger.log_agent_action(
                    agent_type=self.agent_type,
                    action="claude_code_call",
                    status="completed",
                    details={
                        "duration": round(result["duration"], 2),
                        "return_code": result["return_code"],
                        "attempt": attempt + 1,
                    }
                )
                return result

            except ClaudeCodeError as e:
                last_error = e
                self.logger.warning(
                    f"Claude Code attempt {attempt + 1}/{max_retries} failed: "
                    f"{str(e)[:200]}"
                )

                # Attempt self-healing before retry (skipped if already healing)
                if not self._is_healing:
                    await self._diagnose_and_fix(str(e), cwd)

                if attempt < max_retries - 1:
                    delay = 2.0 * (2.0 ** attempt)  # 2s, 4s
                    await asyncio.sleep(delay)
                    continue

                # All retries exhausted
                self.logger.log_agent_action(
                    agent_type=self.agent_type,
                    action="claude_code_call",
                    status="failed",
                    details={
                        "attempts": max_retries,
                        "final_error": str(e)[:200],
                    }
                )
                raise

            except Exception as e:
                self.logger.error(
                    f"Claude Code execution failed: {str(e)}",
                    exc_info=True,
                )

                # Try to recover from unexpected errors
                recovery_result = await handle_error(e, {
                    "agent_type": self.agent_type,
                    "prompt": prompt[:200]
                })

                if recovery_result == "RETRY":
                    raise ClaudeCodeError(f"Retryable error: {str(e)}")

                raise

        raise last_error
    
    # ==========================================
    # MESSAGING
    # ==========================================
    
    def _register_message_handlers(self):
        """Register handlers for common message types"""
        self.messenger.register_handler("task_assignment", self._handle_task_assignment)
        self.messenger.register_handler("request_assistance", self._handle_assistance_request)
        self.messenger.register_handler("status_query", self._handle_status_query)
        self.messenger.register_handler("cancel_task", self._handle_cancel_task)
    
    async def _handle_task_assignment(self, message: AgentMessage):
        """Handle task assignment message"""
        self.logger.info(
            f"Received task assignment from {message.sender}",
            extra={"task": message.content}
        )
        
        if self.is_busy:
            # Send busy response
            await self.messenger.send_message(
                recipient=message.sender,
                message_type="status_update",
                content={
                    "status": "busy",
                    "current_task": self.current_task
                }
            )
            return
        
        # Mark as busy
        self.is_busy = True
        self.current_task = message.content
        
        try:
            # Execute the task
            result = await self.execute_task(message.content)
            
            # Notify completion
            await self.messenger.notify_completion(
                task_id=message.content.get("task_id", "unknown"),
                result=result,
                notify_agent=message.sender.split(":")[0]  # Extract agent type
            )
            
        except Exception as e:
            self.logger.error(f"Task execution failed: {str(e)}", exc_info=True)
            
            # Send error notification
            await self.messenger.send_message(
                recipient=message.sender,
                message_type="error_report",
                content={
                    "task_id": message.content.get("task_id"),
                    "error": str(e),
                    "agent": f"{self.agent_type}:{self.agent_id}"
                }
            )
        finally:
            self.is_busy = False
            self.current_task = None
    
    async def _handle_assistance_request(self, message: AgentMessage):
        """Handle request for assistance from another agent"""
        self.logger.info(
            f"Received assistance request from {message.sender}",
            extra={"problem": message.content.get("problem")}
        )
        
        # Subclasses can override this to provide assistance
        # Default: acknowledge but can't help
        await self.messenger.send_message(
            recipient=message.sender,
            message_type="information_share",
            content={
                "message": "Assistance request received but I cannot help with this",
                "agent": f"{self.agent_type}:{self.agent_id}"
            }
        )
    
    async def _handle_status_query(self, message: AgentMessage):
        """Handle status query from another agent"""
        status = {
            "agent_type": self.agent_type,
            "agent_id": self.agent_id,
            "is_busy": self.is_busy,
            "current_task": self.current_task,
            "current_project": self.current_project,
            "capabilities": self.get_capabilities()
        }
        
        await self.messenger.send_message(
            recipient=message.sender,
            message_type="status_update",
            content=status
        )
    
    async def _handle_cancel_task(self, message: AgentMessage):
        """Handle task cancellation request"""
        task_id = message.content.get("task_id")
        
        if self.current_task and self.current_task.get("task_id") == task_id:
            self.logger.info(f"Cancelling task: {task_id}")
            self.is_busy = False
            self.current_task = None
            
            await self.messenger.send_message(
                recipient=message.sender,
                message_type="status_update",
                content={"status": "cancelled", "task_id": task_id}
            )
    
    async def start_listening(self):
        """Start listening for messages"""
        self.logger.info(f"Agent {self.agent_type} started listening for messages")
        await self.messenger.start_listening()
    
    def stop_listening(self):
        """Stop listening for messages"""
        self.logger.info(f"Agent {self.agent_type} stopped listening")
        self.messenger.stop_listening()
    
    # ==========================================
    # UTILITY METHODS
    # ==========================================
    
    async def send_status_update(self, status: str, details: Dict = None):
        """
        Broadcast status update
        
        Args:
            status: Current status
            details: Additional details
        """
        await self.messenger.send_status_update(
            status=status,
            details=details or {}
        )
    
    async def request_help(self, from_agent: str, problem: str, context: Dict = None):
        """
        Request help from another agent
        
        Args:
            from_agent: Agent type to request help from
            problem: Description of problem
            context: Additional context
        """
        await self.messenger.request_assistance(
            from_agent=from_agent,
            problem=problem,
            context=context or {}
        )
    
    def get_project_path(self, project_name: str) -> Path:
        """
        Get full path for a project
        
        Args:
            project_name: Name of project
        
        Returns:
            Path to project
        """
        return self.workspace_dir / project_name
    
    async def create_project_directory(self, project_name: str) -> Path:
        """
        Create project directory structure
        
        Args:
            project_name: Name of project
        
        Returns:
            Path to created project
        """
        project_path = self.get_project_path(project_name)
        project_path.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(
            f"Created project directory: {project_name}",
            extra={"path": str(project_path)}
        )
        
        return project_path
    
    def get_status(self) -> Dict:
        """
        Get current agent status
        
        Returns:
            Status dictionary
        """
        return {
            "agent_type": self.agent_type,
            "agent_id": self.agent_id,
            "is_busy": self.is_busy,
            "current_task": self.current_task,
            "current_project": self.current_project,
            "capabilities": self.get_capabilities(),
            "timestamp": datetime.now().isoformat()
        }
    
    async def log_action(self, action: str, status: str, details: Dict = None):
        """
        Log an agent action
        
        Args:
            action: Action being performed
            status: Status of action
            details: Additional details
        """
        self.logger.log_agent_action(
            agent_type=self.agent_type,
            action=action,
            status=status,
            details=details or {}
        )
    
    def __repr__(self) -> str:
        """String representation of agent"""
        return f"{self.agent_type.title()}Agent({self.agent_id})"
