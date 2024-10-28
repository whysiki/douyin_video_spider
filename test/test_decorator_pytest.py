import pytest
import aiohttp
import asyncio
from pathlib import Path
from test_decorator import (
    async_download_retry_decorator,
)

temp_file = Path(__file__).parent / "temp_file.txt"


@async_download_retry_decorator(
    retry_times=4,
    sleep_interval_min=1,
    sleep_interval_max=2,
    reset_session_interval=3,
)
async def test_download(
    file_save_path: str | Path,
    session: aiohttp.ClientSession,
    manual_raise_a_exception: bool = False,
):
    url = "https://example.com"
    async with session.get(url) as response:
        response.raise_for_status()
        text = await response.text(encoding="utf-8")
        with open(file_save_path, "w") as f:
            f.write(text)
            if manual_raise_a_exception:
                raise Exception("Manual exception")


async def test_download_retry():
    await test_download(
        file_save_path=temp_file,
        session=aiohttp.ClientSession(),
        manual_raise_a_exception=True,
    )
    assert not temp_file.exists(), "File should not be created"


if __name__ == "__main__":
    asyncio.run(test_download_retry())
