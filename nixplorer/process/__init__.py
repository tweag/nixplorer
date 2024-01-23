import shutil
from typing import Protocol
import backoff
import subprocess

import psutil


class ManagedSubProcess(Protocol):
    """
    A subprocess intended to be managed and consumed by the current application.

    The process is launched in the background to allow the current process to
    interact with it.
    """

    cmd: str
    """The command used to launch the subprocess"""
    working_dir: str
    """The working directory in which to launch the subprocess"""
    process: subprocess.Popen | None = None
    """The handle to the subprocess"""

    def is_ready(self) -> bool:
        """Checks that the managed subprocess is ready to be used"""
        ...

    def cmd_exists(self) -> bool:
        """Checks whether this subprocess' command can be found"""
        if shutil.which(self.cmd) is not None:
            return True
        else:
            return False

    def open(self) -> None:
        """Opens the subprocess"""
        if not self.cmd_exists():
            raise Exception(
                f"The specified command {self.cmd} could not be found in the current environment. "
                "Make sure that you have it installed and on the PATH."
            )
        if self.process:
            return
        self.process = subprocess.Popen(
            self.cmd,
            # Note: As of writing this the janusgraph Nix derivation does not accept an argument for
            # overriding the Janugraph config directory, etc. instead assuming that all conf is in the
            # default location of $PWD/conf. Setting the subprocess working directory as a work-around
            # since I'm feeling lazy ;).
            cwd=self.working_dir,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def is_open(self) -> bool:
        return self.process is not None

    def close(self) -> None:
        """
        Closes the subprocess

        If the subprocess is not already open this is a no-op.
        """
        if self.process:
            for child in psutil.Process(self.process.pid).children(recursive=True):
                child.kill()
            self.process.kill()
            self.process.wait(timeout=30)

    @backoff.on_predicate(backoff.expo, lambda is_ready: not is_ready, max_tries=10)
    def wait_until_ready(self) -> bool:
        """Waits until the managed subprocess is ready"""
        return self.is_ready()

    def __enter__(self):
        self.open()
        self.wait_until_ready()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
