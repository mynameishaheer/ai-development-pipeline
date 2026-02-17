"""
GitHub API Client for AI Development Pipeline
Comprehensive GitHub integration for repository, issue, PR, and branch management
"""

import requests
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import base64
import json


class GitHubClient:
    """
    Full-featured GitHub API client for repository automation
    Supports: repos, issues, PRs, branches, merging, CI/CD
    """
    
    def __init__(
        self,
        token: str,
        username: str,
        org: Optional[str] = None
    ):
        """
        Initialize GitHub client
        
        Args:
            token: GitHub Personal Access Token
            username: GitHub username
            org: Optional GitHub organization name
        """
        self.token = token
        self.username = username
        self.org = org
        self.base_url = "https://api.github.com"
        
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
    
    # ==========================================
    # REPOSITORY OPERATIONS
    # ==========================================
    
    async def create_repository(
        self,
        name: str,
        description: str,
        private: bool = False,
        auto_init: bool = True,
        gitignore_template: Optional[str] = "Python",
        license_template: Optional[str] = None
    ) -> Dict:
        """
        Create a new GitHub repository
        
        Args:
            name: Repository name
            description: Repository description
            private: Whether repository is private
            auto_init: Initialize with README
            gitignore_template: Template for .gitignore (e.g., "Python", "Node")
            license_template: License template (e.g., "mit", "apache-2.0")
        
        Returns:
            Repository data dictionary
        """
        url = f"{self.base_url}/user/repos" if not self.org else f"{self.base_url}/orgs/{self.org}/repos"
        
        data = {
            "name": name,
            "description": description,
            "private": private,
            "auto_init": auto_init,
        }
        
        if gitignore_template:
            data["gitignore_template"] = gitignore_template
        
        if license_template:
            data["license_template"] = license_template
        
        response = requests.post(url, headers=self.headers, json=data)
        response.raise_for_status()
        
        return response.json()
    
    async def get_repository(self, repo_name: str) -> Dict:
        """
        Get repository information
        
        Args:
            repo_name: Repository name
        
        Returns:
            Repository data
        """
        owner = self.org or self.username
        url = f"{self.base_url}/repos/{owner}/{repo_name}"
        
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        
        return response.json()
    
    async def delete_repository(self, repo_name: str) -> bool:
        """
        Delete a repository
        
        Args:
            repo_name: Repository name
        
        Returns:
            True if successful
        """
        owner = self.org or self.username
        url = f"{self.base_url}/repos/{owner}/{repo_name}"
        
        response = requests.delete(url, headers=self.headers)
        response.raise_for_status()
        
        return True
    
    # ==========================================
    # BRANCH OPERATIONS
    # ==========================================
    
    async def create_branch(
        self,
        repo_name: str,
        branch_name: str,
        from_branch: str = "main"
    ) -> Dict:
        """
        Create a new branch
        
        Args:
            repo_name: Repository name
            branch_name: New branch name
            from_branch: Branch to create from
        
        Returns:
            Branch data
        """
        owner = self.org or self.username
        
        # Get SHA of the from_branch
        ref_url = f"{self.base_url}/repos/{owner}/{repo_name}/git/refs/heads/{from_branch}"
        ref_response = requests.get(ref_url, headers=self.headers)
        ref_response.raise_for_status()
        
        sha = ref_response.json()["object"]["sha"]
        
        # Create new branch
        create_url = f"{self.base_url}/repos/{owner}/{repo_name}/git/refs"
        data = {
            "ref": f"refs/heads/{branch_name}",
            "sha": sha
        }
        
        response = requests.post(create_url, headers=self.headers, json=data)
        response.raise_for_status()
        
        return response.json()
    
    async def delete_branch(
        self,
        repo_name: str,
        branch_name: str
    ) -> bool:
        """
        Delete a branch
        
        Args:
            repo_name: Repository name
            branch_name: Branch to delete
        
        Returns:
            True if successful
        """
        owner = self.org or self.username
        url = f"{self.base_url}/repos/{owner}/{repo_name}/git/refs/heads/{branch_name}"
        
        response = requests.delete(url, headers=self.headers)
        response.raise_for_status()
        
        return True
    
    async def list_branches(self, repo_name: str) -> List[Dict]:
        """
        List all branches in a repository
        
        Args:
            repo_name: Repository name
        
        Returns:
            List of branch data
        """
        owner = self.org or self.username
        url = f"{self.base_url}/repos/{owner}/{repo_name}/branches"
        
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        
        return response.json()
    
    async def protect_branch(
        self,
        repo_name: str,
        branch_name: str,
        require_reviews: int = 1,
        require_status_checks: bool = True
    ) -> Dict:
        """
        Set branch protection rules
        
        Args:
            repo_name: Repository name
            branch_name: Branch to protect
            require_reviews: Number of required reviewers
            require_status_checks: Require passing status checks
        
        Returns:
            Protection data
        """
        owner = self.org or self.username
        url = f"{self.base_url}/repos/{owner}/{repo_name}/branches/{branch_name}/protection"
        
        data = {
            "required_status_checks": {
                "strict": require_status_checks,
                "contexts": []
            } if require_status_checks else None,
            "enforce_admins": False,
            "required_pull_request_reviews": {
                "required_approving_review_count": require_reviews
            },
            "restrictions": None
        }
        
        response = requests.put(url, headers=self.headers, json=data)
        response.raise_for_status()
        
        return response.json()
    
    # ==========================================
    # ISSUE OPERATIONS
    # ==========================================
    
    async def create_issue(
        self,
        repo_name: str,
        title: str,
        body: str,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None,
        milestone: Optional[int] = None
    ) -> Dict:
        """
        Create a new issue
        
        Args:
            repo_name: Repository name
            title: Issue title
            body: Issue description
            labels: List of label names
            assignees: List of usernames to assign
            milestone: Milestone number
        
        Returns:
            Issue data
        """
        owner = self.org or self.username
        url = f"{self.base_url}/repos/{owner}/{repo_name}/issues"
        
        data = {
            "title": title,
            "body": body,
        }
        
        if labels:
            data["labels"] = labels
        
        if assignees:
            data["assignees"] = assignees
        
        if milestone:
            data["milestone"] = milestone
        
        response = requests.post(url, headers=self.headers, json=data)
        response.raise_for_status()
        
        return response.json()
    
    async def update_issue(
        self,
        repo_name: str,
        issue_number: int,
        title: Optional[str] = None,
        body: Optional[str] = None,
        state: Optional[str] = None,
        labels: Optional[List[str]] = None
    ) -> Dict:
        """
        Update an existing issue
        
        Args:
            repo_name: Repository name
            issue_number: Issue number
            title: New title
            body: New body
            state: New state ("open" or "closed")
            labels: New labels
        
        Returns:
            Updated issue data
        """
        owner = self.org or self.username
        url = f"{self.base_url}/repos/{owner}/{repo_name}/issues/{issue_number}"
        
        data = {}
        
        if title:
            data["title"] = title
        if body:
            data["body"] = body
        if state:
            data["state"] = state
        if labels:
            data["labels"] = labels
        
        response = requests.patch(url, headers=self.headers, json=data)
        response.raise_for_status()
        
        return response.json()
    
    async def close_issue(self, repo_name: str, issue_number: int) -> Dict:
        """
        Close an issue
        
        Args:
            repo_name: Repository name
            issue_number: Issue number
        
        Returns:
            Updated issue data
        """
        return await self.update_issue(repo_name, issue_number, state="closed")
    
    async def list_issues(
        self,
        repo_name: str,
        state: str = "open",
        labels: Optional[List[str]] = None,
        assignee: Optional[str] = None
    ) -> List[Dict]:
        """
        List issues in a repository
        
        Args:
            repo_name: Repository name
            state: Issue state ("open", "closed", "all")
            labels: Filter by labels
            assignee: Filter by assignee
        
        Returns:
            List of issues
        """
        owner = self.org or self.username
        url = f"{self.base_url}/repos/{owner}/{repo_name}/issues"
        
        params = {"state": state}
        
        if labels:
            params["labels"] = ",".join(labels)
        
        if assignee:
            params["assignee"] = assignee
        
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        
        return response.json()
    
    # ==========================================
    # PULL REQUEST OPERATIONS
    # ==========================================
    
    async def create_pull_request(
        self,
        repo_name: str,
        title: str,
        body: str,
        head: str,
        base: str = "main",
        draft: bool = False
    ) -> Dict:
        """
        Create a pull request
        
        Args:
            repo_name: Repository name
            title: PR title
            body: PR description
            head: Branch to merge from
            base: Branch to merge into
            draft: Create as draft PR
        
        Returns:
            PR data
        """
        owner = self.org or self.username
        url = f"{self.base_url}/repos/{owner}/{repo_name}/pulls"
        
        data = {
            "title": title,
            "body": body,
            "head": head,
            "base": base,
            "draft": draft
        }
        
        response = requests.post(url, headers=self.headers, json=data)
        response.raise_for_status()
        
        return response.json()
    
    async def merge_pull_request(
        self,
        repo_name: str,
        pr_number: int,
        commit_title: Optional[str] = None,
        commit_message: Optional[str] = None,
        merge_method: str = "merge"
    ) -> Dict:
        """
        Merge a pull request
        
        Args:
            repo_name: Repository name
            pr_number: PR number
            commit_title: Optional merge commit title
            commit_message: Optional merge commit message
            merge_method: "merge", "squash", or "rebase"
        
        Returns:
            Merge result data
        """
        owner = self.org or self.username
        url = f"{self.base_url}/repos/{owner}/{repo_name}/pulls/{pr_number}/merge"
        
        data = {"merge_method": merge_method}
        
        if commit_title:
            data["commit_title"] = commit_title
        
        if commit_message:
            data["commit_message"] = commit_message
        
        response = requests.put(url, headers=self.headers, json=data)
        response.raise_for_status()
        
        return response.json()
    
    async def list_pull_requests(
        self,
        repo_name: str,
        state: str = "open",
        base: Optional[str] = None
    ) -> List[Dict]:
        """
        List pull requests
        
        Args:
            repo_name: Repository name
            state: PR state ("open", "closed", "all")
            base: Filter by base branch
        
        Returns:
            List of PRs
        """
        owner = self.org or self.username
        url = f"{self.base_url}/repos/{owner}/{repo_name}/pulls"
        
        params = {"state": state}
        
        if base:
            params["base"] = base
        
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        
        return response.json()
    
    async def request_review(
        self,
        repo_name: str,
        pr_number: int,
        reviewers: List[str]
    ) -> Dict:
        """
        Request reviewers for a PR
        
        Args:
            repo_name: Repository name
            pr_number: PR number
            reviewers: List of reviewer usernames
        
        Returns:
            PR data
        """
        owner = self.org or self.username
        url = f"{self.base_url}/repos/{owner}/{repo_name}/pulls/{pr_number}/requested_reviewers"
        
        data = {"reviewers": reviewers}
        
        response = requests.post(url, headers=self.headers, json=data)
        response.raise_for_status()
        
        return response.json()
    
    # ==========================================
    # FILE OPERATIONS
    # ==========================================
    
    async def create_or_update_file(
        self,
        repo_name: str,
        file_path: str,
        content: str,
        commit_message: str,
        branch: str = "main",
        sha: Optional[str] = None
    ) -> Dict:
        """
        Create or update a file in the repository
        
        Args:
            repo_name: Repository name
            file_path: Path to file in repo
            content: File content (will be base64 encoded)
            commit_message: Commit message
            branch: Branch to commit to
            sha: SHA of existing file (for updates)
        
        Returns:
            Commit data
        """
        owner = self.org or self.username
        url = f"{self.base_url}/repos/{owner}/{repo_name}/contents/{file_path}"
        
        # Base64 encode content
        content_bytes = content.encode('utf-8')
        content_base64 = base64.b64encode(content_bytes).decode('utf-8')
        
        data = {
            "message": commit_message,
            "content": content_base64,
            "branch": branch
        }
        
        if sha:
            data["sha"] = sha
        
        response = requests.put(url, headers=self.headers, json=data)
        response.raise_for_status()
        
        return response.json()
    
    async def get_file_content(
        self,
        repo_name: str,
        file_path: str,
        branch: str = "main"
    ) -> Dict:
        """
        Get file content from repository
        
        Args:
            repo_name: Repository name
            file_path: Path to file
            branch: Branch to read from
        
        Returns:
            File data (includes content and sha)
        """
        owner = self.org or self.username
        url = f"{self.base_url}/repos/{owner}/{repo_name}/contents/{file_path}"
        
        params = {"ref": branch}
        
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        # Decode content
        if 'content' in data:
            content_base64 = data['content']
            content = base64.b64decode(content_base64).decode('utf-8')
            data['decoded_content'] = content
        
        return data
    
    # ==========================================
    # WORKFLOW / CI/CD OPERATIONS
    # ==========================================
    
    async def create_workflow_file(
        self,
        repo_name: str,
        workflow_name: str,
        workflow_content: str,
        branch: str = "main"
    ) -> Dict:
        """
        Create a GitHub Actions workflow file
        
        Args:
            repo_name: Repository name
            workflow_name: Workflow filename (e.g., "ci.yml")
            workflow_content: YAML content of workflow
            branch: Branch to create in
        
        Returns:
            Commit data
        """
        file_path = f".github/workflows/{workflow_name}"
        
        return await self.create_or_update_file(
            repo_name=repo_name,
            file_path=file_path,
            content=workflow_content,
            commit_message=f"Add GitHub Actions workflow: {workflow_name}",
            branch=branch
        )
    
    async def trigger_workflow(
        self,
        repo_name: str,
        workflow_id: str,
        ref: str = "main",
        inputs: Optional[Dict] = None
    ) -> bool:
        """
        Trigger a workflow dispatch
        
        Args:
            repo_name: Repository name
            workflow_id: Workflow filename or ID
            ref: Git ref (branch/tag)
            inputs: Workflow inputs
        
        Returns:
            True if successful
        """
        owner = self.org or self.username
        url = f"{self.base_url}/repos/{owner}/{repo_name}/actions/workflows/{workflow_id}/dispatches"
        
        data = {"ref": ref}
        
        if inputs:
            data["inputs"] = inputs
        
        response = requests.post(url, headers=self.headers, json=data)
        response.raise_for_status()
        
        return True
    
    # ==========================================
    # LABEL OPERATIONS
    # ==========================================
    
    async def create_labels(
        self,
        repo_name: str,
        labels: List[Dict[str, str]]
    ) -> List[Dict]:
        """
        Create multiple labels
        
        Args:
            repo_name: Repository name
            labels: List of label dicts with 'name', 'color', 'description'
        
        Returns:
            List of created labels
        """
        owner = self.org or self.username
        url = f"{self.base_url}/repos/{owner}/{repo_name}/labels"
        
        created = []
        
        for label in labels:
            response = requests.post(url, headers=self.headers, json=label)
            
            if response.status_code == 201:
                created.append(response.json())
        
        return created
    
    # ==========================================
    # UTILITY METHODS
    # ==========================================
    
    async def check_rate_limit(self) -> Dict:
        """
        Check GitHub API rate limit status
        
        Returns:
            Rate limit data
        """
        url = f"{self.base_url}/rate_limit"
        
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        
        return response.json()
    
    async def get_authenticated_user(self) -> Dict:
        """
        Get authenticated user information
        
        Returns:
            User data
        """
        url = f"{self.base_url}/user"
        
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        
        return response.json()


# ==========================================
# CONVENIENCE FUNCTIONS
# ==========================================

def create_github_client(token: str = None, username: str = None) -> GitHubClient:
    """
    Create GitHub client with env variables
    
    Args:
        token: GitHub token (falls back to env)
        username: GitHub username (falls back to env)
    
    Returns:
        GitHubClient instance
    """
    import os
    
    token = token or os.getenv("GITHUB_TOKEN")
    username = username or os.getenv("GITHUB_USERNAME")
    org = os.getenv("GITHUB_ORG")
    
    if not token or not username:
        raise ValueError("GitHub token and username required")
    
    return GitHubClient(token=token, username=username, org=org)


# ==========================================
# EXAMPLE USAGE
# ==========================================

if __name__ == "__main__":
    async def example():
        # Create client
        client = create_github_client()
        
        # Create repository
        repo = await client.create_repository(
            name="test-repo",
            description="Test repository created by automation",
            private=False
        )
        print(f"Created repo: {repo['html_url']}")
        
        # Create issue
        issue = await client.create_issue(
            repo_name="test-repo",
            title="Implement feature X",
            body="We need to implement feature X",
            labels=["enhancement"]
        )
        print(f"Created issue #{issue['number']}")
        
        # Create branch
        branch = await client.create_branch(
            repo_name="test-repo",
            branch_name="feature/x",
            from_branch="main"
        )
        print(f"Created branch: feature/x")
        
        # Create PR
        pr = await client.create_pull_request(
            repo_name="test-repo",
            title="Add feature X",
            body="This PR implements feature X",
            head="feature/x",
            base="main"
        )
        print(f"Created PR #{pr['number']}")
        
        print("Example complete!")
    
    # Run example
    asyncio.run(example())
