"""
Base Agent Class for AI Development Pipeline
Abstract base class that all sub-agents inherit from
Provides common functionality for Claude Code execution, messaging, logging, and error handling
"""

import subprocess
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import time
import uuid

from utils.error_handlers import retry_with_backoff, handle_error, ClaudeCodeError
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
    
    @retry_with_backoff(max_retries=3, base_delay=2.0, exceptions=(ClaudeCodeError,))
    async def call_claude_code(
        self,
        prompt: str,
        project_path: Optional[str] = None,
        allowed_tools: Optional[List[str]] = None,
        context_files: Optional[List[str]] = None,
        timeout: int = CLAUDE_CODE_TIMEOUT
    ) -> Dict[str, Any]:
        """
        Execute Claude Code CLI with error handling and retry logic
        
        Args:
            prompt: Instruction for Claude Code
            project_path: Directory to execute in
            allowed_tools: Tools Claude Code can use
            context_files: Files to include in context
            timeout: Execution timeout in seconds
        
        Returns:
            Dictionary with stdout, stderr, return_code, success
        """
        start_time = time.time()
        
        # Use agent-specific tools if not specified
        if allowed_tools is None:
            allowed_tools = CLAUDE_CODE_TOOLS.get(
                self.agent_type,
                ["Write", "Edit", "Read", "Bash"]
            )
        
        # Build command
        cmd = ["claude", "-p", prompt]
        
        # Add allowed tools
        if allowed_tools:
            cmd.extend(["--allowedTools"] + allowed_tools)
        
        # Add context files
        if context_files:
            for file in context_files:
                cmd.extend(["--context", file])
        
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
        
        try:
            # Execute Claude Code
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=timeout
            )
            
            duration = time.time() - start_time
            
            # Prepare result
            result_dict = {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode,
                "success": result.returncode == 0,
                "duration": duration
            }
            
            # Log the result
            self.logger.log_claude_code_call(
                prompt=prompt,
                result=result_dict,
                duration=duration
            )
            
            # Log action completion
            self.logger.log_agent_action(
                agent_type=self.agent_type,
                action="claude_code_call",
                status="completed" if result_dict["success"] else "failed",
                details={
                    "duration": round(duration, 2),
                    "return_code": result.returncode
                }
            )
            
            # Raise error if failed
            if not result_dict["success"]:
                raise ClaudeCodeError(f"Claude Code failed: {result.stderr}")
            
            return result_dict
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            
            error_msg = f"Claude Code timeout after {timeout}s"
            self.logger.error(error_msg, extra={"duration": duration})
            
            raise ClaudeCodeError(error_msg)
            
        except Exception as e:
            duration = time.time() - start_time
            
            self.logger.error(
                f"Claude Code execution failed: {str(e)}",
                exc_info=True,
                extra={"duration": duration}
            )
            
            # Try to recover from error
            recovery_result = await handle_error(e, {
                "agent_type": self.agent_type,
                "prompt": prompt[:200]
            })
            
            if recovery_result == "RETRY":
                # Error handler suggests retry
                raise ClaudeCodeError(f"Retryable error: {str(e)}")
            
            raise
    
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
