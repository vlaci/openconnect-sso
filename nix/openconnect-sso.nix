{ lib
, stdenv
, openconnect
, python3
, python3Packages
, poetry2nix
, qt6Packages
, wrapQtAppsHook
}:

# Nixpkgs' qutebrowser derivation is a good reference to check if something breaks

poetry2nix.mkPoetryApplication {
  projectDir = ../.;
  python = python3;

  # Skip dev-dependencies (doesn't seem to work, but doesn't hurt)
  groups = [ ];
  checkGroups = [ ];

  buildInputs = [
    python3Packages.setuptools
  ];

  nativeBuildInputs = [
    wrapQtAppsHook
  ];

  propagatedBuildInputs = [
    openconnect
  ] ++ lib.optional (stdenv.isLinux) qt6Packages.qtwayland;

  dontWrapQtApps = true;
  preFixup = ''
    makeWrapperArgs+=(
      # Force the app to use QT_PLUGIN_PATH values from wrapper
      --unset QT_PLUGIN_PATH
      "''${qtWrapperArgs[@]}"
      # avoid persistant warning on starup
      --set QT_STYLE_OVERRIDE Fusion
    )
  '';

  # preferWheels = true;

  overrides = [
    poetry2nix.defaultPoetryOverrides
    (
      self: super: {
        inherit (python3Packages)
          cryptography
          more-itertools
          pyqt6
          pyqt6-sip
          pyqt6-webengine
          pysocks
          requests
          six;

        coverage-enable-subprocess = super.coverage-enable-subprocess.overridePythonAttrs (old: {
          propagatedBuildInputs = (old.propagatedBuildInputs or [ ]) ++ [ self.setuptools ];
        });
      }
    )
  ];
}
