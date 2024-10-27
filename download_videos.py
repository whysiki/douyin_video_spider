import os
import json
import requests
import re
from pathlib import Path
import aiohttp
from rich import print
from loguru import logger
from tqdm import tqdm
from rich.console import Console
from functools import wraps, lru_cache
import asyncio
import random
from fake_useragent import UserAgent


def sanitize_filename(filename: str):
    assert isinstance(filename, str), "filename must be a string"
    filename = filename.replace("\n", "").replace("\r", "")
    return re.sub(r'[\/:*?"<>|]', "_", filename)


# 重试装饰器
def async_download_retry_decorator(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        last_exception = None
        retry_times = 20
        for i in range(retry_times):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                Console().print(
                    f"\nError type: {type(e)}: {str(e)}\n", style="bold red"
                )
                Console().print(
                    f"\nRetrying {func.__name__} for the {i+1}/{retry_times} time\n",
                    style="bold yellow",
                )
                await asyncio.sleep(random.randint(1, 5))

                if kwargs and "session" in kwargs:
                    kwargs["session"] = aiohttp.ClientSession()
                    Console().print(
                        f"\n{func.__name__} session has been reset\n",
                        style="bold green",
                    )
        if kwargs and "file_save_path" in kwargs:
            file_path = (
                Path(kwargs["file_save_path"])
                if isinstance(kwargs["file_save_path"], str)
                else kwargs["file_save_path"]
            )
            if file_path.exists():
                logger.error(
                    f"Deleting {file_path.name} because of reached retry limit"
                )
                file_path.unlink()
        if (
            kwargs
            and "session" in kwargs
            and isinstance(kwargs["session"], aiohttp.ClientSession)
        ):
            await kwargs["session"].close()
            Console().print(
                f"\n{func.__name__} session has been closed\n", style="bold green"
            )
        raise last_exception

    return wrapper


@async_download_retry_decorator
async def download_file_async(
    url: str,
    file_save_path: str | Path,
    headers: dict = None,
    mix_size: int = 512,
    session: aiohttp.ClientSession = None,
):
    if isinstance(headers, dict):
        headers = headers.copy()
        headers.update({"User-Agent": UserAgent().random})
    else:
        headers = {
            "User-Agent": UserAgent().random,
            "Referer": "https://www.douyin.com/",
        }

    assert isinstance(url, str), "url must be a string"
    assert isinstance(file_save_path, str) or isinstance(
        file_save_path, Path
    ), "file_save_path must be a string or Path"
    assert isinstance(headers, dict), "headers must be a dictionary"
    assert isinstance(mix_size, int), "mix_size must be an integer"
    assert (
        isinstance(session, aiohttp.ClientSession) or session is None
    ), "session must be an aiohttp.ClientSession or None"

    file_path = (
        Path(file_save_path) if isinstance(file_save_path, str) else file_save_path
    )
    file_mode = "wb"
    resume_header = {}
    if file_path.exists():
        existing_file_size = file_path.stat().st_size
        resume_header = {"Range": f"bytes={existing_file_size}-"}
        file_mode = "ab"
    else:
        existing_file_size = 0
    total_size = 0
    bar = None
    gived_session = (
        True if session and isinstance(session, aiohttp.ClientSession) else False
    )
    if not gived_session:
        # session = aiohttp.ClientSession()
        # local_addr = random.choice(["192.168.100.170", "192.168.0.102"])
        # connector = aiohttp.TCPConnector(local_addr=(local_addr, 0))
        connector = None
        session = aiohttp.ClientSession(connector=connector)
    try:
        async with session.get(url, headers={**headers, **resume_header}) as response:
            total_size = (
                int(response.headers.get("content-length", 0)) + existing_file_size
            )
            assert (
                total_size > mix_size
            ), "File size too small, is this the correct file?"
            bar = tqdm(
                desc=(
                    file_path.name
                    if isinstance(file_save_path, str)
                    else file_save_path.name
                ),
                total=total_size,
                initial=existing_file_size,
                unit="iB",
                unit_scale=True,
                unit_divisor=1024,
                smoothing=0.1,
                colour="green",
            )
            with open(file_save_path, file_mode) as file:
                while True:
                    chunk = await response.content.read(8192)
                    if not chunk:
                        break
                    downloaded_size: int = file.write(chunk)
                    bar.update(downloaded_size)
                    bar.refresh()
            if file_path.stat().st_size == total_size:
                bar.set_postfix_str("Downloaded")

            logger.success(
                f"Downloaded {file_path.name} to {file_path.parent.as_posix()}"
            )
    finally:
        if not gived_session:
            await session.close()
        if bar and isinstance(bar, tqdm):
            bar.close()
    return total_size


def format_digg_count(digg_count: int | float) -> str:
    """将 digg_count 格式化为易读的格式"""
    assert isinstance(digg_count, int) or isinstance(
        digg_count, float
    ), "digg_count must be an integer or float"
    if digg_count >= 10000:
        return f"{digg_count / 10000:.1f}W"  # 例如：15000 -> "1.5W"
    return str(digg_count)


async def download_main(
    data_save_path: str | Path = "data",  # 数据保存路径
    download_quality: int | None = None,  # 下载质量
    downnload_num: int = 0,  # 下载数量
):
    assert (
        isinstance(download_quality, int) or download_quality is None
    ), "download_quality must be an integer or None"
    assert isinstance(data_save_path, str) or isinstance(
        data_save_path, Path
    ), "data_save_path must be a string or Path"
    base_path = (
        Path(data_save_path) if isinstance(data_save_path, str) else data_save_path
    )
    json_files_Generator = base_path.glob("**/*.json")

    session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=600))
    tasks = []

    downnload_num_count = 0

    for json_file in json_files_Generator:
        logger.info(f"loading aweme json data: {json_file.as_posix()}")

        with open(json_file, "r", encoding="utf-8") as f:
            load_json_objs = json.load(f)

        aweme_lists = [
            obj.get("aweme_list") for obj in load_json_objs if obj.get("aweme_list")
        ]

        id_aweme_data_dict_set = list(
            {aweme.get("aweme_id"): aweme}
            for aweme_list in aweme_lists
            for aweme in aweme_list
            if aweme.get("desc") and aweme.get("aweme_id")
        )
        # print(random.choice(id_aweme_data_dict_set))
        for aweme_data in id_aweme_data_dict_set:
            assert isinstance(aweme_data, dict), (
                "Error aweme_data" + f"type : {type(aweme_data)}"
            )

            # 遍历 JSON 数据并下载封面、音乐、视频和图片
            for aweme_id, data in aweme_data.items():
                # 获取 digg_count 值
                digg_count: int = data.get("statistics", {}).get("digg_count", 0)

                nickname: str = data.get("author", {}).get("nickname", "")

                # 格式化 digg_count
                formatted_digg_count_str: str = format_digg_count(digg_count)

                logger.info(
                    f"视频id:{aweme_id}, 点赞数: {digg_count}, nickname: {nickname}"
                )

                # 下载视频文件，并使用视频描述 (desc) 作为文件名
                desc = data.get("desc", "unknown_desc")
                logger.info(f"desc: {desc}")
                sanitized_desc = sanitize_filename(desc)  # 清理不允许的字符

                # 创建文件夹名称，添加格式化后的 digg_count
                aweme_folder = (
                    json_file.parent
                    / f"{sanitized_desc}-{aweme_id}-{formatted_digg_count_str}"
                )

                # 创建各个子文件夹
                cover_folder = aweme_folder / "cover"
                mp3_folder = aweme_folder / "mp3"
                video_folder = aweme_folder / "video"
                images_folder = aweme_folder / "images"

                # 下载封面图片
                cover_obj = data.get("video", {}).get("cover", {})
                if cover_obj:
                    url_list = cover_obj.get("url_list", [])
                    if url_list:
                        if not download_quality:
                            for index, cover_url in enumerate(url_list):
                                if (
                                    cover_url
                                    and isinstance(cover_url, str)
                                    and cover_url.startswith("http")
                                ):
                                    cover_path = cover_folder / f"cover_{index}.jpg"
                                    cover_path.parent.mkdir(parents=True, exist_ok=True)
                                    tasks.append(
                                        download_file_async(
                                            cover_url,
                                            file_save_path=cover_path,
                                            session=session,
                                        )
                                    )
                                    logger.info(
                                        f"added {index+1} cover_url download task: {cover_url}"
                                    )
                        else:
                            cover_url = url_list[download_quality]
                            if (
                                cover_url
                                and isinstance(cover_url, str)
                                and cover_url.startswith("http")
                            ):
                                cover_path = cover_folder / "cover.jpg"
                                cover_path.parent.mkdir(parents=True, exist_ok=True)
                                tasks.append(
                                    download_file_async(
                                        cover_url,
                                        file_save_path=cover_path,
                                        session=session,
                                    )
                                )
                                logger.info(
                                    f"added cover_url download task: {cover_url}"
                                )
                video_obj = data.get("video", {})
                if video_obj:
                    play_addr_obj = video_obj.get("play_addr", {})
                    if play_addr_obj:
                        url_list = play_addr_obj.get("url_list", [])
                        if url_list:
                            if not download_quality:
                                for index, play_addr_url in enumerate(url_list):
                                    if (
                                        play_addr_url
                                        and isinstance(play_addr_url, str)
                                        and play_addr_url.startswith("http")
                                    ):
                                        video_filename = f"{sanitized_desc}_{index}.mp4"
                                        video_path = video_folder / video_filename
                                        video_path.parent.mkdir(
                                            parents=True, exist_ok=True
                                        )
                                        tasks.append(
                                            download_file_async(
                                                play_addr_url,
                                                file_save_path=video_path,
                                                session=session,
                                            )
                                        )
                                        logger.info(
                                            f"added {index+1} play_addr_url download task: {play_addr_url}"
                                        )
                            else:
                                play_addr_url = url_list[download_quality]
                                if (
                                    play_addr_url
                                    and isinstance(play_addr_url, str)
                                    and play_addr_url.startswith("http")
                                ):
                                    video_filename = f"{sanitized_desc}.mp4"
                                    video_path = video_folder / video_filename
                                    video_path.parent.mkdir(parents=True, exist_ok=True)
                                    tasks.append(
                                        download_file_async(
                                            play_addr_url,
                                            file_save_path=video_path,
                                            session=session,
                                        )
                                    )
                                    logger.info(
                                        f"added play_addr_url download task: {play_addr_url}"
                                    )

                # 下载音乐文件
                music_obj = data.get("music", {})
                if music_obj:
                    play_url_obj = music_obj.get("play_url", {})
                    if play_url_obj:
                        url_list = play_url_obj.get("url_list", [])
                        if url_list:
                            if not download_quality:
                                for index, music_uri in enumerate(url_list):
                                    if (
                                        music_uri
                                        and isinstance(music_uri, str)
                                        and music_uri.startswith("http")
                                    ):
                                        music_filename = f"{sanitized_desc}_{index}.mp3"
                                        music_path = mp3_folder / music_filename
                                        music_path.parent.mkdir(
                                            parents=True, exist_ok=True
                                        )
                                        tasks.append(
                                            download_file_async(
                                                music_uri,
                                                file_save_path=music_path,
                                                session=session,
                                            )
                                        )
                                        logger.info(
                                            f"added {index+1} music_uri download task: {music_uri}"
                                        )
                            else:
                                music_uri = url_list[download_quality]
                                if (
                                    music_uri
                                    and isinstance(music_uri, str)
                                    and music_uri.startswith("http")
                                ):
                                    music_filename = f"{sanitized_desc}.mp3"
                                    music_path = mp3_folder / music_filename
                                    music_path.parent.mkdir(parents=True, exist_ok=True)
                                    tasks.append(
                                        download_file_async(
                                            music_uri,
                                            file_save_path=music_path,
                                            session=session,
                                        )
                                    )
                                    logger.info(
                                        f"added music_uri download task: {music_uri}"
                                    )

                # 下载 images
                images = data.get("images")
                if (
                    images
                    and isinstance(images, (list, tuple, set))
                    and len(images) > 0
                ):
                    if not download_quality:
                        for idx, image_url in enumerate(images):
                            if (
                                image_url
                                and isinstance(image_url, str)
                                and image_url.startswith("http")
                            ):
                                image_path = images_folder / f"{desc}_{idx + 1}.jpg"
                                image_path.parent.mkdir(parents=True, exist_ok=True)
                                tasks.append(
                                    download_file_async(
                                        image_url,
                                        file_save_path=image_path,
                                        session=session,
                                    )
                                )
                                logger.info(
                                    f"added image_url download task: {image_url}"
                                )
                    else:
                        image_url = images[download_quality]
                        if (
                            image_url
                            and isinstance(image_url, str)
                            and image_url.startswith("http")
                        ):
                            image_path = images_folder / f"{desc}.jpg"
                            image_path.parent.mkdir(parents=True, exist_ok=True)
                            tasks.append(
                                download_file_async(
                                    image_url,
                                    file_save_path=image_path,
                                    session=session,
                                )
                            )
                            logger.info(f"added image_url download task: {image_url}")

                downnload_num_count += 1
                logger.info(f"downnload_num_count: {downnload_num_count}")
                if downnload_num > 0 and downnload_num_count >= downnload_num:
                    break
            if downnload_num > 0 and downnload_num_count >= downnload_num:
                logger.success(
                    f"downnload_num_count: {downnload_num_count} == {downnload_num}"
                )
                break
    await asyncio.gather(*tasks)

    await session.close()
