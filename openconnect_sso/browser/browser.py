import asyncio

import structlog

from . import webengine_process as web
from ..config import DisplayMode

logger = structlog.get_logger()


class Browser:
    def __init__(self, proxy=None, display_mode=DisplayMode.SHOWN):
        self.browser_proc = None
        self.updater = None
        self.running = False
        self._urls = asyncio.Queue()
        self.url = None
        self.cookies = {}
        self.loop = asyncio.get_event_loop()
        self.proxy = proxy
        self.display_mode = display_mode

    async def spawn(self):
        self.browser_proc = web.Process(self.proxy, self.display_mode)
        self.browser_proc.start()
        self.running = True

        self.updater = asyncio.ensure_future(self._update_status())

        def stop(_task):
            self.running = False

        asyncio.ensure_future(self.browser_proc.wait()).add_done_callback(stop)

    async def _update_status(self):
        while self.running:
            logger.debug("Waiting for message from browser process")

            try:
                state = await self.browser_proc.get_state_async()
            except EOFError:
                if self.running:
                    logger.warn("Connection terminated with browser")
                    self.running = False
                else:
                    logger.info("Browser exited")
                await self._urls.put(None)
                return
            logger.debug("Message received from browser", message=state)

            if isinstance(state, web.Url):
                await self._urls.put(state.url)
            elif isinstance(state, web.SetCookie):
                self.cookies[state.name] = state.value
            else:
                logger.error("Message unrecognized", message=state)

    async def authenticate_at(self, url, credentials):
        assert self.running
        self.browser_proc.authenticate_at(url, credentials)

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
