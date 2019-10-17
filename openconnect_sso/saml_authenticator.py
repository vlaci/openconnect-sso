import structlog

from openconnect_sso.browser import Browser

log = structlog.get_logger()


async def authenticate_in_browser(login_url, login_final_url, token_cookie_name):
    async with Browser() as browser:
        await browser.authenticate_at(login_url, credentials=None)

        while browser.url != login_final_url:
            await browser.page_loaded()
            log.debug("Browser loaded page", url=browser.url)

    return browser.cookies[token_cookie_name]
