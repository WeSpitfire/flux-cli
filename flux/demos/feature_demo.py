class FluxDemo:
    """
    A demonstration class for showcasing Flux's capabilities.

    Attributes:
        name (str): The name of the Flux demo.
        version (str): The version of the Flux demo.
    """

    def __init__(self, name: str, version: str):
        """
        Initialize the FluxDemo with a name and version.

        Args:
            name (str): The name of the Flux demo.
            version (str): The version of the Flux demo.
        """
        self.name = name
        self.version = version

    def display_info(self):
        """
        Display the information about the FluxDemo instance.

        Prints the name and version of the demo.
        """
        print(f"Flux Demo: {self.name}, Version: {self.version}")

    def update_version(self, new_version: str):
        """
        Update the version of the FluxDemo instance.

        Args:
            new_version (str): The new version to update to.

        Prints the updated version.
        """
        self.version = new_version
        print(f"Version updated to {self.version}")

    def git_commit(self, message: str):
        """
        Simulate a git commit operation.

        Args:
            message (str): The commit message.

        Prints the commit message.
        """
        print(f"Committing changes with message: '{message}'")

    def git_status(self):
        """
        Simulate checking the git status.

        Prints the current branch and status of the working tree.
        """
        print("Checking git status...\nOn branch main\nnothing to commit, working tree clean")
