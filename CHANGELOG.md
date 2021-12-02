# Changelog

## v0.8.0

- Updating dependencies
- Add support for MFA popup dialogs
- Pass cookie in STDIN to hide its value in `ps` output
- Support NixOS 21.11

## v0.7.3

- More failsafe method to reuse existing authentication sessions, so that
  entering password/MFA token may not be needed at all. Persisting HTTP cookies
  were prone to a race condition which is hopefully mitigated by this change.

## v0.7.2

- Update dependencies `keyring` and `importlib-metadata`
  ([pull/52](https://github.com/vlaci/openconnect-sso/pull/52))

## v0.7.1

- Do not fail if keyring is not accessible
  ([issues/45](https://github.com/vlaci/openconnect-sso/issues/45),
  [pull/46](https://github.com/vlaci/openconnect-sso/pull/46))
- Updating dependencies and support `pyxdg 0.27`
  ([pull/49](https://github.com/vlaci/openconnect-sso/pull/49))

## v0.7.0

- It is now possible to reuse previous authentication sessions, so that
  entering password/MFA token may not be needed at all.

## v0.6.3

- Updating `poetry2nix` to fix build on `nixpkgs-unstable`
  ([issues/40](https://github.com/vlaci/openconnect-sso/issues/40),
  [pull/41](https://github.com/vlaci/openconnect-sso/pull/41))
- Relax `structlog`'s version restriction
  ([pull/44](https://github.com/vlaci/openconnect-sso/pull/44))

## v0.6.2

- Updating dependencies to newer versions
- `python-keyring` is updated to 22.0.1 to fix Arch Linux (AUR) packaging

## v0.6.1

- Use "modern" style authentication header
  ([pull/37](https://github.com/vlaci/openconnect-sso/pull/37))

  It is inspired by
  [openconnect/mr/75](https://gitlab.com/openconnect/openconnect/-/merge_requests/75)
  Without this header recent AnyConnect servers will not send the correct
  reply redirecting to the authentication page

## v0.6.0

### New features

- New `--on-disconnect` argument to run shell command when `openconnect` exits
  ([pull/33](https://github.com/vlaci/openconnect-sso/pull/33))

  It is useful for example to restart SSH Control Master connections upon exit.

- Adding `--proxy` argument from OpenConnect
  ([pull/20](https://github.com/vlaci/openconnect-sso/pull/20))

  Authentication honors this argument too

- Experimental Windows support
  ([pull/16](https://github.com/vlaci/openconnect-sso/pull/16))

  `sudo` binary needs to be installed in addition to `openconnect`

### Bug fixes

- Application no longer crashes when the config file is not readable
  ([pull/33](https://github.com/vlaci/openconnect-sso/pull/33))
- Work around issue with password retrieval from `kwallet`
  ([pull/26](https://github.com/vlaci/openconnect-sso/pull/26))

## v0.5.0

### New Features

- Adding `--authgroup` argument from OpenConnect

  Some VPN endpoints require users to post a valid authgroup (in
  OpenConnect lingua) as part of the `group-access` xml node. Up until
  now it was only possilbe to override the authgroup from the
  configuration or from an AnyConnect XML profile.

### Other Notes

- Removed max version constraint from `attrs` and update dependencies.
  It works with a more recent version after the `convert=` deprecation
  issues had been resolved for the previous upgrade.

## v0.4.0

### Prelude

It is now possible to install `openconnect-sso` using a systemwide
installation of `Qt` by declaring dependencies to `PyQt5` and
`PyQtWebEngine` optional.

### New Features

- `--authenticate [json|shell]` command line argument
  Exits after authentication and displays the authentication
  information needed to initiate a connection. When the `shell` output
  format is used the output is formatted the same way as `openconnect`
  formats its output when the same argument is used. When `json`
  format is used, the same information is displayed in json format.

  Kudos to @rschmied for the original pull request.

- `--version/-V` command line argument
  Displays the version of `openconnect-sso`

- `--browser-display-mode [shown|hidden]` command line argument
  If `hidden` is specified the browser login window is not displayed.
  Keep in mind thatin that case there is no way to manually enter
  credentials so make sure that you can login with saved settings
  without interacting with the webpage before selecting this option.

### Upgrade Notes

- Use the `--authenticate` command line argument instead
  of`--auth-only`. The latter argument has been removed from this
  version of `openconnect-sso`.

- As it is now possible to choose between a bundled or preinstalled
  version of Qt, that means that `PyQt5` is no longer a required
  dependency. To keep installing `openconnect-sso` with all its
  dependencies:

      pip install --user --upgrade "openconnect-sso[full]"

  To use the systemwide installation of `PyQt5` and `PyQtWebEngine`
  install them via your distribution's package manager:

      apt install python-pyqt5 python3-pyqt5.qtwebengine

  Then install `openconnect-sso`:

      pip install --user --upgrade openconnect-sso

### Other Notes

- Dependencies updated to newer versions

- The browser window runs its separate process in order to not let
  `PyQt` pollute the root process and make the core able to still use
  `asyncio` without any hassle.

  Unfortunately spawning a separate Python instance is not so trivial
  as it won't inherit all state from the parent process. It makes the
  application harder to integrate in more exotic deployments such as
  in `NixOS`.

  End-users should not observe any changes in behavior.

## v0.3.9

### Bug Fixes

- \#8 Show error returned by VPN endpoint when authentication starts

## v0.3.8

### Bug Fixes

- `--server` command line option only had an effect when
  `openconnect-sso` is started for the first time. Subsequent
  executions always loaded the server setting from the saved
  configuration.

## v0.3.7

### New Features

- Support redirection when e.g. VPN endpoint is behind a load-balancer

## v0.3.6

### Bug Fixes

- Browser window was not shown
- Pasword was logged in debug mode

## v0.3.5

### Bug Fixes

- Add a version constraint to `attrs` package because version `19.2.0`
  removed support for the `convert` constructor argument.

## v0.3.4

### Prelude

It is strongly suggested to remove the `[auto_fill_rules]` section from
the configuration file or delete the entire file located at
`$XDG_CONFIG_HOME/openconnect-sso/config.toml` (most probably
`~/.config/openconnect-sso/config.toml`). The fix of \#4 involves an
update of the auto-fill rules but unfortulately they are persisted when
the application is first started. Removing them from the configuration
forces the updated set of rules to be written in the configuration.

### Bug Fixes

- The embedded browser will now stop and waits for user input when the
  previously stored credentials are invalid. This still not the proper
  solution as saved credentials are not upd# Changelog

## v0.5.0

### New Features

- Adding `--authgroup` argument from OpenConnect

  Some VPN endpoints require users to post a valid authgroup (in
  OpenConnect lingua) as part of the `group-access` xml node. Up until
  now it was only possilbe to override the authgroup from the
  configuration or from an AnyConnect XML profile.

### Other Notes

- Removed max version constraint from `attrs` and update dependencies.
  It works with a more recent version after the `convert=` deprecation
  issues had been resolved for the previous upgrade.

## v0.4.0

### Prelude

It is now possible to install `openconnect-sso` using a systemwide
installation of `Qt` by declaring dependencies to `PyQt5` and
`PyQtWebEngine` optional.

### New Features

- `--authenticate [json|shell]` command line a# Change
