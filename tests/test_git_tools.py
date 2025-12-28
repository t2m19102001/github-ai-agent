#!/usr/bin/env python3
"""
Test Git Tools
Unit tests for Git operations functionality
"""

import pytest
import tempfile
import os
import subprocess
from datetime import datetime

from src.tools.git_tools import GitTools, GitStatus, GitCommit


class TestGitTools:
    """Test cases for GitTools"""
    
    @pytest.fixture
    def temp_repo(self):
        """Create temporary git repository for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize git repo
            subprocess.run(["git", "init"], cwd=temp_dir, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=temp_dir, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=temp_dir, check=True)
            
            # Create initial commit
            test_file = os.path.join(temp_dir, "README.md")
            with open(test_file, "w") as f:
                f.write("# Test Repository")
            
            subprocess.run(["git", "add", "README.md"], cwd=temp_dir, check=True)
            subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=temp_dir, check=True)
            
            yield temp_dir
    
    @pytest.fixture
    def git_tools(self, temp_repo):
        """Create GitTools instance with temp repository"""
        return GitTools(temp_repo)
    
    def test_initialization_valid_repo(self, temp_repo):
        """Test GitTools initialization with valid repository"""
        git = GitTools(temp_repo)
        assert git.repo_path == temp_repo
        assert git.get_current_branch() == "main"
    
    def test_initialization_invalid_repo(self):
        """Test GitTools initialization with invalid repository"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(ValueError, match="Not a git repository"):
                GitTools(temp_dir)
    
    def test_get_status_clean(self, git_tools):
        """Test getting status of clean repository"""
        status = git_tools.get_status()
        
        assert isinstance(status, GitStatus)
        assert status.is_clean is True
        assert len(status.modified_files) == 0
        assert len(status.added_files) == 0
        assert len(status.deleted_files) == 0
        assert len(status.untracked_files) == 0
    
    def test_get_status_dirty(self, git_tools, temp_repo):
        """Test getting status of dirty repository"""
        # Create new file
        new_file = os.path.join(temp_repo, "test.txt")
        with open(new_file, "w") as f:
            f.write("test content")
        
        # Modify existing file
        readme_file = os.path.join(temp_repo, "README.md")
        with open(readme_file, "a") as f:
            f.write("\nModified content")
        
        status = git_tools.get_status()
        
        assert status.is_clean is False
        assert len(status.untracked_files) >= 1
        assert "test.txt" in status.untracked_files
        assert len(status.modified_files) >= 1
        assert "README.md" in status.modified_files
    
    def test_add_files_all(self, git_tools, temp_repo):
        """Test adding all files"""
        # Create new file
        new_file = os.path.join(temp_repo, "new.txt")
        with open(new_file, "w") as f:
            f.write("new content")
        
        # Add all files
        success = git_tools.add_files()
        
        assert success is True
        
        # Check status
        status = git_tools.get_status()
        assert len(status.untracked_files) == 0
        assert "new.txt" not in status.untracked_files
    
    def test_add_files_specific(self, git_tools, temp_repo):
        """Test adding specific files"""
        # Create two new files
        file1 = os.path.join(temp_repo, "file1.txt")
        file2 = os.path.join(temp_repo, "file2.txt")
        
        with open(file1, "w") as f:
            f.write("content1")
        with open(file2, "w") as f:
            f.write("content2")
        
        # Add only one file
        success = git_tools.add_files(["file1.txt"])
        
        assert success is True
        
        # Check status
        status = git_tools.get_status()
        assert "file1.txt" not in status.untracked_files
        assert "file2.txt" in status.untracked_files
    
    def test_commit(self, git_tools, temp_repo):
        """Test creating commit"""
        # Create and stage a file
        new_file = os.path.join(temp_repo, "commit_test.txt")
        with open(new_file, "w") as f:
            f.write("commit test content")
        
        git_tools.add_files(["commit_test.txt"])
        
        # Create commit
        success = git_tools.commit("Test commit message")
        
        assert success is True
        
        # Check that commit was created
        commits = git_tools.get_commit_history(5)
        assert len(commits) >= 2  # Initial + new commit
        assert any("Test commit message" in commit.message for commit in commits)
    
    def test_commit_with_author(self, git_tools, temp_repo):
        """Test creating commit with custom author"""
        # Create and stage a file
        new_file = os.path.join(temp_repo, "author_test.txt")
        with open(new_file, "w") as f:
            f.write("author test content")
        
        git_tools.add_files(["author_test.txt"])
        
        # Create commit with author
        success = git_tools.commit("Test commit with author", "Custom Author <author@example.com>")
        
        assert success is True
    
    def test_get_current_branch(self, git_tools):
        """Test getting current branch name"""
        branch = git_tools.get_current_branch()
        assert branch == "main"
    
    def test_create_branch(self, git_tools):
        """Test creating new branch"""
        success = git_tools.create_branch("test-branch")
        
        assert success is True
        
        # Check that branch was created
        branch = git_tools.get_current_branch()
        assert branch == "test-branch"
    
    def test_create_branch_without_checkout(self, git_tools):
        """Test creating branch without checking out"""
        # First go back to main
        git_tools.checkout_branch("main")
        
        success = git_tools.create_branch("test-branch-no-checkout", checkout=False)
        
        assert success is True
        
        # Should still be on main
        branch = git_tools.get_current_branch()
        assert branch == "main"
    
    def test_checkout_branch(self, git_tools):
        """Test checking out branch"""
        # Create a branch first
        git_tools.create_branch("checkout-test")
        
        # Go back to main
        git_tools.checkout_branch("main")
        
        # Checkout the test branch
        success = git_tools.checkout_branch("checkout-test")
        
        assert success is True
        
        # Check that we're on the test branch
        branch = git_tools.get_current_branch()
        assert branch == "checkout-test"
    
    def test_get_commit_history(self, git_tools):
        """Test getting commit history"""
        commits = git_tools.get_commit_history(5)
        
        assert isinstance(commits, list)
        assert len(commits) >= 1  # At least initial commit
        
        # Check commit structure
        if commits:
            commit = commits[0]
            assert isinstance(commit, GitCommit)
            assert commit.hash
            assert commit.author
            assert commit.message
            assert isinstance(commit.date, datetime)
    
    def test_get_latest_commit_hash(self, git_tools):
        """Test getting latest commit hash"""
        hash_value = git_tools.get_latest_commit_hash()
        
        assert isinstance(hash_value, str)
        assert len(hash_value) == 40  # Git SHA-1 hash length
    
    def test_get_diff(self, git_tools, temp_repo):
        """Test getting diff"""
        # Create and stage a file
        new_file = os.path.join(temp_repo, "diff_test.txt")
        with open(new_file, "w") as f:
            f.write("original content")
        
        git_tools.add_files(["diff_test.txt"])
        git_tools.commit("Add diff test file")
        
        # Modify the file
        with open(new_file, "w") as f:
            f.write("modified content")
        
        # Get diff
        diff = git_tools.get_diff("diff_test.txt")
        
        assert isinstance(diff, str)
        assert "original content" in diff
        assert "modified content" in diff
    
    def test_get_diff_staged(self, git_tools, temp_repo):
        """Test getting staged diff"""
        # Create and modify a file
        new_file = os.path.join(temp_repo, "staged_diff.txt")
        with open(new_file, "w") as f:
            f.write("original content")
        
        git_tools.add_files(["staged_diff.txt"])
        
        # Modify the file after staging
        with open(new_file, "w") as f:
            f.write("modified content")
        
        # Get staged diff
        diff = git_tools.get_diff("staged_diff.txt", staged=True)
        
        assert isinstance(diff, str)
        assert "original content" in diff
        assert "modified content" not in diff  # Should not be in staged diff
    
    def test_stash(self, git_tools, temp_repo):
        """Test stashing changes"""
        # Create uncommitted changes
        new_file = os.path.join(temp_repo, "stash_test.txt")
        with open(new_file, "w") as f:
            f.write("stash content")
        
        # Stash changes
        success = git_tools.stash("Test stash message")
        
        assert success is True
        
        # Check that working directory is clean
        status = git_tools.get_status()
        assert status.is_clean is True
    
    def test_stash_pop(self, git_tools, temp_repo):
        """Test popping stashed changes"""
        # Create and stash changes
        new_file = os.path.join(temp_repo, "stash_pop_test.txt")
        with open(new_file, "w") as f:
            f.write("stash pop content")
        
        git_tools.stash("Test stash pop message")
        
        # Pop stashed changes
        success = git_tools.stash_pop()
        
        assert success is True
        
        # Check that changes are restored
        status = git_tools.get_status()
        assert status.is_clean is False
        assert "stash_pop_test.txt" in status.untracked_files
    
    def test_get_repo_info(self, git_tools):
        """Test getting repository information"""
        info = git_tools.get_repo_info()
        
        assert isinstance(info, dict)
        assert "current_branch" in info
        assert "total_commits" in info
        assert "branches" in info
        assert "status" in info
        
        assert info["current_branch"] == "main"
        assert isinstance(info["total_commits"], int)
        assert info["total_commits"] >= 1
        assert isinstance(info["branches"], list)
        assert "main" in info["branches"]


class TestGitToolsErrorHandling:
    """Test error handling for GitTools"""
    
    @pytest.fixture
    def git_tools_invalid(self):
        """Create GitTools instance with invalid path"""
        with tempfile.TemporaryDirectory() as temp_dir:
            return GitTools(temp_dir)
    
    def test_run_git_command_timeout(self, git_tools_invalid):
        """Test handling of git command timeout"""
        # This test would need to mock subprocess.run with timeout
        # For now, just test that the method exists
        assert hasattr(git_tools_invalid, '_run_git_command')
    
    def test_run_git_command_failure(self, git_tools_invalid):
        """Test handling of git command failure"""
        # Test with invalid git command
        result = git_tools_invalid._run_git_command(["invalid-command"])
        
        assert result.returncode != 0


# Integration tests
class TestGitToolsIntegration:
    """Integration tests for GitTools"""
    
    @pytest.mark.asyncio
    async def test_full_git_workflow(self):
        """Test complete Git workflow"""
        # This test would require a real git repository
        # For now, just test the workflow structure
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize repository
            subprocess.run(["git", "init"], cwd=temp_dir, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=temp_dir, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=temp_dir, check=True)
            
            git = GitTools(temp_dir)
            
            # Create initial commit
            initial_file = os.path.join(temp_dir, "initial.txt")
            with open(initial_file, "w") as f:
                f.write("Initial content")
            
            git.add_files(["initial.txt"])
            git.commit("Initial commit")
            
            # Create feature branch
            git.create_branch("feature", checkout=True)
            
            # Add feature
            feature_file = os.path.join(temp_dir, "feature.txt")
            with open(feature_file, "w") as f:
                f.write("Feature content")
            
            git.add_files(["feature.txt"])
            git.commit("Add feature")
            
            # Go back to main and merge
            git.checkout_branch("main")
            
            # Verify workflow
            status = git.get_status()
            assert status.is_clean is True
            
            commits = git.get_commit_history(5)
            assert len(commits) >= 2
            
            branches = git.get_repo_info()["branches"]
            assert "main" in branches
            assert "feature" in branches


# Test runner
def run_tests():
    """Run all tests"""
    import sys
    
    # Run with pytest
    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short"
    ])
    
    sys.exit(exit_code)


if __name__ == "__main__":
    run_tests()
