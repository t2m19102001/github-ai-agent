#!/usr/bin/env python3
"""
GitHub Repository Operations
Advanced repository management for GitHub AI Agent
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from src.utils.logger import get_logger
from src.github.api_client import get_github_client, RepositoryInfo
from src.security.guardrails import security_guardrails, SecurityError

logger = get_logger(__name__)


@dataclass
class CloneResult:
    """Repository cloning result"""
    success: bool
    repo_path: Optional[str]
    error: Optional[str]
    clone_time: float
    repo_info: Optional[RepositoryInfo]


@dataclass
class BranchInfo:
    """Branch information"""
    name: str
    commit_sha: str
    commit_message: str
    author: str
    is_default: bool
    is_protected: bool


@dataclass
class CommitInfo:
    """Commit information"""
    sha: str
    message: str
    author: str
    date: datetime
    files_changed: int
    additions: int
    deletions: int


class RepositoryOperations:
    """Advanced repository operations manager"""
    
    def __init__(self, workspace_root: str = "/tmp/github-agent-workspace"):
        self.workspace_root = Path(workspace_root)
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.github_client = get_github_client()
        self.cloned_repos: Dict[str, str] = {}  # repo_name -> local_path
        
        logger.info(f"RepositoryOperations initialized with workspace: {workspace_root}")
    
    def clone_repository(self, repo_name: str, branch: Optional[str] = None, shallow: bool = True) -> CloneResult:
        """Clone repository with security validation"""
        start_time = datetime.now()
        
        try:
            # Validate repository access
            if not self.github_client:
                return CloneResult(False, None, "GitHub client not available", 0, None)
            
            # Get repository info
            repo_info = self.github_client.get_repository_info(repo_name)
            if not repo_info:
                return CloneResult(False, None, f"Repository not found: {repo_name}", 0, None)
            
            # Security validation
            validation = security_guardrails.validate_repository_access(repo_info.clone_url, "read")
            if not validation["valid"]:
                return CloneResult(False, None, f"Access denied: {validation['reason']}", 0, repo_info)
            
            # Create local directory
            local_path = self.workspace_root / repo_name.replace("/", "_")
            if local_path.exists():
                shutil.rmtree(local_path)
            
            local_path.mkdir(parents=True, exist_ok=True)
            
            # Clone repository
            clone_url = repo_info.clone_url
            if branch:
                clone_cmd = ["git", "clone", "--branch", branch]
                if shallow:
                    clone_cmd.append("--depth=1")
                clone_cmd.extend([clone_url, str(local_path)])
            else:
                clone_cmd = ["git", "clone"]
                if shallow:
                    clone_cmd.append("--depth=1")
                clone_cmd.extend([clone_url, str(local_path)])
            
            result = subprocess.run(
                clone_cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode != 0:
                return CloneResult(False, None, f"Git clone failed: {result.stderr}", 0, repo_info)
            
            # Store cloned repository info
            self.cloned_repos[repo_name] = str(local_path)
            
            clone_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"Successfully cloned {repo_name} to {local_path} in {clone_time:.2f}s")
            
            return CloneResult(True, str(local_path), None, clone_time, repo_info)
            
        except subprocess.TimeoutExpired:
            return CloneResult(False, None, "Clone timeout (5min)", 0, None)
        except SecurityError as e:
            return CloneResult(False, None, f"Security error: {str(e)}", 0, None)
        except Exception as e:
            return CloneResult(False, None, f"Clone failed: {str(e)}", 0, None)
    
    def get_repository_branches(self, repo_name: str) -> List[BranchInfo]:
        """Get all branches information"""
        if not self.github_client:
            return []
        
        try:
            repo_info = self.github_client.get_repository_info(repo_name)
            if not repo_info:
                return []
            
            # Use PyGitHub to get branches
            if hasattr(self.github_client.client, 'get_repo'):
                repo = self.github_client.client.get_repo(repo_name)
                branches = []
                
                for branch in repo.get_branches():
                    branches.append(BranchInfo(
                        name=branch.name,
                        commit_sha=branch.commit.sha,
                        commit_message=branch.commit.commit.message,
                        author=branch.commit.commit.author.name,
                        is_default=branch.name == repo_info.default_branch,
                        is_protected=branch.protected
                    ))
                
                return branches
            
        except Exception as e:
            logger.error(f"Failed to get branches: {e}")
        
        return []
    
    def create_feature_branch(self, repo_name: str, branch_name: str, from_branch: str = "main") -> bool:
        """Create a new feature branch"""
        try:
            # Create branch via GitHub API
            if self.github_client:
                success = self.github_client.create_branch(repo_name, branch_name, from_branch)
                
                if success:
                    logger.info(f"Created feature branch: {branch_name}")
                    return True
            
        except Exception as e:
            logger.error(f"Failed to create feature branch: {e}")
        
        return False
    
    def get_commit_history(self, repo_name: str, branch: str = "main", limit: int = 10) -> List[CommitInfo]:
        """Get commit history"""
        if not self.github_client:
            return []
        
        try:
            repo_info = self.github_client.get_repository_info(repo_name)
            if not repo_info:
                return []
            
            # Use PyGitHub to get commits
            if hasattr(self.github_client.client, 'get_repo'):
                repo = self.github_client.client.get_repo(repo_name)
                commits = []
                
                for commit in repo.get_commits(sha=branch)[:limit]:
                    commits.append(CommitInfo(
                        sha=commit.sha,
                        message=commit.commit.message,
                        author=commit.commit.author.name,
                        date=commit.commit.author.date,
                        files_changed=len(commit.files) if commit.files else 0,
                        additions=sum(f.additions for f in commit.files) if commit.files else 0,
                        deletions=sum(f.deletions for f in commit.files) if commit.files else 0
                    ))
                
                return commits
            
        except Exception as e:
            logger.error(f"Failed to get commit history: {e}")
        
        return []
    
    def analyze_repository_structure(self, repo_name: str) -> Dict[str, Any]:
        """Analyze repository structure and statistics"""
        local_path = self.cloned_repos.get(repo_name)
        if not local_path or not Path(local_path).exists():
            return {"error": "Repository not cloned"}
        
        try:
            repo_path = Path(local_path)
            
            # File statistics
            all_files = list(repo_path.rglob("*"))
            files = [f for f in all_files if f.is_file()]
            
            # Language breakdown
            language_counts = {}
            total_lines = 0
            
            for file_path in files:
                # Simple language detection by extension
                ext = file_path.suffix.lower()
                if ext:
                    language_counts[ext] = language_counts.get(ext, 0) + 1
                
                # Count lines (only for text files)
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = len(f.readlines())
                        total_lines += lines
                except:
                    pass
            
            # Directory structure
            directories = [d for d in all_files if d.is_dir()]
            
            # Git statistics
            git_stats = self._get_git_statistics(local_path)
            
            return {
                "repository": repo_name,
                "total_files": len(files),
                "total_directories": len(directories),
                "total_lines": total_lines,
                "languages": language_counts,
                "git_statistics": git_stats,
                "analysis_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze repository: {e}")
            return {"error": str(e)}
    
    def _get_git_statistics(self, repo_path: str) -> Dict[str, Any]:
        """Get git statistics for local repository"""
        try:
            result = subprocess.run(
                ["git", "log", "--oneline", "--count"],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            
            commit_count = int(result.stdout.strip()) if result.returncode == 0 else 0
            
            # Get contributors
            result = subprocess.run(
                ["git", "shortlog", "-sn"],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            
            contributors = []
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        parts = line.split('\t')
                        if len(parts) == 2:
                            contributors.append({
                                "commits": int(parts[0]),
                                "name": parts[1].strip()
                            })
            
            return {
                "total_commits": commit_count,
                "contributors": contributors
            }
            
        except Exception as e:
            logger.warning(f"Failed to get git statistics: {e}")
            return {"total_commits": 0, "contributors": []}
    
    def cleanup_repository(self, repo_name: str) -> bool:
        """Clean up cloned repository"""
        local_path = self.cloned_repos.get(repo_name)
        if not local_path:
            return True
        
        try:
            repo_path = Path(local_path)
            if repo_path.exists():
                shutil.rmtree(repo_path)
            
            del self.cloned_repos[repo_name]
            logger.info(f"Cleaned up repository: {repo_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cleanup repository: {e}")
            return False
    
    def get_cloned_repositories(self) -> List[str]:
        """Get list of cloned repositories"""
        return list(self.cloned_repos.keys())
    
    def get_repository_path(self, repo_name: str) -> Optional[str]:
        """Get local path for cloned repository"""
        return self.cloned_repos.get(repo_name)
    
    def cleanup_all(self) -> int:
        """Clean up all cloned repositories"""
        count = 0
        for repo_name in list(self.cloned_repos.keys()):
            if self.cleanup_repository(repo_name):
                count += 1
        
        logger.info(f"Cleaned up {count} repositories")
        return count
    
    def get_workspace_stats(self) -> Dict[str, Any]:
        """Get workspace statistics"""
        return {
            "workspace_root": str(self.workspace_root),
            "cloned_repositories": len(self.cloned_repos),
            "repository_list": list(self.cloned_repos.keys()),
            "workspace_size_mb": self._get_workspace_size()
        }
    
    def _get_workspace_size(self) -> float:
        """Calculate workspace size in MB"""
        try:
            total_size = 0
            for root, dirs, files in os.walk(self.workspace_root):
                for file in files:
                    file_path = os.path.join(root, file)
                    if os.path.isfile(file_path):
                        total_size += os.path.getsize(file_path)
            
            return total_size / (1024 * 1024)  # Convert to MB
            
        except Exception as e:
            logger.warning(f"Failed to calculate workspace size: {e}")
            return 0.0


# Global repository operations instance
_repo_operations: Optional[RepositoryOperations] = None


def get_repository_operations() -> RepositoryOperations:
    """Get global repository operations instance"""
    global _repo_operations
    if _repo_operations is None:
        _repo_operations = RepositoryOperations()
    return _repo_operations


def initialize_repository_operations(workspace_root: str) -> RepositoryOperations:
    """Initialize repository operations with custom workspace"""
    global _repo_operations
    _repo_operations = RepositoryOperations(workspace_root)
    return _repo_operations
