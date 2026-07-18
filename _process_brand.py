"""处理品牌图标：去除背景边框，使图片与侧边栏白色背景无缝融合（纯 PIL 实现）"""
from PIL import Image
import os

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "assets", "icons", "IMG_20260610_161514..jpg")
DST = os.path.join(BASE, "assets", "icons", "app_brand.png")

img = Image.open(SRC)
print(f"原图: {img.size} {img.mode}")

if img.mode != "RGBA":
    img = img.convert("RGBA")

w, h = img.size

# 1. 检测四角背景色
corners = [
    img.getpixel((0, 0)),
    img.getpixel((w - 1, 0)),
    img.getpixel((0, h - 1)),
    img.getpixel((w - 1, h - 1)),
]
bg_r = sum(c[0] for c in corners) // 4
bg_g = sum(c[1] for c in corners) // 4
bg_b = sum(c[2] for c in corners) // 4
print(f"背景色: ({bg_r}, {bg_g}, {bg_b})")

# 2. 逐像素处理：接近背景色的设为透明
pixels = img.load()
threshold = 35
edge_threshold = threshold + 20

for y in range(h):
    for x in range(w):
        r, g, b, a = pixels[x, y]
        dist = max(abs(r - bg_r), abs(g - bg_g), abs(b - bg_b))
        if dist < threshold:
            pixels[x, y] = (r, g, b, 0)
        elif dist < edge_threshold:
            # 边缘渐变半透明
            factor = (dist - threshold) / 20
            pixels[x, y] = (r, g, b, int(a * factor))

# 3. 裁剪掉透明边缘
bbox = img.getbbox()
if bbox:
    pad = 10
    x0 = max(0, bbox[0] - pad)
    y0 = max(0, bbox[1] - pad)
    x1 = min(w, bbox[2] + pad)
    y1 = min(h, bbox[3] + pad)
    img = img.crop((x0, y0, x1, y1))
    print(f"裁剪后: {img.size}")

img.save(DST, "PNG")
print(f"已保存: {DST} ({os.path.getsize(DST) // 1024} KB)")
