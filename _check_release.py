"""检查 Gitee 仓库和 Release 状态"""
import requests

TOKEN = "60102a8720deeb7a15418f41d3004519"
OWNER = "dawalixijie"
REPO = "WenDuo-Roll-Call"

# 1. 检查仓库是否存在
print("=== 1. 检查仓库 ===")
url = f"https://gitee.com/api/v5/repos/{OWNER}/{REPO}"
resp = requests.get(url, params={"access_token": TOKEN}, timeout=15)
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    r = resp.json()
    print(f"  name: {r.get('full_name')}")
    print(f"  private: {r.get('private')}")
else:
    print(resp.text[:300])

# 2. 检查 v2.0.0 release 是否存在
print("\n=== 2. 检查 v2.0.0 Release ===")
url2 = f"https://gitee.com/api/v5/repos/{OWNER}/{REPO}/releases/tags/v2.0.0"
resp2 = requests.get(url2, params={"access_token": TOKEN}, timeout=15)
print(f"Status: {resp2.status_code}")
if resp2.status_code == 200:
    r = resp2.json()
    print(f"  id: {r.get('id')}")
    print(f"  tag: {r.get('tag_name')}")
    assets = r.get("assets", [])
    print(f"  assets: {len(assets)}")
    for a in assets:
        print(f"    - {a.get('name')}")
else:
    print(resp2.text[:300])

# 3. 检查 v3.0.0 tag 是否存在
print("\n=== 3. 检查 v3.0.0 Tag ===")
url3 = f"https://gitee.com/api/v5/repos/{OWNER}/tags"
resp3 = requests.get(url3, params={"access_token": TOKEN}, timeout=15)
print(f"Status: {resp3.status_code}")
if resp3.status_code == 200:
    for t in resp3.json():
        print(f"  - {t.get('name')}")
else:
    print(resp3.text[:300])
