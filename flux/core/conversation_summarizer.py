"""Conversation Summarizer - Condenses old messages to preserve context.

Instead of dropping old messages when context gets full, this module summarizes
them into concise summaries that preserve important information while reducing
token count.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path


@dataclass
class ConversationSummary:
    """A summary of a chunk of conversation messages.
    
    Represents a condensed version of multiple messages, preserving key
    information like files discussed, decisions made, and tasks completed.
    """
    
    # Summary content
    summary_text: str
    message_range: str  # e.g. "messages 10-30"
    
    # Key information extracted
    files_discussed: List[str] = field(default_factory=list)
    decisions_made: List[str] = field(default_factory=list)
    tasks_completed: List[str] = field(default_factory=list)
    errors_encountered: List[str] = field(default_factory=list)
    
    # Metadata
    original_message_count: int = 0
    original_token_count: int = 0
    summary_token_count: int = 0
    created_at: str = ""
    
    def __post_init__(self):
        """Set creation timestamp."""
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
    
    def to_prompt(self) -> str:
        """Convert to prompt text for inclusion in LLM context.
        
        Returns:
            Formatted summary text for system prompt
        """
        lines = [f"[Previous conversation: {self.message_range}]"]
        lines.append(self.summary_text)
        
        if self.files_discussed:
            lines.append(f"Files: {', '.join(self.files_discussed[:5])}")
        
        if self.decisions_made:
            lines.append("Decisions:")
            for decision in self.decisions_made[:3]:
                lines.append(f"  • {decision}")
        
        if self.tasks_completed:
            lines.append("Completed:")
            for task in self.tasks_completed[:3]:
                lines.append(f"  ✓ {task}")
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'summary_text': self.summary_text,
            'message_range': self.message_range,
            'files_discussed': self.files_discussed,
            'decisions_made': self.decisions_made,
            'tasks_completed': self.tasks_completed,
            'errors_encountered': self.errors_encountered,
            'original_message_count': self.original_message_count,
            'original_token_count': self.original_token_count,
            'summary_token_count': self.summary_token_count,
            'created_at': self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "ConversationSummary":
        """Create from dictionary."""
        return cls(**data)


class ConversationSummarizer:
    """Manages conversation summarization to preserve context while reducing tokens.
    
    Strategy:
    - Keep recent messages (last 10) in full detail
    - Summarize older messages (11-50) into concise summaries
    - Drop ancient messages (51+)
    
    This allows much longer effective conversations without hitting token limits.
    """
    
    def __init__(self, project_name: str):
        """Initialize summarizer.
        
        Args:
            project_name: Name of the project (for storage path)
        """
        self.project_name = project_name
        self.summaries: List[ConversationSummary] = []
        
        # Storage path
        self.storage_dir = Path.home() / ".flux" / "projects" / project_name
        self.summaries_file = self.storage_dir / "summaries.json"
        
        # Load existing summaries
        self.load()
    
    def should_summarize(self, 
                        conversation_tokens: int,
                        max_tokens: int,
                        threshold: float = 0.7) -> bool:
        """Check if conversation should be summarized.
        
        Args:
            conversation_tokens: Current conversation token count
            max_tokens: Maximum allowed tokens
            threshold: Trigger summarization at this % of max (default 70%)
        
        Returns:
            True if summarization should be triggered
        """
        if max_tokens <= 0:
            return False
        
        usage_ratio = conversation_tokens / max_tokens
        return usage_ratio >= threshold
    
    def extract_key_info(self, messages: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Extract key information from messages.
        
        Args:
            messages: List of conversation messages
        
        Returns:
            Dictionary with extracted info (files, decisions, tasks, errors)
        """
        files = set()
        decisions = []
        tasks = []
        errors = []
        
        for msg in messages:
            content = msg.get('content', '')
            if isinstance(content, list):
                # Handle multi-part messages
                content = ' '.join([
                    part.get('text', '') if isinstance(part, dict) else str(part)
                    for part in content
                ])
            
            content_lower = content.lower()
            
            # Extract file mentions (simple heuristic)
            import re
            file_patterns = [
                r'`([^`]+\.(py|js|ts|jsx|tsx|go|rs|java|cpp|c|h|rb|php|swift|kt))`',
                r'([a-zA-Z0-9_/-]+\.(py|js|ts|jsx|tsx|go|rs|java|cpp|c|h|rb|php|swift|kt))',
            ]
            for pattern in file_patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    file_name = match[0] if isinstance(match, tuple) else match
                    files.add(file_name)
            
            # Extract decisions (lines starting with decision keywords)
            decision_keywords = ['decided to', 'will use', 'choosing', 'opted for', 'going with']
            for keyword in decision_keywords:
                if keyword in content_lower:
                    # Extract the sentence
                    sentences = content.split('.')
                    for sentence in sentences:
                        if keyword in sentence.lower():
                            decisions.append(sentence.strip()[:100])
                            break
            
            # Extract completed tasks (lines with checkmarks or "completed")
            if any(word in content_lower for word in ['completed', 'finished', 'done', '✓', '✅']):
                # Extract task description
                sentences = content.split('.')
                for sentence in sentences:
                    s_lower = sentence.lower()
                    if any(word in s_lower for word in ['completed', 'finished', 'done']):
                        tasks.append(sentence.strip()[:100])
                        break
            
            # Extract errors
            if any(word in content_lower for word in ['error', 'failed', 'exception', '❌']):
                sentences = content.split('.')
                for sentence in sentences:
                    s_lower = sentence.lower()
                    if any(word in s_lower for word in ['error', 'failed', 'exception']):
                        errors.append(sentence.strip()[:100])
                        break
        
        return {
            'files': list(files)[:10],  # Top 10
            'decisions': decisions[:5],  # Top 5
            'tasks': tasks[:5],  # Top 5
            'errors': errors[:3]  # Top 3
        }
    
    def create_summary_prompt(self, messages: List[Dict[str, Any]]) -> str:
        """Create a prompt for LLM to summarize messages.
        
        Args:
            messages: List of messages to summarize
        
        Returns:
            Prompt text for summarization
        """
        # Format messages for summarization
        formatted_messages = []
        for i, msg in enumerate(messages, 1):
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            if isinstance(content, list):
                content = ' '.join([
                    part.get('text', '') if isinstance(part, dict) else str(part)
                    for part in content
                ])
            
            # Truncate very long messages
            if len(content) > 500:
                content = content[:500] + "..."
            
            formatted_messages.append(f"{i}. {role}: {content}")
        
        prompt = (
            "Summarize the following conversation messages into a concise summary "
            "(max 200 words) that preserves key information:\n\n"
            + "\n".join(formatted_messages) +
            "\n\nProvide a concise summary focusing on:\n"
            "1. What was discussed\n"
            "2. Decisions made\n"
            "3. Tasks completed\n"
            "4. Files modified\n"
            "5. Any issues encountered\n\n"
            "Summary:"
        )
        
        return prompt
    
    async def summarize_messages(self,
                                 messages: List[Dict[str, Any]],
                                 llm_client,
                                 start_index: int,
                                 end_index: int) -> ConversationSummary:
        """Summarize a chunk of messages using LLM.
        
        Args:
            messages: Messages to summarize
            llm_client: LLM client for generating summary
            start_index: Start index in conversation
            end_index: End index in conversation
        
        Returns:
            ConversationSummary object
        """
        # Extract key info first (don't need LLM for this)
        key_info = self.extract_key_info(messages)
        
        # Create summary prompt
        summary_prompt = self.create_summary_prompt(messages)
        
        # Get LLM summary (simple completion, no tools)
        summary_text = ""
        try:
            # Use a simple system prompt for summarization
            system_prompt = (
                "You are a conversation summarizer. Provide concise, factual "
                "summaries focusing on key information."
            )
            
            async for event in llm_client.send_message(
                message=summary_prompt,
                system_prompt=system_prompt,
                tools=[]  # No tools needed for summarization
            ):
                if event["type"] == "text":
                    summary_text += event["content"]
        except Exception:
            # Fallback: use first message as summary
            summary_text = f"Discussion about {', '.join(key_info['files'][:3])}" if key_info['files'] else "General discussion"
        
        # Estimate token counts (rough approximation: 1 token ≈ 4 chars)
        original_tokens = sum(len(str(m.get('content', ''))) for m in messages) // 4
        summary_tokens = len(summary_text) // 4
        
        return ConversationSummary(
            summary_text=summary_text.strip(),
            message_range=f"messages {start_index}-{end_index}",
            files_discussed=key_info['files'],
            decisions_made=key_info['decisions'],
            tasks_completed=key_info['tasks'],
            errors_encountered=key_info['errors'],
            original_message_count=len(messages),
            original_token_count=original_tokens,
            summary_token_count=summary_tokens
        )
    
    def get_summaries_for_prompt(self, max_summaries: int = 3) -> str:
        """Get formatted summaries for inclusion in system prompt.
        
        Args:
            max_summaries: Maximum number of summaries to include
        
        Returns:
            Formatted summary text
        """
        if not self.summaries:
            return ""
        
        # Get most recent summaries
        recent_summaries = self.summaries[-max_summaries:]
        
        lines = ["=" * 60]
        lines.append("CONVERSATION HISTORY (SUMMARIZED)")
        lines.append("=" * 60)
        
        for summary in recent_summaries:
            lines.append(summary.to_prompt())
            lines.append("")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def add_summary(self, summary: ConversationSummary):
        """Add a new summary.
        
        Args:
            summary: ConversationSummary to add
        """
        self.summaries.append(summary)
        self.save()
    
    def save(self):
        """Save summaries to disk."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        data = {
            'summaries': [s.to_dict() for s in self.summaries],
            'updated_at': datetime.now().isoformat()
        }
        
        with open(self.summaries_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def load(self):
        """Load summaries from disk."""
        if not self.summaries_file.exists():
            return
        
        try:
            with open(self.summaries_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.summaries = [
                ConversationSummary.from_dict(s)
                for s in data.get('summaries', [])
            ]
        except Exception:
            # If corrupt, start fresh
            self.summaries = []
    
    def clear(self):
        """Clear all summaries."""
        self.summaries = []
        if self.summaries_file.exists():
            self.summaries_file.unlink()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get summarization statistics.
        
        Returns:
            Dictionary with stats
        """
        if not self.summaries:
            return {
                'total_summaries': 0,
                'total_messages_summarized': 0,
                'total_tokens_saved': 0,
                'compression_ratio': 0.0
            }
        
        total_messages = sum(s.original_message_count for s in self.summaries)
        total_original_tokens = sum(s.original_token_count for s in self.summaries)
        total_summary_tokens = sum(s.summary_token_count for s in self.summaries)
        tokens_saved = total_original_tokens - total_summary_tokens
        compression_ratio = (total_summary_tokens / total_original_tokens * 100) if total_original_tokens > 0 else 0
        
        return {
            'total_summaries': len(self.summaries),
            'total_messages_summarized': total_messages,
            'total_original_tokens': total_original_tokens,
            'total_summary_tokens': total_summary_tokens,
            'total_tokens_saved': tokens_saved,
            'compression_ratio': compression_ratio
        }
