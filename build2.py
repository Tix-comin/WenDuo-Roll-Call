"""构建脚本 - 打包闻铎点名器为 EXE"""
import subprocess
import os
import sys
import time

proj = os.path.dirname(os.path.abspath(__file__))
print(f"项目目录: {proj}")

# 1) 先把 PNG 应用图标转成 ICO（assets/app_icon.ico）
print("[1/3] 生成 ICO 图标...")
result = subprocess.run(
    [sys.executable, os.path.join(proj, "src", "make_icon.py")],
    cwd=proj,
)
if result.returncode != 0:
    print("图标生成失败!")
    sys.exit(1)

# 清理旧文件（允许失败）
def clean():
    for d in ['build', 'dist']:
        p = os.path.join(proj, d)
        if os.path.exists(p):
            for _ in range(3):
                try:
                    import shutil
                    shutil.rmtree(p)
                    break
                except Exception:
                    time.sleep(0.5)

clean()

# 2) 运行 PyInstaller
print("[2/3] 打包 EXE...")
result = subprocess.run(
    [sys.executable, '-m', 'PyInstaller',
     '--onefile', '--windowed',
     '--name', 'WenDuoPicker',
     '--icon', os.path.join(proj, 'assets', 'app_icon.ico'),
     '--add-data', f'src{os.pathsep}src',
     '--add-data', f'assets{os.pathsep}assets',
     'main.py'],
    cwd=proj
)
if result.returncode != 0:
    print("打包失败!")
    sys.exit(1)

# 3) 重命名为中文 EXE
print("[3/3] 重命名...")
src_exe = os.path.join(proj, 'dist', 'WenDuoPicker.exe')
dst_exe = os.path.join(proj, 'dist', '闻铎点名器.exe')
if os.path.exists(src_exe):
    if os.path.exists(dst_exe):
        try:
            os.remove(dst_exe)
        except Exception:
            pass
    try:
        os.rename(src_exe, dst_exe)
    except Exception:
        # 如果无法删除旧 exe，直接用 WenDuoPicker.exe
        print("警告: 中文重命名失败，输出文件为 dist/WenDuoPicker.exe")
        dst_exe = src_exe
    size_mb = os.path.getsize(dst_exe) / (1024 * 1024)
    print(f"\n打包成功! 输出: {dst_exe} ({size_mb:.1f} MB)")
