"""Lightweight local stub of PyGitHub for test environments.

This module is only used when the real `PyGithub` package is unavailable.
"""

from .Repository import Repository
from .Issue import Issue
from .PullRequest import PullRequest


class GithubException(Exception):
    pass


class UnknownObjectException(GithubException):
    pass


class _User:
    login = "mock-user"


class _RateCore:
    remaining = 5000
    limit = 5000
    reset = 0


class _RateLimit:
    core = _RateCore()


class Github:
    def __init__(self, token=None):
        self.token = token

    def get_user(self):
        return _User()

    def get_rate_limit(self):
        return _RateLimit()

    def get_repo(self, repo_name):
        raise UnknownObjectException(f"Repository not found in stub: {repo_name}")
