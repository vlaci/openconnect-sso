{
  inputs = {
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, flake-utils, nixpkgs }: (flake-utils.lib.eachDefaultSystem (
    system:
    let
      pkgs = nixpkgs.legacyPackages.${system};
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
