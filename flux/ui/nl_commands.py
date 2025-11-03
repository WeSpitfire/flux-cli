"""Natural language command parsing for intuitive interactions."""

import re
from typing import Optional, Tuple, List


class NaturalLanguageParser:
    """
    Parse natural language inputs into structured commands.
    
    Allows flexible, intent-based commands instead of rigid slash syntax.
    Examples:
        "show me what changed" -> /diff
        "undo that" -> /undo
        "what's the current task" -> /memory
        "run the tests" -> /test
    """
    
    def __init__(self):
        """Initialize parser with intent patterns."""
        # Pattern format: (regex_pattern, command, extract_args_function)
        self.patterns = [
            # Help & Info
            (r'\b(help|how do i|what can you do)\b', '/help', None),
            (r'\b(show|view|display|see|check)\s+(the\s+)?(current\s+)?model\b', '/model', None),
            
            # History & Memory
            (r'\b(show|view|display|see|check)\s+(the\s+)?(conversation\s+)?history\b', '/history', None),
            (r'\b(what\'?s|show|view|display|see|check)\s+(the\s+)?(current\s+)?task\b', '/memory', None),
            (r'\b(show|view|display|see|check)\s+(the\s+)?memory\b', '/memory', None),
            (r'\bset\s+task\s+(.+)', '/task', lambda m: m.group(1)),
            (r'\b(create|make|add|new)\s+checkpoint\s+(.+)', '/checkpoint', lambda m: m.group(2)),
            
            # Git Operations
            (r'\b(show|view|display|see|check|what|list)\s+(me\s+)?(the\s+)?(what\s+)?(git\s+)?(changed|changes|diff|modifications)\b', '/diff', None),
            (r'\b(commit|save|stage)\s+(the\s+)?(changes|work)\b', '/commit', None),
            (r'\bcommit\s+with\s+message\s+["\'](.+)["\']', '/commit', lambda m: m.group(1)),
            
            # Testing
            (r'\b(run|execute|start|do|perform)\s+(the\s+)?(tests?|testing)\b', '/test', None),
            (r'\b(test|check)\s+(the\s+)?code\b', '/test', None),
            (r'\b(start|enable|begin)\s+(test\s+)?watch(ing)?\s+(mode)?\b', '/watch', None),
            (r'\b(watch|monitor)\s+(tests?|files?)\b', '/watch', None),
            (r'\b(stop|disable|end)\s+(test\s+)?watch(ing)?\s+(mode)?\b', '/watch-stop', None),
            
            # State & Context
            (r'\b(show|view|display|see|check|what\'?s)\s+(the\s+)?(current\s+)?(project\s+)?state\b', '/state', None),
            (r'\b(show|view|display|see|check)\s+(the\s+)?status\b', '/state', None),
            (r'\bwhat\'?s\s+happening\b', '/state', None),
            
            # Undo Operations
            (r'\b(undo|revert|rollback)\s+(that|last|previous)\b', '/undo', None),
            (r'\b(show|view|display|see|check)\s+(the\s+)?undo\s+history\b', '/undo-history', None),
            
            # Workflow
            (r'\b(show|view|display|see|check)\s+(the\s+)?workflow\s+(status)?\b', '/workflow', None),
            (r'\b(show|view|display|see|check)\s+(the\s+)?approval\s+(stats|statistics)?\b', '/approval', None),
            
            # Clear & Reset
            (r'\b(clear|reset|wipe|delete)\s+(the\s+)?(conversation\s+)?history\b', '/clear', None),
            (r'\bstart\s+over\b', '/clear', None),
            
            # Codebase Intelligence
            (r'\b(build|create|make|index)\s+(the\s+)?codebase\s+(graph|index)\b', '/index', None),
            (r'\b(find|show|search|look\s+for)\s+related\s+(files?\s+)?(.+)', '/related', lambda m: m.group(3)),
            (r'\b(show|view|display|see|check)\s+(the\s+)?architecture\b', '/architecture', None),
            (r'\b(preview|show|check)\s+(the\s+)?impact\s+of\s+(.+)', '/preview', lambda m: m.group(3)),
            (r'\b(suggest|recommend|advise)\s+(something|improvements?)?\b', '/suggest', None),
            (r'\bgive\s+me\s+suggestions\b', '/suggest', None),
            
            # Workspace
            (r'\b(show|view|display|list|see|check)\s+(all\s+)?(the\s+)?sessions?\b', '/sessions', None),
            (r'\b(show|view|display|list|see|check)\s+(all\s+)?(the\s+)?tasks?\b', '/tasks', None),
            (r'\b(show|view|display|see|check)\s+(the\s+)?summary\b', '/summary', None),
            (r'\b(show|view|display|see|check)\s+(the\s+)?(project\s+)?stats\b', '/stats', None),
            (r'\bcreate\s+(a\s+)?new\s+task\s+(.+)', '/newtask', lambda m: m.group(2)),
            
            # Validation & Fixes
            (r'\b(validate|check|verify)\s+(the\s+)?(code|files?)\b', '/validate', None),
            (r'\b(fix|repair|correct)\s+(that|this|it|the\s+error)\b', '/fix', None),
            (r'\b(fix|repair|correct)\s+(the\s+)?(last\s+)?error\b', '/fix', None),
            
            # Debug
            (r'\b(enable|turn\s+on|start)\s+debug(ging)?\b', '/debug-on', None),
            (r'\b(disable|turn\s+off|stop)\s+debug(ging)?\b', '/debug-off', None),
            (r'\b(show|view|display|see|check)\s+(the\s+)?debug\s+(log|info|session)?\b', '/debug', None),
            (r'\banalyze\s+(the\s+)?logs?\s+for\s+(.+)', '/debug-analyze', lambda m: m.group(2)),
            
            # Performance
            (r'\b(show|view|display|see|check)\s+(the\s+)?performance\b', '/performance', None),
            (r'\b(show|view|display|see|check)\s+perf\b', '/perf', None),
        ]
        
        # Compile patterns for efficiency
        self.compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), cmd, extractor)
            for pattern, cmd, extractor in self.patterns
        ]
    
    def parse(self, text: str) -> Optional[Tuple[str, Optional[str]]]:
        """
        Parse natural language text into a command.
        
        Args:
            text: User input text
            
        Returns:
            Tuple of (command, args) if matched, None otherwise
            command: The slash command to execute
            args: Optional arguments extracted from the text
        """
        text = text.strip()
        
        # Quick check: if it already starts with /, don't parse
        if text.startswith('/'):
            return None
        
        # Try to match against patterns
        for pattern, command, extractor in self.compiled_patterns:
            match = pattern.search(text)
            if match:
                # Extract arguments if extractor is provided
                args = None
                if extractor:
                    try:
                        args = extractor(match)
                    except (IndexError, AttributeError):
                        pass
                
                return (command, args)
        
        return None
    
    def get_suggestions(self, text: str) -> List[str]:
        """
        Get command suggestions based on partial input.
        
        Args:
            text: Partial user input
            
        Returns:
            List of suggested natural language phrases
        """
        text_lower = text.lower().strip()
        
        # Common phrase starters
        suggestions = []
        
        if text_lower.startswith('show') or text_lower.startswith('what'):
            suggestions.extend([
                "show me what changed",
                "show the current state",
                "show the workflow status",
                "show memory",
                "what's happening"
            ])
        
        elif text_lower.startswith('run') or text_lower.startswith('test'):
            suggestions.extend([
                "run the tests",
                "test the code"
            ])
        
        elif text_lower.startswith('commit') or text_lower.startswith('save'):
            suggestions.extend([
                "commit the changes",
                "save the changes"
            ])
        
        elif text_lower.startswith('undo') or text_lower.startswith('revert'):
            suggestions.extend([
                "undo that",
                "undo last",
                "show undo history"
            ])
        
        elif text_lower.startswith('clear') or text_lower.startswith('reset'):
            suggestions.extend([
                "clear history",
                "start over"
            ])
        
        return suggestions[:5]  # Return top 5


# Singleton instance
_parser = None


def get_parser() -> NaturalLanguageParser:
    """Get the global parser instance."""
    global _parser
    if _parser is None:
        _parser = NaturalLanguageParser()
    return _parser
