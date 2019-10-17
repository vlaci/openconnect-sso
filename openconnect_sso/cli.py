#!/usr/bin/env python3

import argparse
import enum
import logging
import os
import sys

import openconnect_sso
from openconnect_sso import app, config


def create_argparser():
    parser = argparse.ArgumentParser(
        prog="openconnect-sso", description=openconnect_sso.__description__
    )

    parser.add_argument('login_url')
    parser.add_argument('login_final_url')
    parser.add_argument('logout_url')
    parser.add_argument('logout_final_url')
    parser.add_argument('token_cookie_name')
    parser.add_argument('error_cookie_name')

    parser.add_argument(
        "-l",
        "--log-level",
        help="",
        type=LogLevel.parse,
        choices=LogLevel.choices(),
        default=LogLevel.INFO,
    )
    return parser


class LogLevel(enum.IntEnum):
    ERROR = logging.ERROR
    WARNING = logging.WARNING
    INFO = logging.INFO
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


if __name__ == "__main__":
    sys.exit(main())
