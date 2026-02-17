"""
Error Handling Utilities for AI Development Pipeline
Provides retry logic, exponential backoff, and error recovery mechanisms
"""

import asyncio
import functools
import logging
from typing import Callable, Any, Optional, Type
from datetime import datetime
import traceback


class AgentError(Exception):
    """Base exception for agent-related errors"""
    pass


class ClaudeCodeError(AgentError):
    """Errors related to Claude Code CLI execution"""
    pass


class GitHubAPIError(AgentError):
    """Errors related to GitHub API calls"""
    pass


class AgentCommunicationError(AgentError):
    """Errors related to agent-to-agent communication"""
    pass


class RetryableError(AgentError):
    """Errors that should trigger a retry"""
    pass


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator that retries a function with exponential backoff
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries (seconds)
        max_delay: Maximum delay between retries (seconds)
        exponential_base: Base for exponential backoff calculation
        exceptions: Tuple of exceptions to catch and retry
    
    Example:
        @retry_with_backoff(max_retries=3, base_delay=1.0)
        async def unstable_function():
            # This will retry up to 3 times with exponential backoff
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    # Try to execute the function
                    if asyncio.iscoroutinefunction(func):
                        result = await func(*args, **kwargs)
                    else:
                        result = func(*args, **kwargs)
                    
                    # Success - return result
                    if attempt > 0:
                        logging.info(
                            f"✅ {func.__name__} succeeded on attempt {attempt + 1}"
                        )
                    return result
                    
                except exceptions as e:
                    last_exception = e
                    
                    # If this was the last attempt, raise the exception
                    if attempt == max_retries:
                        logging.error(
                            f"❌ {func.__name__} failed after {max_retries + 1} attempts: {str(e)}"
                        )
                        raise
                    
                    # Calculate delay with exponential backoff
                    delay = min(
                        base_delay * (exponential_base ** attempt),
                        max_delay
                    )
                    
                    logging.warning(
                        f"⚠️  {func.__name__} attempt {attempt + 1} failed: {str(e)}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    
                    # Wait before retrying
                    await asyncio.sleep(delay)
            
            # Should never reach here, but just in case
            raise last_exception
        
        return wrapper
    return decorator


def retry_on_rate_limit(
    max_retries: int = 5,
    base_delay: float = 60.0
):
    """
    Specialized retry decorator for GitHub API rate limiting
    Waits longer and has more retries than standard retry
    
    Args:
        max_retries: Maximum number of retry attempts (default 5)
        base_delay: Base delay for rate limit errors (default 60s)
    """
    return retry_with_backoff(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=300.0,  # Max 5 minutes
        exponential_base=1.5,
        exceptions=(GitHubAPIError,)
    )


async def safe_execute(
    func: Callable,
    *args,
    error_message: str = "Operation failed",
    default_return: Any = None,
    log_traceback: bool = True,
    **kwargs
) -> Any:
    """
    Safely execute a function and handle any errors gracefully
    
    Args:
        func: Function to execute
        *args: Positional arguments for func
        error_message: Custom error message to log
        default_return: Value to return if execution fails
        log_traceback: Whether to log full traceback on error
        **kwargs: Keyword arguments for func
    
    Returns:
        Function result or default_return on error
    """
    try:
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            return func(*args, **kwargs)
    except Exception as e:
        logging.error(f"❌ {error_message}: {str(e)}")
        
        if log_traceback:
            logging.error(f"Traceback: {traceback.format_exc()}")
        
        return default_return


class ErrorRecoveryManager:
    """
    Manages error recovery strategies for different types of failures
    """
    
    def __init__(self):
        self.error_history = []
        self.recovery_strategies = {
            ClaudeCodeError: self._recover_claude_code_error,
            GitHubAPIError: self._recover_github_error,
            AgentCommunicationError: self._recover_communication_error,
        }
    
    async def handle_error(
        self,
        error: Exception,
        context: dict
    ) -> Optional[Any]:
        """
        Handle an error and attempt recovery
        
        Args:
            error: The exception that occurred
            context: Context information about the error
        
        Returns:
            Recovery result or None if recovery failed
        """
        # Log the error
        self._log_error(error, context)
        
        # Find appropriate recovery strategy
        error_type = type(error)
        recovery_func = self.recovery_strategies.get(error_type)
        
        if recovery_func:
            logging.info(f"🔧 Attempting recovery for {error_type.__name__}...")
            return await recovery_func(error, context)
        else:
            logging.warning(f"⚠️  No recovery strategy for {error_type.__name__}")
            return None
    
    def _log_error(self, error: Exception, context: dict):
        """Log error to history"""
        self.error_history.append({
            "timestamp": datetime.now().isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context,
            "traceback": traceback.format_exc()
        })
        
        # Keep only last 100 errors
        if len(self.error_history) > 100:
            self.error_history = self.error_history[-100:]
    
    async def _recover_claude_code_error(
        self,
        error: ClaudeCodeError,
        context: dict
    ) -> Optional[Any]:
        """
        Recover from Claude Code execution errors
        
        Strategies:
        1. Check if Claude Code is authenticated
        2. Verify file permissions
        3. Retry with simpler prompt
        """
        logging.info("🔧 Attempting Claude Code error recovery...")
        
        # Strategy 1: Check authentication
        import subprocess
        try:
            result = subprocess.run(
                ["claude", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                logging.error("❌ Claude Code not properly authenticated")
                return None
        except Exception as e:
            logging.error(f"❌ Claude Code check failed: {e}")
            return None
        
        # Strategy 2: Could retry with simplified prompt
        # This would be implemented by the calling agent
        
        return None
    
    async def _recover_github_error(
        self,
        error: GitHubAPIError,
        context: dict
    ) -> Optional[Any]:
        """
        Recover from GitHub API errors
        
        Strategies:
        1. Check if it's a rate limit error -> wait and retry
        2. Check if it's an authentication error -> validate token
        3. Check if resource already exists -> return existing
        """
        error_msg = str(error).lower()
        
        # Rate limit error
        if "rate limit" in error_msg or "429" in error_msg:
            logging.info("🔧 Rate limit detected, waiting 60 seconds...")
            await asyncio.sleep(60)
            return "RETRY"
        
        # Resource already exists
        if "already exists" in error_msg:
            logging.info("ℹ️  Resource already exists, continuing...")
            return "EXISTS"
        
        # Authentication error
        if "401" in error_msg or "authentication" in error_msg:
            logging.error("❌ GitHub authentication failed - check token")
            return None
        
        return None
    
    async def _recover_communication_error(
        self,
        error: AgentCommunicationError,
        context: dict
    ) -> Optional[Any]:
        """
        Recover from agent communication errors
        
        Strategies:
        1. Check if Redis is running
        2. Retry message send
        3. Use alternative communication channel
        """
        logging.info("🔧 Checking Redis connection...")
        
        import redis
        try:
            r = redis.Redis(host='localhost', port=6379, decode_responses=True)
            r.ping()
            logging.info("✅ Redis is responsive")
            return "RETRY"
        except Exception as e:
            logging.error(f"❌ Redis connection failed: {e}")
            return None
    
    def get_error_summary(self) -> dict:
        """Get summary of recent errors"""
        if not self.error_history:
            return {"total_errors": 0, "error_types": {}}
        
        error_types = {}
        for error in self.error_history:
            error_type = error["error_type"]
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        return {
            "total_errors": len(self.error_history),
            "error_types": error_types,
            "recent_errors": self.error_history[-5:]  # Last 5 errors
        }


# Global error recovery manager instance
error_recovery_manager = ErrorRecoveryManager()


# Utility function for quick error handling
async def handle_error(error: Exception, context: dict = None) -> Optional[Any]:
    """
    Quick utility to handle errors through the global recovery manager
    
    Args:
        error: The exception to handle
        context: Optional context information
    
    Returns:
        Recovery result or None
    """
    return await error_recovery_manager.handle_error(
        error,
        context or {}
    )
