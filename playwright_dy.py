import asyncio
import json
import os
import re
from pathlib import Path
from functools import lru_cache
from typing import List, Dict, Tuple, Any
from playwright.async_api import async_playwright, Page, Request, Route, Response
from loguru import logger
from rich import print


async def handle_route_banimg_and_media(route: Route, request: Request) -> None:
    if request.resource_type in ["image", "media"]:
        await route.abort()
        logger.debug(f"Abort: {request.url}")
    else:
        await route.continue_()


async def handle_special_block_urls_keywords(route: Route, request: Request) -> None:
    block_urls_keywords = ["lf-douyin-pc-web", "If9-sec", "bytetos"]
    if any(keyword in request.url for keyword in block_urls_keywords):
        await route.abort()
        logger.debug(f"Abort: {request.url}")
    else:
        await route.continue_()


async def handle_response(response: Response, jsons: List[Dict[str, Any]]) -> None:
    if "aweme/v1/web/aweme/post" in response.url:
        try:
            response_json = await response.json()
            jsons.append(response_json)
            logger.debug(f"Hooked: {response.url}")
        except Exception as e:
            logger.error(f"Error processing response: {e}")


async def match_douyin_number(page: Page) -> str:
    await page.wait_for_selector(
        "#douyin-right-container > div.parent-route-container.route-scroll-container"
    )
    text = page.locator(
        "#douyin-right-container > div.parent-route-container.route-scroll-container > div > div > div > div > div > p > span",
        has_text="抖音号",
    )
    douyin_number_tag = await text.inner_text()
    douyin_number = re.sub(r"抖音号[:：]|<!-- -->", "", douyin_number_tag).strip()
    return douyin_number


async def match_name(page: Page) -> str:
    name_tag = await page.query_selector(
        "#douyin-right-container > div.parent-route-container.route-scroll-container.IhmVuo1S > div > div > div > div.a3i9GVfe.nZryJ1oM._6lTeZcQP.y5Tqsaqg > div.IGPVd8vQ > div.HjcJQS1Z > h1 > span > span > span > span > span > span"
    )
    return await name_tag.inner_text() if name_tag else ""


async def match_expected_works_count(page: Page) -> str:
    await page.wait_for_selector("div.XNarezzx")
    await page.wait_for_selector("span.MNSB3oPV")
    expected_works_count = await page.inner_text("span.MNSB3oPV")
    return str(expected_works_count)


async def roll_page_and_get_all_aweme(
    page: Page, jsons: List[Dict[str, Any]], expected_works_count: int
) -> None:
    while True:
        scroll_div_li_list = await page.query_selector_all(
            "#douyin-right-container > div.parent-route-container.route-scroll-container.IhmVuo1S > div > div > div > div.XA9ZQ2av > div > div > div.z_YvCWYy.Klp5EcJu > div.N8dcwU0m > div.pCVdP6Bb > ul > li"
        )
        if scroll_div_li_list:
            await scroll_div_li_list[-1].scroll_into_view_if_needed()
            print("滚动页面 scroll_div_li_list[-1]")
        end_tag = page.locator("div.gqga5U3W > div.E5QmyeTo", has_text="暂时没有更多了")
        current_count = par_jsons(jsons)
        if await end_tag.is_visible() or current_count >= int(expected_works_count):
            print(
                "没有更多了"
                if await end_tag.is_visible()
                else "当前作品数量已经达到总作品数量"
            )
            break
        print(f"当前读取作品数量: {current_count}，总作品数量: {expected_works_count}")


def par_jsons(jsons: List[Dict[str, Any]]) -> int:
    aweme_lists = [obj.get("aweme_list") for obj in jsons if obj.get("aweme_list")]
    video_informations = {
        (aweme.get("aweme_id"), aweme.get("desc"))
        for aweme_list in aweme_lists
        for aweme in aweme_list
        if aweme.get("desc")
    }
    return len(video_informations)


async def parse_home_page(
    page: Page, user_home_url: str, isloaded: bool
) -> Dict[str, Any]:
    jsons = []
    page.on(
        "response",
        lambda response: asyncio.create_task(handle_response(response, jsons)),
    )
    if isloaded:
        await page.route("**/*", handle_special_block_urls_keywords)
        await page.route("**/*", handle_route_banimg_and_media)
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
    return {"jsons": jsons, "douyin_number": douyin_number, "name": name}


async def print_aweme_responses(
    user_home_urls: List[str], headless: bool = None
) -> List[Dict[str, Any]]:
    async with async_playwright() as p:
        isloaded = os.path.exists("state.json")
        browser = await p.chromium.launch(
            headless=(headless if headless is not None else isloaded),
            args=["--incognito", "--disable-gpu"],
        )
        context = await browser.new_context(
            storage_state="state.json" if isloaded else None
        )
        if not isloaded:
            page = await context.new_page()
            logger.debug("等待用户登录")
            await page.goto(
                "https://www.douyin.com/",
                timeout=10000 * 1000,
                wait_until="domcontentloaded",
            )
            await page.wait_for_selector(
                "div > div:nth-child(8) > div > a > span > img", timeout=10000 * 1000
            )
            logger.debug("登录成功")
            await context.storage_state(path="state.json")
        datas = []
        try:
            for future in asyncio.as_completed(
                [
                    parse_home_page(await context.new_page(), user_home_url, isloaded)
                    for user_home_url in user_home_urls
                ]
            ):
                datas.append(await future)
            await context.storage_state(path="state.json")
            await browser.close()
            return datas
        except Exception as e:
            logger.error(f"Error: {e}")
            if os.path.exists("state.json"):
                acf = input("是否删除state.json文件然后继续(y/n): ")
                if acf.lower() == "y":
                    logger.debug("删除state.json")
                    os.remove("state.json")
                    logger.debug("重试开始")
                    return await print_aweme_responses(user_home_urls, headless)
            raise e


async def save_user_videos_aneme_jsonobjs_async(
    user_home_urls: List[str], data_save_dir: str = "data", headless: bool = None
) -> List[Dict[str, str]]:
    datas = await print_aweme_responses(user_home_urls, headless)
    return_datas = []
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
            {"douyin_number": douyin_number, "name": name, "save_path": save_path}
        )
    return return_datas
