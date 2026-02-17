#!/bin/bash

# AI Development Pipeline - System Health Check Script
# Purpose: Verify all components are operational
# Usage: ./scripts/health_check.sh

echo "🔍 AI Development Pipeline - System Health Check"
echo "=================================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0
WARNINGS=0

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
        ((PASSED++))
    else
        echo -e "${RED}❌ $2${NC}"
        ((FAILED++))
    fi
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
    ((WARNINGS++))
}

echo "1️⃣  Checking System Dependencies"
echo "--------------------------------"

# Check Claude Code CLI
echo -n "Claude Code CLI: "
if command -v claude &> /dev/null; then
    VERSION=$(claude --version 2>&1 | head -n 1)
    echo -e "${GREEN}✅ Installed ($VERSION)${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ Not found${NC}"
    echo "   Install: curl -fsSL https://claude.ai/install.sh | sh"
    ((FAILED++))
fi

# Check Node.js
echo -n "Node.js: "
if command -v node &> /dev/null; then
    VERSION=$(node --version)
    echo -e "${GREEN}✅ Installed ($VERSION)${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ Not found${NC}"
    ((FAILED++))
fi

# Check Python
echo -n "Python: "
if command -v python3 &> /dev/null; then
    VERSION=$(python3 --version)
    echo -e "${GREEN}✅ Installed ($VERSION)${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ Not found${NC}"
    ((FAILED++))
fi

# Check Docker
echo -n "Docker: "
if command -v docker &> /dev/null; then
    VERSION=$(docker --version)
    echo -e "${GREEN}✅ Installed ($VERSION)${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ Not found${NC}"
    ((FAILED++))
fi

# Check Git
echo -n "Git: "
if command -v git &> /dev/null; then
    VERSION=$(git --version)
    echo -e "${GREEN}✅ Installed ($VERSION)${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ Not found${NC}"
    ((FAILED++))
fi

echo ""
echo "2️⃣  Checking Services"
echo "--------------------"

# Check Redis
echo -n "Redis Server: "
if redis-cli ping &> /dev/null; then
    echo -e "${GREEN}✅ Running (responds to PING)${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ Not running or not responding${NC}"
    echo "   Start: sudo systemctl start redis-server"
    ((FAILED++))
fi

echo ""
echo "3️⃣  Checking Python Environment"
echo "-------------------------------"

# Check if virtual environment exists
echo -n "Virtual Environment: "
if [ -d "venv" ]; then
    echo -e "${GREEN}✅ Exists${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ Not found${NC}"
    echo "   Create: python3 -m venv venv"
    ((FAILED++))
fi

# Check if virtual environment is activated
echo -n "Virtual Env Active: "
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo -e "${GREEN}✅ Activated ($VIRTUAL_ENV)${NC}"
    ((PASSED++))
else
    echo -e "${YELLOW}⚠️  Not activated${NC}"
    echo "   Activate: source venv/bin/activate"
    ((WARNINGS++))
fi

# Check Python packages (only if venv is activated)
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo -n "Python Packages: "
    MISSING_PACKAGES=()
    
    for package in fastapi uvicorn discord.py chromadb redis python-dotenv aiohttp; do
        if ! pip show ${package} &> /dev/null; then
            MISSING_PACKAGES+=($package)
        fi
    done
    
    if [ ${#MISSING_PACKAGES[@]} -eq 0 ]; then
        echo -e "${GREEN}✅ All required packages installed${NC}"
        ((PASSED++))
    else
        echo -e "${RED}❌ Missing packages: ${MISSING_PACKAGES[*]}${NC}"
        echo "   Install: pip install -r requirements.txt"
        ((FAILED++))
    fi
fi

echo ""
echo "4️⃣  Checking Project Files"
echo "-------------------------"

# Check critical files
FILES=(
    "agents/master_agent.py:Master Agent"
    "api/discord_bot.py:Discord Bot"
    "requirements.txt:Requirements"
    ".env:Environment Config"
    ".gitignore:Git Ignore"
    "README.md:README"
)

for item in "${FILES[@]}"; do
    IFS=':' read -r file name <<< "$item"
    echo -n "$name: "
    if [ -f "$file" ]; then
        echo -e "${GREEN}✅ Exists${NC}"
        ((PASSED++))
    else
        echo -e "${RED}❌ Missing ($file)${NC}"
        ((FAILED++))
    fi
done

echo ""
echo "5️⃣  Checking Directories"
echo "-----------------------"

# Check critical directories
DIRS=(
    "agents:Agents"
    "api:API"
    "logs:Logs"
    "projects:Projects"
    "memory:Memory"
    "config:Config"
    "scripts:Scripts"
    "docs:Documentation"
)

for item in "${DIRS[@]}"; do
    IFS=':' read -r dir name <<< "$item"
    echo -n "$name: "
    if [ -d "$dir" ]; then
        COUNT=$(ls -1 "$dir" 2>/dev/null | wc -l)
        echo -e "${GREEN}✅ Exists ($COUNT items)${NC}"
        ((PASSED++))
    else
        echo -e "${RED}❌ Missing ($dir)${NC}"
        ((FAILED++))
    fi
done

echo ""
echo "6️⃣  Checking Configuration"
echo "-------------------------"

# Check .env file contents
if [ -f ".env" ]; then
    echo -n "Discord Bot Token: "
    if grep -q "DISCORD_BOT_TOKEN=." .env 2>/dev/null; then
        echo -e "${GREEN}✅ Set${NC}"
        ((PASSED++))
    else
        echo -e "${RED}❌ Not set or empty${NC}"
        ((FAILED++))
    fi
    
    echo -n "GitHub Token: "
    if grep -q "GITHUB_TOKEN=." .env 2>/dev/null; then
        echo -e "${GREEN}✅ Set${NC}"
        ((PASSED++))
    else
        echo -e "${YELLOW}⚠️  Not set (required for Phase 2)${NC}"
        ((WARNINGS++))
    fi
else
    echo -e "${RED}❌ .env file not found${NC}"
    ((FAILED++))
fi

echo ""
echo "7️⃣  Checking Git Repository"
echo "--------------------------"

# Check if git repo exists
echo -n "Git Repository: "
if [ -d ".git" ]; then
    echo -e "${GREEN}✅ Initialized${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ Not initialized${NC}"
    ((FAILED++))
fi

# Check git status
if [ -d ".git" ]; then
    echo -n "Git Remote: "
    if git remote -v &> /dev/null; then
        REMOTE=$(git remote get-url origin 2>/dev/null)
        if [ ! -z "$REMOTE" ]; then
            echo -e "${GREEN}✅ Configured ($REMOTE)${NC}"
            ((PASSED++))
        else
            echo -e "${YELLOW}⚠️  No remote configured${NC}"
            ((WARNINGS++))
        fi
    else
        echo -e "${YELLOW}⚠️  No remote configured${NC}"
        ((WARNINGS++))
    fi
    
    echo -n "Git Branch: "
    BRANCH=$(git branch --show-current 2>/dev/null)
    if [ ! -z "$BRANCH" ]; then
        echo -e "${GREEN}✅ On branch '$BRANCH'${NC}"
        ((PASSED++))
    else
        echo -e "${YELLOW}⚠️  No branch${NC}"
        ((WARNINGS++))
    fi
    
    echo -n "Uncommitted Changes: "
    if git diff --quiet && git diff --cached --quiet; then
        echo -e "${GREEN}✅ Clean working directory${NC}"
        ((PASSED++))
    else
        echo -e "${YELLOW}⚠️  You have uncommitted changes${NC}"
        ((WARNINGS++))
    fi
fi

echo ""
echo "8️⃣  Checking System Resources"
echo "----------------------------"

# Check disk space
echo -n "Disk Space: "
DISK_USAGE=$(df -h . | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $DISK_USAGE -lt 80 ]; then
    echo -e "${GREEN}✅ Available ($DISK_USAGE% used)${NC}"
    ((PASSED++))
elif [ $DISK_USAGE -lt 90 ]; then
    echo -e "${YELLOW}⚠️  Running low ($DISK_USAGE% used)${NC}"
    ((WARNINGS++))
else
    echo -e "${RED}❌ Critical ($DISK_USAGE% used)${NC}"
    ((FAILED++))
fi

# Check memory
echo -n "Memory: "
MEM_AVAILABLE=$(free -m | awk 'NR==2 {print $7}')
if [ $MEM_AVAILABLE -gt 500 ]; then
    echo -e "${GREEN}✅ Available (${MEM_AVAILABLE}MB free)${NC}"
    ((PASSED++))
elif [ $MEM_AVAILABLE -gt 200 ]; then
    echo -e "${YELLOW}⚠️  Running low (${MEM_AVAILABLE}MB free)${NC}"
    ((WARNINGS++))
else
    echo -e "${RED}❌ Critical (${MEM_AVAILABLE}MB free)${NC}"
    ((FAILED++))
fi

echo ""
echo "9️⃣  Testing Functionality"
echo "------------------------"

# Test Master Agent import (only if venv is active)
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo -n "Master Agent Import: "
    if python -c "from agents.master_agent import MasterAgent" 2>/dev/null; then
        echo -e "${GREEN}✅ Can import successfully${NC}"
        ((PASSED++))
    else
        echo -e "${RED}❌ Import failed${NC}"
        ((FAILED++))
    fi
fi

# Check if Discord bot process is running
echo -n "Discord Bot Process: "
if pgrep -f "discord_bot.py" > /dev/null; then
    PID=$(pgrep -f "discord_bot.py")
    echo -e "${GREEN}✅ Running (PID: $PID)${NC}"
    ((PASSED++))
else
    echo -e "${YELLOW}⚠️  Not running${NC}"
    echo "   Start: python api/discord_bot.py"
    ((WARNINGS++))
fi

# Check recent logs
echo -n "Recent Logs: "
LOG_FILE="logs/claude_code_$(date +%Y%m%d).log"
if [ -f "$LOG_FILE" ]; then
    LOG_SIZE=$(du -h "$LOG_FILE" | cut -f1)
    echo -e "${GREEN}✅ Exists ($LOG_SIZE)${NC}"
    ((PASSED++))
else
    echo -e "${YELLOW}⚠️  No logs for today${NC}"
    ((WARNINGS++))
fi

echo ""
echo "=================================================="
echo "📊 Health Check Summary"
echo "=================================================="
echo ""
echo -e "${GREEN}✅ Passed: $PASSED${NC}"
echo -e "${YELLOW}⚠️  Warnings: $WARNINGS${NC}"
echo -e "${RED}❌ Failed: $FAILED${NC}"
echo ""

# Overall status
if [ $FAILED -eq 0 ]; then
    if [ $WARNINGS -eq 0 ]; then
        echo -e "${GREEN}🎉 System Status: EXCELLENT - All checks passed!${NC}"
        exit 0
    else
        echo -e "${YELLOW}✅ System Status: GOOD - Minor warnings, but operational${NC}"
        exit 0
    fi
elif [ $FAILED -le 2 ]; then
    echo -e "${YELLOW}⚠️  System Status: DEGRADED - Some components need attention${NC}"
    exit 1
else
    echo -e "${RED}❌ System Status: CRITICAL - Multiple failures detected${NC}"
    exit 2
fi
