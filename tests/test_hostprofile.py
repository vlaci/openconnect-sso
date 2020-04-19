import pytest

from openconnect_sso.config import HostProfile


@pytest.mark.parametrize(
    ("server", "group", "expected_url"),
    (
        ("hostname", "", "https://hostname"),
        ("hostname", "group", "https://hostname/group"),
        ("hostname/group", "", "https://hostname/group"),
        ("https://hostname", "group", "https://hostname/group"),
        ("https://server.com", "group", "https://server.com/group"),
        ("https://hostname/group", "", "https://hostname/group"),
        ("https://hostname:8443/group", "", "https://hostname:8443/group"),
    ),
)
def test_vpn_url(server, group, expected_url):
    assert HostProfile(server, group, "name").vpn_url == expected_url
