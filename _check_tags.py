"""检查 Gitee Tags 并尝试创建 Release"""
import requests

TOKEN = "60102a8720deeb7a15418f41d3004519"
OWNER = "dawalixijie"
REPO = "WenDuo-Roll-Call"

# 1. 检查 tags（修正路径）
print("=== 1. 列出 Tags ===")
url_tags = f"https://gitee.com/api/v5/repos/{OWNER}/{REPO}/tags"
resp = requests.get(url_tags, params={"access_token": TOKEN}, timeout=15)
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    for t in resp.json():
        print(f"  - {t.get('name')}")
else:
    print(resp.text[:300])

# 2. 尝试创建 Release（多种方式）
print("\n=== 2. 创建 v3.0.0 Release ===")
url_release = f"https://gitee.com/api/v5/repos/{OWNER}/{REPO}/releases"
data = {
    "access_token": TOKEN,
    "tag_name": "v3.0.0",
    "name": "v3.0.0",
    "body": "v3.0.0 release",
    "target_commitish": "master",
}

# 方式 A: 标准 form data
print("--- 方式A: form data ---")
resp = requests.post(url_release, data=data, timeout=30)
print(f"Status: {resp.status_code}")
print(resp.text[:300])

if resp.status_code != 201:
    # 方式 B: query params + json body
    print("--- 方式B: query + json ---")
    resp = requests.post(
        url_release,
        params={"access_token": TOKEN},
        json={
            "tag_name": "v3.0.0",
            "name": "v3.0.0",
            "body": "v3.0.0 release",
            "target_commitish": "master",
        },
        timeout=30,
    )
    print(f"Status: {resp.status_code}")
    print(resp.text[:300])

if resp.status_code == 201:
    r = resp.json()
    print(f"\nRelease ID: {r.get('id')}")
