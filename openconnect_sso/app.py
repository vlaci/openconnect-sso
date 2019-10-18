import json
import logging
import signal
import sys

import structlog

from PyQt5.QtCore import QUrl, QTimer
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineScript
from PyQt5.QtWidgets import QApplication

from openconnect_sso import config

app = None
logger = structlog.get_logger("webengine")


def run(args):
    configure_logger(logging.getLogger(), args.log_level)

    try:
        return run_browser_process(args)
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


def run_browser_process(args):
    signal.signal(signal.SIGTERM, on_sigterm)
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # To work around funky GC conflicts with C++ code by ensuring QApplication terminates last
    global app
    configure_logger(logging.getLogger(), args.log_level)

    cfg = config.load()

    app = QApplication(sys.argv)

    # In order to make Python able to handle signals
    force_python_execution = QTimer()
    force_python_execution.start(200)

    def ignore():
        pass

    force_python_execution.timeout.connect(ignore)
    web = WebBrowser(cfg.auto_fill_rules, args.login_final_url, args.token_cookie_name)

    web.authenticate_at(QUrl(args.login_url), cfg.credentials)

    web.show()
    rc = app.exec_()

    logger.info("Exiting browser")
    return rc


class WebBrowser(QWebEngineView):
    def __init__(self, auto_fill_rules, login_final_url, token_cookie_name):
        super().__init__()
        self.login_final_url = login_final_url
        self._auto_fill_rules = auto_fill_rules
        cookie_store = self.page().profile().cookieStore()
        cookie_store.cookieAdded.connect(self._on_cookie_added)
        self.page().loadFinished.connect(self._on_load_finished)
        self.token_cookie_name = token_cookie_name
        self.cookies = {}

    def authenticate_at(self, url, credentials):
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
        self.cookies[to_str(cookie.name())] = to_str(cookie.value())


    def _on_load_finished(self, success):
        url = self.page().url().toString()
        logger.debug("Page loaded", url=url)

        if url == self.login_final_url:
            sys.stdout.write(self.cookies[self.token_cookie_name])
            sys.stdout.flush()
            QApplication.quit()


def to_str(qval):
    return bytes(qval).decode()


def get_selectors(rules, credentials):
    statements = []
    for i, rule in enumerate(rules):
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


def on_sigterm(signum, frame):
    logger.info("SIGNAL handler")
    QApplication.quit()
