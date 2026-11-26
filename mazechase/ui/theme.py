"""
theme.py - colours, fonts and text drawing, so every screen looks the same.

Colour code used everywhere (game, lab, menu, side panel):
    A*  = red    BFS = violet    Greedy = orange    DFS = green    Runner = cyan
"""

from __future__ import annotations

import pygame

from ..config import HUNTERS, RUNNER_COLOR

Color = tuple[int, int, int]

BACKGROUND: Color = (8, 11, 20)
PANEL: Color = (14, 19, 33)
CARD: Color = (22, 29, 48)
CARD_LIGHT: Color = (33, 43, 70)
LINE: Color = (44, 56, 88)
TEXT: Color = (232, 236, 245)
TEXT_DIM: Color = (146, 157, 184)
TEXT_FAINT: Color = (96, 107, 134)
ACCENT: Color = RUNNER_COLOR
GOOD: Color = (92, 222, 142)
BAD: Color = (255, 92, 110)
WARN: Color = (255, 198, 84)
PELLET: Color = (255, 231, 172)
POWER_ORB: Color = (255, 112, 200)
SCARED: Color = (128, 150, 255)
SCARED_BODY: Color = (48, 60, 98)
WHITE: Color = (250, 250, 255)
INK: Color = (14, 16, 26)

# One colour per algorithm - the same colour as the hunter that uses it.
ALGORITHM_COLORS: dict[str, Color] = {profile.algorithm: profile.color for profile in HUNTERS}

# Map themes: (floor, wall fill, wall edge)
MAP_THEMES: dict[str, tuple[Color, Color, Color]] = {
    "teal": ((11, 17, 27), (16, 52, 64), (58, 196, 206)),
    "amber": ((16, 14, 22), (66, 44, 20), (238, 166, 70)),
    "blue": ((10, 14, 30), (22, 40, 92), (90, 142, 255)),
    "violet": ((14, 11, 28), (50, 28, 88), (178, 120, 255)),
    "green": ((9, 18, 17), (20, 58, 40), (92, 214, 140)),
}

UI_FONTS = "bahnschrift,segoeui,helveticaneue,arial"
MONO_FONTS = "consolas,cascadiamono,menlo,couriernew"


def ui_scale(size: tuple[int, int]) -> float:
    """1.0 on a 1600 x 900 window. Every screen multiplies its sizes by this number, so the
    layout looks the same on a laptop, a big monitor or a projector."""
    width, height = size
    return max(0.62, min(width / 1600, height / 900, 2.2))


_fonts: dict[tuple[int, bool, bool], pygame.font.Font] = {}
_rendered: dict[tuple, pygame.Surface] = {}


def font(size: int, bold: bool = False, mono: bool = False) -> pygame.font.Font:
    """A cached system font (falls back to pygame's built-in font if none is installed)."""
    key = (max(8, int(size)), bold, mono)
    if key not in _fonts:
        try:
            _fonts[key] = pygame.font.SysFont(MONO_FONTS if mono else UI_FONTS, key[0], bold=bold)
        except Exception:                      # very unusual systems without system fonts
            _fonts[key] = pygame.font.Font(None, key[0] + 4)
    return _fonts[key]


def render(text: str, size: int, color: Color = TEXT, bold: bool = False, mono: bool = False) -> pygame.Surface:
    """Text as an image. Images are cached: the same label is drawn 60 times a second."""
    key = (text, int(size), color, bold, mono)
    image = _rendered.get(key)
    if image is None:
        if len(_rendered) > 2000:
            _rendered.clear()
        image = _rendered[key] = font(size, bold, mono).render(text, True, color)
    return image


def draw_text(surface: pygame.Surface, text: str, pos: tuple[float, float], size: int,
              color: Color = TEXT, bold: bool = False, mono: bool = False,
              anchor: str = "topleft") -> pygame.Rect:
    """Draw text and return its rectangle. `anchor` is any pygame.Rect position name
    ("topleft", "center", "midright", ...) and says which point of the text sits at `pos`."""
    image = render(text, size, color, bold, mono)
    rect = image.get_rect(**{anchor: (round(pos[0]), round(pos[1]))})
    surface.blit(image, rect)
    return rect


def text_width(text: str, size: int, bold: bool = False, mono: bool = False) -> int:
    return font(size, bold, mono).size(text)[0]


def mix(a: Color, b: Color, amount: float) -> Color:
    """Blend colour a toward colour b (amount 0 = a, 1 = b)."""
    return tuple(round(x + (y - x) * amount) for x, y in zip(a, b))  # type: ignore[return-value]
