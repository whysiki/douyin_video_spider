import json
import re
from pathlib import Path
import aiohttp
from rich import print
from loguru import logger
from tqdm import tqdm
import asyncio
from fake_useragent import UserAgent
from useful_decorators import async_download_retry_decorator
from useful_tools import sanitize_filename, format_digg_count


@logger.catch
@async_download_retry_decorator(
    retry_times=6,
    sleep_interval_min=1,
    sleep_interval_max=5,
    reset_session_interval=2,
)
async def download_file_async(
    url: str,
    file_save_path: str | Path,
    headers: dict = None,
    mix_size: int = 512,
    session: aiohttp.ClientSession = None,
):
    headers = (
        headers.copy()
        if isinstance(headers, dict)
        else {"User-Agent": UserAgent().random, "Referer": "https://www.douyin.com/"}
    )
    headers.update({"User-Agent": UserAgent().random})

    assert isinstance(url, str), "url must be a string"
    assert isinstance(
        file_save_path, (str, Path)
    ), "file_save_path must be a string or Path"
    assert isinstance(headers, dict), "headers must be a dictionary"
    assert isinstance(mix_size, int), "mix_size must be an integer"
    assert isinstance(
        session, (aiohttp.ClientSession, type(None))
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
    gived_session = bool(session and isinstance(session, aiohttp.ClientSession))
    if not gived_session:
        connector = None
        session = aiohttp.ClientSession(connector=connector)
    try:
        async with session.get(
            url, headers={**headers, **resume_header}, timeout=5
        ) as response:
            total_size = (
                int(response.headers.get("content-length", 0)) + existing_file_size
            )
            # 检查是否是媒体文件
            content_type = response.headers.get("content-type", "")
            if not re.match(r"^video|audio|image", content_type):
                logger.warning(
                    f"Content type is not video/audio/image, is this the correct file? {url} {content_type}"
                )
                raise ValueError(
                    f"Content type is not video/audio/image, is this the correct file? {url} {content_type}"
                )
            if total_size <= mix_size:
                logger.warning(
                    f"File size too small, is this the correct file? {url} {total_size}"
                )
                raise ValueError(
                    f"File size too small, is this the correct file? {url} {total_size}"
                )
            bar = tqdm(
                desc=file_path.name,
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
                    chunk = await response.content.read(1024)
                    logger.debug(f"chunk size: {len(chunk)}")
                    if not chunk:
                        break
                    downloaded_size = file.write(chunk)
                    bar.update(downloaded_size)
                    bar.refresh()
            if file_path.stat().st_size == total_size:
                bar.set_postfix_str("Downloaded")
            logger.success(
                f"Downloaded {file_path.name} to {file_path.parent.as_posix()}"
            )
    finally:
        if (
            not gived_session
            and session
            and isinstance(session, aiohttp.ClientSession)
            and not session.closed
        ):
            await session.close()
        if bar and isinstance(bar, tqdm):
            bar.close()
    return total_size


@logger.catch
async def download_main(
    data_save_path: str | Path = "data",
    download_quality: int | None = None,
    download_num: int = 0,
    semaphore_num: int = 3,
):
    assert isinstance(
        download_quality, (int, type(None))
    ), "download_quality must be an integer or None"
    assert isinstance(
        data_save_path, (str, Path)
    ), "data_save_path must be a string or Path"
    base_path = (
        Path(data_save_path) if isinstance(data_save_path, str) else data_save_path
    )
    json_files_generator = base_path.glob("**/*.json")

    session = aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(connect=5)
    )  # 如果5秒内没有连接成功, 则超时
    tasks = []
    download_num_count = 0

    for json_file in json_files_generator:
        logger.info(f"loading aweme json data: {json_file.as_posix()}")
        with open(json_file, "r", encoding="utf-8") as f:
            load_json_objs = json.load(f)

        aweme_lists = [
            obj.get("aweme_list") for obj in load_json_objs if obj.get("aweme_list")
        ]
        id_aweme_data_dict_set = [
            {aweme.get("aweme_id"): aweme}
            for aweme_list in aweme_lists
            for aweme in aweme_list
            if aweme.get("desc") and aweme.get("aweme_id")
        ]

        for aweme_data in id_aweme_data_dict_set:
            assert isinstance(
                aweme_data, dict
            ), f"Error aweme_data type: {type(aweme_data)}"
            for aweme_id, data in aweme_data.items():
                digg_count = data.get("statistics", {}).get("digg_count", 0)
                nickname = data.get("author", {}).get("nickname", "")
                formatted_digg_count_str = format_digg_count(digg_count)
                logger.info(
                    f"视频id:{aweme_id}, 点赞数: {digg_count}, nickname: {nickname}"
                )

                desc = data.get("desc", "unknown_desc")
                sanitized_desc = sanitize_filename(desc)
                aweme_folder = (
                    json_file.parent
                    / f"{sanitized_desc}-{aweme_id}-{formatted_digg_count_str}"
                )
                cover_folder, mp3_folder, video_folder, images_folder = [
                    aweme_folder / folder
                    for folder in ["cover", "mp3", "video", "images"]
                ]

                await add_download_tasks(
                    data,
                    cover_folder,
                    mp3_folder,
                    video_folder,
                    images_folder,
                    download_quality,
                    sanitized_desc,
                    session,
                    tasks,
                )

                download_num_count += 1
                logger.info(f"download_num_count: {download_num_count}")
                if download_num > 0 and download_num_count >= download_num:
                    logger.success(
                        f"download_num_count: {download_num_count} == {download_num}"
                    )
                    break
            if download_num > 0 and download_num_count >= download_num:
                break
    async with asyncio.Semaphore(semaphore_num):
        await asyncio.gather(*tasks)
    if session and isinstance(session, aiohttp.ClientSession) and not session.closed:
        await session.close()

    print("[green]\n\nAll download tasks are completed\n[/green]")


async def add_download_tasks(
    data,
    cover_folder,
    mp3_folder,
    video_folder,
    images_folder,
    download_quality,
    sanitized_desc,
    session,
    tasks,
):
    await download_cover(data, cover_folder, download_quality, session, tasks)
    await download_video(
        data, video_folder, download_quality, sanitized_desc, session, tasks
    )
    await download_music(
        data, mp3_folder, download_quality, sanitized_desc, session, tasks
    )
    await download_images(
        data, images_folder, download_quality, sanitized_desc, session, tasks
    )


async def download_cover(data, cover_folder, download_quality, session, tasks):
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
                                cover_url, file_save_path=cover_path, session=session
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
                            cover_url, file_save_path=cover_path, session=session
                        )
                    )
                    logger.info(f"added cover_url download task: {cover_url}")


async def download_video(
    data, video_folder, download_quality, sanitized_desc, session, tasks
):
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
                            video_path.parent.mkdir(parents=True, exist_ok=True)
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


async def download_music(
    data, mp3_folder, download_quality, sanitized_desc, session, tasks
):
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
                            music_path.parent.mkdir(parents=True, exist_ok=True)
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
                                music_uri, file_save_path=music_path, session=session
                            )
                        )
                        logger.info(f"added music_uri download task: {music_uri}")


async def download_images(
    data, images_folder, download_quality, sanitized_desc, session, tasks
):
    images = data.get("images")
    if images and isinstance(images, (list, tuple, set)) and len(images) > 0:
        if not download_quality:
            for idx, image_url in enumerate(images):
                if (
                    image_url
                    and isinstance(image_url, str)
                    and image_url.startswith("http")
                ):
                    image_path = images_folder / f"{sanitized_desc}_{idx + 1}.jpg"
                    image_path.parent.mkdir(parents=True, exist_ok=True)
                    tasks.append(
                        download_file_async(
                            image_url, file_save_path=image_path, session=session
                        )
                    )
                    logger.info(f"added image_url download task: {image_url}")
        else:
            image_url = images[download_quality]
            if (
                image_url
                and isinstance(image_url, str)
                and image_url.startswith("http")
            ):
                image_path = images_folder / f"{sanitized_desc}.jpg"
                image_path.parent.mkdir(parents=True, exist_ok=True)
                tasks.append(
                    download_file_async(
                        image_url, file_save_path=image_path, session=session
                    )
                )
                logger.info(f"added image_url download task: {image_url}")
