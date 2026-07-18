"""列出 Gitee Release"""
import requests

TOKEN = "60102a8720deeb7a15418f41d3004519"
OWNER = "dawalixijie"
REPO = "WenDuo-Roll-Call"

url = f"https://gitee.com/api/v5/repos/{OWNER}/releases"
resp = requests.get(url, params={"access_token": TOKEN, "page": 1, "per_page": 20}, timeout=15)
print(f"GET Status: {resp.status_code}")
if resp.status_code == 200:
    for r in resp.json():
        rid = r.get("id")
        tag = r.get("tag_name")
        name = r.get("name")
        print(f"  id={rid} tag={tag} name={name}")
else:
    print(resp.text[:500])
