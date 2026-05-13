"""Generate PWA icons matching the in-app logo (cyan gradient + bold K).

Run from waterpipe repo root:
    python scripts/gen-icons.py
"""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "icons"
OUT.mkdir(exist_ok=True)

# Logo colors from index.html
GRAD_START = (0, 212, 255)   # #00d4ff
GRAD_END = (0, 119, 182)     # #0077b6
TEXT_COLOR = (0, 0, 0)       # black text matches the in-app logo
BG_DARK = (11, 15, 20)       # #0b0f14 (theme bg, used for maskable safe area)


def make_gradient(size: int, start, end) -> Image.Image:
    """Diagonal gradient 135deg (top-left -> bottom-right)."""
    img = Image.new("RGB", (size, size), start)
    px = img.load()
    for y in range(size):
        for x in range(size):
            t = (x + y) / (2 * (size - 1))
            r = int(start[0] + (end[0] - start[0]) * t)
            g = int(start[1] + (end[1] - start[1]) * t)
            b = int(start[2] + (end[2] - start[2]) * t)
            px[x, y] = (r, g, b)
    return img


def find_font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeuib.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def draw_k(img: Image.Image, *, inset_ratio: float = 0.0):
    """Draw centered 'K' on top of gradient. inset_ratio shrinks the glyph
    so the icon survives mask cropping on Android (safe zone)."""
    size = img.size[0]
    draw = ImageDraw.Draw(img)
    font_size = int(size * (0.62 - inset_ratio))
    font = find_font(font_size)
    text = "K"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = (size - tw) // 2 - bbox[0]
    # Visual centering nudge: ascender bias
    y = (size - th) // 2 - bbox[1] - int(size * 0.02)
    draw.text((x, y), text, fill=TEXT_COLOR, font=font)


def make_icon(size: int, *, rounded: bool = True, maskable: bool = False) -> Image.Image:
    grad = make_gradient(size, GRAD_START, GRAD_END)
    if maskable:
        # Maskable icons: full-bleed background, glyph inside safe zone (~80%)
        img = grad.convert("RGBA")
        draw_k(img, inset_ratio=0.18)
        return img

    # Normal icon: rounded square on transparent background
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    mask = Image.new("L", (size, size), 0)
    radius = int(size * 0.22)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, size - 1, size - 1), radius=radius, fill=255
    )
    img.paste(grad, (0, 0), mask)
    draw_k(img)
    return img


targets = [
    ("icon-192.png", 192, False),
    ("icon-512.png", 512, False),
    ("icon-maskable-512.png", 512, True),
    ("apple-touch-icon.png", 180, False),
    ("favicon-32.png", 32, False),
]

for name, size, maskable in targets:
    icon = make_icon(size, maskable=maskable)
    icon.save(OUT / name, "PNG", optimize=True)
    print(f"wrote {OUT / name}  ({size}x{size}{' maskable' if maskable else ''})")
