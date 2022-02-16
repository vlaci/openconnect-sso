import json
import structlog
from logging import CRITICAL

from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver import DesiredCapabilities
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.utils import ChromeType
from selenium.webdriver.common.proxy import Proxy, ProxyType
from ..config import DisplayMode

from openconnect_sso import config

logger = structlog.get_logger()


class Browser:
    def __init__(self, proxy=None, display_mode=DisplayMode.SHOWN):
        self.cfg = config.load()
        self.proxy = proxy
        self.display_mode = display_mode

    def __enter__(self):
        chrome_options = Options()
        capabilities = DesiredCapabilities.CHROME
        if self.display_mode == DisplayMode.HIDDEN:
            chrome_options.add_argument("headless")
            chrome_options.add_argument("no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")

        if self.proxy:
            proxy = Proxy()
            proxy.proxy_type = ProxyType.MANUAL
            parsed = urlparse(self.proxy)
            if parsed.scheme.startswith("socks5"):
                proxy.socks_proxy = f"{parsed.hostname}:{parsed.port}"
            elif parsed.scheme.startswith("http"):
                proxy.http_proxy = f"{parsed.hostname}:{parsed.port}"
            elif parsed.scheme.startswith("ssl"):
                proxy.ssl_proxy = f"{parsed.hostname}:{parsed.port}"
            else:
                raise ValueError("Unsupported proxy type", parsed.scheme)

            proxy.add_to_capabilities(capabilities)

        self.driver = webdriver.Chrome(
            ChromeDriverManager(
                chrome_type=ChromeType.CHROMIUM, log_level=CRITICAL
            ).install(),
            options=chrome_options,
            desired_capabilities=capabilities,
        )
        return self

    def authenticate_at(self, url, credentials, expected_cookie_name):
        self.driver.get(url)
        if credentials:
            for url_pattern, rules in self.cfg.auto_fill_rules.items():
                script = f"""
// ==UserScript==
// @include {url_pattern}
// ==/UserScript==

function autoFill() {{
    {get_selectors(rules, credentials)}
    setTimeout(autoFill, 1000);
}}
autoFill();
"""
        self.driver.execute_script(script)
        WebDriverWait(self.driver, 10).until(
            lambda driver: has_cookie(driver.get_cookies(), expected_cookie_name)
        )
        return get_cookie(self.driver.get_cookies(), expected_cookie_name)

    def __exit__(self, exc_type, exc_value, t):
        self.driver.close()
        return True


def has_cookie(cookies, cookie_name):
    return get_cookie(cookies, cookie_name) is not None


def get_cookie(cookies, cookie_name):
    for c in cookies:
        if c["name"] == cookie_name:
            return c["value"]

    return None


def get_selectors(rules, credentials):
    statements = []
    for rule in rules:
        selector = json.dumps(rule.selector)
        if rule.action == "stop":
            statements.append(
                f"""var elem = document.querySelector({selector}); if (elem) {{ return; }}"""
            )
        elif rule.fill:
            value = json.dumps(getattr(credentials, rule.fill, None))
            if value:
                statements.append(
                    f"""var elem = document.querySelector({selector}); if (elem) {{ elem.dispatchEvent(new Event("focus")); elem.value = {value}; elem.dispatchEvent(new Event("blur")); }}"""
                )
            else:
                logger.warning(
                    "Credential info not available",
                    type=rule.fill,
                    possibilities=dir(credentials),
                )
        elif rule.action == "click":
            statements.append(
                f"""var elem = document.querySelector({selector}); if (elem) {{ elem.dispatchEvent(new Event("focus")); elem.click(); }}"""
            )
    return "\n".join(statements)
