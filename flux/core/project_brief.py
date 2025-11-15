"""Project Brief - Structured state that persists across all conversations.

This module provides a ProjectBrief class that maintains critical project
information that should NEVER be forgotten, even after many messages or restarts.
"""

import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime


@dataclass
class ProjectBrief:
    """Structured project state that persists and is always in the prompt.
    
    This ensures Flux never forgets:
    - What you're building
    - Tech stack and languages
    - Critical constraints
    - Coding conventions
    - Current task and progress
    """
    
    # Core identity
    project_name: str = ""
    project_type: str = ""  # "web_app", "cli_tool", "api", "library", etc.
    description: str = ""
    
    # Tech stack
    languages: List[str] = field(default_factory=list)
    frameworks: List[str] = field(default_factory=list)
    database: Optional[str] = None
    
    # Constraints & Conventions (CRITICAL - never forget these!)
    constraints: List[str] = field(default_factory=list)
    coding_style: List[str] = field(default_factory=list)
    api_format: Optional[str] = None
    
    # Architecture
    key_directories: Dict[str, str] = field(default_factory=dict)
    architecture_notes: List[str] = field(default_factory=list)
    
    # Current state
    current_task: Optional[str] = None
    completed_tasks: List[str] = field(default_factory=list)
    pending_issues: List[str] = field(default_factory=list)
    
    # Metadata
    created_at: str = ""
    updated_at: str = ""
    
    def __post_init__(self):
        """Set timestamps if not provided."""
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()
    
    def to_prompt(self) -> str:
        """Convert to structured prompt that's ALWAYS sent to LLM.
        
        This prompt is injected into every single LLM call, ensuring
        the model never forgets critical project information.
        """
        if not self.project_name and not self.description:
            # Empty brief, don't add noise
            return ""
        
        sections = []
        
        # Header
        sections.append("=" * 60)
        sections.append("PROJECT BRIEF (READ FIRST - ALWAYS FOLLOW)")
        sections.append("=" * 60)
        
        # Core info
        if self.project_name:
            sections.append(f"Project: {self.project_name}")
        if self.project_type:
            sections.append(f"Type: {self.project_type}")
        if self.description:
            sections.append(f"Description: {self.description}")
        
        # Tech stack
        if self.languages or self.frameworks or self.database:
            sections.append("")
            sections.append("TECH STACK:")
            if self.languages:
                sections.append(f"  Languages: {', '.join(self.languages)}")
            if self.frameworks:
                sections.append(f"  Frameworks: {', '.join(self.frameworks)}")
            if self.database:
                sections.append(f"  Database: {self.database}")
        
        # CRITICAL constraints (these should NEVER be violated)
        if self.constraints:
            sections.append("")
            sections.append("CRITICAL CONSTRAINTS (NEVER VIOLATE):")
            for constraint in self.constraints:
                sections.append(f"  ❌ {constraint}")
        
        # Coding style
        if self.coding_style:
            sections.append("")
            sections.append("CODING STYLE (ALWAYS FOLLOW):")
            for style in self.coding_style:
                sections.append(f"  ✓ {style}")
        
        # API format
        if self.api_format:
            sections.append("")
            sections.append(f"API FORMAT: {self.api_format}")
        
        # Architecture
        if self.key_directories:
            sections.append("")
            sections.append("KEY DIRECTORIES:")
            for dir_path, desc in self.key_directories.items():
                sections.append(f"  {dir_path}: {desc}")
        
        if self.architecture_notes:
            sections.append("")
            sections.append("ARCHITECTURE NOTES:")
            for note in self.architecture_notes:
                sections.append(f"  • {note}")
        
        # Current state
        if self.current_task:
            sections.append("")
            sections.append(f"CURRENT TASK: {self.current_task}")
        
        if self.completed_tasks:
            sections.append("")
            sections.append("COMPLETED:")
            for task in self.completed_tasks[-5:]:  # Last 5
                sections.append(f"  ✓ {task}")
        
        if self.pending_issues:
            sections.append("")
            sections.append("PENDING ISSUES:")
            for issue in self.pending_issues[:5]:  # Top 5
                sections.append(f"  ⚠ {issue}")
        
        sections.append("=" * 60)
        
        return "\n".join(sections)
    
    def add_constraint(self, constraint: str):
        """Add a critical constraint that must never be violated."""
        if constraint and constraint not in self.constraints:
            self.constraints.append(constraint)
            self.updated_at = datetime.now().isoformat()
    
    def add_coding_style(self, style: str):
        """Add a coding style guideline."""
        if style and style not in self.coding_style:
            self.coding_style.append(style)
            self.updated_at = datetime.now().isoformat()
    
    def set_current_task(self, task: str):
        """Set the current task being worked on."""
        self.current_task = task
        self.updated_at = datetime.now().isoformat()
    
    def complete_task(self, task: Optional[str] = None):
        """Mark a task as completed."""
        task_to_complete = task or self.current_task
        if task_to_complete:
            if task_to_complete not in self.completed_tasks:
                self.completed_tasks.append(task_to_complete)
            if self.current_task == task_to_complete:
                self.current_task = None
            self.updated_at = datetime.now().isoformat()
    
    def add_issue(self, issue: str):
        """Add a pending issue to track."""
        if issue and issue not in self.pending_issues:
            self.pending_issues.append(issue)
            self.updated_at = datetime.now().isoformat()
    
    def resolve_issue(self, issue: str):
        """Remove a resolved issue."""
        if issue in self.pending_issues:
            self.pending_issues.remove(issue)
            self.updated_at = datetime.now().isoformat()
    
    def update_from_dict(self, data: Dict):
        """Update fields from dictionary (for manual editing)."""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "ProjectBrief":
        """Create ProjectBrief from dictionary."""
        return cls(**data)
    
    def save(self, file_path: Path):
        """Save to JSON file.
        
        Args:
            file_path: Path to save brief.json
        """
        file_path.parent.mkdir(parents=True, exist_ok=True)
        self.updated_at = datetime.now().isoformat()
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
    
    @classmethod
    def load(cls, file_path: Path) -> "ProjectBrief":
        """Load from JSON file.
        
        Args:
            file_path: Path to brief.json
            
        Returns:
            ProjectBrief instance
        """
        if not file_path.exists():
            return cls()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return cls.from_dict(data)
        except Exception:
            # If corrupt, return empty brief
            return cls()
    
    @classmethod
    def auto_detect(cls, cwd: Path) -> "ProjectBrief":
        """Auto-detect project information from codebase.
        
        Looks at:
        - package.json (Node.js)
        - pyproject.toml (Python)
        - Cargo.toml (Rust)
        - go.mod (Go)
        - README.md
        
        Args:
            cwd: Current working directory
            
        Returns:
            ProjectBrief with auto-detected info
        """
        brief = cls()
        brief.project_name = cwd.name
        
        # Detect from package.json
        package_json = cwd / "package.json"
        if package_json.exists():
            try:
                import json
                with open(package_json, 'r') as f:
                    data = json.load(f)
                brief.project_name = data.get("name", brief.project_name)
                brief.description = data.get("description", "")
                brief.project_type = "web_app"
                brief.languages = ["JavaScript"]
                
                # Detect frameworks
                deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                if "react" in deps:
                    brief.frameworks.append("React")
                if "next" in deps:
                    brief.frameworks.append("Next.js")
                if "express" in deps:
                    brief.frameworks.append("Express")
                if "vue" in deps:
                    brief.frameworks.append("Vue")
                if "typescript" in deps:
                    if "JavaScript" in brief.languages:
                        brief.languages.remove("JavaScript")
                    brief.languages.append("TypeScript")
            except Exception:
                pass
        
        # Detect from pyproject.toml
        pyproject = cwd / "pyproject.toml"
        if pyproject.exists():
            try:
                import toml
                data = toml.load(pyproject)
                project = data.get("project", {}) or data.get("tool", {}).get("poetry", {})
                brief.project_name = project.get("name", brief.project_name)
                brief.description = project.get("description", "")
                brief.languages = ["Python"]
                brief.project_type = "library" if "library" in str(pyproject.read_text()).lower() else "cli_tool"
            except Exception:
                pass
        
        # Detect from README.md
        readme = cwd / "README.md"
        if readme.exists() and not brief.description:
            try:
                content = readme.read_text(encoding='utf-8')
                lines = content.split('\n')
                # Get first non-empty, non-title line
                for line in lines[1:]:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        brief.description = line[:200]
                        break
            except Exception:
                pass
        
        # Detect from directory structure
        if (cwd / "src").exists():
            brief.key_directories["src/"] = "main source code"
        if (cwd / "tests").exists() or (cwd / "test").exists():
            brief.key_directories["tests/"] = "test files"
        if (cwd / "docs").exists():
            brief.key_directories["docs/"] = "documentation"
        
        return brief
    
    def is_empty(self) -> bool:
        """Check if brief has any meaningful content."""
        return not (self.project_name or self.description or 
                   self.constraints or self.coding_style or
                   self.current_task)
    
    def __str__(self) -> str:
        """String representation for display."""
        if self.is_empty():
            return "Project Brief: (empty)"
        
        parts = []
        if self.project_name:
            parts.append(f"Project: {self.project_name}")
        if self.project_type:
            parts.append(f"Type: {self.project_type}")
        if self.frameworks:
            parts.append(f"Stack: {', '.join(self.frameworks)}")
        if self.constraints:
            parts.append(f"Constraints: {len(self.constraints)}")
        if self.current_task:
            parts.append(f"Task: {self.current_task}")
        
        return " | ".join(parts)
