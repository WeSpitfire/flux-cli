"""CLI Builder - handles initialization and dependency setup."""

from pathlib import Path
from typing import Optional
from rich.console import Console
import sys

from flux.core.config import Config
from flux.core.project import ProjectDetector
from flux.core.memory import MemoryStore
from flux.core.undo import UndoManager
from flux.core.workflow import WorkflowEnforcer
from flux.core.approval import ApprovalManager
from flux.core.git_utils import GitIntegration
from flux.core.codebase_intelligence import CodebaseGraph
from flux.core.impact_analyzer import ImpactAnalyzer
from flux.core.suggestions import SuggestionsEngine
from flux.core.workspace import Workspace
from flux.core.failure_tracker import FailureTracker
from flux.core.background_processor import SmartBackgroundProcessor
from flux.core.code_validator import CodeValidator
from flux.core.debug_logger import DebugLogger
from flux.core.state_tracker import ProjectStateTracker
from flux.core.error_parser import ErrorParser
from flux.core.test_runner import TestRunner
from flux.core.auto_fixer import AutoFixer
from flux.core.orchestrator import AIOrchestrator
from flux.core.orchestrator_tools import register_all_tools
from flux.core.task_planner import TaskPlanner
from flux.ui.nl_commands import get_parser
from flux.llm.provider_factory import create_provider
from flux.tools.base import ToolRegistry
from flux.tools.file_ops import ReadFilesTool, WriteFileTool, EditFileTool, MoveFileTool, DeleteFileTool
from flux.tools.command import RunCommandTool
from flux.tools.search import GrepSearchTool
from flux.tools.filesystem import ListFilesTool, FindFilesTool
from flux.tools.ast_edit import ASTEditTool
from flux.tools.validation import ValidationTool
from flux.tools.preview import PreviewEditTool
from flux.tools.line_insert import InsertAtLineTool
from flux.ui.display_manager import DisplayManager
from flux.ui.command_router import CommandRouter


class CLIBuilder:
    """Builds and initializes CLI with all dependencies."""

    @staticmethod
    def build(config: Config, cwd: Path):
        """Build a fully initialized CLI instance.
        
        Args:
            config: Configuration
            cwd: Current working directory
            
        Returns:
            Initialized CLI instance with all dependencies
        """
        from flux.ui.cli import CLI
        cli = CLI.__new__(CLI)
        
        # Store config and cwd
        cli.config = config
        cli.cwd = cwd
        
        # Initialize display manager
        cli.display = DisplayManager()
        
        # Keep console for backward compatibility
        cli.console = Console(file=sys.stdout, force_terminal=False)
        cli.llm = create_provider(config)
        
        # Placeholder for command router (set after dependencies)
        cli.commands = None
        
        # Detect project
        cli.project_info = ProjectDetector(cwd).detect()
        
        # Initialize core services
        cli.memory = MemoryStore(config.flux_dir, cwd)
        cli.undo = UndoManager(config.flux_dir, cwd)
        
        # Initialize workflow enforcer
        strict_mode = "haiku" in config.model.lower() or "gpt-3.5" in config.model.lower()
        cli.workflow = WorkflowEnforcer(cwd, strict_mode=strict_mode)
        
        # Initialize managers
        cli.approval = ApprovalManager(auto_approve=config.auto_approve)
        cli.git = GitIntegration(cwd)
        
        # Initialize codebase intelligence (lazy loading)
        cli.codebase_graph = None
        cli._graph_building = False
        cli._project_readme = None
        cli.impact_analyzer = None
        cli.suggestions_engine = None
        
        # Initialize workspace manager
        workspace_dir = config.flux_dir / "workspace"
        cli.workspace = Workspace(workspace_dir, cwd)
        
        # Initialize trackers
        cli.failure_tracker = FailureTracker()
        
        from flux.core.tool_metrics import ToolSuccessTracker
        metrics_path = config.flux_dir / "tool_metrics.json"
        cli.tool_metrics = ToolSuccessTracker(storage_path=metrics_path)
        
        # Initialize processors and utilities
        cli.bg_processor = SmartBackgroundProcessor(cwd)
        cli.code_validator = CodeValidator(cwd)
        cli.debug_logger = DebugLogger(config.flux_dir, enabled=False)
        cli.state_tracker = ProjectStateTracker(cwd)
        cli.nl_parser = get_parser()
        cli.error_parser = ErrorParser(cwd)
        
        # Initialize test runner and watcher
        cli.test_runner = TestRunner(cwd)
        cli.test_watcher = None
        
        # Initialize auto-fixer
        cli.auto_fixer = AutoFixer(cwd, enabled=True)
        cli.auto_fix_watcher = None
        
        # Initialize tool registry
        cli.tools = ToolRegistry()
        cli.tools.register(ReadFilesTool(cwd, workflow_enforcer=cli.workflow, background_processor=cli.bg_processor))
        cli.tools.register(WriteFileTool(cwd, undo_manager=cli.undo, workflow_enforcer=cli.workflow, approval_manager=cli.approval, code_validator=cli.code_validator))
        cli.tools.register(EditFileTool(cwd, undo_manager=cli.undo, workflow_enforcer=cli.workflow, approval_manager=cli.approval, code_validator=cli.code_validator))
        cli.tools.register(MoveFileTool(cwd, undo_manager=cli.undo, workflow_enforcer=cli.workflow, approval_manager=cli.approval))
        cli.tools.register(DeleteFileTool(cwd, undo_manager=cli.undo, workflow_enforcer=cli.workflow, approval_manager=cli.approval))
        cli.tools.register(InsertAtLineTool(cwd, undo_manager=cli.undo, workflow_enforcer=cli.workflow, approval_manager=cli.approval))
        cli.tools.register(PreviewEditTool(cwd))
        cli.tools.register(RunCommandTool(cwd))
        cli.tools.register(GrepSearchTool(cwd, workflow_enforcer=cli.workflow))
        cli.tools.register(ListFilesTool(cwd))
        cli.tools.register(FindFilesTool(cwd))
        
        # Register ast_edit only for larger models
        if "haiku" not in config.model.lower() and "gpt-3.5" not in config.model.lower():
            cli.tools.register(ASTEditTool(cwd, undo_manager=cli.undo, workflow_enforcer=cli.workflow, approval_manager=cli.approval))
        
        cli.tools.register(ValidationTool(cwd))
        
        # Initialize AI Orchestrator
        cli.orchestrator = AIOrchestrator(cli.llm, cwd)
        register_all_tools(cli.orchestrator, cli)
        
        # Initialize Smart Task Planner (lazy)
        cli.task_planner = None
        
        # Initialize Session Manager
        from flux.core.session_manager import SessionManager, EventType
        cli.session_manager = SessionManager(cwd)
        cli.EventType = EventType
        
        # Initialize Proactive Monitor
        from flux.core.proactive_monitor import ProactiveMonitor, MonitorType
        cli.proactive_monitor = ProactiveMonitor(cwd, cli.llm)
        cli.proactive_monitor.add_notification_callback(cli._print_monitor_notification)
        cli.MonitorType = MonitorType
        
        # Initialize Workflow Manager and Executor
        from flux.core.workflows import WorkflowManager, WorkflowExecutor
        cli.workflow_manager = WorkflowManager(cwd)
        cli.workflow_executor = WorkflowExecutor(cli.orchestrator)
        cli.workflow_executor.add_notification_callback(cli._print_monitor_notification)
        
        # Initialize Command Suggestion Engine
        from flux.core.command_suggestions import CommandSuggestionEngine
        cli.command_suggester = CommandSuggestionEngine(
            session_manager=cli.session_manager,
            state_tracker=cli.state_tracker,
            git=cli.git,
            proactive_monitor=cli.proactive_monitor,
            workflow_manager=cli.workflow_manager
        )
        
        # Input blocking state
        cli._llm_processing = False
        cli._processing_cancelled = False
        
        # Initialize feature managers (NOW that all dependencies ready)
        cli.commands = CommandRouter(cli)
        
        from flux.core.conversation_manager import ConversationManager
        cli.conversation = ConversationManager(cli)
        
        from flux.core.workflow_coordinator import WorkflowCoordinator
        cli.workflow_coord = WorkflowCoordinator(cli)
        
        from flux.core.git_test_manager import GitTestManager
        cli.git_test = GitTestManager(cli)
        
        from flux.core.codebase_analyzer import CodebaseAnalyzer
        cli.codebase_analyzer = CodebaseAnalyzer(cli)
        
        from flux.core.session_task_manager import SessionTaskManager
        cli.session_task_mgr = SessionTaskManager(cli)
        
        # Integrate performance improvements
        from flux.core.performance_integration import integrate_performance_improvements
        cli.performance = integrate_performance_improvements(cli)
        
        from flux.core.autofix_manager import AutoFixManager
        cli.autofix_mgr = AutoFixManager(cli)
        
        # Initialize UX Differentiators
        from flux.core.copilot_engine import CopilotEngine
        from flux.core.time_machine import TimeMachine
        from flux.core.smart_context import ProjectKnowledgeGraph
        
        # Copilot Mode - proactive monitoring
        cli.copilot = CopilotEngine(
            cwd=cwd,
            state_tracker=cli.state_tracker,
            git=cli.git,
            test_runner=cli.test_runner,
            llm=cli.llm
        )
        cli.copilot.add_notification_callback(cli._print_copilot_suggestion)
        
        # Time Machine - state snapshots
        cli.time_machine = TimeMachine(
            flux_dir=config.flux_dir,
            cwd=cwd
        )
        
        # Smart Context - knowledge graph
        cli.smart_context = ProjectKnowledgeGraph(
            flux_dir=config.flux_dir
        )
        
        return cli
