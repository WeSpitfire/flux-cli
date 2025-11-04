import os


def scan_for_code_files(directory, extensions=None):
    """
    Scans the given directory for code files with specified extensions.

    :param directory: Directory to scan for code files.
    :param extensions: List of file extensions to look for (e.g., ['.py', '.js']).
                       If None, defaults to common code file extensions.
    :return: List of paths to code files found in the directory.
    """
    if extensions is None:
        extensions = ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.cs', '.rb', '.go', '.rs']

    code_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                code_files.append(os.path.join(root, file))

    return code_files

def count_lines_of_code(file_path):
    """
    Counts the number of lines of code in a given file, excluding empty lines and comments.

    :param file_path: Path to the file to analyze.
    :return: Number of lines of code.
    """
    with open(file_path, 'r') as file:
        lines = file.readlines()

    code_lines = 0
    for line in lines:
        stripped_line = line.strip()
        if stripped_line and not stripped_line.startswith('#'):
            code_lines += 1

    return code_lines

