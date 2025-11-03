from pathlib import Path
from typing import Dict
import subprocess

class FeatureDemo:
    def __init__(self, project_dir: Path):
        """
        Initialize the FeatureDemo with the project directory.

        Args:
            project_dir (Path): The directory of the project.
        """
        self.project_dir = project_dir

    def analyze_files(self) -> Dict[str, int]:
        """
        Analyze the project directory to count Python files.

        Returns:
            Dict[str, int]: A dictionary with the count of Python files.
        """
        py_files_count = len(list(self.project_dir.rglob('*.py')))
        return {'python_files': py_files_count}

    def get_git_info(self) -> Dict[str, str]:
        """
        Get the latest git commit information.

        Returns:
            Dict[str, str]: A dictionary with the latest git commit information.
        """
        try:
            result = subprocess.run(
                ['git', 'log', '-5', '--oneline'],
                cwd=self.project_dir,
                text=True,
                capture_output=True,
                check=True
            )
            return {'git_log': result.stdout.strip()}
        except subprocess.CalledProcessError as e:
            return {'error': str(e)}

    def generate_summary(self) -> str:
        """
        Generate a summary of the analysis and git information.

        Returns:
            str: A formatted string combining the analysis and git information.
        """
        analysis = self.analyze_files()
        git_info = self.get_git_info()
        summary = f"Python Files: {analysis['python_files']}\nGit Info:\n{git_info.get('git_log', 'No git info available')}"
        return summary

def main():
    """
    Main function to create a FeatureDemo instance and print the summary.
    """
    demo = FeatureDemo(Path.cwd())
    print(demo.generate_summary())

if __name__ == "__main__":
    main()
