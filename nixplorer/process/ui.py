import os
import requests
from requests.exceptions import ConnectionError
from nixplorer.process import ManagedSubProcess
import webbrowser


class GraphExplorer(ManagedSubProcess):
    """Managed subprocess for the AWS Graph Explorer UI"""

    host = "0.0.0.0"
    # TODO: Allow the port to be configurable
    port = "8080"

    def __init__(
        self, cmd: str = "launch-graph-explorer", working_dir: str = os.getcwd()
    ):
        self.cmd = cmd
        self.working_dir = working_dir

    def is_ready(self) -> bool:
        try:
            requests.get(f"http://{self.host}:{self.port}")
            return True
        except ConnectionError:
            return False

    def launch_browser(self) -> None:
        """
        Waits for the UI to be ready for connections then attempts to
        launch it in your default browser.
        """
        if not self.is_open():
            return
        is_ready = self.wait_until_ready()
        if not is_ready:
            return
        browser = webbrowser.get()
        browser.open_new(f"http://{self.host}:{self.port}")
