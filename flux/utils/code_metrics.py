import ast
from pathlib import Path
from typing import Dict, Any, List
import os

def count_lines_of_code(file_path):
    """
    Count the total lines of code in a Python file, excluding comments and blank lines.

    :param file_path: Path to the Python file.
    :return: Total lines of code.
    """
    with open(file_path, 'r') as file:
        lines = file.readlines()

    code_lines = 0
    for line in lines:
        stripped_line = line.strip()
        if stripped_line and not stripped_line.startswith('#'):
            code_lines += 1

    return code_lines

def analyze_file(file_path: Path) -> Dict[str, Any]:
    """
    Analyze a Python file to extract various metrics using the AST module.

    :param file_path: Path to the Python file.
    :return: A dictionary containing metrics about the file.
    """
    with open(file_path, 'r') as file:
        file_content = file.read()

    tree = ast.parse(file_content)

    metrics = {
        'total_lines': count_lines_of_code(file_path),
        'total_functions': sum(isinstance(node, ast.FunctionDef) for node in ast.walk(tree)),
        'total_classes': sum(isinstance(node, ast.ClassDef) for node in ast.walk(tree)),
    }

    return metrics

def analyze_directory(directory: Path, extensions: List[str] = ['.py']) -> Dict[str, Dict]:
    """
    Recursively scan a directory for Python files and analyze each file.

    :param directory: Path to the directory to scan.
    :param extensions: List of file extensions to include in the analysis.
    :return: A dictionary with file paths as keys and their analysis metrics as values.
    """
    results = {}
    for root, _, files in os.walk(directory):
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                file_path = Path(root) / file
                results[str(file_path)] = analyze_file(file_path)

    return results
