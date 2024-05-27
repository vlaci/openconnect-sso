{
  inputs = {
    flake-utils.url = "github:numtide/flake-utils";
    poetry2nix = {
      url = "github:nix-community/poetry2nix/2024.5.939250";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.flake-utils.follows = "flake-utils";
    };
  };

  outputs = { self, flake-utils, nixpkgs, ... }@inputs: (flake-utils.lib.eachDefaultSystem (
    system:
    let
      pkgs = import nixpkgs {
        inherit system;
        config.packageOverrides = _: {
          poetry2nix = inputs.poetry2nix.lib.mkPoetry2Nix { inherit pkgs; };
        };
      };
      openconnect-sso = (import ./nix { inherit pkgs; }).openconnect-sso;
    in
    {
      packages = { inherit openconnect-sso; };
      defaultPackage = openconnect-sso;
    }
  ) // {
      overlay = import ./overlay.nix;
  });
}
