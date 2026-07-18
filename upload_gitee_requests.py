"""使用 requests 上传分卷到 Gitee Release"""
import os
import json
import requests

TOKEN = "60102a8720deeb7a15418f41d3004519"
OWNER = "dawalixijie"
REPO = "WenDuo-Roll-Call"
RELEASE_ID = "752031"

files = [
    "dist-install\\WenDuo-Roll-Call-Setup-v2.0.0.part001",
    "dist-install\\WenDuo-Roll-Call-Setup-v2.0.0.part002",
]

url = f"https://gitee.com/api/v5/repos/{OWNER}/{REPO}/releases/{RELEASE_ID}/attach_files?access_token={TOKEN}"

for file_path in files:
    if not os.path.exists(file_path):
        print(f"文件不存在: {file_path}")
        continue

    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    print(f"\n上传: {file_name} ({file_size / 1024 / 1024:.2f} MB)")

    with open(file_path, "rb") as f:
        try:
            resp = requests.post(
                url,
                files={"file": (file_name, f, "application/octet-stream")},
                timeout=(30, 600),
            )
            print(f"  状态码: {resp.status_code}")
            if resp.status_code == 201:
                data = resp.json()
                print(f"  成功: {data.get('browser_download_url')}")
            else:
                print(f"  失败: {resp.text[:500]}")
        except Exception as e:
            print(f"  异常: {e}")
