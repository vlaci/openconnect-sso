{ pkgs ? import <nixpkgs> {} }:

let
  poetry2nixOverlay = import "${builtins.fetchTarball {
    url = https://github.com/nix-community/poetry2nix/archive/1.3.0.tar.gz;
    sha256 = "035w0nz20v7ah5l2gvdn6nr6wp28y3ljx7j9vlh83mgf2wjimgv7";
  }}/overlay.nix";
  pkgs' = pkgs.extend poetry2nixOverlay;

  callPackage = pkgs'.libsForQt512.callPackage;
  pythonPackages = pkgs'.python3Packages;

  openconnect-sso = callPackage ./openconnect-sso.nix { inherit (pkgs') python3Packages; };

  shell = pkgs'.mkShell {
    inputsFrom = [ openconnect-sso ];
    buildInputs = with pkgs'; [
      nixpkgs-fmt
      pandoc
      poetry
      reno
    ];
    shellHook = ''
      PATH=$PATH:${./scripts}

      eval $(${./scripts/devenv} activate)
      echo  # spacing
      echo "Enter \`devenv help\` to display available commands"
    '';
  };
in
{
  inherit openconnect-sso shell;
}
