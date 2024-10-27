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
    """移除文件名中不允许的字符，包括换行符"""
    filename = filename.replace("\n", "").replace("\r", "")
    return re.sub(r'[\/:*?"<>|]', "_", filename)


# 重试装饰器
def async_retry_decorator(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        last_exception = None
        retry_times = 3
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
        raise last_exception

    return wrapper


@async_retry_decorator
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
    finally:
        if not gived_session:
            await session.close()

        if bar and isinstance(bar, tqdm):
            # bar.clear()
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


async def main():
    base_path = Path("data")

    json_files_Generator = base_path.glob("**/*.json")

    session = aiohttp.ClientSession()
    tasks = []
    for json_file in json_files_Generator:
        print(f"loading aweme json data: {json_file.as_posix()}")

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

                print(f"视频id:{aweme_id}, 点赞数: {digg_count}, nickname: {nickname}")

                # 创建文件夹名称，添加格式化后的 digg_count
                aweme_folder = (
                    json_file.parent
                    / f"{digg_count}-{aweme_id}-{formatted_digg_count_str}"
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
                        # cover_url = url_list[-1]
                        for index, cover_url in enumerate(url_list):
                            cover_path = cover_folder / f"cover_{index}.jpg"
                            cover_path.parent.mkdir(parents=True, exist_ok=True)
                            tasks.append(
                                download_file_async(
                                    cover_url,
                                    cover_path,
                                    session=session,
                                )
                            )
                            print(
                                f"added {index+1} cover_url download task: {cover_url}"
                            )
                # 下载视频文件，并使用视频描述 (desc) 作为文件名
                desc = data.get("desc", "unknown_desc")
                print(f"desc: {desc}")
                sanitized_desc = sanitize_filename(desc)  # 清理不允许的字符
                #
                video_obj = data.get("video", {})
                if video_obj:
                    play_addr_obj = video_obj.get("play_addr", {})
                    if play_addr_obj:
                        url_list = play_addr_obj.get("url_list", [])
                        if url_list:
                            for index, play_addr_url in enumerate(url_list):
                                video_filename = f"{sanitized_desc}_{index}.mp4"
                                video_path = video_folder / video_filename
                                video_path.parent.mkdir(parents=True, exist_ok=True)
                                tasks.append(
                                    download_file_async(
                                        play_addr_url,
                                        video_path,
                                        session=session,
                                    )
                                )
                                print(
                                    f"added {index+1} play_addr_url download task: {play_addr_url}"
                                )

                # 下载音乐文件
                music_obj = data.get("music", {})
                if music_obj:
                    play_url_obj = music_obj.get("play_url", {})
                    if play_url_obj:
                        url_list = play_url_obj.get("url_list", [])
                        if url_list:
                            for index, music_uri in enumerate(url_list):
                                music_filename = f"{sanitized_desc}_{index}.mp3"
                                music_path = mp3_folder / music_filename
                                music_path.parent.mkdir(parents=True, exist_ok=True)
                                tasks.append(
                                    download_file_async(
                                        music_uri,
                                        music_path,
                                        session=session,
                                    )
                                )
                                print(
                                    f"added {index+1} music_uri download task: {music_uri}"
                                )

                # 下载 images
                images = data.get("images")
                if images:  # 只在 images 不为 null 时下载
                    for idx, image_url in enumerate(images):
                        image_path = images_folder / f"{desc}_{idx + 1}.jpg"
                        image_path.parent.mkdir(parents=True, exist_ok=True)
                        tasks.append(
                            download_file_async(
                                image_url,
                                image_path,
                                session=session,
                            )
                        )
                        print(f"added image_url download task: {image_url}")

                break  # 测试

            break  # 测试

    await asyncio.gather(*tasks)

    await session.close()


if __name__ == "__main__":

    asyncio.run(main())
