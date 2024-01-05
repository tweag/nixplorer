{
  stdenv,
  mkPoetryApplication,
  janusgraph,
  graph-explorer,
}:
mkPoetryApplication {
  projectDir = ../.;
  preferWheels = true;
  propagatedBuildInputs = [janusgraph graph-explorer];
}
