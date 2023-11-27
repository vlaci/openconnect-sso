{
  inputs = {
    flake-utils.url = "github:numtide/flake-utils";

    poetry2nix = {
      url = "github:nix-community/poetry2nix";
      inputs.flake-utils.follows = "flake-utils";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, ... }@inputs: (inputs.flake-utils.lib.eachDefaultSystem (
    system:
    let
      pkgs = nixpkgs.legacyPackages.${system};
      poetry2nix = inputs.poetry2nix.lib.mkPoetry2Nix { inherit pkgs; };

      openconnect-pkgs = import ./nix {
        inherit pkgs poetry2nix;
        sources = null; # make sure we don't mix flakes and Niv
      };
    in
    {
      packages = rec {
        inherit (openconnect-pkgs) openconnect-sso;

        default = openconnect-sso;
      };

      devShells.default = openconnect-pkgs.shell;
    }
  ) // {
      overlays = rec {
        default = openconnect-sso;

        openconnect-sso = import ./overlay.nix;
      };
  });
}
