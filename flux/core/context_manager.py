"""Context management for any LLM provider's token limits.

Provides intelligent conversation history pruning that works with
OpenAI, Anthropic, and any other LLM provider.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import json


@dataclass
class MessageImportance:
    """Importance scoring for conversation messages."""
    score: float  # 0.0 to 1.0
    reason: str
    keep_priority: int  # Lower = keep first


class ContextManager:
    """Manages conversation history to stay within token budgets."""
    
    def __init__(self, max_context_tokens: int = 3000):
        """Initialize context manager.
        
        Args:
            max_context_tokens: Maximum tokens for conversation history
                               (leaves room for system prompt + response)
        """
        self.max_context_tokens = max_context_tokens
        self.token_estimate_ratio = 4  # ~4 chars per token
    
    def prune_history(
        self,
        history: List[Dict[str, Any]],
        current_file_context: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Prune conversation history to fit within token budget.
        
        Works with ANY LLM provider (OpenAI, Anthropic, etc.).
        
        Strategy:
        - Always keep: Most recent messages (last 3 turns)
        - High priority: Current file content, recent errors, user requests
        - Low priority: Old successful tool outputs, verbose results
        - Drop first: Large file reads from >5 messages ago
        
        Args:
            history: Full conversation history
            current_file_context: Currently active file path (if any)
        
        Returns:
            Pruned history that fits within token budget
        """
        if not history:
            return history
        
        # Estimate current size
        current_tokens = self._estimate_tokens(history)
        
        if current_tokens <= self.max_context_tokens:
            return history  # Already within budget
        
        # Score each message by importance
        scored_messages = []
        for i, msg in enumerate(history):
            importance = self._score_message_importance(
                msg, i, len(history), current_file_context
            )
            scored_messages.append((msg, importance, i))
        
        # Always keep recent messages (last 3 turns = 6 messages)
        recent_threshold = max(0, len(history) - 6)
        must_keep = [item for item in scored_messages if item[2] >= recent_threshold]
        can_prune = [item for item in scored_messages if item[2] < recent_threshold]
        
        # Sort prunable messages by importance (keep highest scores)
        can_prune.sort(key=lambda x: x[1].score, reverse=True)
        
        # Build pruned history
        pruned = [msg for msg, _, _ in must_keep]
        pruned_tokens = self._estimate_tokens(pruned)
        
        # Add messages from prunable set until we hit budget
        for msg, importance, _ in can_prune:
            msg_tokens = self._estimate_tokens([msg])
            if pruned_tokens + msg_tokens <= self.max_context_tokens:
                pruned.append(msg)
                pruned_tokens += msg_tokens
            else:
                # If message is critical, summarize instead of dropping
                if importance.score > 0.8:
                    summary_msg = self._summarize_message(msg)
                    summary_tokens = self._estimate_tokens([summary_msg])
                    if pruned_tokens + summary_tokens <= self.max_context_tokens:
                        pruned.append(summary_msg)
                        pruned_tokens += summary_tokens
        
        # Sort back to chronological order
        # Create index mapping
        original_indices = {id(msg): i for i, msg in enumerate(history)}
        pruned.sort(key=lambda m: original_indices.get(id(m), len(history)))
        
        return pruned
    
    def _score_message_importance(
        self,
        message: Dict[str, Any],
        index: int,
        total_messages: int,
        current_file: Optional[str]
    ) -> MessageImportance:
        """Score a message's importance for keeping in context."""
        role = message.get("role", "")
        content = message.get("content", "")
        
        # Recent messages get high scores (handled separately but scored here too)
        recency = index / max(total_messages, 1)
        
        # User messages are critical
        if role == "user":
            return MessageImportance(
                score=0.95,
                reason="User query",
                keep_priority=1
            )
        
        # Check content type for assistant messages
        if isinstance(content, list):
            # Tool results
            has_error = any(
                "error" in str(block.get("content", "")).lower()
                for block in content
                if isinstance(block, dict)
            )
            
            has_current_file = any(
                current_file and current_file in str(block.get("content", ""))
                for block in content
                if isinstance(block, dict)
            ) if current_file else False
            
            if has_error:
                return MessageImportance(
                    score=0.9,
                    reason="Contains error - important for learning",
                    keep_priority=2
                )
            
            if has_current_file:
                return MessageImportance(
                    score=0.85,
                    reason="Relates to current file",
                    keep_priority=3
                )
            
            # Successful tool result - less important
            return MessageImportance(
                score=0.4 + (recency * 0.2),
                reason="Successful tool result",
                keep_priority=5
            )
        
        # Text responses from assistant
        if isinstance(content, str):
            # Short responses are cheap to keep
            if len(content) < 200:
                return MessageImportance(
                    score=0.6 + (recency * 0.2),
                    reason="Short assistant response",
                    keep_priority=4
                )
            
            # Long responses - evaluate by recency
            return MessageImportance(
                score=0.3 + (recency * 0.3),
                reason="Long assistant response",
                keep_priority=6
            )
        
        # Default - moderate importance
        return MessageImportance(
            score=0.5,
            reason="Unknown message type",
            keep_priority=7
        )
    
    def _estimate_tokens(self, messages: List[Dict[str, Any]]) -> int:
        """Estimate token count for messages."""
        total_chars = 0
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                total_chars += len(content)
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        total_chars += len(json.dumps(block))
        
        return total_chars // self.token_estimate_ratio
    
    def _summarize_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Create a summarized version of a message."""
        role = message.get("role", "")
        content = message.get("content", "")
        
        if isinstance(content, list):
            # Summarize tool results
            summary_blocks = []
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "tool_result":
                        # Keep only essential info
                        tool_id = block.get("tool_use_id", "")
                        result_str = str(block.get("content", ""))
                        
                        if "success" in result_str.lower():
                            summary_blocks.append({
                                "type": "tool_result",
                                "tool_use_id": tool_id,
                                "content": "[SUMMARIZED] Operation succeeded"
                            })
                        elif "error" in result_str.lower():
                            # Keep errors - they're important
                            summary_blocks.append(block)
                        else:
                            summary_blocks.append({
                                "type": "tool_result",
                                "tool_use_id": tool_id,
                                "content": "[SUMMARIZED] Result omitted for brevity"
                            })
            
            return {
                "role": role,
                "content": summary_blocks
            }
        
        # For text, truncate if long
        if isinstance(content, str) and len(content) > 300:
            return {
                "role": role,
                "content": content[:300] + "... [TRUNCATED]"
            }
        
        return message
    
    def get_pruning_stats(
        self,
        original: List[Dict[str, Any]],
        pruned: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Get statistics about pruning operation."""
        return {
            "original_messages": len(original),
            "pruned_messages": len(pruned),
            "messages_removed": len(original) - len(pruned),
            "original_tokens_estimate": self._estimate_tokens(original),
            "pruned_tokens_estimate": self._estimate_tokens(pruned),
            "tokens_saved": self._estimate_tokens(original) - self._estimate_tokens(pruned)
        }
