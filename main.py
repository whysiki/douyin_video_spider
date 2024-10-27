from download_videos import download_main
from playwright_dy import save_user_videos_aneme_jsonobjs
import asyncio

# 用户主页链接是抖音用户主页链接
user_home_page_urls = [
    "https://www.douyin.com/user/MS4wLjABAAAAnH5exW9sbuKNUVck8jWI6ajeA68coGy2fQ1lR5XOARk?from_tab_name=main"
]

# 数据保存目录
# 生成的目录结构如下:
# - f"data_dir"
# - - f"{username}_{douyin_number}"
# - - - aweme.json
# - - - f"{digg_count}-{aweme_id}-{formatted_digg_count_str}"
# - - - - video
# - - - - mp3
# - - - - cover
data_dir = "data"

for user_home_page_url in user_home_page_urls:
    save_user_videos_aneme_jsonobjs(user_home_page_url, data_save_dir=data_dir)
    asyncio.run(download_main(data_save_path=data_dir))
