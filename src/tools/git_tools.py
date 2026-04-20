#!/usr/bin/env python3
"""Structured git helper API used by tests and higher-level tools."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional


@dataclass
class GitStatus:
    is_clean: bool
    modified_files: List[str] = field(default_factory=list)
    added_files: List[str] = field(default_factory=list)
    deleted_files: List[str] = field(default_factory=list)
    untracked_files: List[str] = field(default_factory=list)


@dataclass
class GitCommit:
    hash: str
    author: str
    message: str
    date: datetime


class GitTools:
    def __init__(self, repo_path: str):
        self.repo_path = str(Path(repo_path))
        git_dir = Path(self.repo_path) / ".git"
        self.is_git_repo = git_dir.exists()
        if not self.is_git_repo:
            raise ValueError("Not a git repository")
        self._ensure_main_branch()

    def _run_git_command(self, args: List[str], check: bool = False) -> subprocess.CompletedProcess:
        cmd = ["git", *args]
        try:
            if not self.is_git_repo:
                return subprocess.CompletedProcess(cmd, returncode=1, stdout="", stderr="Not a git repository")
            return subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30,
                check=check,
            )
        except subprocess.CalledProcessError as exc:
            return exc

    def _ensure_main_branch(self) -> None:
        branch = self._run_git_command(["branch", "--show-current"]).stdout.strip()
        if branch == "main":
            return
        if branch == "master":
            self._run_git_command(["branch", "-M", "main"], check=True)

    def get_current_branch(self) -> str:
        return self._run_git_command(["branch", "--show-current"], check=True).stdout.strip()

    def get_status(self) -> GitStatus:
        result = self._run_git_command(["status", "--porcelain"], check=True)
        modified, added, deleted, untracked = [], [], [], []
        for line in result.stdout.splitlines():
            status = line[:2]
            path = line[3:]
            if status == "??":
                untracked.append(path)
                continue
            if "M" in status:
                modified.append(path)
            if "A" in status:
                added.append(path)
            if "D" in status:
                deleted.append(path)
        return GitStatus(
            is_clean=not any([modified, added, deleted, untracked]),
            modified_files=modified,
            added_files=added,
            deleted_files=deleted,
            untracked_files=untracked,
        )

    def add_files(self, files: Optional[List[str]] = None) -> bool:
        args = ["add", *(files or ["."])]
        return self._run_git_command(args).returncode == 0

    def commit(self, message: str, author: Optional[str] = None) -> bool:
        args = ["commit", "-m", message]
        if author:
            args.extend(["--author", author])
        return self._run_git_command(args).returncode == 0

    def create_branch(self, branch_name: str, checkout: bool = True) -> bool:
        args = ["checkout", "-b", branch_name] if checkout else ["branch", branch_name]
        return self._run_git_command(args).returncode == 0

    def checkout_branch(self, branch_name: str) -> bool:
        return self._run_git_command(["checkout", branch_name]).returncode == 0

    def get_commit_history(self, limit: int = 10) -> List[GitCommit]:
        result = self._run_git_command([
            "log",
            f"-{limit}",
            "--pretty=format:%H%x1f%an%x1f%ad%x1f%s",
            "--date=iso",
        ], check=True)
        commits: List[GitCommit] = []
        for line in result.stdout.splitlines():
            commit_hash, author, date_str, message = line.split("\x1f", 3)
            commits.append(
                GitCommit(
                    hash=commit_hash,
                    author=author,
                    message=message,
                    date=datetime.fromisoformat(date_str.strip()),
                )
            )
        return commits

    def get_latest_commit_hash(self) -> str:
        return self._run_git_command(["rev-parse", "HEAD"], check=True).stdout.strip()

    def get_diff(self, file_path: Optional[str] = None, staged: bool = False) -> str:
        args = ["diff"]
        if staged:
            args.append("--cached")
        if file_path:
            args.extend(["--", file_path])
        return self._run_git_command(args, check=True).stdout

    def stash(self, message: str = "") -> bool:
        args = ["stash", "push", "-u"]
        if message:
            args.extend(["-m", message])
        return self._run_git_command(args).returncode == 0

    def stash_pop(self) -> bool:
        return self._run_git_command(["stash", "pop"]).returncode == 0

    def get_repo_info(self) -> dict:
        return {
            "current_branch": self.get_current_branch(),
            "total_commits": len(self.get_commit_history(1000)),
            "branches": [line.strip().lstrip("* ").strip() for line in self._run_git_command(["branch"]).stdout.splitlines() if line.strip()],
            "status": self.get_status(),
        }
