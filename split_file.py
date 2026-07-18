"""把安装包分卷成指定大小"""
import os
import sys

src = "dist-install\\WenDuo-Roll-Call-Setup-v2.0.0.exe"
chunk_size = 90 * 1024 * 1024  # 90MB

if not os.path.exists(src):
    print(f"文件不存在: {src}")
    sys.exit(1)

size = os.path.getsize(src)
base = os.path.splitext(src)[0]

print(f"源文件: {src} ({size / 1024 / 1024:.2f} MB)")
print(f"分卷大小: {chunk_size / 1024 / 1024:.0f} MB")

with open(src, "rb") as f:
    part = 1
    while True:
        data = f.read(chunk_size)
        if not data:
            break
        part_name = f"{base}.part{part:03d}"
        with open(part_name, "wb") as out:
            out.write(data)
        print(f"  生成: {os.path.basename(part_name)} ({len(data) / 1024 / 1024:.2f} MB)")
        part += 1

print(f"共分卷: {part - 1} 个")
