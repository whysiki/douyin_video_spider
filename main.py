from download_videos import download_main
from playwright_dy import save_user_videos_aneme_jsonobjs


user_home_page_urls = [
    "https://www.douyin.com/user/MS4wLjABAAAAnH5exW9sbuKNUVck8jWI6ajeA68coGy2fQ1lR5XOARk?from_tab_name=main"
]

data_dir = "data"

for user_home_page_url in user_home_page_urls:
    save_user_videos_aneme_jsonobjs(user_home_page_url, data_save_dir=data_dir)
    download_main(data_save_path=data_dir)
