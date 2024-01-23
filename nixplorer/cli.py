from pathlib import Path
from typing import Tuple
from gremlin_python.process.graph_traversal import GraphTraversalSource
from gremlin_python.process.anonymous_traversal import traversal
from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection
from nixtract.model import Derivation
import time
import click
from halo import Halo

from nixplorer.process.graph import Janusgraph
from nixplorer.process.ui import GraphExplorer


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
