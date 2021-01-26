import attr
import requests
import structlog
from lxml import etree, objectify

from openconnect_sso.saml_authenticator import authenticate_in_browser


logger = structlog.get_logger()


class Authenticator:
    def __init__(self, host, proxy=None, credentials=None):
        self.host = host
        self.proxy = proxy
        self.credentials = credentials
        self.session = create_http_session(proxy)

    async def authenticate(self, display_mode):
        self._detect_authentication_target_url()

        response = self._start_authentication()
        if not isinstance(response, AuthRequestResponse):
            logger.error(
                "Could not start authentication. Invalid response type in current state",
                response=response,
            )
            raise AuthenticationError(response)

        if response.auth_error:
            logger.error(
                "Could not start authentication. Response contains error",
                error=response.auth_error,
                response=response,
            )
            raise AuthenticationError(response)

        auth_request_response = response

        sso_token = await self._authenticate_in_browser(
            auth_request_response, display_mode
        )

        response = self._complete_authentication(auth_request_response, sso_token)
        if not isinstance(response, AuthCompleteResponse):
            logger.error(
                "Could not finish authentication. Invalid response type in current state",
                response=response,
            )
            raise AuthenticationError(response)

        return response

    def _detect_authentication_target_url(self):
        # Follow possible redirects in a GET request
        # Authentication will occcur using a POST request on the final URL
        response = requests.get(self.host.vpn_url)
        response.raise_for_status()
        self.host.address = response.url
        logger.debug("Auth target url", url=self.host.vpn_url)

    def _start_authentication(self):
        request = _create_auth_init_request(self.host, self.host.vpn_url)
        logger.debug("Sending auth init request", content=request)
        response = self.session.post(self.host.vpn_url, request)
        logger.debug("Auth init response received", content=response.content)
        return parse_response(response)

    async def _authenticate_in_browser(self, auth_request_response, display_mode):
        return await authenticate_in_browser(
            self.proxy, auth_request_response, self.credentials, display_mode
        )

    def _complete_authentication(self, auth_request_response, sso_token):
        request = _create_auth_finish_request(
            self.host, auth_request_response, sso_token
        )
        logger.debug("Sending auth finish request", content=request)
        response = self.session.post(self.host.vpn_url, request)
        logger.debug("Auth finish response received", content=response.content)
        return parse_response(response)


class AuthenticationError(Exception):
    pass


class AuthResponseError(AuthenticationError):
    pass


def create_http_session(proxy):
    session = requests.Session()
    session.proxies = {"http": proxy, "https": proxy}
    session.headers.update(
        {
            "User-Agent": "AnyConnect Linux_64 4.7.00136",
            "Accept": "*/*",
            "Accept-Encoding": "identity",
            "X-Transcend-Version": "1",
            "X-Aggregate-Auth": "1",
            "X-Support-HTTP-Auth": "true",
            "Content-Type": "application/x-www-form-urlencoded",
            # I know, it is invalid but that’s what Anyconnect sends
        }
    )
    return session


E = objectify.ElementMaker(annotate=False)


def _create_auth_init_request(host, url):
    ConfigAuth = getattr(E, "config-auth")
    Version = E.version
    DeviceId = getattr(E, "device-id")
    GroupSelect = getattr(E, "group-select")
    GroupAccess = getattr(E, "group-access")
    Capabilities = E.capabilities
    AuthMethod = getattr(E, "auth-method")

    root = ConfigAuth(
        {"client": "vpn", "type": "init", "aggregate-auth-version": "2"},
        Version({"who": "vpn"}, "4.7.00136"),
        DeviceId("linux-64"),
        GroupSelect(host.name),
        GroupAccess(url),
        Capabilities(AuthMethod("single-sign-on-v2")),
    )
    return etree.tostring(
        root, pretty_print=True, xml_declaration=True, encoding="UTF-8"
    )


def parse_response(resp):
    resp.raise_for_status()
    xml = objectify.fromstring(resp.content)
    t = xml.get("type")
    if t == "auth-request":
        return parse_auth_request_response(xml)
    elif t == "complete":
        return parse_auth_complete_response(xml)


def parse_auth_request_response(xml):
    assert xml.auth.get("id") == "main"

    try:
        resp = AuthRequestResponse(
            auth_id=xml.auth.get("id"),
            auth_title=getattr(xml.auth, "title", ""),
            auth_message=xml.auth.message,
            auth_error=getattr(xml.auth, "error", ""),
            opaque=xml.opaque,
            login_url=xml.auth["sso-v2-login"],
            login_final_url=xml.auth["sso-v2-login-final"],
            token_cookie_name=xml.auth["sso-v2-token-cookie-name"],
        )
    except AttributeError as exc:
        raise AuthResponseError(exc)

    logger.info(
        "Response received",
        id=resp.auth_id,
        title=resp.auth_title,
        message=resp.auth_message,
    )
    return resp


@attr.s
class AuthRequestResponse:
    auth_id = attr.ib(converter=str)
    auth_title = attr.ib(converter=str)
    auth_message = attr.ib(converter=str)
    auth_error = attr.ib(converter=str)
    login_url = attr.ib(converter=str)
    login_final_url = attr.ib(converter=str)
    token_cookie_name = attr.ib(converter=str)
    opaque = attr.ib()


def parse_auth_complete_response(xml):
    assert xml.auth.get("id") == "success"
    resp = AuthCompleteResponse(
        auth_id=xml.auth.get("id"),
        auth_message=xml.auth.message,
        session_token=xml["session-token"],
        server_cert_hash=xml.config["vpn-base-config"]["server-cert-hash"],
    )
    logger.info("Response received", id=resp.auth_id, message=resp.auth_message)
    return resp


@attr.s
class AuthCompleteResponse:
    auth_id = attr.ib(converter=str)
    auth_message = attr.ib(converter=str)
    session_token = attr.ib(converter=str)
    server_cert_hash = attr.ib(converter=str)


def _create_auth_finish_request(host, auth_info, sso_token):
    ConfigAuth = getattr(E, "config-auth")
    Version = E.version
    DeviceId = getattr(E, "device-id")
    SessionToken = getattr(E, "session-token")
    SessionId = getattr(E, "session-id")
    Auth = E.auth
    SsoToken = getattr(E, "sso-token")

    root = ConfigAuth(
        {"client": "vpn", "type": "auth-reply", "aggregate-auth-version": "2"},
        Version({"who": "vpn"}, "4.7.00136"),
        DeviceId("linux-64"),
        SessionToken(),
        SessionId(),
        auth_info.opaque,
        Auth(SsoToken(sso_token)),
    )
    return etree.tostring(
        root, pretty_print=True, xml_declaration=True, encoding="UTF-8"
    )
