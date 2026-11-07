import platform
import subprocess
from subprocess import CalledProcessError
from threading import Event

from pdfaccessguru.exceptions.verapdf_exceptions.oscli_exceptions.cli_execution_failed_exception import CliExecutionFailedException


class PlatformPrompt:
    """
    This class provides a unified interface for executing command-line 
    commands across different operating systems. It abstracts away the differences 
    in how commands are executed on Windows, Linux, and macOS, allowing the rest of 
    the codebase to execute CLI commands without worrying about OS-specific details.
    """

    def __init__(self):
        self.os_type = platform.system()

    def execute(
        self, command: list[str], cancel_event: Event | None = None, env: dict[str, str] | None = None
    ) -> str | None:
        """
        Executes the given command and returns its output.

        In particular decides the use of shell=True for Windows and 
        shell=False for Linux and macOS.

        Arguments:
            command: A list of strings representing the command and 
                its arguments (splitted at spaces), 
                e.g. ["verapdf", "--flavour", "ua1", "--format", "xml", "path/to/pdf"].

        Returns:
            The standard output of the command as a string, 
                maybe empty or None if the command produces no output.

        Raises: 
            OSError: If the operating system is not supported. In particular if 
                the operating system is not Windows, Linux, or macOS.
            CliExecutionFailedException: If the command execution fails 
                (CalledProcessError is raised), i.e. if the command returns a non-zero exit code.
        """

        if self.os_type == "Windows":
            return self._run_command(command, use_shell=True, cancel_event=cancel_event, env=env)
            
        elif self.os_type in ["Linux", "Darwin"]:
            return self._run_command(command, use_shell=False, cancel_event=cancel_event, env=env)
            
        else:
            raise OSError(f"No Support for operating system '{self.os_type}' implemented.")

    def _run_command(
        self,
        command: list[str],
        use_shell: bool,
        cancel_event: Event | None = None,
        env: dict[str, str] | None = None,
    ) -> str | None:
        """
        Internal helper method to run a command with the specified shell usage.

        Raises CliExecutionFailedException if the command execution fails 
        (CalledProcessError is raised), i.e. if the command returns a non-zero exit code.
        """
        try: 
            process = subprocess.Popen(
                command,
                shell=use_shell,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
            )
            while True:
                if cancel_event is not None and cancel_event.is_set():
                    process.terminate()
                    process.wait(timeout=2)
                    raise InterruptedError("Pipeline cancelled")
                try:
                    stdout, _ = process.communicate(timeout=0.1)
                    return stdout.strip()
                except subprocess.TimeoutExpired:
                    continue
            
        except CalledProcessError as e:
            raise CliExecutionFailedException(command, e.stderr.strip()) from e