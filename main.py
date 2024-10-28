from download_videos import download_main
from playwright_dy import save_user_videos_aneme_jsonobjs
import asyncio
from loguru import logger
import shutil  # 用于删除文件夹
import time

logger.add(
    f"logs/log_{time.strftime('%Y-%m-%d', time.localtime())}.log",
    rotation="10 MB",
    retention="10 days",
    level="INFO",
)

# 用户主页链接是抖音用户主页链接, 每行一个链接
user_home_page_urls_strs = """
https://www.douyin.com/user/MS4wLjABAAAAI2E6rxFvVx4Zl-iuLUTw4Z_SR3mDoeWIj38Hady10_M?from_tab_name=main&vid=7430581670090231097
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
shutil.rmtree("testdata", ignore_errors=True)
data_dir = "testdata"

for user_home_page_url in user_home_page_urls:
    save_user_videos_aneme_jsonobjs(
        user_home_page_url, data_save_dir=data_dir, headless=True
    )
    asyncio.run(
        download_main(data_save_path=data_dir, download_quality=-1, download_num=3)
    )  # -1 代表最好的质量
