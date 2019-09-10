import json
import logging
import signal
import sys

import pkg_resources
import structlog

from PyQt5.QtCore import QUrl
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineScript
from PyQt5.QtWidgets import QApplication

from openconnect_sso import config
from openconnect_sso.app import configure_logger
from openconnect_sso.browser import rpc_types as rpc
from openconnect_sso.cli import create_argparser

logger = structlog.get_logger("webengine")


def run_browser_process():
    args = create_argparser().parse_known_args()[0]
    configure_logger(logging.getLogger(), args.log_level)

    cfg = config.load()

    app = QApplication(sys.argv)
    web = WebBrowser(cfg.auto_fill_rules)

    line = sys.stdin.buffer.readline()
    startup_info = rpc.deserialize(line)
    logger.info("Browser started", startup_info=startup_info)

    logger.info("Loading page", url=startup_info.url)

    web.authenticate_at(QUrl(startup_info.url), startup_info.credentials)

    web.show()
    rc = app.exec_()

    logger.info("Exiting browser")
    return rc


class WebBrowser(QWebEngineView):
    def __init__(self, auto_fill_rules):
        super().__init__()
        self._auto_fill_rules = auto_fill_rules
        cookie_store = self.page().profile().cookieStore()
        cookie_store.cookieAdded.connect(self._on_cookie_added)
        self.page().loadFinished.connect(self._on_load_finished)

    def authenticate_at(self, url, credentials):
        script_source = pkg_resources.resource_string(__name__, "user.js").decode()
        script = QWebEngineScript()
        script.setInjectionPoint(QWebEngineScript.DocumentCreation)
        script.setWorldId(QWebEngineScript.ApplicationWorld)
        script.setSourceCode(script_source)
        self.page().scripts().insert(script)

        if credentials:
            logger.info("Initiating autologin", cred=credentials)
            for url_pattern, rules in self._auto_fill_rules.items():
                script = QWebEngineScript()
                script.setInjectionPoint(QWebEngineScript.DocumentReady)
                script.setWorldId(QWebEngineScript.ApplicationWorld)
                script.setSourceCode(
                    f"""
// ==UserScript==
// @include {url_pattern}
// ==/UserScript==

function autoFill() {{
    {get_selectors(rules, credentials)}
    setTimeout(autoFill, 1000);
}}
autoFill();
"""
                )
                self.page().scripts().insert(script)

        self.load(QUrl(url))

    def _on_cookie_added(self, cookie):
        logger.debug("Cookie set", name=to_str(cookie.name()))
        sys.stdout.buffer.write(
            rpc.SetCookie(to_str(cookie.name()), to_str(cookie.value())).serialize()
        )
        sys.stdout.buffer.write(b"\n")
        sys.stdout.flush()

    def _on_load_finished(self, success):
        url = self.page().url().toString()
        logger.debug("Page loaded", url=url)

        sys.stdout.buffer.write(rpc.Url(url).serialize())
        sys.stdout.buffer.write(b"\n")
        sys.stdout.flush()


def to_str(qval):
    return bytes(qval).decode()


def get_selectors(rules, credentials):
    statements = []
    for i, rule in enumerate(rules):
        selector = json.dumps(rule.selector)
        if rule.fill:
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


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    run_browser_process()
