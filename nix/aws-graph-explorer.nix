{
  stdenv,
  writeScriptBin,
  mkPnpmPackage,
  fetchFromGitHub,
  http-server,
}: let
  site = mkPnpmPackage {
    pname = "graph-explorer";
    version = "1.4.0";

    src = fetchFromGitHub {
      owner = "aws";
      repo = "graph-explorer";
      rev = "v1.4.0";
      hash = "sha256-lRysGEyWLaOefpy50as9/6+y1ok45icDro3oT5DUfa0=";
    };

    installInPlace = true;
    distDir = "packages/graph-explorer/dist";
  };
in
  writeScriptBin "launch-graph-explorer"
  ''
    ${http-server}/bin/http-server ${site} $@
  ''
