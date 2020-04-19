{ sources ? import ./sources.nix
, pkgs ? import <nixpkgs> {
    overlays = [ (import "${sources.poetry2nix}/overlay.nix") ];
  }
}:

let
  callPackage = pkgs.qt5.callPackage;
  pythonPackages = pkgs.python3Packages;

  openconnect-sso = callPackage ./openconnect-sso.nix { inherit (pkgs) python3Packages; };

  shell = pkgs.mkShell {
    inputsFrom = [ openconnect-sso ];
    buildInputs = with pkgs; [
      # For Makefile
      gawk
      git
      gnumake
      which
      niv # Dependency manager for Nix expressions
      nixpkgs-fmt # To format Nix source files
      pandoc # To convert reno release notes to markdown
      poetry # Dependency manager for Python
      reno # Manage release nots
    ] ++ (
      with pythonPackages; [
        pre-commit # To check coding style during commit
      ]
    );
    shellHook = ''
      # Python wheels are ZIP files which cannot contain timestamps prior to
      # 1980
      export SOURCE_DATE_EPOCH=315532800
      # Helper for tests to find Qt libraries
      export NIX_QTWRAPPER=${qtwrapper}/bin/wrap-qt

      echo "Run 'make help' for available commands"
    '';
  };

  niv = if pkgs ? niv then pkgs.nim else pkgs.haskellPackages.niv;

  qtwrapper = pkgs.stdenv.mkDerivation {
    name = "qtwrapper";
    dontWrapQtApps = true;
    makeWrapperArgs = [
      "\${qtWrapperArgs[@]}"
    ];
    unpackPhase = ":";
    nativeBuildInputs = [ pkgs.qt5.wrapQtAppsHook ];
    installPhase = ''
      mkdir -p $out/bin
      cat > $out/bin/wrap-qt <<'EOF'
      #!/bin/sh
      "$@"
      EOF
      chmod +x $out/bin/wrap-qt
      wrapQtApp $out/bin/wrap-qt
    '';
  };
in
{
  inherit openconnect-sso shell;
}
