from typing import Dict, Any
import re

class FixGenerator:
    """Generate code fixes using the Flux LLM."""

    def __init__(self, llm):
        """Initialize with LLM provider.

        Args:
            llm: The Flux LLM provider instance (BaseProvider)
        """
        self.llm = llm

    async def generate_fix(self, error_details: Dict[str, Any], file_content: str) -> Dict[str, Any]:
        """
        Use the Flux LLM to generate a code fix based on error details.

        Args:
            error_details: A dictionary containing error details:
                - file: File path where error occurred
                - line: Line number of error
                - error_type: Type of error (e.g., NameError, AttributeError)
                - error_message: The error message
                - function: Function where error occurred (optional)
            file_content: The content of the file where the error occurred

        Returns:
            Dictionary with fix details:
                - file_path: Path to file
                - line_number: Line where error occurred
                - search: The text to search for in edit_file
                - replace: The replacement text
                - confidence: Confidence score (0.0-1.0)
                - explanation: Human-readable explanation of the fix
        """
        # Extract necessary information from error details
        file_path = error_details.get('file')
        line_number = error_details.get('line', 0)
        error_type = error_details.get('error_type', 'Unknown')
        error_message = error_details.get('error_message', '')
        function_name = error_details.get('function', 'unknown')

        # Build context around the error (lines ±5 from error line)
        lines = file_content.split('\n')
        start_line = max(0, line_number - 6)  # -1 for 0-indexing, then -5
        end_line = min(len(lines), line_number + 5)
        context = '\n'.join(lines[start_line:end_line])

        # Generate a prompt for the LLM
        prompt = f"""Fix this Python error:

Error: {error_type}: {error_message}
File: {file_path}
Line: {line_number}
Function: {function_name}

Code context (lines {start_line+1}-{end_line}):
```python
{context}
```

Generate a fix by:
1. Identifying the exact lines that need to change
2. Providing the search text (exact current code)
3. Providing the replacement text (fixed code)
4. Explaining the fix and confidence (0.0-1.0)

Format your response as:
SEARCH:
[exact code to find]

REPLACE:
[fixed code]

EXPLANATION: [why this fixes it]
CONFIDENCE: [0.0-1.0]
"""

        # Call LLM through send_message
        response_text = ""
        async for event in self.llm.send_message(message=prompt, system_prompt="You are a code fixing expert."):
            if event["type"] == "text":
                response_text += event["content"]

        # Parse the response to extract search/replace/confidence
        search_match = re.search(r'SEARCH:\s*(.+?)(?=REPLACE:|$)', response_text, re.DOTALL)
        replace_match = re.search(r'REPLACE:\s*(.+?)(?=EXPLANATION:|$)', response_text, re.DOTALL)
        explanation_match = re.search(r'EXPLANATION:\s*(.+?)(?=CONFIDENCE:|$)', response_text, re.DOTALL)
        confidence_match = re.search(r'CONFIDENCE:\s*([0-9.]+)', response_text)

        search_text = search_match.group(1).strip() if search_match else ""
        replace_text = replace_match.group(1).strip() if replace_match else ""
        explanation = explanation_match.group(1).strip() if explanation_match else "No explanation provided"

        try:
            confidence = float(confidence_match.group(1)) if confidence_match else 0.5
            confidence = max(0.0, min(1.0, confidence))  # Clamp to [0, 1]
        except (ValueError, AttributeError):
            confidence = 0.5

        return {
            'file_path': file_path,
            'line_number': line_number,
            'search': search_text,
            'replace': replace_text,
            'confidence': confidence,
            'explanation': explanation,
            'error_type': error_type,
            'error_message': error_message
        }
