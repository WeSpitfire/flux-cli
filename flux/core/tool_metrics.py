"""Tool success rate tracking for reliability metrics."""

from typing import Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path


@dataclass
class ToolMetrics:
    """Metrics for a single tool."""
    tool_name: str
    attempts: int = 0
    successes: int = 0
    failures: int = 0
    last_used: Optional[datetime] = None
    avg_execution_time_ms: float = 0.0

    @property
    def success_rate(self) -> float:
        """Calculate success rate (0.0 to 1.0)."""
        if self.attempts == 0:
            return 1.0  # Assume success for unused tools
        return self.successes / self.attempts

    @property
    def failure_rate(self) -> float:
        """Calculate failure rate (0.0 to 1.0)."""
        return 1.0 - self.success_rate

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "tool_name": self.tool_name,
            "attempts": self.attempts,
            "successes": self.successes,
            "failures": self.failures,
            "success_rate": self.success_rate,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "avg_execution_time_ms": self.avg_execution_time_ms
        }


class ToolSuccessTracker:
    """Tracks tool success rates for reliability analysis."""

    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize tracker.

        Args:
            storage_path: Path to store metrics (optional, for persistence)
        """
        self.metrics: Dict[str, ToolMetrics] = {}
        self.storage_path = storage_path

        # Load existing metrics if storage path provided
        if storage_path and storage_path.exists():
            self._load_metrics()

    def record_attempt(self, tool_name: str, success: bool, execution_time_ms: float = 0.0):
        """Record a tool execution attempt.

        Args:
            tool_name: Name of the tool
            success: Whether the attempt succeeded
            execution_time_ms: Execution time in milliseconds
        """
        if tool_name not in self.metrics:
            self.metrics[tool_name] = ToolMetrics(tool_name=tool_name)

        metrics = self.metrics[tool_name]
        metrics.attempts += 1

        if success:
            metrics.successes += 1
        else:
            metrics.failures += 1

        metrics.last_used = datetime.now()

        # Update rolling average execution time
        if execution_time_ms > 0:
            total_time = metrics.avg_execution_time_ms * (metrics.attempts - 1)
            metrics.avg_execution_time_ms = (total_time + execution_time_ms) / metrics.attempts

        # Persist if storage path configured
        if self.storage_path:
            self._save_metrics()

    def get_success_rate(self, tool_name: str) -> float:
        """Get success rate for a tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Success rate (0.0 to 1.0)
        """
        if tool_name not in self.metrics:
            return 1.0  # Assume success for unused tools
        return self.metrics[tool_name].success_rate

    def get_most_reliable_tools(self, min_attempts: int = 3, limit: int = 5) -> list:
        """Get most reliable tools based on success rate.

        Args:
            min_attempts: Minimum attempts to be considered
            limit: Maximum number of tools to return

        Returns:
            List of (tool_name, success_rate) tuples
        """
        # Filter tools with enough attempts
        qualified = [
            (name, m) for name, m in self.metrics.items()
            if m.attempts >= min_attempts
        ]

        # Sort by success rate
        sorted_tools = sorted(qualified, key=lambda x: x[1].success_rate, reverse=True)

        return [(name, m.success_rate) for name, m in sorted_tools[:limit]]

    def get_least_reliable_tools(self, min_attempts: int = 3, limit: int = 5) -> list:
        """Get least reliable tools based on success rate.

        Args:
            min_attempts: Minimum attempts to be considered
            limit: Maximum number of tools to return

        Returns:
            List of (tool_name, success_rate) tuples
        """
        # Filter tools with enough attempts
        qualified = [
            (name, m) for name, m in self.metrics.items()
            if m.attempts >= min_attempts
        ]

        # Sort by success rate (ascending)
        sorted_tools = sorted(qualified, key=lambda x: x[1].success_rate)

        return [(name, m.success_rate) for name, m in sorted_tools[:limit]]

    def get_tool_guidance(self, model: str = "sonnet") -> str:
        """Generate guidance on which tools to prefer.

        Args:
            model: Model name to tailor guidance

        Returns:
            Formatted guidance string
        """
        most_reliable = self.get_most_reliable_tools(min_attempts=3, limit=3)
        least_reliable = self.get_least_reliable_tools(min_attempts=3, limit=3)

        if not most_reliable and not least_reliable:
            return "No tool metrics available yet."

        guidance = "**Tool Reliability Guidance:**\n\n"

        if most_reliable:
            guidance += "**Most Reliable Tools:**\n"
            for tool_name, success_rate in most_reliable:
                percentage = success_rate * 100
                guidance += f"- {tool_name}: {percentage:.0f}% success rate\n"
            guidance += "\n"

        if least_reliable:
            guidance += "**Use With Caution:**\n"
            for tool_name, success_rate in least_reliable:
                percentage = success_rate * 100
                guidance += f"- {tool_name}: {percentage:.0f}% success rate (consider alternatives)\n"

        return guidance

    def get_summary(self) -> str:
        """Get formatted summary of all tool metrics.

        Returns:
            Formatted summary string
        """
        if not self.metrics:
            return "No tool usage data yet."

        lines = ["Tool Usage Metrics:", "=" * 60, ""]

        # Sort by attempts (most used first)
        sorted_metrics = sorted(
            self.metrics.items(),
            key=lambda x: x[1].attempts,
            reverse=True
        )

        for tool_name, metrics in sorted_metrics:
            success_pct = metrics.success_rate * 100
            status = "✅" if success_pct >= 80 else "⚠️" if success_pct >= 60 else "❌"

            lines.append(f"{status} {tool_name}:")
            lines.append(f"   Attempts: {metrics.attempts}")
            lines.append(f"   Successes: {metrics.successes}")
            lines.append(f"   Failures: {metrics.failures}")
            lines.append(f"   Success Rate: {success_pct:.1f}%")

            if metrics.avg_execution_time_ms > 0:
                lines.append(f"   Avg Time: {metrics.avg_execution_time_ms:.0f}ms")

            lines.append("")

        return "\n".join(lines)

    def _save_metrics(self):
        """Save metrics to storage."""
        if not self.storage_path:
            return

        # Ensure directory exists
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to JSON
        data = {
            "metrics": {
                name: m.to_dict() for name, m in self.metrics.items()
            },
            "last_updated": datetime.now().isoformat()
        }

        with open(self.storage_path, 'w') as f:
            json.dump(data, f, indent=2)

    def _load_metrics(self):
        """Load metrics from storage."""
        if not self.storage_path or not self.storage_path.exists():
            return

        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)

            # Reconstruct metrics
            for name, metric_data in data.get("metrics", {}).items():
                last_used = metric_data.get("last_used")
                if last_used:
                    last_used = datetime.fromisoformat(last_used)

                self.metrics[name] = ToolMetrics(
                    tool_name=metric_data["tool_name"],
                    attempts=metric_data["attempts"],
                    successes=metric_data["successes"],
                    failures=metric_data["failures"],
                    last_used=last_used,
                    avg_execution_time_ms=metric_data.get("avg_execution_time_ms", 0.0)
                )
        except Exception as e:
            # If loading fails, start fresh
            self.metrics = {}

    def reset(self):
        """Reset all metrics."""
        self.metrics = {}
        if self.storage_path and self.storage_path.exists():
            self.storage_path.unlink()
