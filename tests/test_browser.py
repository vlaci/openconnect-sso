import pytest

from openconnect_sso.browser import Browser


@pytest.mark.asyncio
async def test_browser_context_manager_should_work_in_empty_context_manager():
    async with Browser() as browser:
        pass
