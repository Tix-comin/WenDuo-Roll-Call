"""上传安装包到 Gitee Release"""
import urllib.request
import urllib.parse
import os
import json

TOKEN = "60102a8720deeb7a15418f41d3004519"
OWNER = "dawalixijie"
REPO = "WenDuo-Roll-Call"
RELEASE_ID = "752031"
FILE_PATH = "dist-install\\WenDuo-Roll-Call-Setup-v2.0.0.exe"

url = f"https://gitee.com/api/v5/repos/{OWNER}/{REPO}/releases/{RELEASE_ID}/attach_files?access_token={TOKEN}"

boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
file_name = os.path.basename(FILE_PATH)
file_size = os.path.getsize(FILE_PATH)

print(f"上传文件: {file_name} ({file_size / 1024 / 1024:.2f} MB)")
print(f"目标: {url.split('?')[0]}")

# 构建 multipart body
with open(FILE_PATH, "rb") as f:
    file_data = f.read()

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
        print("上传成功:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
except Exception as e:
    print(f"上传失败: {e}")
    raise
