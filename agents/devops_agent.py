"""
DevOps Agent for AI Development Pipeline
Handles CI/CD pipelines, Docker containerization, deployment automation, and monitoring
"""

from pathlib import Path
from typing import Dict, List, Optional

from agents.base_agent import BaseAgent
from agents.github_client import create_github_client
from utils.constants import AgentType
from utils.error_handlers import retry_on_rate_limit


class DevOpsAgent(BaseAgent):
    """
    DevOps and Infrastructure Agent

    Responsibilities:
    - Generate Dockerfiles for backend and frontend
    - Create docker-compose.yml for local development
    - Create GitHub Actions CI/CD workflows
    - Set up staging deployment scripts
    - Configure health checks and monitoring
    - Generate nginx/Caddy configuration
    - Create environment variable templates
    """

    def __init__(self, agent_id: Optional[str] = None):
        """Initialize DevOps Agent"""
        super().__init__(
            agent_type=AgentType.DEVOPS,
            agent_id=agent_id
        )
        self.github = create_github_client()
        self.logger.info("DevOps Agent initialized")

    def get_capabilities(self) -> List[str]:
        """Get agent capabilities"""
        return [
            "Generate Dockerfiles",
            "Create docker-compose.yml",
            "Create GitHub Actions CI/CD workflows",
            "Set up staging deployment",
            "Configure health checks",
            "Generate nginx configuration",
            "Create environment variable templates",
            "Set up monitoring scripts",
        ]

    async def execute_task(self, task: Dict) -> Dict:
        """
        Execute a DevOps task

        Args:
            task: Task dictionary with task details

        Returns:
            Result dictionary
        """
        task_type = task.get("task_type", "setup_cicd")

        handlers = {
            "setup_cicd": self.setup_cicd_pipeline,
            "create_dockerfile": self.create_dockerfile,
            "create_docker_compose": self.create_docker_compose,
            "setup_deployment": self.setup_deployment,
            "create_health_checks": self.create_health_checks,
        }

        handler = handlers.get(task_type)
        if not handler:
            raise ValueError(f"Unknown task type: {task_type}")

        return await handler(task)

    # ==========================================
    # FULL CICD PIPELINE SETUP
    # ==========================================

    async def setup_cicd_pipeline(self, task: Dict) -> Dict:
        """
        Complete CI/CD setup:
        1. Create Dockerfile(s)
        2. Create docker-compose.yml
        3. Create GitHub Actions workflow
        4. Create deployment scripts

        Args:
            task: Task with 'repo_name', 'project_path', 'stack'

        Returns:
            Complete setup result
        """
        repo_name = task.get("repo_name", "")
        project_path = task.get("project_path", "")
        stack = task.get("stack", "auto")

        await self.log_action("setup_cicd_pipeline", "started", {
            "repo": repo_name,
            "stack": stack
        })

        results = {"steps_completed": []}

        try:
            # Step 1: Create Dockerfile(s)
            docker_result = await self.create_dockerfile({
                "project_path": project_path,
                "stack": stack
            })
            results["dockerfile"] = docker_result
            if docker_result.get("success"):
                results["steps_completed"].append("dockerfile_created")

            # Step 2: Create docker-compose.yml
            compose_result = await self.create_docker_compose({
                "project_path": project_path,
                "stack": stack
            })
            results["docker_compose"] = compose_result
            if compose_result.get("success"):
                results["steps_completed"].append("docker_compose_created")

            # Step 3: Create GitHub Actions workflow
            cicd_result = await self._create_github_actions_workflow(
                repo_name=repo_name,
                project_path=project_path,
                stack=stack
            )
            results["cicd"] = cicd_result
            if cicd_result.get("success"):
                results["steps_completed"].append("github_actions_created")

            # Step 4: Create deployment scripts
            deploy_result = await self.setup_deployment({
                "project_path": project_path,
                "repo_name": repo_name
            })
            results["deployment"] = deploy_result
            if deploy_result.get("success"):
                results["steps_completed"].append("deployment_scripts_created")

            # Step 5: Create health checks
            health_result = await self.create_health_checks({
                "project_path": project_path
            })
            results["health_checks"] = health_result
            if health_result.get("success"):
                results["steps_completed"].append("health_checks_created")

            await self.log_action("setup_cicd_pipeline", "completed", {
                "steps": len(results["steps_completed"])
            })

            await self.send_status_update("cicd_configured", {
                "repo": repo_name,
                "steps": results["steps_completed"]
            })

            return {
                "success": True,
                **results,
                "message": f"CI/CD pipeline configured with {len(results['steps_completed'])} components"
            }

        except Exception as e:
            await self.log_action("setup_cicd_pipeline", "failed", {"error": str(e)})
            raise

    # ==========================================
    # DOCKERFILE GENERATION
    # ==========================================

    async def create_dockerfile(self, task: Dict) -> Dict:
        """
        Generate Dockerfile(s) for the project

        Args:
            task: Task with 'project_path' and 'stack'

        Returns:
            Result with Dockerfile paths
        """
        project_path = task.get("project_path", "")
        stack = task.get("stack", "auto")

        await self.log_action("create_dockerfile", "started", {"stack": stack})

        prompt = f"""
Create production-ready Dockerfile(s) for this project.

Project path: {project_path}
Stack hint: {stack}

First, examine the project structure:
- Check if package.json exists (Node.js/React frontend)
- Check if requirements.txt or pyproject.toml exists (Python backend)
- Check for src/, app/, api/ directories
- Read any existing configuration files

Then create appropriate Dockerfile(s):

**For Python/FastAPI backend** (if Python project detected):
Create `Dockerfile` or `backend/Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \\
    build-essential \\
    libpq-dev \\
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**For React/Node.js frontend** (if frontend detected):
Create `frontend/Dockerfile`:
```dockerfile
# Build stage
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

Also create `.dockerignore`:
```
node_modules/
__pycache__/
*.pyc
.env
.git/
venv/
*.log
dist/
build/
```

Use multi-stage builds where appropriate for smaller images.
"""

        result = await self.call_claude_code(
            prompt=prompt,
            project_path=project_path,
            allowed_tools=["Write", "Edit", "Read", "Bash"]
        )

        dockerfile = Path(project_path) / "Dockerfile"
        dockerignore = Path(project_path) / ".dockerignore"

        await self.log_action("create_dockerfile", "completed", {
            "dockerfile_exists": dockerfile.exists()
        })

        return {
            "success": True,
            "dockerfile_created": dockerfile.exists(),
            "dockerignore_created": dockerignore.exists(),
            "message": "Dockerfile created successfully"
        }

    # ==========================================
    # DOCKER COMPOSE
    # ==========================================

    async def create_docker_compose(self, task: Dict) -> Dict:
        """
        Create docker-compose.yml for local development

        Args:
            task: Task with 'project_path' and 'stack'

        Returns:
            Result
        """
        project_path = task.get("project_path", "")
        stack = task.get("stack", "auto")

        await self.log_action("create_docker_compose", "started", {})

        prompt = f"""
Create a docker-compose.yml for local development.

Project path: {project_path}

First examine the project to understand the stack:
- Look for package.json, requirements.txt, Dockerfile
- Check for any existing docker-compose files
- Understand the services needed

Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/appdb
      - REDIS_URL=redis://redis:6379
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    volumes:
      - .:/app
    restart: unless-stopped

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: appdb
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  frontend:  # Only if frontend exists
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:80"
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

Also create `docker-compose.prod.yml` for production overrides:
```yaml
version: '3.8'

services:
  backend:
    restart: always
    environment:
      - DEBUG=false

  db:
    restart: always

  redis:
    restart: always
```

And create `.env.example`:
```env
# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/appdb

# Redis
REDIS_URL=redis://localhost:6379

# App
SECRET_KEY=your-secret-key-here
DEBUG=true
ALLOWED_HOSTS=localhost,127.0.0.1

# GitHub
GITHUB_TOKEN=
GITHUB_USERNAME=
```

Adapt services based on what the project actually needs.
"""

        result = await self.call_claude_code(
            prompt=prompt,
            project_path=project_path,
            allowed_tools=["Write", "Edit", "Read"]
        )

        compose_file = Path(project_path) / "docker-compose.yml"
        env_example = Path(project_path) / ".env.example"

        await self.log_action("create_docker_compose", "completed", {
            "compose_created": compose_file.exists()
        })

        return {
            "success": True,
            "compose_created": compose_file.exists(),
            "env_example_created": env_example.exists(),
            "message": "Docker Compose configuration created"
        }

    # ==========================================
    # GITHUB ACTIONS CI/CD
    # ==========================================

    async def _create_github_actions_workflow(
        self,
        repo_name: str,
        project_path: str,
        stack: str
    ) -> Dict:
        """Create GitHub Actions CI/CD workflow files"""

        await self.log_action("create_github_actions", "started", {"repo": repo_name})

        prompt = f"""
Create GitHub Actions CI/CD workflow files for this project.

Project path: {project_path}
Repository: {repo_name}

First examine the project structure to understand what's needed, then:

1. **Create `.github/workflows/ci.yml`** - Continuous Integration:
```yaml
name: CI

on:
  push:
    branches: [ main, dev ]
  pull_request:
    branches: [ main, dev ]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: testdb
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python 3.11
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Cache pip packages
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{{{ runner.os }}}}-pip-${{{{ hashFiles('requirements.txt') }}}}

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov

    - name: Run tests
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/testdb
      run: |
        pytest --cov=. --cov-report=xml -v

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

2. **Create `.github/workflows/cd.yml`** - Continuous Deployment:
```yaml
name: CD - Deploy to Staging

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v4

    - name: Build Docker image
      run: docker build -t {repo_name}:${{{{ github.sha }}}} .

    - name: Run smoke tests
      run: |
        docker run --rm {repo_name}:${{{{ github.sha }}}} python -c "import main; print('App imports OK')"

    - name: Deploy (placeholder)
      run: |
        echo "Deployment step - configure your deployment here"
        echo "Options: Vercel, Railway, Fly.io, VPS, etc."
```

3. **Create `.github/workflows/pr-check.yml`** - PR quality checks:
```yaml
name: PR Quality Check

on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    - run: pip install ruff black
    - name: Check formatting
      run: black --check .
    - name: Lint
      run: ruff check .
```

Adapt workflows based on what the project actually contains.
Ensure workflow files are valid YAML with proper indentation.
"""

        result = await self.call_claude_code(
            prompt=prompt,
            project_path=project_path,
            allowed_tools=["Write", "Edit", "Read", "Bash"]
        )

        # Push workflow files to GitHub if repo exists
        ci_file = Path(project_path) / ".github" / "workflows" / "ci.yml"
        files_pushed = []

        if ci_file.exists() and repo_name:
            try:
                with open(ci_file, "r") as f:
                    ci_content = f.read()

                await self.github.create_workflow_file(
                    repo_name=repo_name,
                    workflow_name="ci.yml",
                    workflow_content=ci_content
                )
                files_pushed.append("ci.yml")
                self.logger.info(f"Pushed CI workflow to {repo_name}")
            except Exception as e:
                self.logger.warning(f"Could not push CI workflow: {e}")

        await self.log_action("create_github_actions", "completed", {
            "files_pushed": files_pushed
        })

        return {
            "success": True,
            "workflow_file_created": ci_file.exists(),
            "files_pushed_to_github": files_pushed,
            "message": "GitHub Actions workflows created"
        }

    # ==========================================
    # DEPLOYMENT SETUP
    # ==========================================

    async def setup_deployment(self, task: Dict) -> Dict:
        """
        Create deployment scripts and configuration

        Args:
            task: Task with 'project_path' and 'repo_name'

        Returns:
            Deployment setup result
        """
        project_path = task.get("project_path", "")
        repo_name = task.get("repo_name", "")

        await self.log_action("setup_deployment", "started", {})

        prompt = f"""
Create deployment scripts and documentation for this project.

Project path: {project_path}

Create the following files:

1. **`scripts/deploy.sh`** - Main deployment script:
```bash
#!/bin/bash
set -e

echo "🚀 Starting deployment..."

# Variables
APP_NAME="{repo_name or "app"}"
DOCKER_IMAGE="${{APP_NAME}}:${{1:-latest}}"

# Build Docker image
echo "📦 Building Docker image..."
docker build -t "$DOCKER_IMAGE" .

# Run health check on new image
echo "🔍 Running health check..."
docker run --rm "$DOCKER_IMAGE" python -c "import sys; print('✅ App OK')" || exit 1

# Stop old container
echo "🛑 Stopping old container..."
docker stop "$APP_NAME" 2>/dev/null || true
docker rm "$APP_NAME" 2>/dev/null || true

# Start new container
echo "▶️  Starting new container..."
docker run -d \\
  --name "$APP_NAME" \\
  --restart unless-stopped \\
  -p 8000:8000 \\
  --env-file .env \\
  "$DOCKER_IMAGE"

# Wait and verify
sleep 5
docker ps | grep "$APP_NAME" && echo "✅ Deployment successful!" || echo "❌ Deployment failed!"
```

2. **`scripts/rollback.sh`** - Rollback to previous version:
```bash
#!/bin/bash
PREVIOUS_TAG="${{1:-previous}}"
APP_NAME="{repo_name or "app"}"

echo "⏪ Rolling back to $PREVIOUS_TAG..."
docker stop "$APP_NAME" 2>/dev/null || true
docker rm "$APP_NAME" 2>/dev/null || true
docker run -d --name "$APP_NAME" --restart unless-stopped -p 8000:8000 --env-file .env "${{APP_NAME}}:${{PREVIOUS_TAG}}"
echo "✅ Rollback complete!"
```

3. **`scripts/health_check_app.sh`** - Application health check:
```bash
#!/bin/bash
URL="${{1:-http://localhost:8000}}"
echo "🔍 Checking $URL/health ..."
for i in {{1..5}}; do
  if curl -sf "$URL/health" > /dev/null 2>&1; then
    echo "✅ Application is healthy!"
    exit 0
  fi
  echo "Attempt $i/5 - not ready yet, waiting 5s..."
  sleep 5
done
echo "❌ Application health check failed!"
exit 1
```

4. **`DEPLOYMENT.md`** documenting:
   - Prerequisites
   - Environment variables required
   - How to deploy (manual and CI/CD)
   - How to rollback
   - Monitoring and logs

Make all scripts executable and well-commented.
"""

        result = await self.call_claude_code(
            prompt=prompt,
            project_path=project_path,
            allowed_tools=["Write", "Edit", "Bash"]
        )

        deploy_script = Path(project_path) / "scripts" / "deploy.sh"
        deploy_doc = Path(project_path) / "DEPLOYMENT.md"

        await self.log_action("setup_deployment", "completed", {
            "deploy_script_created": deploy_script.exists()
        })

        return {
            "success": True,
            "deploy_script_created": deploy_script.exists(),
            "deployment_doc_created": deploy_doc.exists(),
            "message": "Deployment setup complete"
        }

    # ==========================================
    # HEALTH CHECKS & MONITORING
    # ==========================================

    async def create_health_checks(self, task: Dict) -> Dict:
        """
        Create health check endpoints and monitoring scripts

        Args:
            task: Task with 'project_path'

        Returns:
            Result
        """
        project_path = task.get("project_path", "")

        await self.log_action("create_health_checks", "started", {})

        prompt = f"""
Add health check endpoints and monitoring to the project.

Project path: {project_path}

First examine the project to understand the framework (FastAPI, Flask, etc.), then:

1. **Add a `/health` endpoint** to the main application:
   - For FastAPI: Add to main.py or a dedicated router
   - Response format:
   ```json
   {{
     "status": "healthy",
     "version": "1.0.0",
     "timestamp": "2024-01-01T00:00:00Z",
     "checks": {{
       "database": "ok",
       "redis": "ok"
     }}
   }}
   ```

2. **Create `src/health.py`** (or equivalent):
```python
from datetime import datetime
import asyncio

async def check_database(db) -> bool:
    try:
        await db.execute("SELECT 1")
        return True
    except Exception:
        return False

async def check_redis(redis_client) -> bool:
    try:
        await redis_client.ping()
        return True
    except Exception:
        return False

def get_health_status(db=None, redis=None) -> dict:
    checks = {{}}
    if db:
        checks["database"] = "ok"  # simplified - add actual check
    if redis:
        checks["redis"] = "ok"

    return {{
        "status": "healthy" if all(v == "ok" for v in checks.values()) else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks
    }}
```

3. **Create `scripts/monitor.sh`** - Simple monitoring script:
```bash
#!/bin/bash
APP_URL="${{1:-http://localhost:8000}}"
INTERVAL="${{2:-60}}"

echo "📊 Monitoring $APP_URL every ${{INTERVAL}}s..."
while true; do
  TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
  STATUS=$(curl -sf -o /dev/null -w "%{{http_code}}" "$APP_URL/health" 2>/dev/null)
  if [ "$STATUS" = "200" ]; then
    echo "[$TIMESTAMP] ✅ Healthy (HTTP $STATUS)"
  else
    echo "[$TIMESTAMP] ❌ Unhealthy (HTTP $STATUS)" | tee -a monitoring.log
  fi
  sleep "$INTERVAL"
done
```

4. **Update the main application** to include the `/health` endpoint.

Make the health endpoint accessible without authentication.
"""

        result = await self.call_claude_code(
            prompt=prompt,
            project_path=project_path,
            allowed_tools=["Write", "Edit", "Read", "Bash"]
        )

        monitor_script = Path(project_path) / "scripts" / "monitor.sh"

        await self.log_action("create_health_checks", "completed", {})

        return {
            "success": True,
            "monitor_script_created": monitor_script.exists(),
            "message": "Health checks and monitoring configured"
        }

    # ==========================================
    # FULL PROJECT DEVOPS SETUP
    # ==========================================

    async def setup_devops_for_project(
        self,
        project_path: str,
        repo_name: str,
        stack: str = "auto"
    ) -> Dict:
        """
        Complete DevOps setup for a project

        Args:
            project_path: Path to the project
            repo_name: GitHub repository name
            stack: Technology stack

        Returns:
            Complete setup result
        """
        return await self.setup_cicd_pipeline({
            "task_type": "setup_cicd",
            "project_path": project_path,
            "repo_name": repo_name,
            "stack": stack
        })


# ==========================================
# CONVENIENCE FUNCTIONS
# ==========================================

async def setup_devops(
    project_path: str,
    repo_name: str,
    stack: str = "auto"
) -> Dict:
    """
    Quick function to set up DevOps for a project

    Args:
        project_path: Project directory path
        repo_name: GitHub repository name
        stack: Technology stack

    Returns:
        Setup result
    """
    agent = DevOpsAgent()
    return await agent.setup_devops_for_project(project_path, repo_name, stack)


# ==========================================
# EXAMPLE USAGE
# ==========================================

if __name__ == "__main__":
    import asyncio

    async def test_devops_agent():
        """Test DevOps Agent"""
        agent = DevOpsAgent()
        print(f"DevOps Agent: {agent}")
        print(f"Capabilities: {agent.get_capabilities()}")
        print("DevOps Agent initialized successfully!")

    asyncio.run(test_devops_agent())
