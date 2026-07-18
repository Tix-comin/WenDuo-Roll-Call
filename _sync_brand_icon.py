import os
from PIL import Image

root = r"d:\桌面\点名器"
# 博士帽图片是 IMG_20260610_161514..jpg
src = os.path.join(root, "assets", "icons", "IMG_20260610_161514..jpg")
dst_png = os.path.join(root, "assets", "icons", "app_brand.png")

print(f"Source exists: {os.path.exists(src)}")
img = Image.open(src)
if img.mode not in ("RGB", "RGBA"):
    img = img.convert("RGBA")

img.save(dst_png, "PNG", optimize=True)
print(f"Saved: {dst_png} size: {img.size} mode: {img.mode}")
