from pathlib import Path

import structlog
from lxml import objectify

from openconnect_sso.config import HostProfile

logger = structlog.get_logger()

ns = {"enc": "http://schemas.xmlsoap.org/encoding/"}


def _get_profiles_from_one_file(path):
    logger.info("Loading profiles from file", path=path.name)

    with path.open() as f:
        xml = objectify.parse(f)

    hostentries = xml.xpath(
        "//enc:AnyConnectProfile/enc:ServerList/enc:HostEntry", namespaces=ns
    )

    profiles = []
    for entry in hostentries:
        profiles.append(
            HostProfile(
                name=entry.HostName,
                address=entry.HostAddress,
                user_group=entry.UserGroup,
            )
        )

    logger.debug("AnyConnect profiles parsed", path=path.name, profiles=profiles)
    return profiles


def get_profiles(path: Path):
    if path.is_file():
        profile_files = [path]
    elif path.is_dir():
        profile_files = path.glob("*.xml")
    else:
        raise ValueError("No profile file found", path.name)

    profiles = []
    for p in profile_files:
        profiles.extend(_get_profiles_from_one_file(p))
    return profiles
