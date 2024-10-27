from download_videos import download_main
from playwright_dy import save_user_videos_aneme_jsonobjs
import asyncio
from loguru import logger

# import os

logger.add("logs/log.log", rotation="10 MB", retention="10 days", level="DEBUG")

# 用户主页链接是抖音用户主页链接
user_home_page_urls = [
    "https://www.douyin.com/user/MS4wLjABAAAAxGBsTN_-uPIoxf31ki3XR74ubWdN97HHXJYGIki4dmpXNVrZ-NBhvBi2m07P29yP?from_tab_name=main&vid=7429654578896833818"
]
# 数据保存目录
# 生成的目录结构如下:
# - f"data_dir"
# - - f"{username}_{douyin_number}"
# - - - aweme.json
# - - - f"{sanitized_desc}-{aweme_id}-{formatted_digg_count_str}"
# - - - - video
# - - - - mp3
# - - - - cover

data_dir = "data"

for user_home_page_url in user_home_page_urls:
    save_user_videos_aneme_jsonobjs(
        user_home_page_url, data_save_dir=data_dir, headless=False
    )
    asyncio.run(
        download_main(data_save_path=data_dir, download_quality=-1, download_num=10)
    )  # -1 代表最好的质量
