import asyncio
import sys
from pathlib import Path

import structlog

from . import rpc_types as rpc

logger = structlog.get_logger()


class Browser:
    def __init__(self):
        self.browser_proc = None
        self.updater = None
        self.running = False
        self._urls = asyncio.Queue()
        self.url = None
        self.cookies = {}
        self.loop = asyncio.get_event_loop()

    async def spawn(self):
        exe = sys.executable
        script = str(Path(__file__).parent.joinpath(Path("webengine_process.py")))
        self.browser_proc = await asyncio.create_subprocess_exec(
            exe,
            script,
            *sys.argv[1:],
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE
        )

        self.updater = asyncio.create_task(self._update_status())
        self.running = True

        def stop(_task):
            self.running = False

        asyncio.create_task(self.browser_proc.wait()).add_done_callback(stop)

    async def _update_status(self):
        assert self.running
        while self.running:
            logger.debug("Waiting for message from browser process")

            try:
                line = await self.browser_proc.stdout.readline()
                state = rpc.deserialize(line)
            except EOFError:
                if self.running:
                    logger.warn("Connection terminated with browser")
                    self.running = False
                else:
                    logger.info("Browser exited")
                await self._urls.put(None)
                return
            logger.debug("Message received from browser", message=state)

            if isinstance(state, rpc.Url):
                await self._urls.put(state.url)
            elif isinstance(state, rpc.SetCookie):
                self.cookies[state.name] = state.value
            else:
                logger.error("Message unrecognized", message=state)

    async def authenticate_at(self, url, credentials):
        assert self.running
        self.browser_proc.stdin.write(rpc.StartupInfo(url, credentials).serialize())
        self.browser_proc.stdin.write(b"\n")
        await self.browser_proc.stdin.drain()

    async def page_loaded(self):
        rv = await self._urls.get()
        if not self.running:
            raise Terminated()
        self.url = rv

    async def __aenter__(self):
        await self.spawn()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            self.running = False
            self.browser_proc.terminate()
        except ProcessLookupError:
            # already stopped
            pass
        await self.browser_proc.wait()
        await self.updater


class Terminated(Exception):
    pass
