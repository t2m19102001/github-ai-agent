#!/usr/bin/env python3
"""
GitHub Tools Module
Provides GitHub API operations for agents
"""

import os
import json
import requests
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta

try:
    from utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class GitHubIssue:
    """GitHub issue data structure"""
    id: int
    number: int
    title: str
    body: str
    state: str
    created_at: datetime
    updated_at: datetime
    user: str
    labels: List[str]
    assignees: List[str]
    milestone: Optional[str]
    comments_count: int
    url: str


@dataclass
class GitHubPullRequest:
    """GitHub pull request data structure"""
    id: int
    number: int
    title: str
    body: str
    state: str
    created_at: datetime
    updated_at: datetime
    user: str
    base_branch: str
    head_branch: str
    labels: List[str]
    assignees: List[str]
    reviewers: List[str]
    comments_count: int
    url: str
    diff_url: str


@dataclass
class GitHubRepository:
    """GitHub repository data structure"""
    name: str
    full_name: str
    description: str
    language: str
    stars: int
    forks: int
    open_issues: int
    default_branch: str
    clone_url: str
    created_at: datetime
    updated_at: datetime


class GitHubTools:
    """GitHub API operations toolkit"""
    
    def __init__(self, token: str, repo: str = None):
        self.token = token
        self.repo = repo
        self.base_url = "https://api.github.com"
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GitHub-AI-Agent/1.0"
        })
        
        logger.info(f"Initialized GitHubTools for repo: {repo}")
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None) -> requests.Response:
        """Make authenticated request to GitHub API"""
        url = f"{self.base_url}/{endpoint}"
        
        try:
            if method.upper() == "GET":
                response = self.session.get(url, params=data, timeout=30)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data, timeout=30)
            elif method.upper() == "PUT":
                response = self.session.put(url, json=data, timeout=30)
            elif method.upper() == "PATCH":
                response = self.session.patch(url, json=data, timeout=30)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            # Handle rate limiting
            if response.status_code == 403:
                reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
                wait_time = max(0, reset_time - int(datetime.now().timestamp()))
                logger.warning(f"Rate limited. Waiting {wait_time} seconds")
                if wait_time > 0:
                    import time
                    time.sleep(wait_time)
                    return self._make_request(method, endpoint, data)
            
            response.raise_for_status()
            return response
            
        except requests.exceptions.RequestException as e:
            logger.error(f"GitHub API request failed: {e}")
            raise
    
    def get_repository(self, owner: str, repo: str) -> Optional[GitHubRepository]:
        """Get repository information"""
        try:
            response = self._make_request("GET", f"repos/{owner}/{repo}")
            data = response.json()
            
            return GitHubRepository(
                name=data["name"],
                full_name=data["full_name"],
                description=data.get("description", ""),
                language=data.get("language", ""),
                stars=data["stargazers_count"],
                forks=data["forks_count"],
                open_issues=data["open_issues_count"],
                default_branch=data["default_branch"],
                clone_url=data["clone_url"],
                created_at=datetime.strptime(data["created_at"], "%Y-%m-%dT%H:%M:%SZ"),
                updated_at=datetime.strptime(data["updated_at"], "%Y-%m-%dT%H:%M:%SZ")
            )
            
        except Exception as e:
            logger.error(f"Error getting repository: {e}")
            return None
    
    def get_issues(self, owner: str, repo: str, state: str = "open", 
                  labels: List[str] = None, limit: int = 100) -> List[GitHubIssue]:
        """Get issues from repository"""
        try:
            params = {"state": state, "per_page": min(limit, 100)}
            if labels:
                params["labels"] = ",".join(labels)
            
            response = self._make_request("GET", f"repos/{owner}/{repo}/issues", params)
            data = response.json()
            
            issues = []
            for item in data:
                # Skip pull requests
                if "pull_request" in item:
                    continue
                
                # Parse labels
                issue_labels = [label["name"] for label in item.get("labels", [])]
                
                # Parse assignees
                assignees = [assignee["login"] for assignee in item.get("assignees", [])]
                
                # Parse milestone
                milestone = item.get("milestone", {}).get("title") if item.get("milestone") else None
                
                issues.append(GitHubIssue(
                    id=item["id"],
                    number=item["number"],
                    title=item["title"],
                    body=item.get("body", ""),
                    state=item["state"],
                    created_at=datetime.strptime(item["created_at"], "%Y-%m-%dT%H:%M:%SZ"),
                    updated_at=datetime.strptime(item["updated_at"], "%Y-%m-%dT%H:%M:%SZ"),
                    user=item["user"]["login"],
                    labels=issue_labels,
                    assignees=assignees,
                    milestone=milestone,
                    comments_count=item["comments"],
                    url=item["html_url"]
                ))
            
            logger.info(f"Retrieved {len(issues)} issues from {owner}/{repo}")
            return issues
            
        except Exception as e:
            logger.error(f"Error getting issues: {e}")
            return []
    
    def get_pull_requests(self, owner: str, repo: str, state: str = "open", 
                       limit: int = 100) -> List[GitHubPullRequest]:
        """Get pull requests from repository"""
        try:
            params = {"state": state, "per_page": min(limit, 100)}
            
            response = self._make_request("GET", f"repos/{owner}/{repo}/pulls", params)
            data = response.json()
            
            prs = []
            for item in data:
                # Parse labels
                pr_labels = [label["name"] for label in item.get("labels", [])]
                
                # Parse assignees
                assignees = [assignee["login"] for assignee in item.get("assignees", [])]
                
                # Parse reviewers
                reviewers = [reviewer["login"] for reviewer in item.get("requested_reviewers", [])]
                
                prs.append(GitHubPullRequest(
                    id=item["id"],
                    number=item["number"],
                    title=item["title"],
                    body=item.get("body", ""),
                    state=item["state"],
                    created_at=datetime.strptime(item["created_at"], "%Y-%m-%dT%H:%M:%SZ"),
                    updated_at=datetime.strptime(item["updated_at"], "%Y-%m-%dT%H:%M:%SZ"),
                    user=item["user"]["login"],
                    base_branch=item["base"]["ref"],
                    head_branch=item["head"]["ref"],
                    labels=pr_labels,
                    assignees=assignees,
                    reviewers=reviewers,
                    comments_count=item["comments"],
                    url=item["html_url"],
                    diff_url=item["diff_url"]
                ))
            
            logger.info(f"Retrieved {len(prs)} PRs from {owner}/{repo}")
            return prs
            
        except Exception as e:
            logger.error(f"Error getting pull requests: {e}")
            return []
    
    def create_issue_comment(self, owner: str, repo: str, issue_number: int, 
                         body: str) -> bool:
        """Create comment on issue"""
        try:
            data = {"body": body}
            response = self._make_request("POST", 
                                     f"repos/{owner}/{repo}/issues/{issue_number}/comments", 
                                     data)
            
            success = response.status_code == 201
            if success:
                logger.info(f"Created comment on issue #{issue_number}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error creating issue comment: {e}")
            return False
    
    def create_pull_request_comment(self, owner: str, repo: str, pr_number: int, 
                               body: str) -> bool:
        """Create comment on pull request"""
        try:
            data = {"body": body}
            response = self._make_request("POST", 
                                     f"repos/{owner}/{repo}/pulls/{pr_number}/comments", 
                                     data)
            
            success = response.status_code == 201
            if success:
                logger.info(f"Created comment on PR #{pr_number}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error creating PR comment: {e}")
            return False
    
    def add_label_to_issue(self, owner: str, repo: str, issue_number: int, 
                         labels: List[str]) -> bool:
        """Add labels to issue"""
        try:
            data = {"labels": labels}
            response = self._make_request("POST", 
                                     f"repos/{owner}/{repo}/issues/{issue_number}/labels", 
                                     data)
            
            success = response.status_code == 200
            if success:
                logger.info(f"Added labels {labels} to issue #{issue_number}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error adding labels: {e}")
            return False
    
    def assign_issue(self, owner: str, repo: str, issue_number: int, 
                   assignees: List[str]) -> bool:
        """Assign issue to users"""
        try:
            data = {"assignees": assignees}
            response = self._make_request("POST", 
                                     f"repos/{owner}/{repo}/issues/{issue_number}/assignees", 
                                     data)
            
            success = response.status_code == 201
            if success:
                logger.info(f"Assigned issue #{issue_number} to {assignees}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error assigning issue: {e}")
            return False
    
    def close_issue(self, owner: str, repo: str, issue_number: int, 
                  comment: str = None) -> bool:
        """Close issue"""
        try:
            # Add comment if provided
            if comment:
                self.create_issue_comment(owner, repo, issue_number, comment)
            
            # Close issue
            data = {"state": "closed"}
            response = self._make_request("PATCH", 
                                     f"repos/{owner}/{repo}/issues/{issue_number}", 
                                     data)
            
            success = response.status_code == 200
            if success:
                logger.info(f"Closed issue #{issue_number}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error closing issue: {e}")
            return False
    
    def get_file_content(self, owner: str, repo: str, path: str, 
                      ref: str = "main") -> Optional[str]:
        """Get file content from repository"""
        try:
            response = self._make_request("GET", 
                                     f"repos/{owner}/{repo}/contents/{path}", 
                                     {"ref": ref})
            
            if response.status_code == 200:
                data = response.json()
                if data.get("content"):
                    import base64
                    content = base64.b64decode(data["content"]).decode('utf-8')
                    return content
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting file content: {e}")
            return None
    
    def create_issue(self, owner: str, repo: str, title: str, body: str, 
                   labels: List[str] = None, assignees: List[str] = None) -> Optional[int]:
        """Create new issue"""
        try:
            data = {
                "title": title,
                "body": body
            }
            
            if labels:
                data["labels"] = labels
            if assignees:
                data["assignees"] = assignees
            
            response = self._make_request("POST", f"repos/{owner}/{repo}/issues", data)
            
            if response.status_code == 201:
                issue_data = response.json()
                issue_number = issue_data["number"]
                logger.info(f"Created issue #{issue_number}: {title}")
                return issue_number
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating issue: {e}")
            return None
    
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get API rate limit status"""
        try:
            response = self._make_request("GET", "rate_limit")
            data = response.json()
            
            return {
                "core_limit": data["resources"]["core"]["limit"],
                "core_remaining": data["resources"]["core"]["remaining"],
                "core_reset": datetime.fromtimestamp(data["resources"]["core"]["reset"]),
                "search_limit": data["resources"]["search"]["limit"],
                "search_remaining": data["resources"]["search"]["remaining"],
                "search_reset": datetime.fromtimestamp(data["resources"]["search"]["reset"])
            }
            
        except Exception as e:
            logger.error(f"Error getting rate limit status: {e}")
            return {}


# Global instance
_github_tools: Optional[GitHubTools] = None


def get_github_tools(token: str, repo: str = None) -> GitHubTools:
    """Get global GitHubTools instance"""
    global _github_tools
    if _github_tools is None:
        _github_tools = GitHubTools(token, repo)
    return _github_tools


# Test function
def test_github_tools():
    """Test GitHubTools functionality"""
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN environment variable not set")
        return
    
    try:
        github = GitHubTools(token, "torvalds/linux")
        
        # Test repository info
        repo = github.get_repository("torvalds", "linux")
        if repo:
            print(f"Repository: {repo.full_name}")
            print(f"Stars: {repo.stars}")
            print(f"Language: {repo.language}")
        
        # Test rate limit
        rate_limit = github.get_rate_limit_status()
        print(f"Rate limit remaining: {rate_limit.get('core_remaining', 'Unknown')}")
        
    except Exception as e:
        print(f"Error testing GitHubTools: {e}")


if __name__ == "__main__":
    test_github_tools()
