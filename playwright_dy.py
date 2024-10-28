import asyncio
from playwright.async_api import async_playwright
from rich import print
import json
import os
import re
from pathlib import Path
from functools import lru_cache
import random

# 依赖安装，命令行执行以下命令
# pip install playwright
# playwright install firefox
# pip install rich


async def handle_route_banimg_and_media(route, request):
    if request.resource_type in ["image", "media"]:
        await route.abort()
        print(f"Blocked: {request.url}")
        pass
    else:
        await route.continue_()


async def handle_special_block_urls_keywords(route, request):
    block_urls_keywords = ["lf-douyin-pc-web", "If9-sec", "bytetos"]
    for keyword in block_urls_keywords:
        keyword = keyword.strip()
        if keyword in request.url:
            await route.abort()
            print(f"Blocked: {request.url}")
            pass
        else:
            await route.continue_()


async def print_aweme_responses(
    user_home_url, headless: bool = None
) -> tuple[str, str, str]:
    async with async_playwright() as p:
        isloaded = True if os.path.exists("state.json") else False
        # headless=False 会打开浏览器
        # headless=True 不会打开浏览器
        browser = await p.chromium.launch(
            headless=(
                headless if headless is not None else (True if isloaded else False)
            ),
            args=[
                "--incognito",  # 隐身模式
                "--disable-gpu",  # 禁用 GPU 硬件加速
                # "--no-sandbox",  # 禁用沙盒
                # "--remote-debugging-port=9222",  # 启用远程调试
                # "--window-size=1280,800",  # 设置窗口大小
                # firefox 配置
                # "-foreground",  # 前台运行
                # "-private",  # 隐身模式
                # "-headless",  # 无头模式
            ],
            # devtools=True,
            # ignore_default_args=True,
        )
        if isloaded:
            context = await browser.new_context(storage_state="state.json")
            isloaded = True
        else:
            context = await browser.new_context()

        page = await context.new_page()

        if isloaded:
            await page.route("**/*", handle_special_block_urls_keywords)
            await page.route("**/*", handle_route_banimg_and_media)
            pass
        jsons = []

        async def handle_response(response):
            if "aweme/v1/web/aweme/post" in response.url:
                try:
                    response_json = await response.json()
                    jsons.append(response_json)
                except Exception as e:
                    print(f"Error processing response: {e}")

        page.on(
            "response", lambda response: asyncio.create_task(handle_response(response))
        )
        try:
            print("正在打开抖音主页")
            await page.goto(
                "https://www.douyin.com/",
                timeout=10000 * 1000,
                wait_until="domcontentloaded",
            )
            print("正在打开用户主页")
            await page.goto(
                user_home_url, wait_until="domcontentloaded", timeout=10000 * 1000
            )
            if not isloaded:
                print("等待用户登录")
                await page.wait_for_selector(
                    "div > div:nth-child(8) > div > a > span > img",
                    timeout=10000 * 1000,
                )

            print("登录成功")

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
            douyin_number = re.sub(
                r"抖音号[:：]|<!-- -->", "", douyin_number_tag
            ).strip()

            print(f"抖音号: {douyin_number}")

            # 获取用户昵称
            name_tag = await page.query_selector(
                "#douyin-right-container > div.parent-route-container.route-scroll-container.IhmVuo1S > div > div > div > div.a3i9GVfe.nZryJ1oM._6lTeZcQP.y5Tqsaqg > div.IGPVd8vQ > div.HjcJQS1Z > h1 > span > span > span > span > span > span"
            )
            name = ""
            if name_tag:
                name = await name_tag.inner_text()
                print(f"用户昵称: {name}")

            await page.wait_for_selector("div.XNarezzx")
            await page.wait_for_selector("span.MNSB3oPV")
            expected_works_count = await page.inner_text("span.MNSB3oPV")
            print(f"总作品数量: {expected_works_count}")
            while True:
                scroll_div_li_list = await page.query_selector_all(
                    "#douyin-right-container > div.parent-route-container.route-scroll-container.IhmVuo1S > div > div > div > div.XA9ZQ2av > div > div > div.z_YvCWYy.Klp5EcJu > div.N8dcwU0m > div.pCVdP6Bb > ul > li"
                )
                if scroll_div_li_list:
                    last_li = scroll_div_li_list[-1]
                    await last_li.scroll_into_view_if_needed()
                    print("滚动页面 scroll_div_li_list[-1]")
                end_tag = page.locator(
                    "div.gqga5U3W > div.E5QmyeTo", has_text="暂时没有更多了"
                )
                current_count = par_jsons(jsons)
                if await end_tag.is_visible():
                    print("没有更多了")
                    break
                if current_count >= int(expected_works_count):
                    print("当前作品数量已经达到总作品数量")
                    break
                print(
                    f"当前读取作品数量: {current_count}，总作品数量: {expected_works_count}"
                )
            await context.storage_state(path="state.json")

            await browser.close()
            return (
                jsons,
                douyin_number if isinstance(douyin_number, str) else str(douyin_number),
                name,
            )
        except Exception as e:
            print(f"Error: {e}")
            await browser.close()
            # 确认

            if os.path.exists("state.json"):
                acf = input("是否删除state.json文件然后继续(y/n): ")
                if acf == "y":
                    print("删除state.json")
                    os.remove("state.json")
            print("重试")
            await print_aweme_responses()
            print("退出")


def par_jsons(jsons: list) -> int:
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


def save_user_videos_aneme_jsonobjs(
    user_home_url: str, data_save_dir: str = "data", headless: bool = None
) -> tuple[str, str, str]:
    jsons, douyin_number, name = asyncio.run(
        print_aweme_responses(user_home_url, headless)
    )
    save_path = Path(
        f"{data_save_dir}/{re.sub(r'[<>:"/\\|?*]', '', name)}_{re.sub(r'[<>:"/\\|?*]', '', douyin_number)}/aweme.json"
    )
    save_path.parent.mkdir(parents=True, exist_ok=True)
    with open(save_path, "w", encoding="UTF-8") as f:
        json.dump(jsons, f, indent=4, ensure_ascii=False)
    return jsons, douyin_number, name


async def save_user_videos_aneme_jsonobjs_async(
    user_home_url: str, data_save_dir: str = "data", headless: bool = None
) -> tuple[str, str, str]:
    jsons, douyin_number, name = await print_aweme_responses(user_home_url, headless)
    save_path = Path(
        f"{data_save_dir}/{re.sub(r'[<>:"/\\|?*]', '', name)}_{re.sub(r'[<>:"/\\|?*]', '', douyin_number)}/aweme.json"
    )
    save_path.parent.mkdir(parents=True, exist_ok=True)
    with open(save_path, "w", encoding="UTF-8") as f:
        json.dump(jsons, f, indent=4, ensure_ascii=False)
    return jsons, douyin_number, name


# if __name__ == "__main__":
#     # 用户主页链接
#     user_home_url = "https://www.douyin.com/user/MS4wLjABAAAAnH5exW9sbuKNUVck8jWI6ajeA68coGy2fQ1lR5XOARk?from_tab_name=main"
#     jsons, douyin_number, name = asyncio.run(print_aweme_responses(user_home_url))
#     save_path = Path(f"data/{name}_{douyin_number}/aweme.json")
#     save_path.parent.mkdir(parents=True, exist_ok=True)
#     with open(save_path, "w", encoding="UTF-8") as f:
#         json.dump(jsons, f, indent=4, ensure_ascii=False)
#     # load_json_objs = jsons
#     # aweme_lists = [
#     #     obj.get("aweme_list") for obj in load_json_objs if obj.get("aweme_list")
#     # ]
#     # video_informations = set(
#     #     [
#     #         (aweme.get("aweme_id"), aweme.get("desc"))
#     #         for aweme_list in aweme_lists
#     #         for aweme in aweme_list
#     #         if aweme.get("desc")
#     #     ]
#     # )
#     # print(video_informations, f"len: {len(video_informations)}")
