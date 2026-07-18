from PIL import Image, ImageDraw, ImageFilter
import math

W, H = 1024, 1024

# ========= 1. 基础画布（纯白背景） =========
canvas = Image.new("RGBA", (W, H), (255, 255, 255, 255))
dr = ImageDraw.Draw(canvas)

# ========= 2. 柔和投影（椭圆阴影，底部居中） =========
shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
sh = ImageDraw.Draw(shadow)
sh.ellipse([W // 2 - 420, H - 220, W // 2 + 420, H - 60], fill=(180, 195, 220, 160))
shadow = shadow.filter(ImageFilter.GaussianBlur(radius=45))
canvas.alpha_composite(shadow)

# ========= 3. 盒子（等轴侧视图） =========
# 颜色
BOX_FRONT = (175, 205, 245, 255)   # 正面：柔和淡蓝
BOX_SIDE = (135, 170, 225, 255)     # 侧面：稍深蓝
BOX_TOP = (200, 225, 250, 255)      # 顶面：更浅
BOX_DARK_EDGE = (110, 150, 210, 255)
HOLE_DARK = (60, 90, 160, 255)

cx, cy = W // 2, H // 2 + 50

# --- 盒子主体：绘制为带圆角的“伪3D”盒子（前+右+顶三面） ---
box_left = cx - 340
box_right = cx + 340
box_top = cy - 100
box_bottom = cy + 260

# 右侧面（梯形）
side_top_y = box_top - 40
side_bottom_y = box_bottom
side_right = box_right + 160
side = Image.new("RGBA", (W, H), (0, 0, 0, 0))
sd = ImageDraw.Draw(side)
sd.polygon(
    [(box_right, box_top), (side_right, side_top_y),
     (side_right, side_bottom_y - 40), (box_right, box_bottom)],
    fill=BOX_SIDE, outline=BOX_DARK_EDGE,
)
# 右侧面的高光
sd.polygon(
    [(box_right + 10, box_top + 20), (box_right + 50, side_top_y + 30),
     (box_right + 50, side_top_y + 80), (box_right + 10, box_top + 80)],
    fill=(220, 235, 255, 200),
)
canvas.alpha_composite(side)

# 顶面（斜四边形）
top = Image.new("RGBA", (W, H), (0, 0, 0, 0))
td = ImageDraw.Draw(top)
# 顶面（盒内的"蓝色内部"）
td.polygon(
    [(box_left, box_top), (box_right, box_top),
     (side_right, side_top_y), (box_left + 160, side_top_y)],
    fill=(95, 130, 200, 255), outline=BOX_DARK_EDGE,
)
# 让顶面有一点亮度渐变（前亮后暗）
for i in range(20):
    shade = int(180 + i * 2)
    td.polygon(
        [(box_left, box_top - 5 - i), (box_right, box_top - 5 - i),
         (side_right, side_top_y - 5 - i), (box_left + 160, side_top_y - 5 - i)],
        fill=(shade - 20, shade, min(shade + 40, 255), 40),
    )
canvas.alpha_composite(top)

# 正面（圆角矩形）
front = Image.new("RGBA", (W, H), (0, 0, 0, 0))
fd = ImageDraw.Draw(front)
fd.rounded_rectangle(
    [box_left, box_top, box_right, box_bottom],
    radius=55, fill=BOX_FRONT, outline=BOX_DARK_EDGE,
)
# 正面左上角高光（柔和的斜向亮带）
for i in range(25):
    alpha = max(30, 150 - i * 5)
    fd.line(
        [(box_left + 20 + i * 2, box_top + 20 + i * 3),
         (box_left + 80 + i * 2, box_top + 20 + i * 3 + 60)],
        fill=(255, 255, 255, alpha), width=3,
    )
# 正面左侧高光带（强）
fd.rounded_rectangle(
    [box_left + 30, box_top + 30, box_left + 80, box_bottom - 30],
    radius=20, fill=(220, 235, 255, 180),
)
# 正面右下的“长槽”（椭圆形深色孔）
slit_x = box_right - 250
slit_y = box_bottom - 180
slit_w = 140
slit_h = 55
# 外槽（稍暗）
fd.rounded_rectangle(
    [slit_x - slit_w // 2, slit_y - slit_h // 2,
     slit_x + slit_w // 2, slit_y + slit_h // 2],
    radius=25, fill=(100, 130, 190, 255), outline=HOLE_DARK,
)
# 内槽（更暗）
fd.rounded_rectangle(
    [slit_x - slit_w // 2 + 8, slit_y - slit_h // 2 + 8,
     slit_x + slit_w // 2 - 8, slit_y + slit_h // 2 - 8],
    radius=22, fill=(75, 110, 180, 255),
)
# 正面左下“圆孔”
circle_x = box_left + 90
circle_y = box_bottom - 140
fd.ellipse(
    [circle_x - 35, circle_y - 35, circle_x + 35, circle_y + 35],
    fill=(100, 130, 190, 255), outline=HOLE_DARK,
)
fd.ellipse(
    [circle_x - 25, circle_y - 25, circle_x + 25, circle_y + 25],
    fill=(70, 100, 170, 255),
)
# 圆孔内部的小高光（给立体感）
fd.ellipse(
    [circle_x - 12, circle_y - 18, circle_x + 3, circle_y - 3],
    fill=(140, 175, 225, 255),
)
canvas.alpha_composite(front)

# ========= 4. 后面的大盖子（弧形盖子，露出一角在盒子后上方） =========
lid = Image.new("RGBA", (W, H), (0, 0, 0, 0))
ld = ImageDraw.Draw(lid)
# 大的圆角弧形（像一个圆角矩形斜立在盒子后上方）
# 用一个大的圆角矩形，稍微倾斜
lid_box = [box_left - 30, box_top - 300, box_right - 50, box_top + 10]
ld.rounded_rectangle(lid_box, radius=90, fill=(205, 225, 250, 255), outline=BOX_DARK_EDGE)
# 盖子内部的蓝色边（暗示盖子的内层颜色）
ld.rounded_rectangle(
    [lid_box[0] + 15, lid_box[1] + 15, lid_box[2] - 15, lid_box[3] - 15],
    radius=75, fill=(175, 205, 245, 255), outline=(130, 170, 220, 255),
)
# 盖子上的高光
ld.rounded_rectangle(
    [lid_box[0] + 25, lid_box[1] + 25, lid_box[0] + 100, lid_box[3] - 25],
    radius=20, fill=(225, 240, 255, 200),
)
canvas.alpha_composite(lid)

# ========= 5. 右侧露出的纸片（蓝色部分） =========
paper_right = Image.new("RGBA", (W, H), (0, 0, 0, 0))
pr = ImageDraw.Draw(paper_right)
# 蓝色纸片（被主纸挡住一部分）
pr.polygon(
    [(box_right - 80, box_top + 50), (box_right + 120, box_top - 30),
     (box_right + 220, box_top + 160), (box_right - 20, box_top + 230)],
    fill=(120, 150, 210, 255), outline=(85, 120, 190, 255),
)
# 纸片上的蓝色横线
pr.line(
    [(box_right - 60, box_top + 80), (box_right + 160, box_top + 30)],
    fill=(60, 90, 150, 255), width=10,
)
pr.line(
    [(box_right - 60, box_top + 130), (box_right + 170, box_top + 80)],
    fill=(60, 90, 150, 255), width=10,
)
pr.line(
    [(box_right - 60, box_top + 180), (box_right + 180, box_top + 130)],
    fill=(60, 90, 150, 255), width=10,
)
canvas.alpha_composite(paper_right)

# ========= 6. 主白纸（最前面，带横线，一条有蓝色高亮段） =========
paper = Image.new("RGBA", (W, H), (0, 0, 0, 0))
pd = ImageDraw.Draw(paper)
# 主纸（白色，略带倾斜）
paper_left = cx - 230
paper_right2 = cx + 260
paper_top2 = box_top - 50
paper_bottom2 = box_top + 230

# 绘制一个倾斜的白纸（用四个角点的多边形模拟倾斜）
# 纸的四个角（稍微倾斜：上面比下面略右移）
paper_pts = [
    (paper_left, paper_top2 + 50),
    (paper_right2, paper_top2),
    (paper_right2 + 50, paper_bottom2 + 30),
    (paper_left + 30, paper_bottom2 + 80),
]
pd.polygon(paper_pts, fill=(255, 255, 255, 255), outline=(220, 225, 235, 255))

# 纸上的横线（按纸的倾斜角度画）
def draw_tilted_line(draw_obj, x1_rel, y1_rel, x2_rel, y2_rel, color, width_):
    """在纸上画一条随纸倾斜的线。相对坐标（左上角为0,0）"""
    # 简化：直接按纸的倾斜方向画线
    draw_obj.line([(x1_rel, y1_rel), (x2_rel, y2_rel)], fill=color, width=width_)

# 纸的起始角（top-left of paper in canvas coords）
# 简单做法：重新计算四条横线
lines_y = [paper_top2 + 110, paper_top2 + 160, paper_top2 + 210, paper_top2 + 260]
for ly in lines_y:
    # 横线左端点（随纸张倾斜）
    lx = paper_left + 40 + (ly - (paper_top2 + 50)) * 0.12
    rx = paper_right2 + 10 + (ly - (paper_top2 + 50)) * 0.12
    pd.line([(lx, ly), (rx, ly)], fill=(215, 220, 230, 255), width=14)

# 第二条线中间有蓝色高亮段
blue_line_y = lines_y[1]
lx = paper_left + 40 + (blue_line_y - (paper_top2 + 50)) * 0.12
rx = paper_right2 + 10 + (blue_line_y - (paper_top2 + 50)) * 0.12
blue_left_x = lx + (rx - lx) * 0.35
blue_right_x = lx + (rx - lx) * 0.75
pd.line([(blue_left_x, blue_line_y), (blue_right_x, blue_line_y)],
        fill=(110, 140, 200, 255), width=14)

# 纸的边缘再次描边加粗（让纸更有层次）
pd.line([paper_pts[0], paper_pts[1]], fill=(235, 238, 245, 255), width=4)
pd.line([paper_pts[1], paper_pts[2]], fill=(235, 238, 245, 255), width=4)
pd.line([paper_pts[2], paper_pts[3]], fill=(235, 238, 245, 255), width=4)
pd.line([paper_pts[3], paper_pts[0]], fill=(235, 238, 245, 255), width=4)

canvas.alpha_composite(paper)

# ========= 7. 右上角黄色五角星装饰 =========
star = Image.new("RGBA", (W, H), (0, 0, 0, 0))
std = ImageDraw.Draw(star)
star_cx = side_right - 180
star_cy = side_top_y + 80

def draw_star_five(cx_, cy_, r_out, r_in, fill_c, outline_c):
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rr = r_out if i % 2 == 0 else r_in
        pts.append((cx_ + rr * math.cos(ang), cy_ + rr * math.sin(ang)))
    std.polygon(pts, fill=fill_c, outline=outline_c)

# 五角星（柔和黄色，有一点立体边缘）
draw_star_five(star_cx, star_cy, 90, 40, (255, 210, 85, 255), (230, 175, 55, 255))
# 内部小高光
draw_star_five(star_cx - 15, star_cy - 15, 30, 15, (255, 240, 180, 255), (240, 200, 90, 255))
canvas.alpha_composite(star)

# ========= 8. 整体非常轻微的柔化（让边缘更柔和，卡通感） =========
canvas = canvas.filter(ImageFilter.GaussianBlur(radius=0.6))

# ========= 保存 =========
canvas.save("assets/icons/ballot_box.png", "PNG")
canvas.save("assets/icons/package.png", "PNG")

# 预览
preview = canvas.resize((512, 512), Image.Resampling.LANCZOS)
preview.save("debug_new_ballot_preview.png")
print("已生成 ballot_box.png 和 package.png")
print("预览: debug_new_ballot_preview.png")
