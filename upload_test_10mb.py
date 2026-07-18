"""测试上传 10MB 文件到 Gitee Release"""
import requests

TOKEN = "60102a8720deeb7a15418f41d3004519"
OWNER = "dawalixijie"
REPO = "WenDuo-Roll-Call"
RELEASE_ID = "752031"
FILE_PATH = "dist-install\\test_10mb.bin"

url = f"https://gitee.com/api/v5/repos/{OWNER}/{REPO}/releases/{RELEASE_ID}/attach_files?access_token={TOKEN}"
file_name = "test_10mb.bin"

with open(FILE_PATH, "rb") as f:
    resp = requests.post(
        url,
        files={"file": (file_name, f, "application/octet-stream")},
        timeout=(30, 120),
    )
    print(f"状态码: {resp.status_code}")
    print(resp.text[:500])
