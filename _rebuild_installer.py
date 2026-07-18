"""重新打包安装程序（包含最新主程序）"""
import os
import sys
import zipfile
import subprocess
import shutil

ROOT = r"d:\桌面\点名器"
DIST = os.path.join(ROOT, "dist-install")
payload_stage = os.path.join(DIST, "_payload_stage")
payload_zip = os.path.join(ROOT, "payload.zip")

if os.path.exists(payload_zip):
    os.remove(payload_zip)
with zipfile.ZipFile(payload_zip, "w", zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(payload_stage):
        for f in files:
            full = os.path.join(root, f)
            rel = os.path.relpath(full, payload_stage)
            zf.write(full, rel)
print("payload.zip:", f"{os.path.getsize(payload_zip) / 1024 / 1024:.2f} MB")

cmd = [
    sys.executable, "-m", "PyInstaller",
    "--onefile", "--windowed",
    "--name", "闻铎点名器 安装程序",
    "--icon", os.path.join(ROOT, "assets", "app_icon.ico"),
    "--add-data", f"{payload_zip};.",
    "--add-data", f"{os.path.join(ROOT, 'assets', 'app_icon.ico')};.",
    os.path.join(ROOT, "setup_installer.py"),
]
r = subprocess.run(cmd, cwd=ROOT)
if r.returncode != 0:
    print("installer build failed")
    sys.exit(1)

src = os.path.join(ROOT, "dist", "闻铎点名器 安装程序.exe")
dst = os.path.join(DIST, "闻铎点名器 安装程序.exe")
shutil.copyfile(src, dst)
print("installer:", f"{os.path.getsize(dst) / 1024 / 1024:.2f} MB")

# 同步一份带版本号的命名，方便分卷上传
dst2 = os.path.join(DIST, "WenDuo-Roll-Call-Setup-v3.0.2.exe")
shutil.copyfile(dst, dst2)
print("done")
