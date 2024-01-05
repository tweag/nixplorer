from pathlib import Path
import subprocess
from typing import Tuple
from gremlin_python.process.graph_traversal import GraphTraversalSource
import requests
import backoff
import shutil
from gremlin_python.process.anonymous_traversal import traversal
from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection
from requests.exceptions import ConnectionError
from nixtract.model import Derivation
import subprocess
import time
import psutil
import click
import webbrowser
from halo import Halo
from importlib import resources
from nixplorer import janusgraph

janusgraph_dir = resources.files(janusgraph)


# TODO: Refactor this to make it a bit more re-usable (will be shared with front-end)
class GraphProcess:
    def __init__(self, cmd: str = "janusgraph-server", host="0.0.0.0", port=8182):
        self.cmd = cmd
        self.host = host
        self.port = port
        self._proc: subprocess.Popen | None = None

    def cmd_exists(self) -> bool:
        if shutil.which(self.cmd) is not None:
            return True
        else:
            return False

    def open(self) -> None:
        if not self.cmd_exists():
            raise Exception(
                f"The specified command {self.cmd} could not be found in the current environment. "
                "Make sure that you have it installed and on the PATH."
            )
        if self._proc:
            return
        self._proc = subprocess.Popen(
            self.cmd,
            # Note: As of writing this the janusgraph Nix derivation does not accept an argument for
            # overriding the Janugraph config directory, etc. instead assuming that all conf is in the
            # default location of $PWD/conf. Setting the subprocess working directory as a work-around
            # since I'm feeling lazy ;).
            cwd=str(janusgraph_dir),
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def close(self) -> None:
        if self._proc:
            for child in psutil.Process(self._proc.pid).children(recursive=True):
                child.kill()
            self._proc.kill()
            self._proc.wait(timeout=30)

    def __enter__(self):
        self.open()
        self.wait_until_ready()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    @backoff.on_predicate(backoff.expo, lambda is_ready: not is_ready, max_tries=10)
    def wait_until_ready(self) -> bool:
        return self.is_ready()

    def is_ready(self) -> bool:
        try:
            requests.get(f"http://{self.host}:{self.port}")
            return True
        except ConnectionError:
            return False


class UIProcess:
    def __init__(self, cmd: str = "launch-graph-explorer"):
        self.cmd = cmd
        self.host = "0.0.0.0"
        self.port = "8080"
        # TODO: Make port configurable
        self._proc: subprocess.Popen | None = None

    def cmd_exists(self) -> bool:
        if shutil.which(self.cmd) is not None:
            return True
        else:
            return False

    def open(self) -> None:
        if not self.cmd_exists():
            raise Exception(
                f"The specified command {self.cmd} could not be found in the current environment. "
                "Make sure that you have it installed and on the PATH."
            )
        if self._proc:
            return
        self._proc = subprocess.Popen(
            self.cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

    def close(self) -> None:
        if self._proc:
            for child in psutil.Process(self._proc.pid).children(recursive=True):
                child.kill()
            self._proc.kill()
            self._proc.wait(timeout=30)

    def __enter__(self):
        self.open()
        self.wait_until_ready()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    @backoff.on_predicate(backoff.expo, lambda is_ready: not is_ready, max_tries=10)
    def wait_until_ready(self) -> bool:
        return self.is_ready()

    def is_ready(self) -> bool:
        try:
            requests.get(f"http://{self.host}:{self.port}")
            return True
        except ConnectionError:
            return False

    def launch_browser(self) -> None:
        if not self._proc:
            return
        is_ready = self.wait_until_ready()
        if not is_ready:
            return
        browser = webbrowser.get()
        browser.open_new(f"http://{self.host}:{self.port}")


def load_graph(derivations: list[Derivation], g: GraphTraversalSource) -> None:
    # TODO: It might make sense to do a bit of batching here to improve performance,
    # only calling iterate after N derivations have been processed.
    for drv in derivations:
        if drv.output_path is None:
            continue
        t = (
            g.add_v("derivation")
            .property("output_path", drv.output_path)
            .property("name", drv.name)
        )
        if drv.nixpkgs_metadata:
            if drv.nixpkgs_metadata.pname is not None:
                t = t.property("pname", drv.nixpkgs_metadata.pname)
            if drv.nixpkgs_metadata.description is not None:
                t = t.property("description", drv.nixpkgs_metadata.description)
            if drv.nixpkgs_metadata.license is not None:
                t = t.property("license", drv.nixpkgs_metadata.license)
            if drv.nixpkgs_metadata.version is not None:
                t = t.property("version", drv.nixpkgs_metadata.version)
        t.iterate()
    # Then in our second pass we draw edges between vertices. This assumes that all vertices involved
    # in the edges were created in our first pass, otherwise the edge will not be created.
    for drv in derivations:
        for bi in drv.build_inputs:
            if bi.output_path is None:
                continue
            t = (
                g.V()
                .has("output_path", drv.output_path)
                .as_("a")
                .V()
                .has("output_path", bi.output_path)
                .add_e("has_build_input")
                .from_("a")
            )
            # _echo(t.bytecode)
            t.iterate()


def read_graph_jsonl(input_graph: Path) -> Tuple[list[Derivation], list[Exception]]:
    with input_graph.open() as f:
        lines = f.readlines()
    derivations: list[Derivation] = []
    errors: list[Exception] = []
    for l in lines:
        try:
            derivations.append(Derivation.parse_raw(l))
        except Exception as e:
            errors.append(e)
    return (derivations, errors)


def _echo(message: str) -> None:
    # Echo with a bit of indentation for rendering in coordination
    # with halo spinners.
    click.echo(6 * " " + message)


@click.command()
@click.option(
    "--graph", "input_graph_file", required=True, type=click.Path(exists=True)
)
def cli(input_graph_file: str):
    spinner = Halo(text="Reading input graph file", spinner="dots")
    derivations, errors = read_graph_jsonl(Path(input_graph_file))
    spinner.succeed()
    if errors:
        _echo(f"Failed to parse {len(derivations)} objects in input file.")
    _echo(f"Found {len(derivations)} derivations in input!")

    spinner.start("Launching nixplorer back-end")
    with GraphProcess() as graph:
        g = traversal().with_remote(
            DriverRemoteConnection(f"ws://{graph.host}:{graph.port}/gremlin", "g")
        )
        spinner.succeed()
        _echo(f"Gremlin back-end launched at http://{graph.host}:{graph.port}")

        spinner.start("Loading graph to back-end")
        load_graph(derivations, g)
        spinner.succeed()
        _echo("Graph construction complete!")
        _echo(f"N Vertices = {g.V().count().to_list()}")
        _echo(f"N Edges = {g.E().count().to_list()}")

        spinner.start("Launching nixplorer UI")
        with UIProcess() as ui:
            ui.launch_browser()
            spinner.succeed()
            _echo("UI now available at http://0.0.0.0:8080")
            _echo("Use ctrl+C to close nixplorer.")
            while True:
                time.sleep(1)
