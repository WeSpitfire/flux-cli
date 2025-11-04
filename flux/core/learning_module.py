import json
from pathlib import Path
from typing import List, Dict, Any

class LearningModule:
    """Module to store and query successful fixes."""

    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_path.exists():
            self._initialize_storage()

    def _initialize_storage(self):
        """Initialize the storage file."""
        with open(self.storage_path, 'w') as f:
            json.dump([], f)

    def record_fix(self, error_details: Dict[str, Any], fix_details: Dict[str, Any]):
        """Record a successful fix.

        Args:
            error_details: Details of the error that was fixed
            fix_details: Details of the fix applied
        """
        with open(self.storage_path, 'r+') as f:
            data = json.load(f)
            data.append({'error': error_details, 'fix': fix_details})
            f.seek(0)
            json.dump(data, f, indent=4)

    def query_fixes(self, error_signature: str) -> List[Dict[str, Any]]:
        """Query stored fixes for similar issues.

        Args:
            error_signature: A string signature of the error to search for

        Returns:
            List of fixes that match the error signature
        """
        with open(self.storage_path, 'r') as f:
            data = json.load(f)
            return [entry for entry in data if error_signature in entry['error'].get('error_message', '')]
