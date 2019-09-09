import attr
import requests
import structlog
from lxml import etree, objectify

from openconnect_sso.saml_authenticator import authenticate_in_browser


logger = structlog.get_logger()


class Authenticator:
    def __init__(self, host, credentials=None):
        self.session = create_http_session()
        self.host = host
        self.credentials = credentials

        self.auth_state = StartAuthentication(authenticator=self)

    async def authenticate(self):
        assert isinstance(self.auth_state, StartAuthentication)
        logger.debug("Entering state", state=self.auth_state)
        while not isinstance(self.auth_state, AuthenticationCompleted):
            self.auth_state = await self.auth_state.trigger()
            logger.debug("Entering state", state=self.auth_state)
        return self.auth_state.auth_completed_response


def create_http_session():
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "AnyConnect Linux_64 4.7.00136",
            "Accept": "*/*",
            "Accept-Encoding": "identity",
            "X-Transcend-Version": "1",
            "X-Aggregate-Auth": "1",
            "X-AnyConnect-Platform": "linux-64",
            "Content-Type": "application/x-www-form-urlencoded",
            # I know, it is invalid but that’s what Anyconnect sends
        }
    )
    return session


class AuthenticationState:
    def __init__(self, *, authenticator=None, previous=None):
        self.authenticator = authenticator
        self.auth_request_response = None
        self.auth_completed_response = None
        self.sso_token = None
        if previous:
            self.authenticator = previous.authenticator
            self.auth_request_response = previous.auth_request_response
            self.auth_completed_response = previous.auth_completed_response
            self.sso_token = previous.sso_token

    def __repr__(self):
        return f"<STATE {self.__class__.__name__}>"


class StartAuthentication(AuthenticationState):
    async def trigger(self):
        request = _create_auth_init_request(
            self.authenticator.host, self.authenticator.host.vpn_url
        )
        response = self.authenticator.session.post(
            self.authenticator.host.vpn_url, request
        )
        logger.debug("Auth init response received", content=response.content)
        response = parse_response(response)

        if isinstance(response, AuthRequestResponse):
            self.auth_request_response = response
            return ExternalAuthentication(previous=self)
        else:
            logger.error(
                "Error occurred during authentication. Invalid response type in state",
                state=self,
                response=response,
            )
            return self


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
    resp = AuthRequestResponse(
        auth_id=xml.auth.get("id"),
        auth_title=xml.auth.title,
        auth_message=xml.auth.message,
        opaque=xml.opaque,
        login_url=xml.auth["sso-v2-login"],
        login_final_url=xml.auth["sso-v2-login-final"],
        token_cookie_name=xml.auth["sso-v2-token-cookie-name"],
    )
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
    login_url = attr.ib(converter=str)
    login_final_url = attr.ib(convert=str)
    token_cookie_name = attr.ib(convert=str)
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


class ExternalAuthentication(AuthenticationState):
    async def trigger(self):
        self.sso_token = await authenticate_in_browser(
            self.auth_request_response, self.authenticator.credentials
        )
        return CompleteAuthentication(previous=self)


class CompleteAuthentication(AuthenticationState):
    async def trigger(self):
        request = _create_auth_finish_request(
            self.authenticator.host, self.auth_request_response, self.sso_token
        )
        response = self.authenticator.session.post(
            self.authenticator.host.vpn_url, request
        )
        logger.debug("Auth finish response received", content=response.content)
        response = parse_response(response)

        if isinstance(response, AuthCompleteResponse):
            self.auth_completed_response = response
            return AuthenticationCompleted(previous=self)
        else:
            logger.error(
                "Error occurred during authentication. Invalid response type in state",
                state=self,
                response=response,
            )
            return StartAuthentication()


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


class AuthenticationCompleted(AuthenticationState):
    pass
