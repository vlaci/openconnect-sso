import argparse
import enum
import logging

import openconnect_sso
from openconnect_sso import app


def create_argparser():
    parser = argparse.ArgumentParser(
        prog="openconnect-sso", description=openconnect_sso.__description__
    )
    parser.add_argument(
        "-p",
        "--profile",
        dest="profile_path",
        help="Use a profile from this file or directory",
        default="/opt/cisco/anyconnect/profile",
    )

    parser.add_argument(
        "-P",
        "--profile-selector",
        dest="use_profile_selector",
        help="Always display profile selector",
        action="store_true",
        default=False,
    )

    parser.add_argument(
        "--login-only",
        help="Complete authentication but do not acquire a session token or initiate a connection",
        action="store_true",
        default=False,
    )

    parser.add_argument(
        "-l",
        "--log-level",
        help="",
        type=LogLevel.parse,
        choices=LogLevel.choices(),
        default=LogLevel.INFO,
    )

    credentials_group = parser.add_argument_group("Credentials for automatic login")
    credentials_group.add_argument(
        "-u", "--user", help="Authenticate as the given user", default=None
    )
    return parser


class LogLevel(enum.IntEnum):
    INFO = logging.INFO
    WARNING = logging.WARNING
    DEBUG = logging.DEBUG

    def __str__(self):
        return self.name

    @classmethod
    def parse(cls, name):
        return cls.__members__[name.upper()]

    @classmethod
    def choices(cls):
        return cls.__members__.values()


def main():
    parser = create_argparser()
    args = parser.parse_args()
    return app.run(args)
