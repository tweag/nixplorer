from importlib import resources

import requests
from requests.exceptions import ConnectionError

from nixplorer import janusgraph
from nixplorer.process import ManagedSubProcess

JANUSGRAPH_DIR = str(resources.files(janusgraph))
"""The Janusgraph home directory containing all Janusgraph configuration"""


class Janusgraph(ManagedSubProcess):
    """A managed subprocess for running Janusgraph"""

    host: str = "0.0.0.0"
    port: int = 8182

    def __init__(
        self,
        cmd: str = "janusgraph-server",
        working_dir: str = JANUSGRAPH_DIR,
    ):
        self.cmd = cmd
        self.working_dir = working_dir

    def is_ready(self) -> bool:
        try:
            requests.get(f"http://{self.host}:{self.port}")
            return True
        except ConnectionError:
            return False
