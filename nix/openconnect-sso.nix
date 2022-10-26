{ lib
, openconnect
, python3
, python3Packages
, poetry2nix
, substituteAll
, wrapQtAppsHook
}:

poetry2nix.mkPoetryApplication {
  src = lib.cleanSource ../.;
  pyproject = ../pyproject.toml;
  poetrylock = ../poetry.lock;
  python = python3;
  buildInputs = [ wrapQtAppsHook ];
  propagatedBuildInputs = [ openconnect ];

  dontWrapQtApps = true;
  makeWrapperArgs = [
    "\${qtWrapperArgs[@]}"
  ];

  preferWheels = true;

  overrides = [
    poetry2nix.defaultPoetryOverrides
    (
      self: super: {
        inherit (python3Packages) cryptography pyqt6 pyqt6-sip pyqt6-webengine six more-itertools;
      }
    )
  ];
}
