{
  description = "A tool for visualizing and exploring Nix dependency graphs produced by nixtract.";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    pnpm2nix = {
      url = "github:nzbr/pnpm2nix-nzbr";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    poetry2nix = {
      url = "github:nix-community/poetry2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = {
    self,
    nixpkgs,
    flake-utils,
    pnpm2nix,
    poetry2nix,
  }: let
    pkgsForSystem = system:
      import nixpkgs {
        overlays = [
          pnpm2nix.overlays.default
        ];
        inherit system;
      };
  in
    flake-utils.lib.eachDefaultSystem (system: let
      pkgs = pkgsForSystem system;
      inherit (poetry2nix.lib.mkPoetry2Nix {inherit pkgs;}) mkPoetryApplication;
    in rec {
      packages = import ./nix {inherit pkgs mkPoetryApplication;};

      devShells.default = pkgs.mkShell {
        packages = with pkgs; [janusgraph alejandra zlib poetry packages.graph-explorer];
      };
    });
}
