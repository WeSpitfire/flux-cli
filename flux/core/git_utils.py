"""Git integration utilities for Flux."""

import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass


@dataclass
class GitStatus:
    """Git repository status."""
    is_repo: bool
    branch: str = ""
    modified_files: List[str] = None
    staged_files: List[str] = None
    untracked_files: List[str] = None
    ahead: int = 0
    behind: int = 0
    
    def __post_init__(self):
        if self.modified_files is None:
            self.modified_files = []
        if self.staged_files is None:
            self.staged_files = []
        if self.untracked_files is None:
            self.untracked_files = []
    
    @property
    def has_changes(self) -> bool:
        """Check if there are any changes."""
        return bool(self.modified_files or self.staged_files or self.untracked_files)
    
    @property
    def total_changes(self) -> int:
        """Total number of changed files."""
        return len(self.modified_files) + len(self.staged_files) + len(self.untracked_files)


class GitIntegration:
    """Git integration for Flux workflows."""
    
    def __init__(self, cwd: Path):
        """Initialize git integration.
        
        Args:
            cwd: Current working directory (should be in a git repo)
        """
        self.cwd = cwd
    
    def is_git_repo(self) -> bool:
        """Check if current directory is in a git repository."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.cwd,
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def get_status(self) -> GitStatus:
        """Get current git status.
        
        Returns:
            GitStatus object with repository information
        """
        if not self.is_git_repo():
            return GitStatus(is_repo=False)
        
        status = GitStatus(is_repo=True)
        
        # Get current branch
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.cwd,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                status.branch = result.stdout.strip()
        except subprocess.TimeoutExpired:
            pass
        
        # Get file status
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.cwd,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if not line:
                        continue
                    
                    status_code = line[:2]
                    file_path = line[3:].strip()
                    
                    # Staged files
                    if status_code[0] in ['A', 'M', 'D', 'R', 'C']:
                        status.staged_files.append(file_path)
                    
                    # Modified files
                    if status_code[1] in ['M', 'D']:
                        status.modified_files.append(file_path)
                    
                    # Untracked files
                    if status_code == '??':
                        status.untracked_files.append(file_path)
        except subprocess.TimeoutExpired:
            pass
        
        # Get ahead/behind status
        try:
            result = subprocess.run(
                ["git", "rev-list", "--left-right", "--count", "HEAD...@{u}"],
                cwd=self.cwd,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                parts = result.stdout.strip().split()
                if len(parts) == 2:
                    status.ahead = int(parts[0])
                    status.behind = int(parts[1])
        except (subprocess.TimeoutExpired, ValueError):
            pass
        
        return status
    
    def get_diff(self, file_path: Optional[str] = None, staged: bool = False) -> str:
        """Get git diff for file(s).
        
        Args:
            file_path: Specific file to diff (None for all files)
            staged: Show staged changes instead of working directory
            
        Returns:
            Diff output as string
        """
        if not self.is_git_repo():
            return ""
        
        cmd = ["git", "diff"]
        if staged:
            cmd.append("--cached")
        if file_path:
            cmd.append("--")
            cmd.append(file_path)
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.cwd,
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.stdout if result.returncode == 0 else ""
        except subprocess.TimeoutExpired:
            return ""
    
    def stage_files(self, files: List[str]) -> Tuple[bool, str]:
        """Stage files for commit.
        
        Args:
            files: List of file paths to stage
            
        Returns:
            Tuple of (success, message)
        """
        if not self.is_git_repo():
            return False, "Not a git repository"
        
        try:
            result = subprocess.run(
                ["git", "add"] + files,
                cwd=self.cwd,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return True, f"Staged {len(files)} file(s)"
            else:
                return False, result.stderr
        except subprocess.TimeoutExpired:
            return False, "Operation timed out"
    
    def commit(self, message: str, files: Optional[List[str]] = None) -> Tuple[bool, str]:
        """Create a commit.
        
        Args:
            message: Commit message
            files: Optional list of files to commit (stages them first)
            
        Returns:
            Tuple of (success, message/error)
        """
        if not self.is_git_repo():
            return False, "Not a git repository"
        
        # Stage files if provided
        if files:
            success, msg = self.stage_files(files)
            if not success:
                return False, f"Failed to stage files: {msg}"
        
        try:
            result = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=self.cwd,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return True, "Commit created successfully"
            else:
                return False, result.stderr
        except subprocess.TimeoutExpired:
            return False, "Commit operation timed out"
    
    def get_recent_commits(self, count: int = 10) -> List[Dict[str, str]]:
        """Get recent commits.
        
        Args:
            count: Number of commits to retrieve
            
        Returns:
            List of commit dictionaries with hash, message, author, date
        """
        if not self.is_git_repo():
            return []
        
        try:
            result = subprocess.run(
                ["git", "log", f"-{count}", "--pretty=format:%H|%s|%an|%ar"],
                cwd=self.cwd,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                return []
            
            commits = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                parts = line.split('|')
                if len(parts) == 4:
                    commits.append({
                        "hash": parts[0][:7],  # Short hash
                        "message": parts[1],
                        "author": parts[2],
                        "date": parts[3]
                    })
            return commits
        except subprocess.TimeoutExpired:
            return []
    
    def get_changed_files_in_commit(self, commit_hash: str = "HEAD") -> List[str]:
        """Get list of files changed in a specific commit.
        
        Args:
            commit_hash: Commit hash or reference (default: HEAD)
            
        Returns:
            List of changed file paths
        """
        if not self.is_git_repo():
            return []
        
        try:
            result = subprocess.run(
                ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit_hash],
                cwd=self.cwd,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return [f for f in result.stdout.strip().split('\n') if f]
            return []
        except subprocess.TimeoutExpired:
            return []
    
    def create_smart_commit_message(
        self,
        files: List[str],
        changes_summary: Optional[str] = None
    ) -> str:
        """Generate a smart commit message based on changed files.
        
        Args:
            files: List of changed files
            changes_summary: Optional summary of changes
            
        Returns:
            Generated commit message
        """
        if not files:
            return "Update files"
        
        # Categorize files
        categories = {
            "docs": [],
            "tests": [],
            "core": [],
            "ui": [],
            "tools": [],
            "config": [],
            "other": []
        }
        
        for file in files:
            if "test" in file.lower():
                categories["tests"].append(file)
            elif file.endswith(".md") or "doc" in file.lower():
                categories["docs"].append(file)
            elif "core" in file:
                categories["core"].append(file)
            elif "ui" in file:
                categories["ui"].append(file)
            elif "tool" in file:
                categories["tools"].append(file)
            elif file.endswith((".json", ".yaml", ".yml", ".toml")):
                categories["config"].append(file)
            else:
                categories["other"].append(file)
        
        # Build message
        parts = []
        for category, cat_files in categories.items():
            if cat_files:
                if len(cat_files) == 1:
                    parts.append(f"{category}: update {Path(cat_files[0]).name}")
                else:
                    parts.append(f"{category}: update {len(cat_files)} files")
        
        message = ", ".join(parts[:3])  # Limit to 3 categories
        
        if changes_summary:
            message = f"{message}\n\n{changes_summary}"
        
        return message or "Update files"
