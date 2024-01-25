{
  pkgs,
  mkPoetryApplication,
}: rec {
  graph-explorer = pkgs.callPackage ./aws-graph-explorer.nix {http-server = pkgs.nodePackages.http-server;};
  nixplorer = pkgs.callPackage ./nixplorer.nix {inherit mkPoetryApplication graph-explorer;};
  default = nixplorer;
}
