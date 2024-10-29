import asyncio
from playwright.async_api import async_playwright
from rich import print
import json
import os
import re
from pathlib import Path
from functools import lru_cache
import random
from playwright.async_api import Page, Request, Route
from loguru import logger


async def handle_route_banimg_and_media(route, request):
    # 禁止加载图片和媒体
    if request.resource_type in ["image", "media"]:
        await route.abort()
        logger.debug(f"Abort: {request.url}")
        pass
    else:
        await route.continue_()


async def handle_special_block_urls_keywords(route, request):
    # 特殊关键字拦截
    block_urls_keywords = ["lf-douyin-pc-web", "If9-sec", "bytetos"]
    for keyword in block_urls_keywords:
        keyword = keyword.strip()
        if keyword in request.url:
            await route.abort()
            logger.debug(f"Abort: {request.url}")
            pass
        else:
            await route.continue_()


async def handle_response(response, jsons: list):
    # hook aweme/v1/web/aweme/post 得到视频信息
    if "aweme/v1/web/aweme/post" in response.url:
        try:
            response_json = await response.json()
            jsons.append(response_json)
            logger.debug(f"Hooked: {response.url}")
        except Exception as e:
            logger.error(f"Error processing response: {e}")


async def match_douyin_number(page: Page) -> str:
    # 获取抖音号 正则匹配
    await page.wait_for_selector(
        "#douyin-right-container > div.parent-route-container.route-scroll-container"
    )
    # 包含抖音号的span标签
    text = page.locator(
        "#douyin-right-container > div.parent-route-container.route-scroll-container > div > div > div > div > div > p > span",
        has_text="抖音号",
    )
    douyin_number_tag = await text.inner_text()
    # 匹配抖音号
    # douyin_number = re.search(r"(\d+)", douyin_number_tag).group(1)
    douyin_number = re.sub(r"抖音号[:：]|<!-- -->", "", douyin_number_tag).strip()
    return douyin_number


async def match_name(page: Page) -> str:
    # 获取用户昵称
    name_tag = await page.query_selector(
        "#douyin-right-container > div.parent-route-container.route-scroll-container.IhmVuo1S > div > div > div > div.a3i9GVfe.nZryJ1oM._6lTeZcQP.y5Tqsaqg > div.IGPVd8vQ > div.HjcJQS1Z > h1 > span > span > span > span > span > span"
    )
    name = ""
    if name_tag:
        name = await name_tag.inner_text()
    return name


async def match_expected_works_count(page: Page) -> str:
    # 获取用户作品数量
    await page.wait_for_selector("div.XNarezzx")
    await page.wait_for_selector("span.MNSB3oPV")
    expected_works_count = await page.inner_text("span.MNSB3oPV")
    return (
        expected_works_count
        if isinstance(expected_works_count, str)
        else str(expected_works_count)
    )


async def roll_page_and_get_all_aweme(
    page: Page, jsons: list, expected_works_count: int
) -> list:
    # 滚动页面获取所有作品
    while True:
        scroll_div_li_list = await page.query_selector_all(
            "#douyin-right-container > div.parent-route-container.route-scroll-container.IhmVuo1S > div > div > div > div.XA9ZQ2av > div > div > div.z_YvCWYy.Klp5EcJu > div.N8dcwU0m > div.pCVdP6Bb > ul > li"
        )
        if scroll_div_li_list:
            last_li = scroll_div_li_list[-1]
            await last_li.scroll_into_view_if_needed()
            print("滚动页面 scroll_div_li_list[-1]")
        end_tag = page.locator("div.gqga5U3W > div.E5QmyeTo", has_text="暂时没有更多了")
        current_count = par_jsons(jsons)
        if await end_tag.is_visible():
            print("没有更多了")
            break
        if current_count >= int(expected_works_count):
            print("当前作品数量已经达到总作品数量")
            break
        print(f"当前读取作品数量: {current_count}，总作品数量: {expected_works_count}")


def par_jsons(jsons: list) -> int:
    # 解析jsons 获取作品数量
    aweme_lists = [obj.get("aweme_list") for obj in jsons if obj.get("aweme_list")]
    video_informations = set(
        [
            (aweme.get("aweme_id"), aweme.get("desc"))
            for aweme_list in aweme_lists
            for aweme in aweme_list
            if aweme.get("desc")
        ]
    )
    return len(video_informations)


async def parse_home_page(page: Page, user_home_url: str) -> dict:
    # 解析用户主页, 获取aweme jsons, 抖音号, 用户昵称
    jsons = []
    page.on(
        "response",
        lambda response: asyncio.create_task(handle_response(response, jsons)),
    )
    logger.debug("正在打开对应抖音用户主页")
    await page.goto(
        user_home_url,
        wait_until="domcontentloaded",
        timeout=10000 * 1000,
        referer=page.url,
    )
    douyin_number = await match_douyin_number(page)
    name = await match_name(page)
    expected_works_count = await match_expected_works_count(page)
    logger.info(f"抖音号: {douyin_number}")
    logger.info(f"用户昵称: {name}")
    logger.info(f"总作品数量: {expected_works_count}")
    await roll_page_and_get_all_aweme(page, jsons, expected_works_count)
    return dict(
        jsons=jsons,
        douyin_number=(
            douyin_number if isinstance(douyin_number, str) else str(douyin_number)
        ),
        name=name if isinstance(name, str) else str(name),
    )


async def save_user_videos_aneme_jsonobjs_async(
    user_home_urls: str, data_save_dir: str = "data", headless: bool = None
) -> tuple[str, str, str]:
    datas: list[dict] = await print_aweme_responses(user_home_urls, headless)
    return_datas: list[dict] = []
    for data in datas:
        jsons = data.get("jsons")
        douyin_number = data.get("douyin_number")
        name = data.get("name")
        save_path = Path(
            f"{data_save_dir}/{re.sub(r'[<>:\"/\\|?*]', '', name)}_{re.sub(r'[<>:\"/\\|?*]', '', douyin_number)}/aweme.json"
        )
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "w", encoding="UTF-8") as f:
            logger.success(
                f"抖音{name}_{douyin_number},保存视频anemejsonlist数据到: {save_path.as_posix()}"
            )
            json.dump(jsons, f, indent=4, ensure_ascii=False)
        return_datas.append(
            dict(
                douyin_number=douyin_number,
                name=name,
                save_path=save_path,
            )
        )
    return return_datas


async def print_aweme_responses(
    user_home_urls, headless: bool = None
) -> tuple[str, str, str]:
    async with async_playwright() as p:
        isloaded = True if os.path.exists("state.json") else False
        browser = await p.chromium.launch(
            headless=(
                headless if headless is not None else (True if isloaded else False)
            ),
            args=[
                "--incognito",  # 隐身模式
                "--disable-gpu",  # 禁用 GPU 硬件加速
                # "--no-sandbox",  # 禁用沙盒
                # firefox 配置
                # "-foreground",  # 前台运行
                # "-private",  # 隐身模式
                # "-headless",  # 无头模式
            ],
        )
        if isloaded:
            context = await browser.new_context(storage_state="state.json")
            isloaded = True
        else:
            context = await browser.new_context()
        page = await context.new_page()
        if isloaded:
            # await page.route("**/*", handle_special_block_urls_keywords)
            # await page.route("**/*", handle_route_banimg_and_media)
            pass
        logger.debug("正在打开抖音主页")
        await page.goto(
            "https://www.douyin.com/",
            timeout=10000 * 1000,
            wait_until="domcontentloaded",
        )
        if not isloaded:
            logger.debug("等待用户登录")
            await page.wait_for_selector(
                "div > div:nth-child(8) > div > a > span > img",
                timeout=10000 * 1000,
            )
            logger.debug("登录成功")
        datas: list[dict] = []
        try:
            for future in asyncio.as_completed(
                [
                    parse_home_page(await context.new_page(), user_home_url)
                    for user_home_url in user_home_urls
                ]
            ):
                datas.append(await future)
            await context.storage_state(path="state.json")
            await browser.close()
            return datas
        except Exception as e:
            print(f"Error: {e}")
            if os.path.exists("state.json"):
                acf = input("是否删除state.json文件然后继续(y/n): ")
                if acf == "y":
                    print("删除state.json")
                    os.remove("state.json")
                    print("重试开始")
                    await print_aweme_responses()
                    print("退出")
            raise e
