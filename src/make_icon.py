"""
将应用图标 PNG 转换为 ICO 格式
策略：用背景色填充为正方形（不裁剪内容），确保铜铎图完整保留
源文件：assets/icons/app_icon.png（用户提供的铜铎图）
输出：assets/app_icon.ico（多尺寸，16/32/48/64/128/256）
"""
from PIL import Image
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_PNG = os.path.join(PROJECT_ROOT, "assets", "icons", "app_icon.png")
DST_ICO = os.path.join(PROJECT_ROOT, "assets", "app_icon.ico")


def _detect_background_color(img: "Image.Image") -> tuple:
    """从图像四角/边缘采样估算背景色"""
    w, h = img.size
    samples = [
        img.getpixel((0, 0)),
        img.getpixel((w - 1, 0)),
        img.getpixel((0, h - 1)),
        img.getpixel((w - 1, h - 1)),
        img.getpixel((w // 2, 0)),
        img.getpixel((w // 2, h - 1)),
        img.getpixel((0, h // 2)),
        img.getpixel((w - 1, h // 2)),
    ]
    r = sum(s[0] for s in samples) // len(samples)
    g = sum(s[1] for s in samples) // len(samples)
    b = sum(s[2] for s in samples) // len(samples)
    return (r, g, b, 255)


def main():
    if not os.path.exists(SRC_PNG):
        print(f"未找到源图标: {SRC_PNG}")
        return False

    os.makedirs(os.path.dirname(DST_ICO), exist_ok=True)

    img = Image.open(SRC_PNG).convert("RGBA")
    print(f"源图: {img.size} {img.mode}")

    w, h = img.size
    side = max(w, h)  # 正方形边长 = 最大边（保留全部内容）
    bg_color = _detect_background_color(img)
    print(f"背景色: {bg_color}")
    print(f"正方形画布: {side}x{side}（原图 {w}x{h} 居中放置，不裁剪内容）")

    # 创建正方形画布，背景色填充
    canvas = Image.new("RGBA", (side, side), bg_color)
    # 原图居中贴到画布上
    x = (side - w) // 2
    y = (side - h) // 2
    canvas.paste(img, (x, y), img)

    # 缩放到 256 作为 ICO 主图（高采样质量）
    master_256 = canvas.resize((256, 256), Image.Resampling.LANCZOS)

    # 保存为多尺寸 ICO
    master_256.save(
        DST_ICO,
        format="ICO",
        sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
    )

    size_kb = os.path.getsize(DST_ICO) / 1024
    print(f"已生成: {DST_ICO} ({size_kb:.1f} KB)")

    # 验证：保存一张 256 的预览
    preview = Image.open(DST_ICO)
    preview.save(os.path.join(PROJECT_ROOT, "icon_preview_256.png"))
    print(f"预览图: icon_preview_256.png（可核对内容）")
    return True


if __name__ == "__main__":
    main()
