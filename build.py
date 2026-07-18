"""
构建脚本 - 打包闻铎点名器为 EXE
"""
import subprocess
import shutil
import os
import sys

proj = os.path.dirname(os.path.abspath(__file__))
print(f"项目目录: {proj}")

# 清理旧构建
for d in ['build', 'dist']:
    p = os.path.join(proj, d)
    if os.path.exists(p):
        try:
            shutil.rmtree(p)
            print(f"已清理: {d}/")
        except Exception as e:
            print(f"清理 {d}/ 失败: {e}")

# 运行 PyInstaller
spec_file = os.path.join(proj, 'WenDuoPicker.spec')
if os.path.exists(spec_file):
    os.remove(spec_file)
    print("已删除旧 spec 文件")

print("开始打包...")
result = subprocess.run(
    [
        sys.executable, '-m', 'PyInstaller',
        '--onefile',
        '--windowed',
        '--name', 'WenDuoPicker',
        '--icon', os.path.join(proj, 'assets', 'app_icon.ico'),
        '--add-data', f'src{os.pathsep}src',
        'main.py'
    ],
    cwd=proj,
    capture_output=False
)

if result.returncode != 0:
    print("打包失败!")
    sys.exit(1)

# 重命名为中文名
src_exe = os.path.join(proj, 'dist', 'WenDuoPicker.exe')
dst_exe = os.path.join(proj, 'dist', '闻铎点名器.exe')
if os.path.exists(src_exe):
    if os.path.exists(dst_exe):
        os.remove(dst_exe)
    os.rename(src_exe, dst_exe)
    size_mb = os.path.getsize(dst_exe) / (1024 * 1024)
    print(f"\n打包成功!")
    print(f"输出文件: {dst_exe}")
    print(f"文件大小: {size_mb:.1f} MB")
else:
    print(f"未找到输出文件: {src_exe}")
