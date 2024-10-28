from rich.console import Console
from functools import wraps
from pathlib import Path
import aiohttp
import asyncio
import random
from loguru import logger
from typing import Any, Callable, Coroutine
from useful_tools import read_statejson_and_get_cookie_headers

console = Console()


def async_download_retry_decorator(
    retry_times: int = 10,
    sleep_interval_min: int = 1,
    sleep_interval_max: int = 2,
    reset_session_interval: int = 2,
) -> Callable[..., Coroutine[Any, Any, Any]]:
    """
    Handle function kwargs:

    - session: aiohttp.ClientSession, if the function reset_session_interval reached, it will close the session and create a new one.

    - file_save_path: Union[str, Path], if the function reached the retry limit, it will delete the file.

    Attention:

    - If the function raises an AssertionError, it will not retry.

    Args:
        retry_times (int, optional): _description_. Defaults to 10.
        sleep_interval_min (int, optional): _description_. Defaults to 1.
        sleep_interval_max (int, optional): _description_. Defaults to 2.
        reset_session_interval (int, optional): _description_. Defaults to 3.
    Returns:
        Callable[..., Coroutine[Any, Any, Any]]: _description_

    """

    def wrapper2(
        func: Callable[..., Coroutine[Any, Any, Any]]
    ) -> Callable[..., Coroutine[Any, Any, Any]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None

            for i in range(retry_times):
                try:
                    return await func(*args, **kwargs)
                except AssertionError as e:
                    console.print(
                        f"\nYou have an assertion error: {str(e)}\n", style="bold red"
                    )
                    raise e
                except Exception as e:
                    last_exception = e
                    console.print(
                        f"\nError type: {type(e)}: {str(e)}\n", style="bold red"
                    )
                    console.print(
                        f"\nRetrying {func.__name__} for the {i+1}/{retry_times} time\n",
                        style="bold yellow",
                    )
                    await asyncio.sleep(
                        random.randint(sleep_interval_min, sleep_interval_max)
                    )

                    # if (i + 1) % reset_session_interval == 0:
                        # await reset_session(kwargs, func.__name__)

            await handle_retry_limit(kwargs, func.__name__, last_exception)

            return 0

        return wrapper

    return wrapper2


# async def reset_session(kwargs: dict, func_name: str) -> None:
#     if "session" in kwargs and isinstance(kwargs["session"], aiohttp.ClientSession):
#         if not kwargs["session"].closed:
#             await kwargs["session"].close()
#         # session = aiohttp.ClientSession()
#         # local_addr = random.choice(["10.193.2.171", "192.168.0.103"])
#         # connector = aiohttp.TCPConnector(local_addr=(local_addr, 0))
#         connector = None
#         cookies, headers = read_statejson_and_get_cookie_headers()
#         kwargs["session"] = aiohttp.ClientSession(
#             timeout=aiohttp.ClientTimeout(connect=6),
#             # headers=headers,
#             cookies=cookies,
#             connector=connector
#         )
#         console.print(f"\n{func_name} session has been reset\n", style="bold green")


async def handle_retry_limit(
    kwargs: dict, func_name: str, last_exception: Exception
) -> None:
    if "file_save_path" in kwargs and isinstance(kwargs["file_save_path"], (str, Path)):
        file_path = (
            Path(kwargs["file_save_path"])
            if isinstance(kwargs["file_save_path"], str)
            else kwargs["file_save_path"]
        )
        if file_path.exists():
            logger.error(f"Deleting {file_path.name} because of reached retry limit")
            file_path.unlink()

    if (
        "session" in kwargs
        and isinstance(kwargs["session"], aiohttp.ClientSession)
        # and not kwargs["session"].closed
    ):
        await kwargs["session"].close()
        console.print(f"\n{func_name} session has been closed\n", style="bold green")

    console.print(
        f"\nRetry limit reached for {func_name}: {str(last_exception)}\n",
        style="bold red",
    )
