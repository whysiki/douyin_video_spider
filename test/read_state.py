import json
import aiohttp
from aiohttp import ClientSession
from rich import print
import asyncio
from pathlib import Path

# 读取 state.json 文件
with open(Path(__file__).parent.parent / "state.json", "r", encoding="utf-8") as file:
    state_data = json.load(file)

# 提取 cookies
cookies = {
    cookie["name"]: cookie["value"]
    for cookie in state_data["cookies"]
    if cookie["name"]
}

# print(cookies)

# 提取 headers (假设 headers 存储在 localStorage 中)
headers = {
    item["name"]: item["value"]
    for item in state_data["origins"][0]["localStorage"]
    if item["name"]
}

print(list(headers.keys()))
[
    "FeedBackFlag",
    "__tea_cache_tokens_2018",
    "ExitTimestamp",
    "SysInfo",
    "SLARDARdouyin_login_sdk",
    "SEARCH_HISTORY_MS4wLjABAAAAxLv_LDfQo9_WPUhrQNbDNq1BpnxW16kC-Gtl6iP4l6E",
    "is_allow_trust",
    "security-sdk/s_sdk_cert_key",
    "video_can_play_type",
    "xmst",
    "security-sdk/s_sdk_sign_data_key/sso",
    "liveModalTeaLogParams",
    "security-sdk/s_sdk_sign_data_key/login/time",
    "__tea_cache_tokens_6383",
    "player_volume",
    "IS_SUPPORT_HEVC_TEST_1",
    "__msuuid__",
    "__tea_cache_first_1300",
    "SLARDARmfa_web",
    "__tea_cache_first_6383",
    "security-sdk/s_sdk_sign_data_key/web_protect",
    "security-sdk/s_sdk_sign_data_key/sso/time",
    "SLARDARdouyin_web",
    "business/login",
    "SLARDARuc_secure_sdk",
    "SEARCH_HISTORY_guest",
    "HasUserLogin",
    "LoginGuidingStrategyCounter",
    "a11y_device_id",
    "__tea_sdk_ab_version_6383",
    "powerEfficient",
    "user_info",
    "last_login_way",
    "_sds",
    "has_login_show",
    "x-secsdk-csrf-session",
    "https://www.douyin.com-operation",
    "security-sdk/s_sdk_crypt_sdk",
    "security-sdk/s_sdk_sign_data_key/login",
    "=^_^=athena_web_id",
    "PREVIEW_IS_MUTE",
    "__tea_cache_tokens_1300",
    "__tea_cache_first_2018",
    "set_is_allow_trust",
    "web_store_TNC_STORE_V1_1_tnc_config_table_-1",
    "g_ven",
    "LoginGuidingStrategy",
    "HEADER_RECHARGE_GUIDE",
]


# 创建 aiohttp.ClientSession 并传递 cookies 和 headers
async def create_session():
    session = ClientSession(cookies=cookies, headers=headers)
    return session


# 示例异步函数，展示如何使用创建的 session
async def fetch_data(url):
    async with await create_session() as session:
        async with session.get(url) as response:
            return await response.text()


# 示例调用
url = "https://www.example.com"
data = asyncio.run(fetch_data(url))
print(data)
