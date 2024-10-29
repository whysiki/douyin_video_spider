from download_videos import download_main
from playwright_dy import (
    save_user_videos_aneme_jsonobjs_async,
)
import asyncio
from loguru import logger
import shutil  # 用于删除文件夹
import time
from rich import print

logger.add(
    f"logs/log_{time.strftime('%Y-%m-%d', time.localtime())}.log",
    rotation="10 MB",
    retention="10 days",
    level="INFO",
)

# 用户主页链接是抖音用户主页链接, 每行一个链接
user_home_page_urls_strs = """
https://www.douyin.com/user/MS4wLjABAAAAI2E6rxFvVx4Zl-iuLUTw4Z_SR3mDoeWIj38Hady10_M?from_tab_name=main&vid=7430581670090231097
https://www.douyin.com/user/MS4wLjABAAAAjDBNeFQqzBbbOuZP1ZOeP4ALuxrBoWH8O0fx9Epetec?from_tab_name=main&vid=7428813867314187555
https://www.douyin.com/user/MS4wLjABAAAAWxzfIxWGMTIPDv3aD2eiJYnskDyf_dQN-ST5tbpv5M2dorEFfKdayfErIA7sf-yC?from_tab_name=main&vid=7430297272526654756
""".strip()


user_home_page_urls = list(
    url.strip()
    for url in user_home_page_urls_strs.split("\n")
    if len(url.strip()) > 0 and url.strip().startswith("http")
)

# 数据保存目录
# 生成的目录结构如下:
# - f"data_dir"
# - - f"{username}_{douyin_number}"
# - - - aweme.json
# - - - f"{sanitized_desc}-{aweme_id}-{formatted_digg_count_str}"
# - - - - video
# - - - - mp3
# - - - - cover

# 删除之前的数据
shutil.rmtree("datatest", ignore_errors=True)
data_dir = "datatest"
if __name__ == "__main__":
    return_datas = asyncio.run(
        save_user_videos_aneme_jsonobjs_async(
            user_home_page_urls, data_dir, headless=True
        )
    )
    print(return_datas)
