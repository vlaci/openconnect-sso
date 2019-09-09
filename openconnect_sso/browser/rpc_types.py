import base64
import pickle

import attr


class Type:
    def serialize(self):
        return base64.b64encode(pickle.dumps(self))


def deserialize(data):
    return pickle.loads(base64.b64decode(data))


@attr.s
class Url(Type):
    url = attr.ib()


@attr.s
class Credentials(Type):
    credentials = attr.ib()


@attr.s
class StartupInfo(Type):
    url = attr.ib()
    credentials = attr.ib()


@attr.s
class SetCookie(Type):
    name = attr.ib()
    value = attr.ib()
