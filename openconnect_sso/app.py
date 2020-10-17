import asyncio
import getpass
import json
import logging
import shlex
import signal
from pathlib import Path

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

    try:
        return asyncio.run(_run(args))
    except KeyboardInterrupt:
        logger.warn("CTRL-C pressed, exiting")
    except Terminated:
        logger.warn("Browser window terminated, exiting")
    except AuthResponseError as exc:
        logger.error(
            f'Required attributes not found in response ("{exc}", does this endpoint do SSO?), exiting'
        )
    except HTTPError as exc:
        logger.error(f"Request error: {exc}")


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


async def _run(args):
    cfg = config.load()

    credentials = None
    if cfg.credentials:
        credentials = cfg.credentials
    elif args.user:
        credentials = Credentials(args.user)
        credentials.password = getpass.getpass(prompt=f"Password ({args.user}): ")
        cfg.credentials = credentials

    if cfg.default_profile and not (args.use_profile_selector or args.server):
        selected_profile = cfg.default_profile
    elif args.use_profile_selector or args.profile_path:
        profiles = get_profiles(Path(args.profile_path))
        if not profiles:
            logger.error("No profile found")
            return 17

        selected_profile = await select_profile(profiles)
        if not selected_profile:
            logger.error("No profile selected")
            return 18
    elif args.server:
        selected_profile = config.HostProfile(
            args.server, args.usergroup, args.authgroup, args.on_disconnect
        )
    else:
        raise ValueError(
            "Cannot determine server address. Invalid arguments specified."
        )

    cfg.default_profile = selected_profile

    config.save(cfg)

    display_mode = config.DisplayMode[args.browser_display_mode.upper()]

    auth_response = await authenticate_to(selected_profile, credentials, display_mode)
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
        return await run_openconnect(
            auth_response, selected_profile, args.openconnect_args
        )
    finally:
        await handle_disconnect(selected_profile.on_disconnect)


async def select_profile(profile_list):
    selection = await radiolist_dialog(
        title="Select AnyConnect profile",
        text=HTML(
            "The following AnyConnect profiles are detected.\n"
            "The selection will be <b>saved</b> and not asked again unless the <pre>--profile-selector</pre> command line option is used"
        ),
        values=[(p, p.name) for i, p in enumerate(profile_list)],
    ).run_async()
    asyncio.get_event_loop().remove_signal_handler(signal.SIGWINCH)
    if not selection:
        return selection
    logger.info("Selected profile", profile=selection.name)
    return selection


def authenticate_to(host, credentials, display_mode):
    logger.info("Authenticating to VPN endpoint", name=host.name, address=host.address)
    return Authenticator(host, credentials).authenticate(display_mode)


async def run_openconnect(auth_info, host, args):
    command_line = [
        "sudo",
        "openconnect",
        "--cookie-on-stdin",
        "--servercert",
        auth_info.server_cert_hash,
        *args,
    ]

    logger.debug("Starting OpenConnect", command_line=command_line)
    try:
        proc = await asyncio.create_subprocess_exec(
            *command_line,
            host.vpn_url,
            stdin=asyncio.subprocess.PIPE,
            stdout=None,
            stderr=None,
        )
        proc.stdin.write(f"{auth_info.session_token}\n".encode())
        await proc.stdin.drain()
        return await proc.wait()
    finally:
        await proc.wait()


async def handle_disconnect(command):
    if command:
        logger.info(f"Running {command!r} on shutdown...")
        command = str(Path(command).expanduser())
        proc = await asyncio.create_subprocess_exec(command)
        await asyncio.wait_for(proc.wait(), timeout=5)
