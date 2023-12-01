{ sources ? import ./sources.nix
, pkgs ? import <nixpkgs> { }
, poetry2nix ? import sources.poetry2nix { inherit pkgs; }
}:

let
  inherit (pkgs) python3Packages qt6Packages;

  openconnect-sso = qt6Packages.callPackage ./openconnect-sso.nix { inherit poetry2nix; };

  shell = pkgs.mkShell {
    buildInputs = with pkgs; [
      # For Makefile
      gawk
      git
      gnumake
      which
      niv # Dependency manager for Nix expressions
      nixpkgs-fmt # To format Nix source files
      poetry # Dependency manager for Python
    ] ++ (
      with python3Packages; [
        pre-commit # To check coding style during commit
      ]
    ) ++ (
      # only install those dependencies in the shell env which are meant to be
      # visible in the environment after installation of the actual package.
      # Specifying `inputsFrom = [ openconnect-sso ]` introduces weird errors as
      # it brings transitive dependencies into scope.
      openconnect-sso.propagatedBuildInputs
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

    nativeBuildInputs = [
      qt6Packages.wrapQtAppsHook
    ];

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
