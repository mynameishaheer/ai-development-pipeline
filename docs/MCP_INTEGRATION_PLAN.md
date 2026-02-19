# MCP Server Integration Plan

**Last Updated**: February 19, 2026
**Status**: Planned (Phase 10)

MCP (Model Context Protocol) servers extend Claude Code with external API access via standardized tools. This document covers which MCP servers to integrate, why, how to set them up, and exactly how each agent will use them.

---

## Overview

| MCP Server | Integrates With | Value |
|------------|----------------|-------|
| Playwright | QA Agent | Browser E2E testing on deployed apps |
| Supabase | Database Agent | Managed PostgreSQL + Auth + Storage |
| Sentry | PipelineMonitor | Runtime error tracking for deployed apps |
| GitHub | Project Manager, QA | Deeper PR/issue automation |
| Vercel | Deployer | Frontend-only app deployment |

---

## 1. Playwright MCP

### What It Does
Playwright MCP gives Claude Code control of a real browser: navigate pages, click, fill forms, take screenshots, assert DOM state. This replaces hand-written Selenium scripts with natural language browser instructions.

### Why This Pipeline Needs It
Currently the QA agent only runs unit tests (`pytest`). It has no way to verify that the deployed app actually works in a browser. Playwright closes this gap: after every deploy, the QA agent can run a smoke test against the live URL.

### Setup

```bash
# Install Playwright MCP server
npm install -g @playwright/mcp

# Install browsers
npx playwright install chromium

# Verify
npx @playwright/mcp --help
```

Add to Claude Code's MCP config (`~/.claude/mcp_servers.json`):
```json
{
  "playwright": {
    "command": "npx",
    "args": ["@playwright/mcp", "--headless"]
  }
}
```

### Integration Point: `agents/qa_agent.py`

New method `run_e2e_tests(deploy_url, project_path)`:

```python
async def run_e2e_tests(self, deploy_url: str, project_path: str) -> Dict:
    prompt = f"""
    Using the Playwright MCP tools, run a smoke test on {deploy_url}:
    1. Navigate to {deploy_url}
    2. Verify the page loads (no 5xx errors)
    3. Find the main interactive element (form, button, or link) and interact with it
    4. Take a screenshot of the result
    5. Report PASS or FAIL with details

    Project path: {project_path}
    Look at the README.md for any specific test scenarios mentioned.
    """
    result = await self.call_claude_code(
        prompt=prompt,
        project_path=project_path,
        allowed_tools=["mcp__playwright__navigate", "mcp__playwright__click",
                        "mcp__playwright__fill", "mcp__playwright__screenshot",
                        "mcp__playwright__get_text", "Read"],
    )
    return self._parse_e2e_result(result)
```

### When It Runs

After `_auto_deploy()` completes successfully in `worker_daemon.py`:
```python
# After deploy succeeds
if deploy_result["success"] and self._master:
    await self._master.current_project_qa_agent.run_e2e_tests(
        deploy_url=deploy_result["url"],
        project_path=project["path"],
    )
```

### Output
- GitHub comment on the latest merged PR: "E2E smoke test: ✅ PASS" or "❌ FAIL — [details]"
- Screenshot stored in project `reports/e2e/` directory
- On failure: creates a new GitHub issue with label `bug` and enqueues a `fix_bug` task

---

## 2. Supabase MCP

### What It Does
The Supabase MCP server allows Claude Code to create and manage Supabase projects: apply SQL schemas, create tables, set up Row Level Security (RLS) policies, manage Auth providers, and handle Storage buckets.

### Why This Pipeline Needs It
Generated apps currently use SQLite (simple, but not production-ready). Supabase gives every deployed app a real hosted PostgreSQL database, built-in authentication, and file storage — all free tier — without the complexity of self-hosting Postgres.

### Setup

```bash
# Install Supabase MCP server
npm install -g @supabase/mcp-server-supabase

# Requires: SUPABASE_ACCESS_TOKEN in environment
```

Add to Claude Code MCP config:
```json
{
  "supabase": {
    "command": "npx",
    "args": ["@supabase/mcp-server-supabase"],
    "env": {
      "SUPABASE_ACCESS_TOKEN": "${SUPABASE_ACCESS_TOKEN}"
    }
  }
}
```

Add to `.env`:
```env
SUPABASE_ACCESS_TOKEN=sbp_your_token_here
SUPABASE_ORG_ID=your_org_id
```

### Integration Point: `agents/database_agent.py`

New method `setup_supabase_for_project(project_name, schema_sql)`:

```python
async def setup_supabase_for_project(
    self,
    project_name: str,
    schema_sql: str,
    project_path: str,
) -> Dict:
    """
    Create a Supabase project, apply schema, return connection string.
    """
    prompt = f"""
    Using Supabase MCP tools:
    1. Create a new Supabase project named "{project_name}" in org {SUPABASE_ORG_ID}
    2. Wait for the project to become active (poll project status)
    3. Apply this SQL schema:
    ---
    {schema_sql}
    ---
    4. Enable Row Level Security on all tables
    5. Return the project URL and anon key

    Store the connection string in {project_path}/.env as:
    SUPABASE_URL=https://xxx.supabase.co
    SUPABASE_ANON_KEY=xxx
    DATABASE_URL=postgresql://postgres:xxx@db.xxx.supabase.co:5432/postgres
    """
    result = await self.call_claude_code(
        prompt=prompt,
        project_path=project_path,
        allowed_tools=["mcp__supabase__create_project", "mcp__supabase__execute_sql",
                        "mcp__supabase__get_project", "Write"],
    )
    return self._parse_supabase_result(result)
```

### When It Runs

In `master_agent.handle_run_full_pipeline()`:
```python
# After database_agent.setup_database_for_project() generates the schema:
supabase_result = await database_agent.setup_supabase_for_project(
    project_name=sanitized_name,
    schema_sql=schema_content,
    project_path=project_path,
)
if supabase_result["success"]:
    project["supabase_url"] = supabase_result["url"]
    project["supabase_project_id"] = supabase_result["project_id"]
```

### Fallback
If Supabase MCP is not configured (no `SUPABASE_ACCESS_TOKEN`), the pipeline falls back to SQLite — existing behaviour is preserved.

### What Changes for Generated Apps
- Backend agent's `implement_feature` prompt gets additional context: "Use Supabase (URL and key are in .env) instead of SQLite"
- The Dockerfile no longer needs to install SQLite or manage migrations at startup — Supabase handles that

---

## 3. Sentry MCP

### What It Does
Sentry MCP allows Claude Code to read Sentry issues, create projects, retrieve error details, and manage alerts. Used here to detect runtime errors in deployed apps automatically.

### Why This Pipeline Needs It
CI logs only catch pre-deploy errors. Sentry catches what happens after users (or the Playwright tests) actually hit the app. An uncaught exception in production currently goes unnoticed.

### Setup

```bash
# Sentry MCP — community server
npm install -g @sentry/mcp-server

# Or use the official Sentry MCP when available
```

Add to MCP config:
```json
{
  "sentry": {
    "command": "npx",
    "args": ["@sentry/mcp-server"],
    "env": {
      "SENTRY_AUTH_TOKEN": "${SENTRY_AUTH_TOKEN}",
      "SENTRY_ORG": "${SENTRY_ORG}"
    }
  }
}
```

Add to `.env`:
```env
SENTRY_AUTH_TOKEN=sntrys_your_token_here
SENTRY_ORG=your-org-slug
```

### Integration Point: `agents/devops_agent.py`

New method `setup_sentry_for_project(project_name, project_path)`:

```python
async def setup_sentry_for_project(self, project_name: str, project_path: str) -> Dict:
    prompt = f"""
    Using Sentry MCP tools:
    1. Create a new Sentry project named "{project_name}" for platform "python"
    2. Get the DSN for the project
    3. Write the DSN to {project_path}/.env as: SENTRY_DSN=https://xxx@sentry.io/xxx
    4. Create a basic Sentry initialization snippet in {project_path}/utils/sentry_init.py
       that reads the DSN from environment and calls sentry_sdk.init()
    """
    ...
```

### Integration Point: `agents/pipeline_monitor.py`

New method `check_sentry_errors(project_name)` — called every 5 minutes alongside the CI poll:

```python
async def check_sentry_errors(self, sentry_project_id: str) -> List[Dict]:
    prompt = f"""
    Using Sentry MCP tools:
    1. List unresolved issues for project {sentry_project_id} created in the last 5 minutes
    2. For each issue: get title, culprit, event count, first seen timestamp
    3. Return as JSON list
    """
    ...
```

When new errors are found:
1. Create a GitHub issue: `[Sentry] {error title}` with label `bug`
2. Enqueue a `fix_bug` task for the appropriate agent
3. Send Discord notification via `master._notify()`

---

## 4. GitHub MCP

### What It Does
The official GitHub MCP server provides Claude Code with tools to read/write issues, PRs, files, and more — mirroring what our `github_client.py` does but with richer natural language control.

### Why This Pipeline Needs It
Our `github_client.py` covers the happy path but complex operations (e.g., "review this PR and suggest improvements", "find all issues related to authentication") are awkward with raw REST API calls. GitHub MCP makes these natural language-driven.

### Setup

```bash
# Official GitHub MCP server
npm install -g @github/github-mcp-server
```

Add to MCP config:
```json
{
  "github": {
    "command": "npx",
    "args": ["@github/github-mcp-server"],
    "env": {
      "GITHUB_TOKEN": "${GITHUB_TOKEN}"
    }
  }
}
```

### Integration Points

**`agents/qa_agent.py`** — `review_pull_request()`:
Instead of a generic "review this PR" prompt with just the diff, use GitHub MCP to fetch the full file context, related issues, and commit history:
```python
# Additional tools: mcp__github__get_pull_request, mcp__github__list_files
# mcp__github__get_file_contents, mcp__github__create_review
```

**`agents/project_manager_agent.py`** — `create_issues_from_prd()`:
Use GitHub MCP to batch-create issues rather than looping REST calls:
```python
# mcp__github__create_issue with full markdown bodies
```

### Coexistence with `github_client.py`
Keep `github_client.py` for all programmatic, non-Claude-Code operations (the Python code that directly calls the GitHub API). Use GitHub MCP only inside `call_claude_code()` prompts where natural language control is an advantage.

---

## 5. Vercel MCP

### What It Does
Vercel MCP allows Claude Code to create Vercel projects, trigger deployments, and retrieve deployment URLs — covering the Vercel deployment workflow that Docker+Cloudflare doesn't handle well for frontend-only apps.

### Why This Pipeline Needs It
React/Next.js/Vite frontends don't need Docker — they're just static files or a Node.js server. Vercel handles CDN, HTTPS, preview deployments, and instant rollbacks for free. Docker + Cloudflare Tunnel adds unnecessary overhead for these project types.

### Setup

```bash
npm install -g @vercel/mcp-server
```

Add to MCP config:
```json
{
  "vercel": {
    "command": "npx",
    "args": ["@vercel/mcp-server"],
    "env": {
      "VERCEL_TOKEN": "${VERCEL_TOKEN}"
    }
  }
}
```

Add to `.env`:
```env
VERCEL_TOKEN=your_vercel_token
VERCEL_TEAM_ID=optional_team_id
```

### Integration Point: `agents/deployer.py`

New function `deploy_frontend_to_vercel(project_path, project_name)`:

```python
async def deploy_frontend_to_vercel(project_path: str, project_name: str) -> Dict:
    """
    Deploy a frontend-only project to Vercel instead of Docker.
    Returns {"success": bool, "url": str, "deployment_id": str}
    """
```

### Detection Logic

In `deploy_project()`, detect project type before choosing deployment target:

```python
async def deploy_project(project_path, project_name):
    if _is_frontend_project(project_path):
        return await deploy_frontend_to_vercel(project_path, project_name)
    else:
        return await deploy_docker_cloudflare(project_path, project_name)

def _is_frontend_project(project_path: str) -> bool:
    """True if project has package.json with next/vite/react-scripts but no Dockerfile."""
    path = Path(project_path)
    has_dockerfile = (path / "Dockerfile").exists()
    if has_dockerfile:
        return False
    pkg = path / "package.json"
    if not pkg.exists():
        return False
    data = json.loads(pkg.read_text())
    deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
    return any(k in deps for k in ["next", "vite", "react-scripts"])
```

---

## MCP Setup Checklist

### Minimum (High Value, Low Friction)

- [ ] **GitHub MCP** — just needs `GITHUB_TOKEN` (already have it). Add to MCP config. Immediate improvement to QA and Project Manager agents.
- [ ] **Playwright MCP** — install Node + Playwright. No extra credentials needed. Adds browser E2E testing.

### Medium Effort

- [ ] **Supabase MCP** — create a Supabase account (free), get `SUPABASE_ACCESS_TOKEN`. Transforms database setup.
- [ ] **Sentry MCP** — create a Sentry account (free), get `SENTRY_AUTH_TOKEN`. Adds production monitoring.

### Optional / Project-Dependent

- [ ] **Vercel MCP** — create Vercel account, get token. Only needed if building frontend-only projects.

---

## Implementation Order

1. **GitHub MCP** — lowest friction, highest immediate value for QA agent PR reviews
2. **Playwright MCP** — closes the E2E testing gap, pairs well with Phase 8 deploy hardening
3. **Supabase MCP** — transforms database agent; implement when building a project that needs real auth/data
4. **Sentry MCP** — implement alongside Phase 11 PipelineMonitor upgrades
5. **Vercel MCP** — implement when the first Next.js/Vite project comes through the pipeline
