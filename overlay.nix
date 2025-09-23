final: prev: {
  inherit (import ./nix { pkgs = prev; }) openconnect-sso;
}
