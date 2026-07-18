"""测试不同大小文件上传到 Gitee Release"""
import requests
import os

TOKEN = "60102a8720deeb7a15418f41d3004519"
OWNER = "dawalixijie"
REPO = "WenDuo-Roll-Call"
RELEASE_ID = "752031"

url = f"https://gitee.com/api/v5/repos/{OWNER}/{REPO}/releases/{RELEASE_ID}/attach_files?access_token={TOKEN}"

for mb in [20, 30, 40, 50]:
    file_path = f"dist-install\\test_{mb}mb.bin"
    file_name = f"test_{mb}mb.bin"
    print(f"\n测试 {mb}MB...")
    try:
        with open(file_path, "rb") as f:
            resp = requests.post(
                url,
                files={"file": (file_name, f, "application/octet-stream")},
                timeout=(30, 300),
            )
        print(f"  状态码: {resp.status_code}")
        if resp.status_code == 201:
            data = resp.json()
            print(f"  成功: {data.get('name')} ({data.get('size')} bytes)")
        else:
            print(f"  失败: {resp.text[:200]}")
    except Exception as e:
        print(f"  异常: {e}")
