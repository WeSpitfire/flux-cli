"""Debug logging system for Flux to track inputs, context, and decision-making."""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict


@dataclass
class DebugEntry:
    """A single debug log entry."""
    timestamp: str
    event_type: str  # 'input', 'context', 'prompt', 'tool_call', 'response'
    data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None


class DebugLogger:
    """Comprehensive debug logging for Flux."""

    def __init__(self, flux_dir: Path, enabled: bool = False):
        """Initialize debug logger.

        Args:
            flux_dir: Flux configuration directory
            enabled: Whether debug logging is enabled
        """
        self.enabled = enabled
        self.session_id = f"debug_{int(time.time())}"
        self.debug_dir = flux_dir / "debug"
        self.debug_dir.mkdir(exist_ok=True)

        self.log_file = self.debug_dir / f"{self.session_id}.jsonl"
        self.entries: List[DebugEntry] = []

    def enable(self):
        """Enable debug logging."""
        self.enabled = True

    def disable(self):
        """Disable debug logging."""
        self.enabled = False

    def log(self, event_type: str, data: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None):
        """Log a debug event.

        Args:
            event_type: Type of event (input, context, prompt, tool_call, response)
            data: Event data
            metadata: Optional metadata
        """
        if not self.enabled:
            return

        entry = DebugEntry(
            timestamp=datetime.now().isoformat(),
            event_type=event_type,
            data=data,
            metadata=metadata or {}
        )

        self.entries.append(entry)

        # Write to file immediately for crash recovery
        self._write_entry(entry)

    def log_user_input(self, raw_input: str, processed_input: str):
        """Log user input and how it was processed.

        Args:
            raw_input: The raw input string from the user
            processed_input: The processed input after sanitization
        """
        self.log("user_input", {
            "raw": raw_input,
            "processed": processed_input,
            "length": len(raw_input),
            "has_newlines": "\n" in raw_input,
            "has_multiple_newlines": "\n\n" in raw_input,
            "line_count": len(raw_input.split("\n"))
        })

    def log_system_prompt(self, prompt: str, breakdown: Optional[Dict[str, Any]] = None):
        """Log the complete system prompt sent to LLM.

        Args:
            prompt: The system prompt
            breakdown: Optional breakdown of prompt components
        """
        self.log("system_prompt", {
            "prompt": prompt,
            "length": len(prompt),
            "estimated_tokens": len(prompt) // 4,  # Rough estimate
            "breakdown": breakdown or {}
        })

    def log_context_state(self, context: Dict[str, Any]):
        """Log the current context state.

        Args:
            context: Context information (files, tasks, memory, etc.)
        """
        self.log("context_state", context)

    def log_tool_call(self, tool_name: str, tool_input: Dict[str, Any],
                      result: Any, success: bool):
        """Log a tool execution.

        Args:
            tool_name: Name of the tool
            tool_input: Input parameters
            result: Result of execution
            success: Whether execution succeeded
        """
        self.log("tool_call", {
            "tool_name": tool_name,
            "input": tool_input,
            "result_preview": str(result)[:200],  # Truncate for readability
            "success": success
        })

    def log_llm_response(self, response: str, tool_uses: List[Dict[str, Any]]):
        """Log LLM response.

        Args:
            response: Text response from LLM
            tool_uses: List of tool calls in response
        """
        self.log("llm_response", {
            "text": response,
            "text_length": len(response),
            "tool_count": len(tool_uses),
            "tools": [t.get("name") for t in tool_uses]
        })

    def log_conversation_history(self, history: List[Dict[str, Any]]):
        """Log current conversation history.

        Args:
            history: Conversation history
        """
        # Create summarized version to avoid huge logs
        summarized = []
        for msg in history:
            summarized.append({
                "role": msg.get("role"),
                "content_length": len(str(msg.get("content", ""))),
                "has_tool_calls": "tool_calls" in msg,
                "has_tool_results": msg.get("role") == "tool"
            })

        self.log("conversation_history", {
            "message_count": len(history),
            "messages": summarized,
            "estimated_tokens": sum(len(str(m.get("content", ""))) // 4 for m in history)
        })

    def _write_entry(self, entry: DebugEntry):
        """Write a single entry to the log file.

        Args:
            entry: Debug entry to write
        """
        try:
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(asdict(entry)) + "\n")
        except Exception as e:
            # Don't crash on logging errors
            print(f"[Debug] Failed to write log entry: {e}")

    def get_summary(self) -> str:
        """Get a summary of the debug session.

        Returns:
            Formatted summary string
        """
        if not self.entries:
            return "No debug entries logged."

        # Count events by type
        event_counts = {}
        for entry in self.entries:
            event_counts[entry.event_type] = event_counts.get(entry.event_type, 0) + 1

        summary = f"Debug Session: {self.session_id}\n"
        summary += f"Total entries: {len(self.entries)}\n"
        summary += f"Log file: {self.log_file}\n\n"
        summary += "Events:\n"
        for event_type, count in sorted(event_counts.items()):
            summary += f"  {event_type}: {count}\n"

        return summary

    def get_last_entries(self, n: int = 10, event_type: Optional[str] = None) -> List[DebugEntry]:
        """Get the last N debug entries.

        Args:
            n: Number of entries to retrieve
            event_type: Optional filter by event type

        Returns:
            List of debug entries
        """
        entries = self.entries
        if event_type:
            entries = [e for e in entries if e.event_type == event_type]

        return entries[-n:]

    def analyze_issue(self, issue_description: str) -> str:
        """Analyze recent logs to diagnose an issue.

        Args:
            issue_description: Description of the issue

        Returns:
            Analysis report
        """
        report = f"Issue Analysis: {issue_description}\n"
        report += "=" * 60 + "\n\n"

        # Get recent inputs
        recent_inputs = self.get_last_entries(5, "user_input")
        if recent_inputs:
            report += "Recent Inputs:\n"
            for entry in recent_inputs:
                data = entry.data
                report += f"  - Length: {data['length']}, Lines: {data['line_count']}, "
                report += f"Has newlines: {data['has_newlines']}\n"
                report += f"    Raw (first 100 chars): {data['raw'][:100]}...\n"

        # Get recent tool calls
        recent_tools = self.get_last_entries(10, "tool_call")
        if recent_tools:
            report += "\nRecent Tool Calls:\n"
            tool_counts = {}
            for entry in recent_tools:
                tool_name = entry.data["tool_name"]
                tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1

            for tool, count in tool_counts.items():
                report += f"  - {tool}: {count} times\n"

        # Check for patterns
        report += "\nPattern Detection:\n"

        # Check for repeated empty inputs
        empty_count = sum(1 for e in recent_inputs
                         if e.data.get("length", 0) == 0)
        if empty_count > 2:
            report += f"  ⚠️  {empty_count} empty inputs detected - possible parsing issue\n"

        # Check for tool retry loops
        if recent_tools:
            last_3_tools = [e.data["tool_name"] for e in recent_tools[-3:]]
            if len(set(last_3_tools)) == 1:
                report += f"  ⚠️  Same tool called 3 times in a row: {last_3_tools[0]}\n"

        # Check for multi-line input issues
        multiline_inputs = [e for e in recent_inputs
                           if e.data.get("has_multiple_newlines")]
        if multiline_inputs:
            report += f"  ⚠️  {len(multiline_inputs)} multi-line inputs detected\n"

        return report
