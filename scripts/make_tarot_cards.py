"""Generate a license-free placeholder deck of the 22 Major Arcana as SVG.

The show ships with the public-domain Rider-Waite-Smith JPEGs
(``scripts/fetch_tarot_art.ps1``), so this script is the **fallback**: a
deterministic, geometric card per arcanum (double frame, roman numeral, name and
keywords) for a repo without that art, or for anyone who prefers a minimal deck.

No fonts are embedded and no randomness is involved, so the same file comes out
on every machine. To use it:

    build_draw_props(drawn, art_ext="svg")

    python scripts/make_tarot_cards.py            # (re)write the 22 SVGs
    python scripts/make_tarot_cards.py --check    # exit 1 when a file is stale
"""

import argparse
import math
import os
import sys
from xml.sax.saxutils import escape

# Add project root to path to enable imports (same as the live scripts).
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.open_llm_vtuber.utils.tarot import DECK, TarotCard  # noqa: E402

CARD_W = 512
CARD_H = 768
ART_DIR = os.path.join(project_root, "backgrounds", "cards")
ART_EXT = "svg"
GENERATOR = "scripts/make_tarot_cards.py"

#: (top colour, bottom colour, accent) cycled over the deck: four moods, no art.
PALETTES = (
    ("#1b1030", "#2d1a4a", "#ffd479"),
    ("#0f1c2e", "#1c3350", "#8fd3ff"),
    ("#241028", "#3d1b3a", "#ff9ec4"),
    ("#101f1a", "#1d3a2f", "#a8e6a3"),
)
ROMAN = (
    "0",
    "I",
    "II",
    "III",
    "IV",
    "V",
    "VI",
    "VII",
    "VIII",
    "IX",
    "X",
    "XI",
    "XII",
    "XIII",
    "XIV",
    "XV",
    "XVI",
    "XVII",
    "XVIII",
    "XIX",
    "XX",
    "XXI",
)


def _wrap(text: str, limit: int) -> list[str]:
    """Break ``text`` into lines of at most ``limit`` characters."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= limit or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines[:3]


def _star_points(cx: float, cy: float, radius: float, points: int) -> str:
    """Alternating radii, so the motif is a star instead of a polygon."""
    coords = []
    for step in range(points * 2):
        angle = math.pi * step / points - math.pi / 2
        length = radius if step % 2 == 0 else radius * 0.55
        x = cx + math.cos(angle) * length
        y = cy + math.sin(angle) * length
        coords.append(f"{x:.1f},{y:.1f}")
    return " ".join(coords)


def card_svg(card: TarotCard, index: int) -> str:
    """One self-contained SVG for ``card`` (deterministic for its index)."""
    top, bottom, accent = PALETTES[index % len(PALETTES)]
    numeral = ROMAN[index]
    name_lines = _wrap(card.name, 14)
    keywords = " · ".join(card.keywords)
    name_y = 470 - (len(name_lines) - 1) * 26
    name_spans = "".join(
        f'<tspan x="{CARD_W / 2}" dy="{0 if position == 0 else 52}">{escape(line)}</tspan>'
        for position, line in enumerate(name_lines)
    )

    # A ring of dots plus a star: readable at 15% screen size, no font needed.
    dots = "".join(
        f'<circle cx="{CARD_W / 2 + math.cos(math.pi * i / 6 - math.pi / 2) * 150:.1f}" '
        f'cy="{265 + math.sin(math.pi * i / 6 - math.pi / 2) * 150:.1f}" '
        f'r="{5 + (i % 3) * 2}" fill="{accent}" opacity="{0.35 + (i % 4) * 0.12:.2f}" />'
        for i in range(12)
    )
    star = _star_points(CARD_W / 2, 265, 92, 3 + index % 6)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CARD_W} {CARD_H}" width="{CARD_W}" height="{CARD_H}" role="img" aria-label="{escape(card.name)}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{top}" />
      <stop offset="1" stop-color="{bottom}" />
    </linearGradient>
  </defs>
  <rect width="{CARD_W}" height="{CARD_H}" rx="28" fill="url(#bg)" />
  <rect x="18" y="18" width="{CARD_W - 36}" height="{CARD_H - 36}" rx="20" fill="none" stroke="{accent}" stroke-width="3" opacity="0.85" />
  <rect x="30" y="30" width="{CARD_W - 60}" height="{CARD_H - 60}" rx="14" fill="none" stroke="{accent}" stroke-width="1" opacity="0.45" />
  <text x="{CARD_W / 2}" y="96" text-anchor="middle" font-family="Georgia, serif" font-size="42" fill="{accent}" letter-spacing="4">{numeral}</text>
  <line x1="150" y1="120" x2="{CARD_W - 150}" y2="120" stroke="{accent}" stroke-width="1" opacity="0.5" />
  {dots}
  <polygon points="{star}" fill="none" stroke="{accent}" stroke-width="2.5" opacity="0.9" />
  <circle cx="{CARD_W / 2}" cy="265" r="10" fill="{accent}" opacity="0.9" />
  <text x="{CARD_W / 2}" y="{name_y}" text-anchor="middle" font-family="Georgia, serif" font-size="46" fill="#fdf6e3">{name_spans}</text>
  <line x1="120" y1="612" x2="{CARD_W - 120}" y2="612" stroke="{accent}" stroke-width="1" opacity="0.4" />
  <text x="{CARD_W / 2}" y="660" text-anchor="middle" font-family="system-ui, sans-serif" font-size="18" fill="{accent}" opacity="0.9">{escape(keywords)}</text>
  <text x="{CARD_W / 2}" y="{CARD_H - 34}" text-anchor="middle" font-family="system-ui, sans-serif" font-size="14" fill="#fdf6e3" opacity="0.35">placeholder · {escape(card.id)}</text>
</svg>
"""


def build_cards() -> dict[str, str]:
    """``{filename: content}`` for the whole deck."""
    return {
        f"{card.id}.{ART_EXT}": card_svg(card, index) for index, card in enumerate(DECK)
    }


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as handle:
        return handle.read().replace("\r\n", "\n")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=ART_DIR, help="directory for the cards")
    parser.add_argument(
        "--check",
        action="store_true",
        help="compare with the committed cards instead of writing them",
    )
    args = parser.parse_args(argv)

    cards = build_cards()
    if args.check:
        stale = []
        for name, content in cards.items():
            path = os.path.join(args.out, name)
            if not os.path.exists(path) or _read(path) != content:
                stale.append(name)
        if stale:
            print(f"stale or missing cards: {', '.join(sorted(stale))}")
            print(f"run: python {GENERATOR}")
            return 1
        print(f"{len(cards)} cards up to date")
        return 0

    os.makedirs(args.out, exist_ok=True)
    for name, content in cards.items():
        with open(
            os.path.join(args.out, name), "w", encoding="utf-8", newline="\n"
        ) as handle:
            handle.write(content)
    print(f"wrote {len(cards)} cards to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
