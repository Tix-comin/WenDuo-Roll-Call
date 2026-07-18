"""
闻铎点名器 - 安装包一键构建脚本
流程：
  1. 打包 uninstaller.py -> dist-install/uninstall.exe
  2. 将主程序、uninstall.exe 和其他资源打包为 payload.zip
  3. 打包 setup_installer.py 并嵌入 payload.zip -> 闻铎点名器 安装程序.exe
"""
import os
import sys
import shutil
import zipfile
import subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "dist-install")  # 本脚本输出目录
os.makedirs(DIST, exist_ok=True)


def run_pyinstaller(args, desc):
    print(f"\n======================================")
    print(f"  {desc}")
    print(f"======================================")
    cmd = [sys.executable, "-m", "PyInstaller"] + args
    print(">>", " ".join(cmd))
    r = subprocess.run(cmd, cwd=ROOT)
    if r.returncode != 0:
        raise RuntimeError(f"{desc} 失败，退出码 {r.returncode}")


def zip_dir(src_dir, zip_path, base_dir_name=""):
    """把 src_dir 下所有文件压入 zip_path（可选放到 zip 的子目录 base_dir_name）"""
    print(f"  压缩 {src_dir} -> {zip_path}")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(src_dir):
            for f in files:
                full = os.path.join(root, f)
                rel = os.path.relpath(full, src_dir)
                if base_dir_name:
                    arcname = os.path.join(base_dir_name, rel)
                else:
                    arcname = rel
                zf.write(full, arcname)
    size = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"  完成 ({size:.2f} MB)")


# ---------- 1. 打包 uninstaller ----------
run_pyinstaller(
    [
        "--onefile", "--windowed",
        "--name", "uninstall",
        "--icon", os.path.join(ROOT, "assets", "app_icon.ico"),
        os.path.join(ROOT, "uninstaller.py"),
    ],
    "打包卸载程序",
)
uninstall_exe = os.path.join(ROOT, "dist", "uninstall.exe")
assert os.path.exists(uninstall_exe), "uninstall.exe 未生成"


# ---------- 2. 组装 payload.zip ----------
print("\n======================================")
print("  组装 payload.zip")
print("======================================")

payload_stage = os.path.join(DIST, "_payload_stage")
os.makedirs(payload_stage, exist_ok=True)

# 复制主程序
main_exe = os.path.join(ROOT, "dist", "闻铎点名器.exe")
if not os.path.exists(main_exe):
    # 可能还叫 WenDuoPicker.exe
    alt = os.path.join(ROOT, "dist", "WenDuoPicker.exe")
    if os.path.exists(alt):
        main_exe = alt
assert os.path.exists(main_exe), "主程序 闻铎点名器.exe 不存在，请先运行 build2.py"

shutil.copy(main_exe, os.path.join(payload_stage, "闻铎点名器.exe"))
shutil.copy(uninstall_exe, os.path.join(payload_stage, "uninstall.exe"))

# 复制图标资源（用于安装后可能的关联）
os.makedirs(os.path.join(payload_stage, "assets"), exist_ok=True)
shutil.copy(os.path.join(ROOT, "assets", "app_icon.ico"),
            os.path.join(payload_stage, "assets", "app_icon.ico"))

APP_VERSION = "3.0.2"
INSTALLER_NAME = f"WenDuo-Roll-Call-Setup-v{APP_VERSION}.exe"

# 写入 README
with open(os.path.join(payload_stage, "readme.txt"), "w", encoding="utf-8") as f:
    f.write(f"闻铎点名器 v{APP_VERSION}\n")
    f.write("开发者: Tix comin\n")
    f.write("联系邮箱: dwlxjjtz@qq.com\n")
    f.write(f"\n更新日志 v{APP_VERSION}:\n")
    f.write("- 统一使用 Lucide SVG 线性图标，移除 emoji/中文图标\n")
    f.write("- 设置页改为与主界面同尺寸、不可移动、位置同步的新界面\n")
    f.write("- 修复检查更新误报失败的问题，区分已是最新与全部节点失败\n")
    f.write("- 启动时自动静默下载更新，完成后提示重启并提供重启按钮\n")
    f.write("- 更新安装默认使用现有安装目录，无需再次选择路径\n")
    f.write("- 安装程序支持 /SILENT /DIR /WAITPID /LAUNCH 静默更新参数\n")
    f.write("- 统一 Apple 设计规范，单一蓝色强调\n")

# 打包 payload.zip（安装器会把这个一起打包进 exe）
payload_zip = os.path.join(ROOT, "payload.zip")
if os.path.exists(payload_zip):
    os.remove(payload_zip)
zip_dir(payload_stage, payload_zip)


# ---------- 3. 打包 setup_installer 为最终安装程序 ----------
run_pyinstaller(
    [
        "--onefile", "--windowed",
        "--name", "闻铎点名器 安装程序",
        "--icon", os.path.join(ROOT, "assets", "app_icon.ico"),
        "--add-data", f"{payload_zip};.",
        "--add-data", f"{os.path.join(ROOT, 'assets', 'app_icon.ico')};.",
        os.path.join(ROOT, "setup_installer.py"),
    ],
    "打包安装程序",
)


# ---------- 4. 整理输出 ----------
final_installer = os.path.join(ROOT, "dist", "闻铎点名器 安装程序.exe")
out_path = os.path.join(DIST, INSTALLER_NAME)
if os.path.exists(out_path):
    os.remove(out_path)
shutil.copy(final_installer, out_path)

print("\n======================================")
print("  构建完成！")
print("======================================")
print(f"主程序: {main_exe}")
print(f"卸载程序: {uninstall_exe}")
print(f"安装包: {out_path}")
print(f"\n安装包大小: {os.path.getsize(out_path) / (1024*1024):.2f} MB")
