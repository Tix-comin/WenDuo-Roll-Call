from PIL import Image, ImageDraw, ImageFilter
import math

# 画布尺寸（与原来的品牌图比例类似，略方形）
W, H = 2048, 2048
canvas = Image.new("RGBA", (W, H), (255, 255, 255, 0))
draw = ImageDraw.Draw(canvas)

# --- 1. 圆角背景（柔和米黄，与主题呼应） ---
bg = Image.new("RGBA", (W, H), (255, 253, 248, 255))
bg_draw = ImageDraw.Draw(bg)
# 四角圆角，半径
R = 200
bg_draw.rounded_rectangle([0, 0, W, H], radius=R, fill=(255, 253, 248, 255))
canvas = bg

# --- 2. 3D 投票箱（前视图+侧视图+俯视图组成的伪3D盒子） ---
# 主体参数
cx = W // 2
cy = H // 2 + 60  # 略靠下，上方留空放小装饰

box_w = 1100
box_h = 780
box_d = 260  # 3D 透视的“深度”偏移

# 颜色
face_top = (170, 200, 255, 255)   # 顶部浅蓝
face_front = (96, 135, 255, 255)   # 正面蓝
face_side = (70, 110, 225, 255)    # 侧面深蓝
edge = (50, 80, 180, 255)
outline = (30, 55, 130, 255)

# 透视计算（等轴侧）
# 正面矩形
front_left = cx - box_w // 2
front_right = cx + box_w // 2
front_top = cy - box_h // 2
front_bottom = cy + box_h // 2

# 顶面（向后/向上偏移形成等轴侧视觉）
top_dx = box_d * 0.7
top_dy = -box_d * 0.6
# 顶面四点
top_p1 = (front_left, front_top)           # 左上（正面）
top_p2 = (front_right, front_top)           # 右上（正面）
top_p3 = (front_right + top_dx, front_top + top_dy)  # 右上后
top_p4 = (front_left + top_dx, front_top + top_dy)   # 左上后

# 侧面（右侧）
side_p1 = (front_right, front_top)
side_p2 = (front_right, front_bottom)
side_p3 = (front_right + top_dx, front_bottom + top_dy)
side_p4 = (front_right + top_dx, front_top + top_dy)

# 画侧面
draw.polygon([side_p1, side_p2, side_p3, side_p4], fill=face_side, outline=outline)

# 画顶面
draw.polygon([top_p1, top_p2, top_p3, top_p4], fill=face_top, outline=outline)

# 画正面（圆角）
front_img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
front_draw = ImageDraw.Draw(front_img)
# 正面圆角矩形
front_radius = 80
front_draw.rounded_rectangle(
    [front_left, front_top, front_right, front_bottom],
    radius=front_radius,
    fill=face_front,
    outline=outline,
)
canvas.alpha_composite(front_img)

# 正面高光（左上一条亮带）
highlight = Image.new("RGBA", (W, H), (0, 0, 0, 0))
hl_draw = ImageDraw.Draw(highlight)
hl_draw.rounded_rectangle(
    [front_left + 30, front_top + 30, front_left + 120, front_bottom - 30],
    radius=40,
    fill=(200, 220, 255, 180),
)
canvas.alpha_composite(highlight)

# --- 3. 投票口（顶部凸起的白色卡片） ---
slit_w = 620
slit_h = 60
slit_y = front_top + 90
# 卡片纸（露出投票口的白色纸张）
card = Image.new("RGBA", (W, H), (0, 0, 0, 0))
card_draw = ImageDraw.Draw(card)

# 白色卡片主体
card_draw.rounded_rectangle(
    [cx - slit_w // 2 - 30, slit_y - 300, cx + slit_w // 2 + 30, slit_y + 60],
    radius=30,
    fill=(255, 255, 255, 255),
    outline=(200, 210, 230, 255),
)

# 卡片上的横线（模拟纸纹/列表项）
for i, offset_y in enumerate([-200, -140, -80, -20]):
    fill_c = (180, 195, 220, 255)
    card_draw.rounded_rectangle(
        [cx - slit_w // 2 + 50, slit_y + offset_y, cx + slit_w // 2 - 50 - 80, slit_y + offset_y + 20],
        radius=10, fill=fill_c,
    )
# 第二条带蓝色高亮（“当前”项）
card_draw.rounded_rectangle(
    [cx - slit_w // 2 + 50, slit_y - 140, cx - slit_w // 2 + 400, slit_y - 120],
    radius=10, fill=(100, 140, 240, 255),
)
card_draw.rounded_rectangle(
    [cx - slit_w // 2 + 440, slit_y - 140, cx + slit_w // 2 - 50, slit_y - 120],
    radius=10, fill=(180, 195, 220, 255),
)

canvas.alpha_composite(card)

# 投票口（盒子上的一条细缝）
slit = Image.new("RGBA", (W, H), (0, 0, 0, 0))
slit_draw = ImageDraw.Draw(slit)
slit_draw.rounded_rectangle(
    [cx - slit_w // 2, slit_y - 30, cx + slit_w // 2, slit_y + 30],
    radius=20, fill=outline,
)
# 投票口内阴影
slit_draw.rounded_rectangle(
    [cx - slit_w // 2 + 8, slit_y - 22, cx + slit_w // 2 - 8, slit_y + 22],
    radius=14, fill=(20, 40, 100, 255),
)
canvas.alpha_composite(slit)

# --- 4. 正面装饰：小圆 + 把手（拟物化细节） ---
# 左侧小圆
circle_x = front_left + 140
circle_y = front_bottom - 120
dr = ImageDraw.Draw(canvas)
dr.ellipse([circle_x - 50, circle_y - 50, circle_x + 50, circle_y + 50],
           fill=(255, 255, 255, 255), outline=outline, width=6)
dr.ellipse([circle_x - 28, circle_y - 28, circle_x + 28, circle_y + 28],
           fill=(60, 120, 220, 255))

# 右侧“投票纸 把手”（蓝色圆角矩形）
handle_left = front_right - 280
handle_top = front_bottom - 160
handle_right = front_right - 60
handle_bottom = front_bottom - 60
dr.rounded_rectangle([handle_left, handle_top, handle_right, handle_bottom],
                     radius=20, fill=(255, 255, 255, 240), outline=(80, 110, 200), width=4)

# --- 5. 顶部“星星”装饰（右上角小点缀） ---
star_cx = front_right + top_dx - 40
star_cy = front_top + top_dy + 200
# 小星星
def draw_star(cx_, cy_, r, fill):
    pts = []
    for i in range(10):
        angle = -math.pi / 2 + i * math.pi / 5
        rad = r if i % 2 == 0 else r * 0.45
        pts.append((cx_ + rad * math.cos(angle), cy_ + rad * math.sin(angle)))
    dr.polygon(pts, fill=fill, outline=outline)

draw_star(star_cx, star_cy, 80, (255, 220, 80, 255))
# 更小的副星
draw_star(star_cx + 140, star_cy + 120, 40, (255, 200, 80, 255))

# --- 6. 轻微投影与柔和模糊增加立体感 ---
shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
sh_draw = ImageDraw.Draw(shadow)
sh_draw.ellipse(
    [cx - 500, H - 220, cx + 500, H - 100],
    fill=(0, 0, 0, 60),
)
shadow = shadow.filter(ImageFilter.GaussianBlur(radius=60))
canvas.alpha_composite(shadow, (0, 0))

# --- 7. 整体柔光叠加，让边缘更柔和 ---
canvas = canvas.filter(ImageFilter.GaussianBlur(radius=0.6))

# 保存
canvas.save("assets/icons/ballot_box.png", "PNG")
print(f"已生成 ballot_box.png: {canvas.size}")

# 同步保存一份到 app_icon.png 的同目录备用
canvas.save("assets/icons/package.png", "PNG")
print("已同步保存 package.png")
