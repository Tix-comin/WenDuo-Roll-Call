"""上传分卷文件到 Gitee Release"""
import urllib.request
import os
import json
import sys

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
        file_data = f.read()

    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{file_name}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode("utf-8") + file_data + f"\r\n--{boundary}--\r\n".encode("utf-8")

    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "Mozilla/5.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"  成功: {data.get('browser_download_url')}")
    except Exception as e:
        print(f"  失败: {e}")
        sys.exit(1)

print("\n所有分卷上传完成")
