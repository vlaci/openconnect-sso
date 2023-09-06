import asyncio
import getpass
import json
import logging
import os
import signal
import subprocess
from pathlib import Path

import shlex
import shutil
import structlog
from prompt_toolkit import HTML
from prompt_toolkit.shortcuts import radiolist_dialog

from openconnect_sso import config
from openconnect_sso.authenticator import Authenticator, AuthResponseError
from openconnect_sso.browser import Terminated
from openconnect_sso.config import Credentials
from openconnect_sso.profile import get_profiles

from requests.exceptions import HTTPError

logger = structlog.get_logger()


def run(args):
    configure_logger(logging.getLogger(), args.log_level)

    cfg = config.load()

    try:
        if os.name == "nt":
            asyncio.set_event_loop(asyncio.ProactorEventLoop())
        auth_response, selected_profile = asyncio.get_event_loop().run_until_complete(
            _run(args, cfg)
        )
    except KeyboardInterrupt:
        logger.warn("CTRL-C pressed, exiting")
        return 130
    except ValueError as e:
        msg, retval = e.args
        logger.error(msg)
        return retval
    except Terminated:
        logger.warn("Browser window terminated, exiting")
        return 2
    except AuthResponseError as exc:
        logger.error(
            f'Required attributes not found in response ("{exc}", does this endpoint do SSO?), exiting'
        )
        return 3
    except HTTPError as exc:
        logger.error(f"Request error: {exc}")
        return 4

    config.save(cfg)

    if args.authenticate:
        logger.warn("Exiting after login, as requested")
        details = {
            "host": selected_profile.vpn_url,
            "cookie": auth_response.session_token,
            "fingerprint": auth_response.server_cert_hash,
        }
        if args.authenticate == "json":
            print(json.dumps(details, indent=4))
        elif args.authenticate == "shell":
            print(
                "\n".join(f"{k.upper()}={shlex.quote(v)}" for k, v in details.items())
            )
        return 0

    try:
        return run_openconnect(
            auth_response,
            selected_profile,
            args.proxy,
            args.ac_version,
            args.openconnect_args,
        )
    except KeyboardInterrupt:
        logger.warn("CTRL-C pressed, exiting")
        return 0
    finally:
        handle_disconnect(cfg.on_disconnect)


def configure_logger(logger, level):
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.format_exc_info,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.dev.ConsoleRenderer()
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(level)


async def _run(args, cfg):
    credentials = None
    if cfg.credentials:
        credentials = cfg.credentials
    elif args.user:
        credentials = Credentials(args.user)

    if credentials and not credentials.password and args.passwd:
        credentials._passwd = args.passwd
        cfg.credentials = credentials
    elif credentials and not credentials.password:
        credentials.password = getpass.getpass(prompt=f"Password ({args.user}): ")
        cfg.credentials = credentials

    if credentials and not credentials.totp and args.totp:
        credentials._totp = args.totp
        cfg.credentials = credentials
    elif credentials and not credentials.totp:
        credentials.totp = getpass.getpass(
            prompt=f"TOTP secret (leave blank if not required) ({args.user}): "
        )
        cfg.credentials = credentials

    if cfg.default_profile and not (args.use_profile_selector or args.server):
        selected_profile = cfg.default_profile
    elif args.use_profile_selector or args.profile_path:
        profiles = get_profiles(Path(args.profile_path))
        if not profiles:
            raise ValueError("No profile found", 17)

        selected_profile = await select_profile(profiles)
        if not selected_profile:
            raise ValueError("No profile selected", 18)
    elif args.server:
        selected_profile = config.HostProfile(
            args.server, args.usergroup, args.authgroup
        )
    else:
        raise ValueError(
            "Cannot determine server address. Invalid arguments specified.", 19
        )

    cfg.default_profile = config.HostProfile(
        selected_profile.address, selected_profile.user_group, selected_profile.name
    )

    display_mode = config.DisplayMode[args.browser_display_mode.upper()]

    auth_response = await authenticate_to(
        selected_profile, args.proxy, credentials, display_mode, args.ac_version
    )

    if args.on_disconnect and not cfg.on_disconnect:
        cfg.on_disconnect = args.on_disconnect

    return auth_response, selected_profile


async def select_profile(profile_list):
    selection = await radiolist_dialog(
        title="Select AnyConnect profile",
        text=HTML(
            "The following AnyConnect profiles are detected.\n"
            "The selection will be <b>saved</b> and not asked again unless the <pre>--profile-selector</pre> command line option is used"
        ),
        values=[(p, p.name) for i, p in enumerate(profile_list)],
    ).run_async()
    # Somehow prompt_toolkit sets up a bogus signal handler upon exit
    # TODO: Report this issue upstream
    if hasattr(signal, "SIGWINCH"):
        asyncio.get_event_loop().remove_signal_handler(signal.SIGWINCH)
    if not selection:
        return selection
    logger.info("Selected profile", profile=selection.name)
    return selection


def authenticate_to(host, proxy, credentials, display_mode, version):
    logger.info("Authenticating to VPN endpoint", name=host.name, address=host.address)
    return Authenticator(host, proxy, credentials, version).authenticate(display_mode)


def run_openconnect(auth_info, host, proxy, version, args):
    as_root = next(([prog] for prog in ("doas", "sudo") if shutil.which(prog)), [])
    try:
        if not as_root:
            if os.name == "nt":
                import ctypes

                if not ctypes.windll.shell32.IsUserAnAdmin():
                    raise PermissionError
            else:
                raise PermissionError
    except PermissionError:
        logger.error(
            "Cannot find suitable program to execute as superuser (doas/sudo), exiting"
        )
        return 20

    command_line = as_root + [
        "openconnect",
        "--useragent",
        f"AnyConnect Linux_64 {version}",
        "--version-string",
        version,
        "--cookie-on-stdin",
        "--servercert",
        auth_info.server_cert_hash,
        *args,
        host.vpn_url,
    ]
    if proxy:
        command_line.extend(["--proxy", proxy])

    session_token = auth_info.session_token.encode("utf-8")
    logger.debug("Starting OpenConnect", command_line=command_line)
    return subprocess.run(command_line, input=session_token).returncode


def handle_disconnect(command):
    if command:
        logger.info("Running command on disconnect", command_line=command)
        return subprocess.run(command, timeout=5, shell=True).returncode
