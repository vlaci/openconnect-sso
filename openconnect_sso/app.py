import asyncio
import getpass
import logging
import os
import signal
from pathlib import Path

import structlog
from prompt_toolkit import HTML
from prompt_toolkit.eventloop import use_asyncio_event_loop
from prompt_toolkit.shortcuts import radiolist_dialog

from openconnect_sso import config
from openconnect_sso.config import Credentials
from openconnect_sso.saml_authenticator import authenticate_in_browser

logger = structlog.get_logger()


def run(args):
    configure_logger(logging.getLogger(), args.log_level)
    loop = asyncio.get_event_loop()
    use_asyncio_event_loop(loop)

    try:
        return asyncio.get_event_loop().run_until_complete(_run(args))
    except KeyboardInterrupt:
        logger.warn("CTRL-C pressed, exiting")


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
    logger.info(str(args))
    session_token = await authenticate_in_browser(args.login_url, args.login_final_url, args.token_cookie_name)

    print(session_token)
