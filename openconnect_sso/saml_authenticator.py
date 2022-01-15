import structlog

from openconnect_sso.browser import Browser

log = structlog.get_logger()


def authenticate_in_browser(proxy, auth_info, credentials, display_mode):
    browser = Browser(proxy, display_mode)
    return browser.authenticate_at(auth_info.login_url, credentials, auth_info.token_cookie_name)
