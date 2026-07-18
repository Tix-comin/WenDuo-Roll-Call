"""生成分卷并上传到 Gitee Release（替换旧的）"""
import os
import sys
import time
import requests

TOKEN = "60102a8720deeb7a15418f41d3004519"
OWNER = "dawalixijie"
REPO = "WenDuo-Roll-Call"
RELEASE_ID = "752031"
SRC = r"d:\桌面\点名器\dist-install\WenDuo-Roll-Call-Setup-v2.0.0.exe"
CHUNK_SIZE = 30 * 1024 * 1024
MAX_RETRIES = 10

base = os.path.splitext(SRC)[0]

# 1. 先删除旧的分卷附件
print("正在删除旧的分卷附件...")
base_name = os.path.basename(base)
pattern_prefix = base_name + ".part"
list_url = f"https://gitee.com/api/v5/repos/{OWNER}/{REPO}/releases/{RELEASE_ID}?access_token={TOKEN}"
resp = requests.get(list_url, timeout=15)
if resp.status_code == 200:
    assets = resp.json().get("assets", [])
    for a in assets:
        name = a.get("name", "")
        if name.startswith(pattern_prefix):
            aid = a.get("id") or a.get("gid") or a.get("asset_id")
            if aid is None:
                print(f"  跳过 {name}（无 id 字段），可用键: {list(a.keys())}")
                continue
            del_url = f"https://gitee.com/api/v5/repos/{OWNER}/{REPO}/releases/{RELEASE_ID}/attach_files/{aid}?access_token={TOKEN}"
            r = requests.delete(del_url, timeout=15)
            print(f"  删除 {name}: {r.status_code}")
else:
    print(f"  获取附件列表失败: {resp.status_code}")

# 2. 生成分卷
parts = []
with open(SRC, "rb") as f:
    i = 1
    while True:
        data = f.read(CHUNK_SIZE)
        if not data:
            break
        part_path = f"{base}.part{i:03d}"
        with open(part_path, "wb") as out:
            out.write(data)
        parts.append(part_path)
        print(f"生成分卷: {os.path.basename(part_path)} ({len(data)/1024/1024:.2f} MB)")
        i += 1

print(f"\n共分卷 {len(parts)} 个，开始上传...")

# 3. 逐个上传
url = f"https://gitee.com/api/v5/repos/{OWNER}/{REPO}/releases/{RELEASE_ID}/attach_files?access_token={TOKEN}"
for part_path in parts:
    file_name = os.path.basename(part_path)
    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\n上传 {file_name}，第 {attempt}/{MAX_RETRIES} 次...")
        try:
            with open(part_path, "rb") as f:
                resp = requests.post(
                    url,
                    files={"file": (file_name, f, "application/octet-stream")},
                    timeout=(30, 900),
                )
            if resp.status_code == 201:
                data = resp.json()
                print(f"  成功: {data.get('browser_download_url')}")
                break
            else:
                print(f"  失败: {resp.status_code} {resp.text[:200]}")
        except Exception as e:
            print(f"  异常: {e}")
        if attempt < MAX_RETRIES:
            time.sleep(10)
    else:
        print(f"  {file_name} 上传最终失败")
        sys.exit(1)

print("\n所有分卷上传完成")
