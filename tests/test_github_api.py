#!/usr/bin/env python3
"""
Tests for GitHub API integration
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from src.github.api_client import GitHubAPIClient, get_github_client, initialize_github_client
from src.github.repository_operations import RepositoryOperations, get_repository_operations
from src.github.webhook_manager import WebhookManager, get_webhook_manager, WebhookEvent


class TestGitHubAPIClient:
    """Test GitHub API client"""
    
    def setup_method(self):
        self.test_token = "test_token_123"
        self.client = GitHubAPIClient(token=self.test_token)
    
    def test_client_initialization(self):
        """Test client initialization"""
        assert self.client.token == self.test_token
        assert self.client.request_count == 0
    
    @patch('src.github.api_client.PYGITHUB_AVAILABLE', True)
    @patch('src.github.api_client.Github')
    def test_client_with_pygithub(self, mock_github):
        """Test client with PyGitHub available"""
        mock_github_instance = Mock()
        mock_github.return_value = mock_github_instance
        
        client = GitHubAPIClient(token="test")
        assert client.client == mock_github_instance
    
    @patch('src.github.api_client.PYGITHUB_AVAILABLE', False)
    def test_client_without_pygithub(self):
        """Test client without PyGitHub"""
        with pytest.raises(ValueError):
            GitHubAPIClient(token="test")
    
    @patch('src.github.api_client.PYGITHUB_AVAILABLE', True)
    def test_get_repository_info(self):
        """Test getting repository information"""
        # Mock repository
        mock_repo = Mock()
        mock_repo.name = "test-repo"
        mock_repo.full_name = "owner/test-repo"
        mock_repo.description = "Test repository"
        mock_repo.language = "Python"
        mock_repo.stargazers_count = 10
        mock_repo.forks_count = 5
        mock_repo.open_issues_count = 2
        mock_repo.clone_url = "https://github.com/owner/test-repo.git"
        mock_repo.ssh_url = "git@github.com:owner/test-repo.git"
        mock_repo.default_branch = "main"
        mock_repo.size = 1024
        mock_repo.created_at = datetime.now()
        mock_repo.updated_at = datetime.now()
        
        # Mock client
        mock_github = Mock()
        mock_github.get_repo.return_value = mock_repo
        self.client.client = mock_github
        
        # Mock rate limit
        self.client.rate_limit_info = Mock()
        self.client.rate_limit_info.remaining = 1000
        
        result = self.client.get_repository_info("owner/test-repo")
        
        assert result is not None
        assert result.name == "test-repo"
        assert result.full_name == "owner/test-repo"
        assert result.language == "Python"
        assert result.stars == 10
    
    @patch('src.github.api_client.PYGITHUB_AVAILABLE', True)
    def test_get_repository_info_not_found(self):
        """Test getting non-existent repository"""
        from github import UnknownObjectException
        
        mock_github = Mock()
        mock_github.get_repo.side_effect = UnknownObjectException(None, None, None)
        self.client.client = mock_github
        
        result = self.client.get_repository_info("owner/nonexistent")
        
        assert result is None
    
    @patch('src.github.api_client.PYGITHUB_AVAILABLE', True)
    def test_list_repository_files(self):
        """Test listing repository files"""
        # Mock file content
        mock_file = Mock()
        mock_file.type = "file"
        mock_file.path = "src/main.py"
        
        mock_dir = Mock()
        mock_dir.type = "dir"
        mock_dir.path = "src"
        
        # Mock repository
        mock_repo = Mock()
        mock_repo.get_contents.return_value = [mock_file, mock_dir]
        
        mock_github = Mock()
        mock_github.get_repo.return_value = mock_repo
        self.client.client = mock_github
        
        # Mock rate limit
        self.client.rate_limit_info = Mock()
        self.client.rate_limit_info.remaining = 1000
        
        result = self.client.list_repository_files("owner/test-repo")
        
        assert len(result) >= 1
        assert "src/main.py" in result
    
    @patch('src.github.api_client.PYGITHUB_AVAILABLE', True)
    def test_create_branch(self):
        """Test creating a branch"""
        # Mock branch
        mock_source_branch = Mock()
        mock_source_branch.commit.sha = "abc123"
        
        mock_repo = Mock()
        mock_repo.get_branch.return_value = mock_source_branch
        mock_repo.create_git_ref.return_value = Mock()
        
        mock_github = Mock()
        mock_github.get_repo.return_value = mock_repo
        self.client.client = mock_github
        
        # Mock rate limit
        self.client.rate_limit_info = Mock()
        self.client.rate_limit_info.remaining = 1000
        
        result = self.client.create_branch("owner/test-repo", "feature-branch")
        
        assert result is True
        mock_repo.create_git_ref.assert_called_once()
    
    @patch('src.github.api_client.PYGITHUB_AVAILABLE', True)
    def test_create_pull_request(self):
        """Test creating a pull request"""
        # Mock PR
        mock_pr = Mock()
        mock_pr.html_url = "https://github.com/owner/test-repo/pull/1"
        
        mock_repo = Mock()
        mock_repo.create_pull_request.return_value = mock_pr
        
        mock_github = Mock()
        mock_github.get_repo.return_value = mock_repo
        self.client.client = mock_github
        
        # Mock rate limit
        self.client.rate_limit_info = Mock()
        self.client.rate_limit_info.remaining = 1000
        
        result = self.client.create_pull_request(
            "owner/test-repo",
            "Test PR",
            "Test description",
            "feature-branch",
            "main"
        )
        
        assert result == "https://github.com/owner/test-repo/pull/1"
    
    def test_get_rate_limit_status(self):
        """Test rate limit status"""
        mock_rate_info = Mock()
        mock_rate_info.remaining = 1000
        mock_rate_info.limit = 5000
        mock_rate_info.used = 4000
        mock_rate_info.reset_time = datetime.now()
        
        self.client.rate_limit_info = mock_rate_info
        
        result = self.client.get_rate_limit_status()
        
        assert result["remaining"] == 1000
        assert result["limit"] == 5000
        assert result["used"] == 4000
        assert "usage_percentage" in result
    
    def test_get_api_stats(self):
        """Test API statistics"""
        self.client.request_count = 10
        self.client.last_request_time = 1234567890
        
        result = self.client.get_api_stats()
        
        assert result["total_requests"] == 10
        assert result["last_request_time"] == 1234567890
        assert "rate_limit_info" in result


class TestRepositoryOperations:
    """Test repository operations"""
    
    def setup_method(self):
        self.workspace_root = "/tmp/test-workspace"
        self.repo_ops = RepositoryOperations(self.workspace_root)
    
    def test_initialization(self):
        """Test repository operations initialization"""
        assert str(self.repo_ops.workspace_root) == self.workspace_root
        assert len(self.repo_ops.cloned_repos) == 0
    
    @patch('src.github.repository_operations.get_github_client')
    def test_clone_repository_success(self, mock_get_client):
        """Test successful repository cloning"""
        # Mock GitHub client
        mock_client = Mock()
        mock_repo_info = Mock()
        mock_repo_info.clone_url = "https://github.com/owner/test-repo.git"
        mock_client.get_repository_info.return_value = mock_repo_info
        mock_get_client.return_value = mock_client
        
        # Mock security guardrails
        with patch('src.github.repository_operations.security_guardrails') as mock_guardrails:
            mock_guardrails.validate_repository_access.return_value = {"valid": True}
            
            # Mock subprocess
            with patch('subprocess.run') as mock_run:
                mock_run.return_value.returncode = 0
                
                result = self.repo_ops.clone_repository("owner/test-repo")
                
                assert result.success is True
                assert result.repo_path is not None
                assert result.error is None
                assert result.clone_time > 0
    
    @patch('src.github.repository_operations.get_github_client')
    def test_clone_repository_security_error(self, mock_get_client):
        """Test repository cloning with security error"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        with patch('src.github.repository_operations.security_guardrails') as mock_guardrails:
            mock_guardrails.validate_repository_access.return_value = {
                "valid": False,
                "reason": "Access denied"
            }
            
            result = self.repo_ops.clone_repository("owner/test-repo")
            
            assert result.success is False
            assert "Access denied" in result.error
    
    @patch('src.github.repository_operations.get_github_client')
    def test_clone_repository_not_found(self, mock_get_client):
        """Test cloning non-existent repository"""
        mock_client = Mock()
        mock_client.get_repository_info.return_value = None
        mock_get_client.return_value = mock_client
        
        result = self.repo_ops.clone_repository("owner/nonexistent")
        
        assert result.success is False
        assert "not found" in result.error
    
    def test_get_cloned_repositories(self):
        """Test getting list of cloned repositories"""
        # Add some test repos
        self.repo_ops.cloned_repos["owner/test-repo"] = "/tmp/test-repo"
        self.repo_ops.cloned_repos["owner/another-repo"] = "/tmp/another-repo"
        
        result = self.repo_ops.get_cloned_repositories()
        
        assert len(result) == 2
        assert "owner/test-repo" in result
        assert "owner/another-repo" in result
    
    def test_get_repository_path(self):
        """Test getting repository path"""
        self.repo_ops.cloned_repos["owner/test-repo"] = "/tmp/test-repo"
        
        result = self.repo_ops.get_repository_path("owner/test-repo")
        assert result == "/tmp/test-repo"
        
        result = self.repo_ops.get_repository_path("owner/nonexistent")
        assert result is None
    
    @patch('subprocess.run')
    def test_analyze_repository_structure(self, mock_run):
        """Test repository structure analysis"""
        # Mock cloned repository
        self.repo_ops.cloned_repos["owner/test-repo"] = "/tmp/test-repo"
        
        # Mock git log
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "10"
        
        # Mock directory structure
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.rglob', return_value=[]), \
             patch('pathlib.Path.is_file', return_value=False):
            
            result = self.repo_ops.analyze_repository_structure("owner/test-repo")
            
            assert "repository" in result
            assert "total_files" in result
            assert "git_statistics" in result


class TestWebhookManager:
    """Test webhook manager"""
    
    def setup_method(self):
        self.secret = "webhook_secret"
        self.manager = WebhookManager(secret=self.secret)
    
    def test_initialization(self):
        """Test webhook manager initialization"""
        assert self.manager.secret == self.secret
        assert len(self.manager.event_handlers) == 0
        assert len(self.manager.delivery_stats) == 0
    
    def test_verify_signature_success(self):
        """Test successful signature verification"""
        payload = '{"test": "data"}'
        signature = "sha256=" + hmac.new(
            self.secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        result = self.manager.verify_signature(payload, signature)
        assert result is True
    
    def test_verify_signature_failure(self):
        """Test failed signature verification"""
        payload = '{"test": "data"}'
        signature = "sha256=invalid_signature"
        
        result = self.manager.verify_signature(payload, signature)
        assert result is False
    
    def test_parse_webhook_event(self):
        """Test webhook event parsing"""
        headers = {
            "X-GitHub-Event": "push",
            "X-GitHub-Delivery": "delivery-123",
            "X-Hub-Signature-256": "sha256=valid_signature"
        }
        body = '{"repository": {"full_name": "owner/test-repo"}}'
        
        with patch.object(self.manager, 'verify_signature', return_value=True):
            result = self.manager.parse_webhook_event(headers, body)
            
            assert result["event_type"] == "push"
            assert result["repository"] == "owner/test-repo"
            assert result["verified"] is True
    
    def test_register_event_handler(self):
        """Test registering event handler"""
        async def test_handler(event_data):
            return {"handled": True}
        
        self.manager.register_event_handler("push", test_handler)
        
        assert "push" in self.manager.event_handlers
        assert len(self.manager.event_handlers["push"]) == 1
    
    @pytest.mark.asyncio
    async def test_handle_webhook_event(self):
        """Test handling webhook event"""
        headers = {
            "X-GitHub-Event": "push",
            "X-GitHub-Delivery": "delivery-123",
            "X-Hub-Signature-256": "sha256=valid_signature"
        }
        body = '{"repository": {"full_name": "owner/test-repo"}}'
        
        async def test_handler(event_data):
            return {"handled": True}
        
        self.manager.register_event_handler("push", test_handler)
        
        with patch.object(self.manager, 'parse_webhook_event', return_value={
            "event_type": "push",
            "repository": "owner/test-repo",
            "payload": {},
            "delivery": Mock(delivered=False, timestamp=datetime.now()),
            "verified": True
        }):
            result = await self.manager.handle_webhook_event(headers, body)
            
            assert result["success"] is True
            assert result["event_type"] == "push"
            assert result["handlers_executed"] == 1
    
    def test_get_webhook_stats(self):
        """Test getting webhook statistics"""
        # Add some test stats
        from src.github.webhook_manager import WebhookStats, WebhookDelivery
        
        stats = WebhookStats()
        stats.total_deliveries = 10
        stats.successful_deliveries = 8
        stats.failed_deliveries = 2
        stats.last_delivery = datetime.now()
        
        self.manager.delivery_stats["owner/test-repo"] = stats
        
        result = self.manager.get_webhook_stats("owner/test-repo")
        
        assert result["total_deliveries"] == 10
        assert result["successful_deliveries"] == 8
        assert result["failed_deliveries"] == 2
        assert result["success_rate"] == 80.0


class TestGlobalFunctions:
    """Test global functions"""
    
    def test_get_github_client(self):
        """Test getting global GitHub client"""
        client = get_github_client()
        assert client is not None
    
    def test_initialize_github_client(self):
        """Test initializing GitHub client"""
        client = initialize_github_client("test_token")
        assert client is not None
        assert client.token == "test_token"
    
    def test_get_repository_operations(self):
        """Test getting global repository operations"""
        ops = get_repository_operations()
        assert ops is not None
    
    def test_get_webhook_manager(self):
        """Test getting global webhook manager"""
        manager = get_webhook_manager()
        assert manager is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
