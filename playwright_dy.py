import asyncio
from playwright.async_api import async_playwright
from rich import print
import json
import os

# 依赖安装，命令行执行以下命令
# pip install playwright
# playwright install firefox
# pip install rich

# 用户主页链接
test_url = "https://www.douyin.com/user/MS4wLjABAAAAnH5exW9sbuKNUVck8jWI6ajeA68coGy2fQ1lR5XOARk?from_tab_name=main"


async def handle_route_banimg_and_media(route, request):
    if request.resource_type in ["image", "media"]:
        await route.abort()
    else:
        await route.continue_()


async def handle_special_block_urls_keywords(route, request):
    block_urls_keywords = ["lf-douyin-pc-web.douyinstatic.com"]
    for keyword in block_urls_keywords:
        if keyword in request.url:
            await route.abort()
        else:
            await route.continue_()


async def handle_response(response):
    if "aweme/v1/web/aweme/post" in response.url:
        try:
            response_json = await response.json()
            jsons.append(response_json)
        except Exception as e:
            print(f"Error processing response: {e}")


async def print_aweme_responses():
    async with async_playwright() as p:
        isloaded = False
        # headless=False 会打开浏览器
        # headless=True 不会打开浏览器
        browser = await p.chromium.launch(
            headless=False,
            args=[
                # "--incognito",  # 隐身模式
                # "--disable-gpu",  # 禁用 GPU 硬件加速
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
        if os.path.exists("state.json"):
            context = await browser.new_context(storage_state="state.json")
            isloaded = True
        else:
            context = await browser.new_context()

        page = await context.new_page()

        page.route("**/*", handle_special_block_urls_keywords)

        jsons = []

        page.on(
            "response", lambda response: asyncio.create_task(handle_response(response))
        )
        try:
            await page.goto("https://www.douyin.com/", timeout=10000 * 1000)
            if not isloaded:
                print("等待用户登录")
                await page.wait_for_selector(
                    "div > div:nth-child(8) > div > a > span > img",
                    timeout=10000 * 1000,
                )
            await page.goto(
                test_url, wait_until="domcontentloaded", timeout=10000 * 1000
            )
            await page.wait_for_selector("div.XNarezzx")
            await page.wait_for_selector("span.MNSB3oPV")
            expected_works_count = await page.inner_text("span.MNSB3oPV")
            print(f"总作品数量: {expected_works_count}")

            while True:
                current_count = par_jsons(jsons)
                if current_count >= int(expected_works_count):
                    break
                previous_height = await page.evaluate("document.body.scrollHeight")
                await page.mouse.wheel(0, previous_height)
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(2000)
                print(
                    f"当前读取作品数量: {current_count}，总作品数量: {expected_works_count}"
                )
                print(f"如果当前作品数量不再增加，请手动滚动页面")

            await context.storage_state(path="state.json")

            await browser.close()
            return jsons
        except Exception as e:
            print(f"Error: {e}")
            await browser.close()
            if os.path.exists("state.json"):
                print("删除state.json")
                os.remove("state.json")
            await print_aweme_responses()


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


if __name__ == "__main__":
    jsons = asyncio.run(print_aweme_responses())
    with open("aweme.json", "w", encoding="UTF-8") as f:
        json.dump(jsons, f, indent=4, ensure_ascii=False)
    load_json_objs = []
    with open("aweme.json", "r", encoding="UTF-8") as f:
        load_json_objs = json.load(f)

    aweme_lists = [
        obj.get("aweme_list") for obj in load_json_objs if obj.get("aweme_list")
    ]

    video_informations = set(
        [
            (aweme.get("aweme_id"), aweme.get("desc"))
            for aweme_list in aweme_lists
            for aweme in aweme_list
            if aweme.get("desc")
        ]
    )
    print(video_informations, f"len: {len(video_informations)}")
