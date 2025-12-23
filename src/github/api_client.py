#!/usr/bin/env python3
"""
GitHub API Client for GitHub AI Agent
Provides comprehensive GitHub API integration with PyGitHub
"""

import os
import time
import asyncio
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime, timedelta

# Try to import PyGitHub, fallback to mock implementation
try:
    from github import Github, GithubException, UnknownObjectException
    from github.Repository import Repository
    from github.Issue import Issue
    from github.PullRequest import PullRequest
    PYGITHUB_AVAILABLE = True
except ImportError:
    PYGITHUB_AVAILABLE = False
    # Create mock classes for fallback
    class Github:
        def __init__(self, token):
            self.token = token
        def get_repo(self, repo_name):
            raise Exception("PyGitHub not installed")
    class GithubException(Exception):
        pass
    class UnknownObjectException(Exception):
        pass

from src.utils.logger import get_logger
from src.core.config import GITHUB_TOKEN, GITHUB_APP_ID, GITHUB_APP_KEY

logger = get_logger(__name__)


@dataclass
class RateLimitInfo:
    """GitHub API rate limit information"""
    remaining: int
    limit: int
    reset_time: datetime
    used: int


@dataclass
class RepositoryInfo:
    """Repository information"""
    name: str
    full_name: str
    description: str
    language: str
    stars: int
    forks: int
    open_issues: int
    clone_url: str
    ssh_url: str
    default_branch: str
    size: int
    created_at: datetime
    updated_at: datetime


class GitHubAPIClient:
    """Comprehensive GitHub API client"""
    
    def __init__(self, token: Optional[str] = None, app_id: Optional[str] = None, app_key: Optional[str] = None):
        self.token = token or GITHUB_TOKEN
        self.app_id = app_id or GITHUB_APP_ID
        self.app_key = app_key or GITHUB_APP_KEY
        self.client = None
        self.rate_limit_info: Optional[RateLimitInfo] = None
        self.last_request_time = 0
        self.request_count = 0
        
        # Initialize client
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize GitHub client with authentication"""
        try:
            if self.token:
                self.client = Github(self.token)
                logger.info("GitHub client initialized with personal access token")
            elif self.app_id and self.app_key:
                # App authentication would require jwt and github apps integration
                logger.warning("GitHub App authentication not fully implemented")
                self.client = Github(self.token)  # Fallback to token
            else:
                logger.error("No GitHub authentication provided")
                raise ValueError("GitHub token or app credentials required")
                
            # Test connection
            self.client.get_user().login
            logger.info("GitHub API connection successful")
            
        except Exception as e:
            logger.error(f"Failed to initialize GitHub client: {e}")
            raise
    
    def _check_rate_limit(self):
        """Check and update rate limit information"""
        if not PYGITHUB_AVAILABLE:
            return
        
        try:
            rate_limit = self.client.get_rate_limit()
            core = rate_limit.core
            
            self.rate_limit_info = RateLimitInfo(
                remaining=core.remaining,
                limit=core.limit,
                reset_time=datetime.fromtimestamp(core.reset),
                used=core.limit - core.remaining
            )
            
            # Log warning if rate limit is low
            if self.rate_limit_info.remaining < 100:
                logger.warning(f"GitHub API rate limit low: {self.rate_limit_info.remaining}/{self.rate_limit_info.limit}")
                
        except Exception as e:
            logger.warning(f"Failed to check rate limit: {e}")
    
    def _wait_for_rate_limit(self):
        """Wait if rate limit is exceeded"""
        if not self.rate_limit_info:
            return
        
        if self.rate_limit_info.remaining <= 1:
            wait_time = (self.rate_limit_info.reset_time - datetime.now()).total_seconds()
            if wait_time > 0:
                logger.info(f"Rate limit exceeded, waiting {wait_time:.0f}s")
                time.sleep(min(wait_time, 60))  # Don't wait more than 60s
    
    def get_repository_info(self, repo_name: str) -> Optional[RepositoryInfo]:
        """Get comprehensive repository information"""
        if not PYGITHUB_AVAILABLE:
            logger.error("PyGitHub not available")
            return None
        
        try:
            self._check_rate_limit()
            self._wait_for_rate_limit()
            
            repo = self.client.get_repo(repo_name)
            
            return RepositoryInfo(
                name=repo.name,
                full_name=repo.full_name,
                description=repo.description or "",
                language=repo.language or "",
                stars=repo.stargazers_count,
                forks=repo.forks_count,
                open_issues=repo.open_issues_count,
                clone_url=repo.clone_url,
                ssh_url=repo.ssh_url,
                default_branch=repo.default_branch,
                size=repo.size,
                created_at=repo.created_at,
                updated_at=repo.updated_at
            )
            
        except UnknownObjectException:
            logger.error(f"Repository not found: {repo_name}")
            return None
        except Exception as e:
            logger.error(f"Failed to get repository info: {e}")
            return None
    
    def list_repository_files(self, repo_name: str, branch: Optional[str] = None, path: str = "") -> List[str]:
        """List files in repository"""
        if not PYGITHUB_AVAILABLE:
            return []
        
        try:
            self._check_rate_limit()
            self._wait_for_rate_limit()
            
            repo = self.client.get_repo(repo_name)
            if branch:
                repo = repo.get_branch(branch)
            
            contents = repo.get_contents(path)
            files = []
            
            while contents:
                content = contents.pop(0)
                if content.type == "dir":
                    contents.extend(repo.get_contents(content.path))
                else:
                    files.append(content.path)
            
            return files
            
        except Exception as e:
            logger.error(f"Failed to list repository files: {e}")
            return []
    
    def get_file_content(self, repo_name: str, file_path: str, branch: Optional[str] = None) -> Optional[str]:
        """Get file content from repository"""
        if not PYGITHUB_AVAILABLE:
            return None
        
        try:
            self._check_rate_limit()
            self._wait_for_rate_limit()
            
            repo = self.client.get_repo(repo_name)
            
            if branch:
                content = repo.get_file_contents(file_path, ref=branch)
            else:
                content = repo.get_file_contents(file_path)
            
            if content.type == "file":
                return content.decoded_content.decode('utf-8')
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get file content: {e}")
            return None
    
    def create_branch(self, repo_name: str, branch_name: str, from_branch: str = "main") -> bool:
        """Create a new branch"""
        if not PYGITHUB_AVAILABLE:
            return False
        
        try:
            self._check_rate_limit()
            self._wait_for_rate_limit()
            
            repo = self.client.get_repo(repo_name)
            
            # Get source branch reference
            source_branch = repo.get_branch(from_branch)
            
            # Create new branch
            repo.create_git_ref(f"refs/heads/{branch_name}", source_branch.commit.sha)
            
            logger.info(f"Created branch: {branch_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create branch: {e}")
            return False
    
    def create_pull_request(self, repo_name: str, title: str, body: str, head: str, base: str = "main") -> Optional[str]:
        """Create a pull request"""
        if not PYGITHUB_AVAILABLE:
            return None
        
        try:
            self._check_rate_limit()
            self._wait_for_rate_limit()
            
            repo = self.client.get_repo(repo_name)
            
            pr = repo.create_pull_request(title=title, body=body, head=head, base=base)
            
            logger.info(f"Created PR: {pr.html_url}")
            return pr.html_url
            
        except Exception as e:
            logger.error(f"Failed to create pull request: {e}")
            return None
    
    def list_issues(self, repo_name: str, state: str = "open", labels: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """List repository issues"""
        if not PYGITHUB_AVAILABLE:
            return []
        
        try:
            self._check_rate_limit()
            self._wait_for_rate_limit()
            
            repo = self.client.get_repo(repo_name)
            
            issues = repo.get_issues(state=state, labels=labels)
            
            issue_list = []
            for issue in issues:
                # Skip pull requests
                if issue.pull_request:
                    continue
                
                issue_list.append({
                    "number": issue.number,
                    "title": issue.title,
                    "body": issue.body or "",
                    "state": issue.state,
                    "created_at": issue.created_at,
                    "updated_at": issue.updated_at,
                    "labels": [label.name for label in issue.labels],
                    "user": issue.user.login,
                    "html_url": issue.html_url
                })
            
            return issue_list
            
        except Exception as e:
            logger.error(f"Failed to list issues: {e}")
            return []
    
    def create_issue_comment(self, repo_name: str, issue_number: int, body: str) -> bool:
        """Create comment on issue"""
        if not PYGITHUB_AVAILABLE:
            return False
        
        try:
            self._check_rate_limit()
            self._wait_for_rate_limit()
            
            repo = self.client.get_repo(repo_name)
            issue = repo.get_issue(issue_number)
            
            issue.create_comment(body)
            
            logger.info(f"Created comment on issue #{issue_number}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create issue comment: {e}")
            return False
    
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limit status"""
        if not PYGITHUB_AVAILABLE:
            return {"error": "PyGitHub not available"}
        
        self._check_rate_limit()
        
        if not self.rate_limit_info:
            return {"error": "Rate limit info not available"}
        
        return {
            "remaining": self.rate_limit_info.remaining,
            "limit": self.rate_limit_info.limit,
            "used": self.rate_limit_info.used,
            "reset_time": self.rate_limit_info.reset_time.isoformat(),
            "reset_in_seconds": (self.rate_limit_info.reset_time - datetime.now()).total_seconds(),
            "usage_percentage": (self.rate_limit_info.used / self.rate_limit_info.limit) * 100
        }
    
    def get_api_stats(self) -> Dict[str, Any]:
        """Get API usage statistics"""
        return {
            "total_requests": self.request_count,
            "last_request_time": self.last_request_time,
            "rate_limit_info": self.get_rate_limit_status(),
            "client_type": "PyGitHub" if PYGITHUB_AVAILABLE else "Mock",
            "authenticated": bool(self.token or self.app_id)
        }


# Global GitHub client instance
_github_client: Optional[GitHubAPIClient] = None


def get_github_client() -> Optional[GitHubAPIClient]:
    """Get global GitHub client instance"""
    global _github_client
    if _github_client is None:
        try:
            _github_client = GitHubAPIClient()
        except Exception as e:
            logger.error(f"Failed to create GitHub client: {e}")
    return _github_client


def initialize_github_client(token: Optional[str] = None) -> GitHubAPIClient:
    """Initialize GitHub client with custom token"""
    global _github_client
    _github_client = GitHubAPIClient(token=token)
    return _github_client


# Decorator for rate limit handling
def with_rate_limit(func):
    """Decorator to handle rate limiting"""
    def wrapper(*args, **kwargs):
        client = get_github_client()
        if client:
            client._check_rate_limit()
            client._wait_for_rate_limit()
        return func(*args, **kwargs)
    return wrapper
