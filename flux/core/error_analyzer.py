import re
from typing import Dict, Any

class ErrorAnalyzer:
    @staticmethod
    def parse_traceback(traceback: str) -> Dict[str, Any]:
        """
        Parse a Python traceback to extract file, line number, and error type.

        :param traceback: The traceback string to parse.
        :return: A dictionary with file, line, and error type.
        """
        # Regular expression to match the traceback lines
        traceback_regex = re.compile(r'File "(.*?)", line (\d+), in (.*?)\n(\w+): (.*)')
        match = traceback_regex.search(traceback)
        if match:
            return {
                'file': match.group(1),
                'line': int(match.group(2)),
                'function': match.group(3),
                'error_type': match.group(4),
                'error_message': match.group(5)
            }
        return {}

    @staticmethod
    def categorize_error(error_type: str) -> str:
        """
        Categorize the error type into broader categories.

        :param error_type: The specific error type.
        :return: A string representing the error category.
        """
        if error_type in ['ImportError', 'ModuleNotFoundError']:
            return 'Import Error'
        elif error_type in ['AttributeError', 'NameError']:
            return 'Attribute/Name Error'
        elif error_type in ['TypeError', 'ValueError']:
            return 'Type/Value Error'
        else:
            return 'Other Error'

    def analyze(self, traceback: str) -> Dict[str, Any]:
        """
        Analyze the traceback to extract and categorize error information.

        :param traceback: The traceback string to analyze.
        :return: A structured dictionary with error details and category.
        """
        error_details = self.parse_traceback(traceback)
        if error_details:
            error_details['category'] = self.categorize_error(error_details['error_type'])
        return error_details
