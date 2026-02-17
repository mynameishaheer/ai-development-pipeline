"""
Shared Constants for AI Development Pipeline
Centralized configuration and constants used across all agents
"""

from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ==========================================
# DIRECTORY PATHS
# ==========================================

# Base project directory
BASE_DIR = Path(__file__).parent.parent
WORKSPACE_DIR = BASE_DIR / "projects"
LOGS_DIR = BASE_DIR / "logs"
MEMORY_DIR = BASE_DIR / "memory"
CONFIG_DIR = BASE_DIR / "config"
AGENTS_DIR = BASE_DIR / "agents"
DOCS_DIR = BASE_DIR / "docs"

# Ensure directories exist
for directory in [WORKSPACE_DIR, LOGS_DIR, MEMORY_DIR, CONFIG_DIR, DOCS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# ==========================================
# AGENT TYPES
# ==========================================

class AgentType:
    """Agent type identifiers"""
    MASTER = "master"
    PRODUCT_MANAGER = "product_manager"
    PROJECT_MANAGER = "project_manager"
    BACKEND = "backend"
    FRONTEND = "frontend"
    DESIGNER = "designer"
    DATABASE = "database"
    DEVOPS = "devops"
    QA = "qa"
    SECURITY = "security"
    DOCUMENTATION = "documentation"


# ==========================================
# AGENT PRIORITIES
# ==========================================

AGENT_PRIORITIES = {
    AgentType.MASTER: 0,  # Highest priority
    AgentType.PRODUCT_MANAGER: 1,
    AgentType.PROJECT_MANAGER: 2,
    AgentType.DESIGNER: 3,
    AgentType.DATABASE: 4,
    AgentType.BACKEND: 5,
    AgentType.FRONTEND: 6,
    AgentType.QA: 7,
    AgentType.DEVOPS: 8,
    AgentType.SECURITY: 9,
    AgentType.DOCUMENTATION: 10,
}

# ==========================================
# REDIS CONFIGURATION
# ==========================================

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))

# Redis channel names for agent communication
class RedisChannels:
    """Redis pub/sub channel names"""
    MASTER_COMMANDS = "agent:master:commands"
    AGENT_RESPONSES = "agent:responses"
    TASK_QUEUE = "agent:tasks"
    STATUS_UPDATES = "agent:status"
    ERROR_NOTIFICATIONS = "agent:errors"
    
    # Agent-specific channels
    PRODUCT_MANAGER = "agent:product_manager"
    PROJECT_MANAGER = "agent:project_manager"
    BACKEND = "agent:backend"
    FRONTEND = "agent:frontend"
    DESIGNER = "agent:designer"
    DATABASE = "agent:database"
    DEVOPS = "agent:devops"
    QA = "agent:qa"


# Redis queue names
class RedisQueues:
    """Redis queue names for task management"""
    GITHUB_REPO_CREATION = "queue:github:repo_creation"
    GITHUB_ISSUE_CREATION = "queue:github:issue_creation"
    GITHUB_PR_CREATION = "queue:github:pr_creation"
    GITHUB_PR_MERGE = "queue:github:pr_merge"
    CODE_REVIEW = "queue:code_review"
    DEPLOYMENT = "queue:deployment"
    TESTING = "queue:testing"


# ==========================================
# GITHUB CONFIGURATION
# ==========================================

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME", "mynameishaheer")
GITHUB_ORG = os.getenv("GITHUB_ORG")  # Optional, for organization repos

# GitHub API endpoints
GITHUB_API_BASE = "https://api.github.com"

# GitHub branch naming conventions
class GitHubBranches:
    """Standard branch names"""
    MAIN = "main"
    DEVELOPMENT = "dev"
    STAGING = "staging"
    
    # Feature branch prefix
    FEATURE_PREFIX = "feature/"
    BUGFIX_PREFIX = "bugfix/"
    HOTFIX_PREFIX = "hotfix/"
    RELEASE_PREFIX = "release/"


# ==========================================
# CLAUDE CODE CONFIGURATION
# ==========================================

# Claude Code CLI timeout (seconds)
CLAUDE_CODE_TIMEOUT = 300  # 5 minutes default

# Allowed tools for different agent types
CLAUDE_CODE_TOOLS = {
    AgentType.PRODUCT_MANAGER: ["Write", "Read"],
    AgentType.PROJECT_MANAGER: ["Write", "Read", "Bash"],
    AgentType.BACKEND: ["Write", "Edit", "Bash", "Read"],
    AgentType.FRONTEND: ["Write", "Edit", "Bash", "Read"],
    AgentType.DATABASE: ["Write", "Edit", "Bash", "Read"],
    AgentType.DEVOPS: ["Write", "Edit", "Bash", "Read"],
    AgentType.QA: ["Read", "Bash"],
    AgentType.DESIGNER: ["Write", "Read"],
}

# ==========================================
# LOGGING CONFIGURATION
# ==========================================

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "json"  # "json" or "text"

# Log file naming
LOG_FILE_PREFIX = "agent"
LOG_ROTATION_SIZE = 10 * 1024 * 1024  # 10MB
LOG_RETENTION_DAYS = 30

# ==========================================
# PROJECT CONFIGURATION
# ==========================================

# Default project structure template
DEFAULT_PROJECT_STRUCTURE = {
    "docs": ["README.md", "ARCHITECTURE.md", "API.md"],
    "src": [],
    "tests": [],
    ".github": ["workflows"],
}

# Default files to create in new projects
DEFAULT_PROJECT_FILES = [
    "README.md",
    ".gitignore",
    "PLAN.md",
    "CONTEXT.md",
    "ARCHITECTURE.md",
]

# ==========================================
# TASK CONFIGURATION
# ==========================================

class TaskStatus:
    """Task status values"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class TaskPriority:
    """Task priority levels"""
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3


# ==========================================
# RETRY CONFIGURATION
# ==========================================

# Default retry settings
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_BASE_DELAY = 1.0
DEFAULT_RETRY_MAX_DELAY = 60.0
DEFAULT_RETRY_EXPONENTIAL_BASE = 2.0

# GitHub API specific retries (more patient with rate limits)
GITHUB_MAX_RETRIES = 5
GITHUB_RETRY_BASE_DELAY = 60.0
GITHUB_RETRY_MAX_DELAY = 300.0

# ==========================================
# MESSAGE FORMATS
# ==========================================

class MessageType:
    """Message types for agent communication"""
    TASK_ASSIGNMENT = "task_assignment"
    STATUS_UPDATE = "status_update"
    ERROR_REPORT = "error_report"
    COMPLETION_NOTIFICATION = "completion_notification"
    REQUEST_ASSISTANCE = "request_assistance"
    INFORMATION_SHARE = "information_share"


# ==========================================
# CHROMADB CONFIGURATION
# ==========================================

CHROMADB_PATH = MEMORY_DIR / "vector_store"
CHROMADB_COLLECTION_PREFIX = "agent_memory"

# Memory categories
class MemoryCategory:
    """Memory storage categories"""
    USER_MESSAGE = "user_message"
    AGENT_RESPONSE = "agent_response"
    PROJECT_CONTEXT = "project_context"
    CODE_SNIPPET = "code_snippet"
    ERROR_LOG = "error_log"
    DECISION_RECORD = "decision_record"
    LEARNING = "learning"


# ==========================================
# FILE PATTERNS
# ==========================================

# Gitignore patterns for new projects
DEFAULT_GITIGNORE_PATTERNS = [
    "# Python",
    "__pycache__/",
    "*.py[cod]",
    "*$py.class",
    "*.so",
    ".Python",
    "build/",
    "develop-eggs/",
    "dist/",
    "downloads/",
    "eggs/",
    ".eggs/",
    "lib/",
    "lib64/",
    "parts/",
    "sdist/",
    "var/",
    "wheels/",
    "*.egg-info/",
    ".installed.cfg",
    "*.egg",
    "",
    "# Virtual Environment",
    "venv/",
    "ENV/",
    "env/",
    "",
    "# IDE",
    ".vscode/",
    ".idea/",
    "*.swp",
    "*.swo",
    "*~",
    "",
    "# Environment",
    ".env",
    ".env.local",
    "",
    "# Node",
    "node_modules/",
    "npm-debug.log*",
    "yarn-debug.log*",
    "yarn-error.log*",
    "",
    "# Build",
    "*.log",
    "dist/",
    "build/",
    "",
    "# OS",
    ".DS_Store",
    "Thumbs.db",
]

# ==========================================
# SUPABASE CONFIGURATION
# ==========================================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# ==========================================
# DEPLOYMENT CONFIGURATION
# ==========================================

# Deployment environments
class DeploymentEnvironment:
    """Deployment environment identifiers"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


# Default deployment ports
DEFAULT_BACKEND_PORT = 8000
DEFAULT_FRONTEND_PORT = 3000

# ==========================================
# TESTING CONFIGURATION
# ==========================================

# Test coverage threshold
MIN_TEST_COVERAGE = 80  # Percentage

# Test types
class TestType:
    """Test type identifiers"""
    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"
    PERFORMANCE = "performance"
    SECURITY = "security"


# ==========================================
# SECURITY CONFIGURATION
# ==========================================

# Security scan types
class SecurityScanType:
    """Security scan identifiers"""
    DEPENDENCY_SCAN = "dependency_scan"
    CODE_SCAN = "code_scan"
    SECRET_SCAN = "secret_scan"
    CONTAINER_SCAN = "container_scan"


# ==========================================
# NOTIFICATION CONFIGURATION
# ==========================================

# Discord webhook (if configured)
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# Notification types
class NotificationType:
    """Notification type identifiers"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"
    CRITICAL = "critical"


# ==========================================
# VERSION INFORMATION
# ==========================================

PIPELINE_VERSION = "2.0.0"  # Phase 2
API_VERSION = "v1"

# ==========================================
# HELPER FUNCTIONS
# ==========================================

def get_agent_channel(agent_type: str) -> str:
    """Get Redis channel name for a specific agent type"""
    return f"agent:{agent_type}"


def get_project_path(project_name: str) -> Path:
    """Get full path for a project"""
    return WORKSPACE_DIR / project_name


def get_log_path(log_name: str, date_suffix: bool = True) -> Path:
    """Get full path for a log file"""
    from datetime import datetime
    
    if date_suffix:
        date_str = datetime.now().strftime("%Y%m%d")
        filename = f"{log_name}_{date_str}.log"
    else:
        filename = f"{log_name}.log"
    
    return LOGS_DIR / filename


def validate_config() -> bool:
    """
    Validate that all required configuration is present
    
    Returns:
        True if configuration is valid, False otherwise
    """
    errors = []
    
    # Check required environment variables
    if not GITHUB_TOKEN:
        errors.append("GITHUB_TOKEN not set in .env")
    
    # Check required directories
    required_dirs = [WORKSPACE_DIR, LOGS_DIR, MEMORY_DIR]
    for directory in required_dirs:
        if not directory.exists():
            errors.append(f"Required directory missing: {directory}")
    
    if errors:
        print("❌ Configuration Errors:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    return True


# ==========================================
# AGENT CAPABILITIES
# ==========================================

AGENT_CAPABILITIES = {
    AgentType.PRODUCT_MANAGER: [
        "Create PRD",
        "Define user stories",
        "Prioritize features",
        "Clarify requirements",
    ],
    AgentType.PROJECT_MANAGER: [
        "Create GitHub repository",
        "Create GitHub issues",
        "Manage sprints",
        "Merge pull requests",
        "Track progress",
    ],
    AgentType.BACKEND: [
        "Implement APIs",
        "Write server-side logic",
        "Create database models",
        "Write tests",
        "Create feature branches",
        "Submit pull requests",
    ],
    AgentType.FRONTEND: [
        "Build UI components",
        "Implement client logic",
        "Write tests",
        "Create feature branches",
        "Submit pull requests",
    ],
    AgentType.DATABASE: [
        "Design schemas",
        "Create migrations",
        "Optimize queries",
        "Manage backups",
    ],
    AgentType.DEVOPS: [
        "Set up CI/CD",
        "Configure deployments",
        "Manage infrastructure",
        "Monitor systems",
    ],
    AgentType.QA: [
        "Run automated tests",
        "Validate PRs",
        "Report bugs",
        "Approve deployments",
    ],
}
