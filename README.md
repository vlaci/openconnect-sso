# openconnect-sso
Wrapper script for OpenConnect supporting Azure AD (SAMLv2) authentication
to Cisco SSL-VPNs

## TL; DR
```bash
$ pip install openconnect-sso
$ openconnect-sso --server vpn.server.com/group
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
Linux installations it is located under `$HOME/.configopenconnect-sso/config.toml`
