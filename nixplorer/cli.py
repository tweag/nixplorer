from pathlib import Path
from typing import Tuple
from gremlin_python.process.anonymous_traversal import traversal
from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection
from nixtract.model import Derivation
import time
import click
from halo import Halo
from nixplorer.ingest import load_graph

from nixplorer.process.graph import Janusgraph
from nixplorer.process.ui import GraphExplorer


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
    with Janusgraph() as graph:
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
        with GraphExplorer() as ui:
            ui.launch_browser()
            spinner.succeed()
            _echo("UI now available at http://0.0.0.0:8080")
            _echo("Use ctrl+C to close nixplorer.")
            while True:
                time.sleep(1)
