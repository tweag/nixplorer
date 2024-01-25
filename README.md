# nixplorer

![Build](https://img.shields.io/github/actions/workflow/status/tweag/nixplorer/ci.yml) [![Discord channel](https://img.shields.io/discord/1174731094726295632)](https://discord.gg/53XwX7Ft)

A tool for visualizing Nix dependency graphs produced by [`nixtract`](https://www.github.com/tweag/nixtract).

> This tool is still in a prototype stage and is subject to bugs and major changes. Please report any issues you encounter :smile:.

## Installation / Dependencies

This project is packaged with Nix. You will need Nix installed and the Nix flakes
feature enabled to run `nixplorer`. One good option for doing this is the Nix installer
available here: https://github.com/DeterminateSystems/nix-installer.

## Usage

### 1. Generate a dependency graph with nixtract

First, install and run nixtract for the target of choice. This can generally be
done either via pip or Nix.

With pip:

```sh
# Assumes that you already have Python installed
pip install nixtract
nixtract --target-attribute-path python3Packages.jedi example-graph.jsonl
```

Or via the Nix flake:

```sh
nix run github:tweag/nixtract -- --target-attribute-path python3Packages.jedi example-graph.jsonl
```

### 2. Run nixplorer

Once you have an input graph JSONL file you are ready to run nixplorer. You can
do so using the project's Nix flake. For example:

```sh
nix run .#nixplorer -- --graph ./example-graph.jsonl
```

nixplorer will prepare the graph and launch its front-end in a browser window. You can also
navigate to the application in the browser yourself at http://0.0.0.0:8080.

#### 2.1 Configure the UI

The first time you load the ui, you will need to configure a connection for the nixplorer back-end
which is running at http://0.0.0.0:8182.

![connection-ui](./docs/add-connection.png)

### UI features

We currently leverage AWS's graph-explorer for the nixplorer UI. Some key
features include:

- Searching for derivations by attributes (e.g. name, license)
- Viewing data in a table
- Plotting stylable subgraphs and exporting static images

You can find
further documentation on how to use graph-explorer at it's homepage here:
https://github.com/aws/graph-explorer.

## Development

### Set-up

This project is implemented in Python along with some Nix packaging for
applications we leverage under the hood such as AWS's Graph Explorer.

The project is packaged using a combination of Nix and Poetry. You can
use the project's Nix shell to get an environment which includes both
Poetry and the binaries we depend on such as Janusgraph and Graph Explorer.

The only system requirement is Nix with the flakes feature enabled.

```sh
nix develop
```

Once in the shell you can use Poetry as usual for local development:

```
# Install dependencies
poetry install

# Enter a Poetry shell
poetry shell
```

We leverage `alejandra` for formatting Nix code (provided by the Nix shell) and a
combination of `black`, `ruff`, and `pyright` for formatting and linting Python code
(provided by Poetry).

### Architecture

![architecture](docs/architecture.drawio.png)
