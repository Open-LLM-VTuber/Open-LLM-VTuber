from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ICON_PATH = ROOT / "scripts" / "nyx_icon.ico"
PNG_PATH = ROOT / "scripts" / "nyx_icon.png"


def make_icon() -> None:
    size = 256
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # Rounded dark-blue gradient-like background
    for i in range(size):
        alpha = int(255 * (1 - i / size))
        color = (12 + i // 12, 26 + i // 10, 55 + i // 8, 255)
        draw.line((0, i, size, i), fill=color)

    # Soft glow circle
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse((18, 18, size - 18, size - 18), fill=(52, 101, 255, 220))
    image = Image.alpha_composite(image, glow)

    # Central emblem: stylized N with cyan accent
    emblem = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    emblem_draw = ImageDraw.Draw(emblem)
    emblem_draw.rounded_rectangle((58, 38, 198, 218), radius=24, fill=(7, 13, 28, 220))
    emblem_draw.line((80, 176, 80, 76), fill=(56, 220, 255, 255), width=18)
    emblem_draw.line((80, 76, 176, 176), fill=(56, 220, 255, 255), width=18)
    emblem_draw.line((176, 176, 176, 76), fill=(56, 220, 255, 255), width=18)
    emblem_draw.line((176, 76, 176, 176), fill=(56, 220, 255, 255), width=18)
    image = Image.alpha_composite(image, emblem)

    # Add a subtle highlight and a tiny "Y" accent for the local AI feel
    highlight = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    highlight_draw = ImageDraw.Draw(highlight)
    highlight_draw.arc((26, 26, size - 26, size - 26), 220, 330, fill=(255, 255, 255, 90), width=8)
    image = Image.alpha_composite(image, highlight)

    # Save PNG source + ICO for Windows
    image.save(PNG_PATH, format="PNG")
    image.save(ICON_PATH, format="ICO")


if __name__ == "__main__":
    make_icon()
    print(f"Icon generated: {ICON_PATH}")
