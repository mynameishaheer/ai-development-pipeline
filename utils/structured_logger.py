"""
Structured Logging System for AI Development Pipeline
Provides JSON-formatted logging for easier parsing and analysis
"""

import logging
import json
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
import traceback


class StructuredLogger:
    """
    Structured logger that outputs JSON-formatted logs
    Makes it easy to parse, search, and analyze logs programmatically
    """
    
    def __init__(
        self,
        name: str,
        log_file: Optional[Path] = None,
        level: str = "INFO",
        include_console: bool = True
    ):
        """
        Initialize structured logger
        
        Args:
            name: Logger name (usually agent name)
            log_file: Path to log file (optional)
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            include_console: Whether to also log to console
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))
        self.logger.handlers.clear()  # Clear any existing handlers
        
        # Create formatter
        self.formatter = CustomJsonFormatter()
        
        # Add file handler if log file specified
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(self.formatter)
            self.logger.addHandler(file_handler)
        
        # Add console handler if requested
        if include_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(self.formatter)
            self.logger.addHandler(console_handler)
    
    def _add_context(self, extra: Optional[Dict] = None) -> Dict:
        """Add default context to log entries"""
        context = {
            "timestamp": datetime.now().isoformat(),
            "pid": os.getpid(),
        }
        if extra:
            context.update(extra)
        return context
    
    def debug(self, message: str, extra: Optional[Dict] = None):
        """Log debug message"""
        self.logger.debug(message, extra=self._add_context(extra))
    
    def info(self, message: str, extra: Optional[Dict] = None):
        """Log info message"""
        self.logger.info(message, extra=self._add_context(extra))
    
    def warning(self, message: str, extra: Optional[Dict] = None):
        """Log warning message"""
        self.logger.warning(message, extra=self._add_context(extra))
    
    def error(self, message: str, extra: Optional[Dict] = None, exc_info: bool = False):
        """Log error message"""
        context = self._add_context(extra)
        if exc_info:
            context["traceback"] = traceback.format_exc()
        self.logger.error(message, extra=context)
    
    def critical(self, message: str, extra: Optional[Dict] = None, exc_info: bool = False):
        """Log critical message"""
        context = self._add_context(extra)
        if exc_info:
            context["traceback"] = traceback.format_exc()
        self.logger.critical(message, extra=context)
    
    def log_agent_action(
        self,
        agent_type: str,
        action: str,
        status: str,
        details: Optional[Dict] = None
    ):
        """
        Log an agent action with structured data
        
        Args:
            agent_type: Type of agent performing action
            action: Action being performed
            status: Status of action (started, completed, failed)
            details: Additional details about the action
        """
        extra = {
            "agent_type": agent_type,
            "action": action,
            "status": status,
            "details": details or {}
        }
        
        if status == "failed":
            self.error(f"Agent action failed: {action}", extra=extra)
        elif status == "completed":
            self.info(f"Agent action completed: {action}", extra=extra)
        else:
            self.info(f"Agent action {status}: {action}", extra=extra)
    
    def log_claude_code_call(
        self,
        prompt: str,
        result: Dict,
        duration: float
    ):
        """
        Log a Claude Code CLI call
        
        Args:
            prompt: The prompt sent to Claude Code
            result: Result dictionary from Claude Code
            duration: Execution duration in seconds
        """
        extra = {
            "prompt_preview": prompt[:200],  # First 200 chars
            "success": result.get("success", False),
            "return_code": result.get("return_code"),
            "duration_seconds": round(duration, 2),
            "output_length": len(result.get("stdout", "")),
            "error_length": len(result.get("stderr", ""))
        }
        
        if result.get("success"):
            self.info("Claude Code call succeeded", extra=extra)
        else:
            self.error("Claude Code call failed", extra=extra)
    
    def log_github_operation(
        self,
        operation: str,
        repo: str,
        status: str,
        details: Optional[Dict] = None
    ):
        """
        Log a GitHub operation
        
        Args:
            operation: Type of operation (create_repo, create_issue, etc.)
            repo: Repository name
            status: Operation status
            details: Additional details
        """
        extra = {
            "operation": operation,
            "repository": repo,
            "status": status,
            "details": details or {}
        }
        
        if status == "success":
            self.info(f"GitHub {operation} succeeded", extra=extra)
        else:
            self.error(f"GitHub {operation} failed", extra=extra)
    
    def log_task_lifecycle(
        self,
        task_id: str,
        task_type: str,
        phase: str,
        details: Optional[Dict] = None
    ):
        """
        Log task lifecycle events
        
        Args:
            task_id: Unique task identifier
            task_type: Type of task
            phase: Task phase (created, assigned, started, completed, failed)
            details: Additional task details
        """
        extra = {
            "task_id": task_id,
            "task_type": task_type,
            "phase": phase,
            "details": details or {}
        }
        
        self.info(f"Task {phase}: {task_type}", extra=extra)


class CustomJsonFormatter(logging.Formatter):
    """
    Custom JSON formatter that formats log records as JSON
    """
    
    def format(self, record):
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add extra fields if present
        if hasattr(record, 'timestamp'):
            log_data['timestamp'] = record.timestamp
        if hasattr(record, 'agent_type'):
            log_data['agent_type'] = record.agent_type
        if hasattr(record, 'action'):
            log_data['action'] = record.action
        if hasattr(record, 'status'):
            log_data['status'] = record.status
        if hasattr(record, 'details'):
            log_data['details'] = record.details
        if hasattr(record, 'traceback'):
            log_data['traceback'] = record.traceback
        if hasattr(record, 'pid'):
            log_data['pid'] = record.pid
        
        return json.dumps(log_data)


# ==========================================
# LOGGER FACTORY
# ==========================================

_loggers = {}  # Cache of created loggers


def get_logger(
    name: str,
    agent_type: Optional[str] = None,
    log_to_file: bool = True,
    log_level: str = "INFO"
) -> StructuredLogger:
    """
    Get or create a structured logger
    
    Args:
        name: Logger name
        agent_type: Agent type (for file naming)
        log_to_file: Whether to log to file
        log_level: Logging level
    
    Returns:
        StructuredLogger instance
    """
    # Use cached logger if exists
    if name in _loggers:
        return _loggers[name]
    
    # Determine log file path
    log_file = None
    if log_to_file:
        # Import constants (avoid circular import)
        try:
            from utils.constants import LOGS_DIR
        except ImportError:
            # Fallback if constants not available
            LOGS_DIR = Path(__file__).parent.parent / "logs"
            LOGS_DIR.mkdir(exist_ok=True)
        
        # Create log file name
        date_str = datetime.now().strftime("%Y%m%d")
        log_name = agent_type or name
        log_file = LOGS_DIR / f"{log_name}_{date_str}.log"
    
    # Create logger
    logger = StructuredLogger(
        name=name,
        log_file=log_file,
        level=log_level,
        include_console=True
    )
    
    # Cache it
    _loggers[name] = logger
    
    return logger


# ==========================================
# CONVENIENCE FUNCTIONS
# ==========================================

def log_info(message: str, **kwargs):
    """Quick info log"""
    logger = get_logger("default")
    logger.info(message, extra=kwargs)


def log_error(message: str, exc_info: bool = False, **kwargs):
    """Quick error log"""
    logger = get_logger("default")
    logger.error(message, extra=kwargs, exc_info=exc_info)


def log_warning(message: str, **kwargs):
    """Quick warning log"""
    logger = get_logger("default")
    logger.warning(message, extra=kwargs)


def log_debug(message: str, **kwargs):
    """Quick debug log"""
    logger = get_logger("default")
    logger.debug(message, extra=kwargs)


# ==========================================
# LOG ANALYSIS UTILITIES
# ==========================================

def parse_log_file(log_file: Path) -> list:
    """
    Parse a JSON log file and return entries
    
    Args:
        log_file: Path to log file
    
    Returns:
        List of parsed log entries
    """
    entries = []
    
    with open(log_file, 'r') as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                entries.append(entry)
            except json.JSONDecodeError:
                continue
    
    return entries


def filter_logs(
    entries: list,
    level: Optional[str] = None,
    agent_type: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None
) -> list:
    """
    Filter log entries by criteria
    
    Args:
        entries: List of log entries
        level: Filter by log level
        agent_type: Filter by agent type
        start_time: Filter by start time
        end_time: Filter by end time
    
    Returns:
        Filtered list of entries
    """
    filtered = entries
    
    if level:
        filtered = [e for e in filtered if e.get('level') == level]
    
    if agent_type:
        filtered = [e for e in filtered if e.get('agent_type') == agent_type]
    
    if start_time:
        filtered = [
            e for e in filtered
            if datetime.fromisoformat(e.get('timestamp', '')) >= start_time
        ]
    
    if end_time:
        filtered = [
            e for e in filtered
            if datetime.fromisoformat(e.get('timestamp', '')) <= end_time
        ]
    
    return filtered


def get_error_summary(log_file: Path) -> Dict:
    """
    Get summary of errors from a log file
    
    Args:
        log_file: Path to log file
    
    Returns:
        Dictionary with error summary
    """
    entries = parse_log_file(log_file)
    errors = filter_logs(entries, level='ERROR')
    
    error_types = {}
    for error in errors:
        error_type = error.get('message', 'Unknown')
        error_types[error_type] = error_types.get(error_type, 0) + 1
    
    return {
        'total_errors': len(errors),
        'error_types': error_types,
        'recent_errors': errors[-10:]  # Last 10 errors
    }


# ==========================================
# EXAMPLE USAGE
# ==========================================

if __name__ == "__main__":
    # Example: Create a logger for an agent
    logger = get_logger("example_agent", agent_type="backend")
    
    # Log various types of messages
    logger.info("Agent started", extra={"version": "2.0.0"})
    
    logger.log_agent_action(
        agent_type="backend",
        action="implement_api",
        status="started",
        details={"endpoint": "/api/users"}
    )
    
    logger.log_claude_code_call(
        prompt="Create a FastAPI endpoint for user management",
        result={"success": True, "return_code": 0, "stdout": "Created successfully"},
        duration=12.5
    )
    
    logger.log_github_operation(
        operation="create_pr",
        repo="test-repo",
        status="success",
        details={"pr_number": 42, "branch": "feature/user-management"}
    )
    
    logger.info("Agent completed work")
