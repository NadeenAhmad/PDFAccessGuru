

class CliExecutionFailedException(Exception):
    """Raised when the execution of a CLI command fails."""
    def __init__(self, command: list[str], error_output: str):
        self.command = command
        self.error_output = error_output
        super().__init__(f"Failed to execute CLI command: {' '.join(command)}\nError output: {error_output}")
