self: super: {
  inherit (super.callPackage ./nix { pkgs = self; }) openconnect-sso;
}
