"""创建 Gitee v3.0.0 Release - 尝试多种方式"""
import requests

TOKEN = "60102a8720deeb7a15418f41d3004519"
OWNER = "dawalixijie"
REPO = "WenDuo-Roll-Call"

url = f"https://gitee.com/api/v5/repos/{OWNER}/releases"

# 方式1: JSON body
print("=== 方式1: JSON body ===")
data = {
    "tag_name": "v3.0.0",
    "name": "闻铎点名器 v3.0.0",
    "body": "## v3.0.0 更新内容\n\n- 移除所有 emoji 图标，应用 Apple 设计风格\n- 实现 Gitee 分卷并发下载（3 并发）\n- 下载速度提升约 3 倍\n- GitHub/Gitee 双端同步",
    "target_commitish": "master",
}
resp = requests.post(url, params={"access_token": TOKEN}, json=data, timeout=30)
print(f"Status: {resp.status_code}")
print(resp.text[:500])

if resp.status_code != 201:
    # 方式2: form data
    print("\n=== 方式2: form data ===")
    resp = requests.post(url, data={"access_token": TOKEN, **data}, timeout=30)
    print(f"Status: {resp.status_code}")
    print(resp.text[:500])

if resp.status_code == 201:
    r = resp.json()
    print(f"\nRelease ID: {r.get('id')}")
    print(f"URL: {r.get('html_url')}")
