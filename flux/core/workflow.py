"""Workflow system to enforce proper analysis before making changes."""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from pathlib import Path
from enum import Enum


class WorkflowStage(Enum):
    """Stages in the Flux workflow."""
    UNDERSTAND = "understand"  # Read files, understand structure
    PLAN = "plan"              # Plan changes
    VALIDATE = "validate"      # Validate plan
    EXECUTE = "execute"        # Make changes
    VERIFY = "verify"          # Verify changes


@dataclass
class WorkflowContext:
    """Context for tracking workflow progress."""
    stage: WorkflowStage
    files_read: List[Path]
    files_searched: List[str]
    plan: Optional[str]
    validations: List[Dict[str, Any]]
    modifications: List[Dict[str, Any]]
    file_cache: Dict[Path, str] = None  # Cache file contents during workflow

    def __post_init__(self):
        """Initialize file_cache if not provided."""
        if self.file_cache is None:
            self.file_cache = {}

    def has_read_target_file(self, target: Path) -> bool:
        """Check if we've read the target file we want to modify."""
        return target in self.files_read

    def has_understanding(self) -> bool:
        """Check if we have sufficient understanding to plan."""
        return len(self.files_read) > 0 or len(self.files_searched) > 0

    def has_plan(self) -> bool:
        """Check if we have a plan."""
        return self.plan is not None

    def can_execute(self) -> bool:
        """Check if we're ready to execute changes."""
        return (
            self.stage == WorkflowStage.EXECUTE and
            self.has_understanding()
        )


class WorkflowEnforcer:
    """Enforces proper workflow stages before allowing file modifications."""

    def __init__(self, cwd: Path, strict_mode: bool = False):
        """Initialize workflow enforcer."""
        self.cwd = cwd
        self.context: Optional[WorkflowContext] = None
        self.strict_mode = strict_mode  # Enforce workflow stages (disabled by default - LLM follows naturally)

    def start_workflow(self):
        """Start a new workflow."""
        self.context = WorkflowContext(
            stage=WorkflowStage.UNDERSTAND,
            files_read=[],
            files_searched=[],
            plan=None,
            validations=[],
            modifications=[]
        )

    def record_file_read(self, path: Path, content: Optional[str] = None):
        """Record that a file was read and optionally cache its content.

        Args:
            path: Path to the file that was read
            content: Optional file content to cache for reuse in same workflow
        """
        if self.context:
            if path not in self.context.files_read:
                self.context.files_read.append(path)
            # Cache the content if provided
            if content is not None:
                self.context.file_cache[path] = content
            # Auto-progress to EXECUTE if we have understanding
            if self.context.stage == WorkflowStage.UNDERSTAND and self.context.has_understanding():
                self.context.stage = WorkflowStage.EXECUTE

    def record_search(self, query: str):
        """Record that a search was performed."""
        if self.context:
            self.context.files_searched.append(query)
            # Auto-progress to EXECUTE if we have understanding
            if self.context.stage == WorkflowStage.UNDERSTAND and self.context.has_understanding():
                self.context.stage = WorkflowStage.EXECUTE

    def record_plan(self, plan: str):
        """Record the plan for changes."""
        if self.context:
            self.context.plan = plan
            if self.context.stage == WorkflowStage.UNDERSTAND:
                self.context.stage = WorkflowStage.PLAN

    def record_validation(self, validation: Dict[str, Any]):
        """Record a validation check."""
        if self.context:
            self.context.validations.append(validation)
            if self.context.stage == WorkflowStage.PLAN:
                self.context.stage = WorkflowStage.VALIDATE

    def allow_execution(self):
        """Move to execution stage."""
        if self.context and self.context.stage == WorkflowStage.VALIDATE:
            self.context.stage = WorkflowStage.EXECUTE

    def get_cached_file(self, path: Path) -> Optional[str]:
        """Get cached file content if available.

        Args:
            path: Path to the file

        Returns:
            Cached file content if available, None otherwise
        """
        if self.context and path in self.context.file_cache:
            return self.context.file_cache[path]
        return None

    def check_modification_allowed(self, file_path: Path, operation: str) -> Dict[str, Any]:
        """
        Check if a file modification is allowed given current workflow state.

        Returns dict with:
        - allowed: bool
        - reason: str (if not allowed)
        - suggestions: List[str] (what to do instead)
        """
        if not self.strict_mode:
            return {"allowed": True}

        if not self.context:
            return {
                "allowed": False,
                "reason": "No workflow started. Start by understanding the problem.",
                "suggestions": [
                    f"Read {file_path} first to understand its current state",
                    "Search for related files in the project",
                    "List directory contents to see project structure"
                ]
            }

        # Check if we're in UNDERSTAND stage and trying to modify
        if self.context.stage == WorkflowStage.UNDERSTAND:
            if operation in ["write_file", "edit_file", "ast_edit"]:
                # For write_file on NEW files (that don't exist), skip the read check
                file_exists = file_path.exists()
                
                # Check if we've even read the target file (but only for existing files being modified)
                if operation in ["edit_file", "ast_edit"] and file_exists:
                    if not self.context.has_read_target_file(file_path):
                        return {
                            "allowed": False,
                            "reason": f"Must read {file_path} before modifying it",
                            "suggestions": [f"Read {file_path} first to understand its current content"]
                        }

                # If we've read the file, auto-progress to EXECUTE
                self.context.stage = WorkflowStage.EXECUTE

        # PLAN and VALIDATE stages are optional - skip them

        # If we're in EXECUTE stage and have done proper analysis, allow it
        if self.context.can_execute():
            self.context.modifications.append({
                "file": file_path,
                "operation": operation
            })
            return {"allowed": True}

        return {
            "allowed": False,
            "reason": f"Not ready to execute in stage {self.context.stage.value}",
            "suggestions": ["Follow the workflow: understand → plan → validate → execute"]
        }

    def get_summary(self) -> str:
        """Get a summary of the workflow progress."""
        if not self.context:
            return "No workflow active"

        lines = [
            f"Stage: {self.context.stage.value}",
            f"Files read: {len(self.context.files_read)}",
            f"Searches: {len(self.context.files_searched)}",
            f"Plan: {'✓' if self.context.has_plan() else '✗'}",
            f"Validations: {len(self.context.validations)}",
            f"Modifications: {len(self.context.modifications)}"
        ]
        return "\n".join(lines)
