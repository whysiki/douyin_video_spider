import requests
from fake_useragent import UserAgent
from rich import print

remoteapi = "http://124.70.100.14:61188"

endpoint = "/api/douyin/web/fetch_user_post_videos"


test_url = "https://www.douyin.com/user/MS4wLjABAAAANPb3sb-P2SwTU6rGLnLppoHAAMVniLwq4V8zFhMS_No?from_tab_name=main"

# 用途:
# 获取用户主页作品数据
# 参数:
# sec_user_id: 用户sec_user_id
# max_cursor: 最大游标
# count: 最大数量
# 返回:
# 用户作品数据


endpoint2 = "/api/douyin/web/get_sec_user_id"
# 用途:
# 提取单个用户id
# 参数:
# url: 用户主页链接
# 返回:
# 用户sec_user_id

sec_user_id = requests.get(
    remoteapi + endpoint2,
    params={"url": test_url},
).json()["data"]
print(sec_user_id)

# max_cursor = 0
# max_count = 20

url = remoteapi + endpoint

ua = UserAgent()
headers = {"User-Agent": ua.random}

response = requests.get(url, headers=headers, params={"sec_user_id": sec_user_id})
print(response.json())
