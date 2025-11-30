#!/usr/bin/env python3
"""
Git Operations Tool
Provides safe Git operations for AI agents
"""

import subprocess
import os
from typing import Optional, Dict, Any
from src.utils.logger import get_logger

logger = get_logger(__name__)


def ensure_git_repo():
    """Ensure git repository is initialized"""
    if not os.path.exists('.git'):
        logger.info("📦 Initializing git repository...")
        subprocess.run(['git', 'init'], check=True)
        return True
    return False


def git_commit(message: str) -> Dict[str, Any]:
    """
    Stage all changes and commit with message
    
    Args:
        message: Commit message
    
    Returns:
        Dict with success status and output
    """
    try:
        # Ensure git is initialized
        if ensure_git_repo():
            return {
                "success": True,
                "output": "✅ Initialized new git repository. Run commit again to add changes."
            }
        
        # Stage all changes
        result_add = subprocess.run(
            ["git", "add", "."],
            check=True,
            capture_output=True,
            text=True
        )
        logger.info("✅ Staged all changes")
        
        # Commit
        result_commit = subprocess.run(
            ["git", "commit", "-m", message],
            check=True,
            capture_output=True,
            text=True
        )
        logger.info(f"✅ Committed: {message}")
        
        # Push
        result_push = subprocess.run(
            ["git", "push"],
            check=True,
            capture_output=True,
            text=True
        )
        logger.info("✅ Pushed to remote")
        
        return {
            "success": True,
            "message": "Committed and pushed successfully",
            "commit_message": message,
            "output": result_commit.stdout
        }
        
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr if e.stderr else str(e)
        logger.error(f"❌ Git commit failed: {error_msg}")
        return {
            "success": False,
            "error": error_msg,
            "message": "Commit failed"
        }


def git_create_branch(name: str) -> Dict[str, Any]:
    """
    Create and checkout a new branch
    
    Args:
        name: Branch name
    
    Returns:
        Dict with success status and output
    """
    try:
        # Ensure git is initialized
        if ensure_git_repo():
            return {
                "success": True,
                "output": "✅ Initialized new git repository. Run branch creation again."
            }
        
        result = subprocess.run(
            ["git", "checkout", "-b", name],
            check=True,
            capture_output=True,
            text=True
        )
        logger.info(f"✅ Created and checked out branch: {name}")
        
        return {
            "success": True,
            "message": f"Branch '{name}' created successfully",
            "branch": name,
            "output": result.stdout
        }
        
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr if e.stderr else str(e)
        logger.error(f"❌ Branch creation failed: {error_msg}")
        return {
            "success": False,
            "error": error_msg,
            "message": "Branch creation failed"
        }


def git_status() -> Dict[str, Any]:
    """
    Get current Git status
    
    Returns:
        Dict with status information
    """
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            check=True,
            capture_output=True,
            text=True
        )
        
        return {
            "success": True,
            "status": result.stdout,
            "has_changes": len(result.stdout.strip()) > 0
        }
        
    except subprocess.CalledProcessError as e:
        return {
            "success": False,
            "error": str(e)
        }


def git_diff() -> Dict[str, Any]:
    """
    Get diff of unstaged changes
    
    Returns:
        Dict with diff output
    """
    try:
        result = subprocess.run(
            ["git", "diff"],
            check=True,
            capture_output=True,
            text=True
        )
        
        return {
            "success": True,
            "diff": result.stdout
        }
        
    except subprocess.CalledProcessError as e:
        return {
            "success": False,
            "error": str(e)
        }


def git_branch_list() -> Dict[str, Any]:
    """
    List all branches
    
    Returns:
        Dict with branch list
    """
    try:
        result = subprocess.run(
            ["git", "branch", "-a"],
            check=True,
            capture_output=True,
            text=True
        )
        
        branches = [b.strip() for b in result.stdout.split('\n') if b.strip()]
        current = next((b[2:] for b in branches if b.startswith('*')), None)
        
        return {
            "success": True,
            "branches": branches,
            "current": current
        }
        
    except subprocess.CalledProcessError as e:
        return {
            "success": False,
            "error": str(e)
        }


def git_log(n: int = 10) -> Dict[str, Any]:
    """
    Get recent commit history
    
    Args:
        n: Number of commits to retrieve
    
    Returns:
        Dict with commit history
    """
    try:
        result = subprocess.run(
            ["git", "log", f"-{n}", "--oneline"],
            check=True,
            capture_output=True,
            text=True
        )
        
        commits = [c.strip() for c in result.stdout.split('\n') if c.strip()]
        
        return {
            "success": True,
            "commits": commits,
            "count": len(commits)
        }
        
    except subprocess.CalledProcessError as e:
        return {
            "success": False,
            "error": str(e)
        }


# Tool wrapper for agent integration
class GitCommitTool:
    """Tool for committing changes"""
    
    name = "git_commit"
    description = "Commit all changes with a message and push to remote"
    
    def execute(self, message: str) -> str:
        """Execute git commit"""
        result = git_commit(message)
        if result["success"]:
            return f"✅ {result['message']}: {message}"
        else:
            return f"❌ {result['message']}: {result.get('error', 'Unknown error')}"


class GitBranchTool:
    """Tool for creating branches"""
    
    name = "git_create_branch"
    description = "Create and checkout a new Git branch"
    
    def execute(self, name: str) -> str:
        """Execute branch creation"""
        result = git_create_branch(name)
        if result["success"]:
            return f"✅ {result['message']}"
        else:
            return f"❌ {result['message']}: {result.get('error', 'Unknown error')}"


class GitStatusTool:
    """Tool for checking Git status"""
    
    name = "git_status"
    description = "Check Git repository status"
    
    def execute(self) -> str:
        """Execute git status"""
        result = git_status()
        if result["success"]:
            if result["has_changes"]:
                return f"📝 Changes:\n{result['status']}"
            else:
                return "✅ No changes"
        else:
            return f"❌ Error: {result.get('error', 'Unknown error')}"
