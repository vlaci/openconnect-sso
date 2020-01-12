# openconnect-sso

Wrapper script for OpenConnect supporting Azure AD (SAMLv2) authentication
to Cisco SSL-VPNs

## TL; DR

### Using pip

This will install `openconect-sso` along with its dependencies including Qt:
```bash
$ pip install "openconnect-sso[full]"
$ openconnect-sso --server vpn.server.com/group
```

If have Qt 5.x installed, you can skip the installation of bundled Qt version:

``` bash
$ pip install openconnect-sso
```

### Using nix:

The easiest method to try is by installing directly:

``` bash
$ nix-env -f https://github.com/vlaci/openconnect-sso/archive/master.tar.gz -i
```

An overlay is also available to use in nix expressions:

``` nix
let
  openconnectOverlay = import "${builtins.fetchTarball https://github.com/vlaci/openconnect-sso/archive/master.tar.gz}/overlay.nix";
  pkgs = import <nixpkgs> { overlays = [ openconnectOverlay ]; };
in
  #  pkgs.openconnect-sso is available in this context
```


... or to use in `configuration.nix`:

``` nix
{ config, ... }:

{
  nixpkgs.overlays = [
    (import "${builtins.fetchTarball https://github.com/vlaci/openconnect-sso/archive/master.tar.gz}/overlay.nix")
  ];
}
```

## Configuration

If you want to save credentials and get them automatically
injected in the web browser:

```bash
$ openconnect-sso --server vpn.server.com/group --user user@domain.com
Password (user@domain.com):
[info     ] Authenticating to VPN endpoint ...
```

User credentials are automatically saved to the users login keyring (if available).

If you already have Cisco AnyConnect set-up, then `--server` argument is optional.
Also, the last used `--server` address is saved between sessions so there is no need
to always type in the same arguments:

```bash
$ openconnect-sso
[info     ] Authenticating to VPN endpoint ...
```

Configuration is saved in `$XDG_CONFIG_HOME/openconnect-sso/config.toml`. On typical
Linux installations it is located under `$HOME/.config/openconnect-sso/config.toml`

## Development

`openconnect-sso` is developed using [Nix](https://nixos.org/nix/). Refer to the [Quick Start section of
the Nix manual](https://nixos.org/nix/manual/#chap-quick-start) to see how to
get it installed on your machine.

To get dropped into a development environment, just type `nix-shell`:

``` bash
$ nix-shell
Sourcing python-catch-conflicts-hook.sh
Sourcing python-remove-bin-bytecode-hook.sh
Sourcing pip-build-hook
Using pipBuildPhase
Sourcing pip-install-hook
Using pipInstallPhase
Sourcing python-imports-check-hook.sh
Using pythonImportsCheckPhase

[nix-shell]$ 
```


To try an installed version of the package, issue `nix-build`:

``` bash
$ nix-build

$ result/bin/openconnect-sso --help
```

Alternatively you may just [get Poetry](https://python-poetry.org/docs/) and
start developing using the `scripts/devenv` helper script.
