final: prev: {
  inherit (prev.callPackage ./nix { pkgs = final; }) openconnect-sso;
}
