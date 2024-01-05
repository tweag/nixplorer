/*
 Janusgraph database intialization script for nixplorer.

 This script is intended to be run when Janusgraph is started and is used
 for doing usual database things like defining out data model, indices, etc.
*/

// #####################################################
// # Initialization
// #####################################################
def globals = [:]

// defines a sample LifeCycleHook that prints some output to the Gremlin Server console.
// note that the name of the key in the "global" map is unimportant.
globals << [hook : [
        onStartUp: { ctx ->
            ctx.logger.warn("Executed once at startup of Gremlin Server.")
        },
        onShutDown: { ctx ->
            ctx.logger.warn("Executed once at shutdown of Gremlin Server.")
        }
] as LifeCycleHook]

// #####################################################
// # Schema / Graph management
// #####################################################

mgmt = graph.openManagement()

// Define labels
derivationLabel = mgmt.makeVertexLabel('derivation').make()

hasBuildInputLabel = mgmt.makeEdgeLabel('has_build_input').make()


// Define properties we know will exist
outputPath = mgmt.makePropertyKey('output_path').dataType(String.class).make()
name = mgmt.makePropertyKey('name').dataType(String.class).make()
description = mgmt.makePropertyKey('description').dataType(String.class).make()
pname = mgmt.makePropertyKey('pname').dataType(String.class).make()
license = mgmt.makePropertyKey('license').dataType(String.class).make()
version = mgmt.makePropertyKey('version').dataType(String.class).make()

// Create indices
// Note that individual vertex-centric property indices are automatically created by Janusgraph,
// so we only need to define ones we want in addition to those here.
// Docs: https://docs.janusgraph.org/schema/index-management/index-performance/#property-indexes
mgmt.buildIndex('outputPathPrimaryKey', Vertex.class).addKey(outputPath).unique().buildCompositeIndex()


mgmt.commit()

// #####################################################
// # Exports
// #####################################################
// Finaly, define the default TraversalSource to bind queries to - this one will be named "g".
globals << [g: graph.traversal()]
