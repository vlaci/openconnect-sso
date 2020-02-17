self: super: {
  inherit (super.callPackage ./lib.nix { pkgs = self; }) openconnect-sso;
}
