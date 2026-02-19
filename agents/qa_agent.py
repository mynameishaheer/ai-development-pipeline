"""
QA Agent for AI Development Pipeline
Automated testing, PR review, code quality checks, and approval workflows
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from agents.base_agent import BaseAgent
from agents.github_client import create_github_client
from utils.constants import AgentType, GitHubBranches
from utils.error_handlers import retry_on_rate_limit


class QAAgent(BaseAgent):
    """
    Quality Assurance Agent

    Responsibilities:
    - Run automated tests (pytest for backend, jest for frontend)
    - Review pull requests and check test results
    - Validate code quality (linting, formatting, coverage)
    - Auto-approve or request changes on GitHub PRs
    - Create detailed review comments
    - Track test history and failure patterns
    """

    def __init__(self, agent_id: Optional[str] = None):
        """Initialize QA Agent"""
        super().__init__(
            agent_type=AgentType.QA,
            agent_id=agent_id
        )

        self.github = create_github_client()

        # Minimum coverage threshold
        self.min_coverage = int(os.getenv("MIN_TEST_COVERAGE", "80"))

        self.logger.info("QA Agent initialized", extra={"min_coverage": self.min_coverage})

    def get_capabilities(self) -> List[str]:
        """Get agent capabilities"""
        return [
            "Run pytest tests",
            "Run jest tests",
            "Check test coverage",
            "Review pull requests",
            "Auto-approve passing PRs",
            "Request changes on failing PRs",
            "Lint and format checks",
            "Create inline code review comments",
        ]

    async def execute_task(self, task: Dict) -> Dict:
        """
        Execute a QA task

        Args:
            task: Task dictionary with task details

        Returns:
            Result dictionary
        """
        task_type = task.get("task_type", "review_pr")

        handlers = {
            "review_pr": self.review_pull_request,
            "run_tests": self.run_tests_for_project,
            "check_coverage": self.check_coverage,
            "validate_pr": self.validate_pull_request,
        }

        handler = handlers.get(task_type)
        if not handler:
            raise ValueError(f"Unknown task type: {task_type}")

        return await handler(task)

    # ==========================================
    # PULL REQUEST REVIEW
    # ==========================================

    async def review_pull_request(self, task: Dict) -> Dict:
        """
        Full PR review workflow:
        1. Fetch PR details and changed files
        2. Run tests on the PR branch
        3. Check test coverage
        4. Validate code quality
        5. Post review (approve or request changes)

        Args:
            task: Task with 'repo_name', 'pr_number', optional 'project_path'

        Returns:
            Review result with decision and comments
        """
        repo_name = task.get("repo_name", "")
        pr_number = task.get("pr_number", 0)
        project_path = task.get("project_path", "")

        await self.log_action("review_pull_request", "started", {
            "repo": repo_name,
            "pr": pr_number
        })

        review_results = {
            "repo_name": repo_name,
            "pr_number": pr_number,
            "checks": {},
            "issues": [],
            "approved": False,
        }

        try:
            # Fetch PR details
            pr = await self.github.get_pull_request(repo_name, pr_number)
            pr_title = pr.get("title", "")
            branch_name = pr.get("head", {}).get("ref", "")
            base_branch = pr.get("base", {}).get("ref", "main")

            self.logger.info(f"Reviewing PR #{pr_number}: {pr_title}")

            # Get changed files
            changed_files = await self.github.get_pr_files(repo_name, pr_number)
            file_names = [f.get("filename", "") for f in changed_files]

            review_results["branch"] = branch_name
            review_results["files_changed"] = len(file_names)

            # Determine what type of project this is
            has_python = any(f.endswith(".py") for f in file_names)
            has_js_ts = any(f.endswith((".js", ".ts", ".jsx", ".tsx")) for f in file_names)

            # Run tests using Claude Code on the project
            if project_path and Path(project_path).exists():
                test_result = await self._run_tests_with_claude(
                    project_path=project_path,
                    has_python=has_python,
                    has_js_ts=has_js_ts,
                    pr_number=pr_number
                )
                review_results["checks"]["tests"] = test_result
                if not test_result.get("passed"):
                    review_results["issues"].append(
                        f"Tests failing: {test_result.get('summary', 'unknown failure')}"
                    )

            # Code quality check using Claude Code
            if project_path and Path(project_path).exists():
                quality_result = await self._check_code_quality(
                    project_path=project_path,
                    file_names=file_names
                )
                review_results["checks"]["code_quality"] = quality_result
                if quality_result.get("issues"):
                    review_results["issues"].extend(quality_result["issues"])

            # Make approval decision
            approved = len(review_results["issues"]) == 0
            review_results["approved"] = approved

            # Post review to GitHub
            await self._post_github_review(
                repo_name=repo_name,
                pr_number=pr_number,
                approved=approved,
                issues=review_results["issues"],
                checks=review_results["checks"],
                pr_title=pr_title
            )

            status = "approved" if approved else "changes_requested"
            await self.log_action("review_pull_request", "completed", {
                "repo": repo_name,
                "pr": pr_number,
                "decision": status,
                "issues_found": len(review_results["issues"])
            })

            return {
                "success": True,
                **review_results,
                "decision": status,
                "message": f"PR #{pr_number} {'approved' if approved else 'needs changes'}"
            }

        except Exception as e:
            await self.log_action("review_pull_request", "failed", {"error": str(e)})
            raise

    async def validate_pull_request(self, task: Dict) -> Dict:
        """
        Quick validation of a PR (checks structure and labels, no test execution).
        Used for fast feedback before full review.

        Args:
            task: Task with 'repo_name', 'pr_number'

        Returns:
            Validation result
        """
        repo_name = task.get("repo_name", "")
        pr_number = task.get("pr_number")

        if not pr_number:
            return {
                "success": False,
                "valid": False,
                "issues": ["pr_number is required"],
                "reason": "Missing pr_number",
            }

        try:
            pr = await self.github.get_pull_request(repo_name, pr_number)
        except Exception as e:
            return {
                "success": False,
                "valid": False,
                "issues": [f"GitHub error: {e}"],
                "reason": str(e),
            }

        issues = []

        # Check PR has a description
        if not pr.get("body"):
            issues.append("PR is missing a description")

        # Check PR title follows convention
        title = pr.get("title", "")
        valid_prefixes = ["feat:", "fix:", "docs:", "refactor:", "test:", "chore:", "feat("]
        if not any(title.startswith(p) for p in valid_prefixes):
            issues.append(
                f"PR title '{title}' doesn't follow convention "
                "(use feat:, fix:, docs:, refactor:, test:, or chore:)"
            )

        # Check base branch
        base = pr.get("base", {}).get("ref", "")
        if base not in [GitHubBranches.DEVELOPMENT, GitHubBranches.MAIN]:
            issues.append(f"PR targets '{base}' instead of '{GitHubBranches.DEVELOPMENT}'")

        return {
            "success": True,
            "pr_number": pr_number,
            "valid": len(issues) == 0,
            "issues": issues,
        }

    # ==========================================
    # TEST EXECUTION
    # ==========================================

    async def run_tests_for_project(self, task: Dict) -> Dict:
        """
        Run all tests for a project and return results

        Args:
            task: Task with 'project_path' and optional 'framework'

        Returns:
            Test results dictionary
        """
        project_path = task.get("project_path", "")
        framework = task.get("framework", "auto")

        await self.log_action("run_tests", "started", {"path": project_path})

        if not Path(project_path).exists():
            return {"success": False, "error": f"Project path does not exist: {project_path}"}

        # Auto-detect framework
        if framework == "auto":
            framework = self._detect_test_framework(project_path)

        result = await self._run_tests_with_claude(
            project_path=project_path,
            has_python=(framework in ("pytest", "both")),
            has_js_ts=(framework in ("jest", "both")),
            pr_number=None
        )

        await self.log_action("run_tests", "completed", {
            "framework": framework,
            "passed": result.get("passed", False)
        })

        return result

    async def check_coverage(self, task: Dict) -> Dict:
        """
        Check test coverage for a project

        Args:
            task: Task with 'project_path'

        Returns:
            Coverage report
        """
        project_path = task.get("project_path", "")

        prompt = f"""
Check test coverage for this Python project.

Run these commands and report the results:
1. Run: pytest --cov=. --cov-report=term-missing --cov-report=json -q 2>&1 | tail -20
2. If coverage.json exists, read it and report total coverage percentage
3. List any files with coverage below {self.min_coverage}%

Report:
- Total coverage percentage
- Files below threshold
- Whether coverage meets the {self.min_coverage}% minimum requirement
"""
        result = await self.call_claude_code(
            prompt=prompt,
            project_path=project_path,
            allowed_tools=["Bash", "Read"]
        )

        output = result.get("stdout", "")
        coverage_pct = self._extract_coverage_percentage(output)

        return {
            "success": True,
            "coverage_percentage": coverage_pct,
            "meets_threshold": coverage_pct >= self.min_coverage if coverage_pct else False,
            "threshold": self.min_coverage,
            "details": output[:1000],
        }

    # ==========================================
    # INTERNAL HELPERS
    # ==========================================

    async def _run_tests_with_claude(
        self,
        project_path: str,
        has_python: bool,
        has_js_ts: bool,
        pr_number: Optional[int]
    ) -> Dict:
        """Run tests using Claude Code and return structured results"""

        test_commands = []
        if has_python:
            test_commands.append("pytest -v --tb=short -q 2>&1 | tail -30")
        if has_js_ts:
            test_commands.append("npm test -- --watchAll=false --passWithNoTests 2>&1 | tail -30")

        if not test_commands:
            return {
                "passed": True,
                "summary": "No tests to run",
                "details": ""
            }

        commands_str = "\n".join([f"- {cmd}" for cmd in test_commands])

        prompt = f"""
Run the project tests and report results.

Commands to run:
{commands_str}

For each command:
1. Run it
2. Report whether tests passed or failed
3. Show the number of tests passed/failed
4. Show any error messages for failures

End with a clear PASS or FAIL summary.
"""

        result = await self.call_claude_code(
            prompt=prompt,
            project_path=project_path,
            allowed_tools=["Bash"]
        )

        output = result.get("stdout", "")
        passed = self._determine_test_pass(output, result.get("success", False))

        return {
            "passed": passed,
            "summary": "Tests passed" if passed else "Tests failed",
            "details": output[:2000],
            "pr_number": pr_number,
        }

    async def _check_code_quality(
        self,
        project_path: str,
        file_names: List[str]
    ) -> Dict:
        """Check code quality using linting tools"""

        python_files = [f for f in file_names if f.endswith(".py")]
        has_python = len(python_files) > 0

        if not has_python:
            return {"passed": True, "issues": []}

        prompt = f"""
Check code quality for the Python files in this project.

Run these quality checks (skip any tool that's not installed):
1. ruff check . --select E,W --quiet 2>&1 | head -20
2. If above fails: python -m py_compile {' '.join(python_files[:5])} && echo "Syntax OK"

Report:
- Any critical errors (syntax errors, undefined names)
- Warning count
- Whether code quality is acceptable

Focus only on actual errors, not style warnings.
"""

        result = await self.call_claude_code(
            prompt=prompt,
            project_path=project_path,
            allowed_tools=["Bash"]
        )

        output = result.get("stdout", "")
        issues = self._extract_quality_issues(output)

        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "details": output[:1000],
        }

    @retry_on_rate_limit()
    async def _post_github_review(
        self,
        repo_name: str,
        pr_number: int,
        approved: bool,
        issues: List[str],
        checks: Dict,
        pr_title: str
    ):
        """Post a review to GitHub"""

        event = "APPROVE" if approved else "REQUEST_CHANGES"

        if approved:
            body = f"""## ✅ QA Review: APPROVED

**PR**: {pr_title}

All quality checks passed:
"""
            for check_name, check_result in checks.items():
                if isinstance(check_result, dict):
                    status = "✅" if check_result.get("passed", True) else "❌"
                    body += f"\n- {status} **{check_name.replace('_', ' ').title()}**"

            body += "\n\n*Reviewed by QA Agent*"
        else:
            body = f"""## ❌ QA Review: CHANGES REQUESTED

**PR**: {pr_title}

The following issues were found:
"""
            for i, issue in enumerate(issues, 1):
                body += f"\n{i}. {issue}"

            body += "\n\n**Required Actions:**\n"
            body += "- Fix all failing tests\n"
            body += "- Address any linting errors\n"
            body += "- Re-run tests before requesting re-review\n"
            body += "\n*Reviewed by QA Agent*"

        try:
            await self.github.create_pr_review(
                repo_name=repo_name,
                pr_number=pr_number,
                event=event,
                body=body
            )
            self.logger.info(
                f"Posted {event} review on PR #{pr_number}",
                extra={"repo": repo_name, "pr": pr_number}
            )
        except Exception as e:
            # Fall back to a comment if review fails (e.g., own PR)
            self.logger.warning(f"Could not create review, posting comment: {e}")
            try:
                await self.github.add_issue_comment(
                    repo_name=repo_name,
                    issue_number=pr_number,
                    body=body
                )
            except Exception as comment_err:
                self.logger.error(f"Could not post review or comment: {comment_err}")

    def _detect_test_framework(self, project_path: str) -> str:
        """Detect what test framework the project uses"""
        path = Path(project_path)

        # Check for pytest: config files or pytest in requirements.txt
        has_pytest = (path / "pytest.ini").exists() or (path / "setup.cfg").exists()
        if not has_pytest:
            req_file = path / "requirements.txt"
            if req_file.exists():
                req_content = req_file.read_text().lower()
                has_pytest = "pytest" in req_content
        if not has_pytest:
            has_pytest = bool(list(path.glob("tests/test_*.py")))

        # Check for jest: package.json with jest dependency
        has_jest = False
        pkg_json = path / "package.json"
        if pkg_json.exists():
            try:
                import json as _json
                pkg = _json.loads(pkg_json.read_text())
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                has_jest = "jest" in deps
            except Exception:
                has_jest = True  # package.json exists but unreadable, assume jest

        if has_pytest and has_jest:
            return "pytest+jest"
        elif has_pytest:
            return "pytest"
        elif has_jest:
            return "jest"
        else:
            return "none"

    def _determine_test_pass(self, output: str, execution_success: bool) -> bool:
        """Determine if tests passed based on output"""
        # Execution failure always means tests did not pass
        if not execution_success:
            return False

        # Empty output is ambiguous — treat as failure
        if not output.strip():
            return False

        output_lower = output.lower()

        # Look for explicit failure indicators
        failure_indicators = [
            "failed",
            "error",
            "tests failed",
            "test suite failed",
            "assertion error",
            "import error",
        ]

        # Look for success indicators
        success_indicators = [
            "passed",
            "ok",
            "all tests passed",
            "no tests ran",
            "test suite completed",
        ]

        has_failure = any(indicator in output_lower for indicator in failure_indicators)
        has_success = any(indicator in output_lower for indicator in success_indicators)

        # Failure indicators take priority over success indicators
        if has_failure:
            return False
        elif has_success:
            return True
        else:
            return False

    def _extract_coverage_percentage(self, output: str) -> Optional[float]:
        """Extract coverage percentage from test output"""
        import re

        # Look for patterns like "TOTAL ... 85%" or "TOTAL ... 85.5%" or "Coverage: 85%"
        patterns = [
            r"TOTAL\s+\d+\s+\d+\s+(\d+(?:\.\d+)?)%",
            r"coverage[:\s]+(\d+(?:\.\d+)?)%",
            r"(\d+(?:\.\d+)?)%\s+(?:coverage|covered)",
        ]

        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                return float(match.group(1))

        return None

    def _extract_quality_issues(self, output: str) -> List[str]:
        """Extract quality issues from linting output"""
        issues = []
        lines = output.split("\n")

        for line in lines:
            # Look for error-level issues (not warnings)
            if any(indicator in line.upper() for indicator in ["ERROR", "E9", "SYNTAX"]):
                issue = line.strip()
                if issue and len(issue) > 10:
                    issues.append(issue[:200])

        return issues[:10]  # Max 10 issues


# ==========================================
# CONVENIENCE FUNCTIONS
# ==========================================

async def review_pr(repo_name: str, pr_number: int, project_path: str = "") -> Dict:
    """
    Quick function to review a pull request

    Args:
        repo_name: Repository name
        pr_number: PR number
        project_path: Optional local project path for running tests

    Returns:
        Review result
    """
    qa = QAAgent()
    return await qa.review_pull_request({
        "task_type": "review_pr",
        "repo_name": repo_name,
        "pr_number": pr_number,
        "project_path": project_path,
    })


# ==========================================
# EXAMPLE USAGE
# ==========================================

if __name__ == "__main__":
    import asyncio

    async def test_qa_agent():
        """Test QA Agent"""
        qa = QAAgent()
        print(f"QA Agent: {qa}")
        print(f"Capabilities: {qa.get_capabilities()}")

        # Test PR validation (no real GitHub call needed for this test)
        print("\nQA Agent initialized successfully!")
        print(f"Min coverage threshold: {qa.min_coverage}%")

    asyncio.run(test_qa_agent())
