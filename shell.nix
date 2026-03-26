{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = [
    pkgs.python3
    pkgs.python3Packages.flake8
    pkgs.zsh
    pkgs.uv
    pkgs.ruff
    pkgs.mypy
  ];

  shellHook = ''
    uv sync
    source .venv/bin/activate

    exec zsh
  '';
}
