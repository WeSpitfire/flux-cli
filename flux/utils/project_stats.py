from pathlib import Path
from typing import Dict, Any
import subprocess
import os

class ProjectAnalyzer:
    def analyze_codebase(self, directory: Path) -> Dict[str, Any]:
        metrics = {
            'total_files': 0,
            'total_lines': 0,
            'total_functions': 0,
            'total_classes': 0
        }

        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith('.py'):
                    metrics['total_files'] += 1
                    file_path = Path(root) / file
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        metrics['total_lines'] += len(lines)
                        for line in lines:
                            line = line.strip()
                            if line.startswith('def '):
                                metrics['total_functions'] += 1
                            elif line.startswith('class '):
                                metrics['total_classes'] += 1
                                def get_git_stats(self) -> Dict[str, Any]:
                                    stats = {
                                        'total_commits': 0,
                                        'total_branches': 0,
                                        'total_contributors': 0
                                    }

                                    try:
                                        # Get total commits
                                        result = subprocess.run(['git', 'rev-list', '--count', 'HEAD'], capture_output=True, text=True, check=True)
                                        stats['total_commits'] = int(result.stdout.strip())

                                        # Get total branches
                                        result = subprocess.run(['git', 'branch', '--all'], capture_output=True, text=True, check=True)
                                        stats['total_branches'] = len(result.stdout.strip().split('\n'))

                                        # Get total contributors
                                        result = subprocess.run(['git', 'shortlog', '-s', '-n'], capture_output=True, text=True, check=True)
                                        stats['total_contributors'] = len(result.stdout.strip().split('\n'))

                                    except subprocess.CalledProcessError as e:
                                        print(f"An error occurred while fetching git stats: {e}")

                                    return stats


        return metrics
