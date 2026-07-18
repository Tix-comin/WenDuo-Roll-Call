"""
根据主窗口代码中的 brand_candidates，检查所有候选文件是否存在。
"""
import os

root = r"d:\桌面\点名器\assets\icons"
candidates = [
    "app_brand.png",
    "996c5d860acaf05686ba7d63bf350770_750.png",
    "IMG_20260610_125401..jpg",
    "IMG_20260610_161514..jpg",
]

for c in candidates:
    full = os.path.join(root, c)
    exists = os.path.exists(full)
    size = ""
    if exists:
        size = f", size={os.path.getsize(full)} bytes"
    print(f"{'✓' if exists else '✗'} {c}{size}")
