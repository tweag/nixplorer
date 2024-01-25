"""
Utilities for ingesting data into the nixplorer back-end.
"""

from gremlin_python.process.graph_traversal import GraphTraversal, GraphTraversalSource
from nixtract.model import Derivation

GremlinPropertyType = int | str


class VertexLabels:
    DERIVATION = "derivation"


class EdgeLabels:
    BUILD_INPUT = "has_build_input"


def append_property(name: str, value: GremlinPropertyType | None, traversal: GraphTraversal) -> GraphTraversal:
    if value is None:
        return traversal
    return traversal.property(name, value)


def insert_derivation_vertex(derivation: Derivation, traversal_base: GraphTraversal) -> GraphTraversal:
    """
    Constructs a graph traversal which creates a vertex corresponding to
    a derivation along with vertex properties.
    """
    properties = {
        "output_path": derivation.output_path,
        "name": derivation.name,
    }
    if derivation.nixpkgs_metadata:
        properties |= {
            "pname": derivation.nixpkgs_metadata.pname,
            "description": derivation.nixpkgs_metadata.description,
            "license": derivation.nixpkgs_metadata.license,
            "version": derivation.nixpkgs_metadata.version,
        }
    traversal = traversal_base.add_v(VertexLabels.DERIVATION)
    for name, value in properties.items():
        traversal = append_property(name, value, traversal)
    return traversal


def insert_build_input_edge(
    derivation_output_path: str,
    build_input_output_path: str,
    traversal_base: GraphTraversal,
) -> GraphTraversal:
    """Constructs a traversal which draws an edge from a given derivation to its build input"""
    return (
        traversal_base.V()
        .has_label(VertexLabels.DERIVATION)
        .has("output_path", derivation_output_path)
        .as_("a")
        .V()
        .has_label(VertexLabels.DERIVATION)
        .has("output_path", build_input_output_path)
        .add_e("has_build_input")
        .from_("a")
    )


def load_graph(derivations: list[Derivation], g: GraphTraversalSource) -> None:
    """
    Traverses the provided list of derivations, inserting corresponding
    entities into the provided Gremlin graph.
    """
    # TODO: It might make sense to do a bit of batching here to improve performance,
    # only calling iterate after N derivations have been processed.
    for drv in derivations:
        # Ignore derivations which do not have an output path since we require this property
        if drv.output_path is None:
            continue
        insert_derivation_vertex(drv, g.get_graph_traversal()).iterate()

    # Then in our second pass we draw edges between vertices. This assumes that all vertices involved
    # in the edges were created in our first pass, otherwise the edge will not be created.
    for drv in derivations:
        # Ignore derivations which do not have an output path since we require this property
        if drv.output_path is None:
            continue
        for bi in drv.build_inputs:
            # Ignore derivations which do not have an output path since we require this property
            if bi.output_path is None:
                continue
            insert_build_input_edge(drv.output_path, bi.output_path, g.get_graph_traversal()).iterate()
