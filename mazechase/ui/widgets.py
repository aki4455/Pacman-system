"""
widgets.py - small drawing helpers shared by the screens: cards, chips, bars, key caps and
text that wraps or shortens itself to fit.
"""

from __future__ import annotations

import pygame

from . import theme
from .theme import Color


def card(surface: pygame.Surface, rect: pygame.Rect, fill: Color = theme.CARD,
         border: Color | None = theme.LINE, radius: int = 10) -> None:
    pygame.draw.rect(surface, fill, rect, border_radius=radius)
    if border is not None:
        pygame.draw.rect(surface, border, rect, 1, border_radius=radius)


def chip(surface: pygame.Surface, text: str, pos: tuple[float, float], size: int, color: Color,
         filled: bool = True, anchor: str = "topleft") -> pygame.Rect:
    """A rounded label, used for algorithm names and AI modes. Returns its rectangle."""
    image = theme.render(text, size, theme.INK if filled else color, bold=True)
    pad_x, pad_y = max(5, size // 2), max(2, size // 6)
    height = theme.font(size, bold=True).get_height()        # not the image's: "y" can stick out
    rect = pygame.Rect(0, 0, image.get_width() + 2 * pad_x, height + 2 * pad_y)
    setattr(rect, anchor, (round(pos[0]), round(pos[1])))
    if filled:
        pygame.draw.rect(surface, color, rect, border_radius=rect.h // 2)
    else:
        pygame.draw.rect(surface, theme.mix(color, theme.BACKGROUND, 0.82), rect, border_radius=rect.h // 2)
        pygame.draw.rect(surface, theme.mix(color, theme.BACKGROUND, 0.3), rect, 1, border_radius=rect.h // 2)
    surface.blit(image, image.get_rect(center=rect.center))
    return rect


def bar(surface: pygame.Surface, rect: pygame.Rect, share: float, color: Color,
        back: Color = theme.CARD_LIGHT) -> None:
    """A progress bar, `share` between 0 and 1."""
    pygame.draw.rect(surface, back, rect, border_radius=rect.h // 2)
    share = max(0.0, min(1.0, share))
    if share > 0:
        filled = pygame.Rect(rect.x, rect.y, max(rect.h, round(rect.w * share)), rect.h)
        pygame.draw.rect(surface, color, filled, border_radius=rect.h // 2)


def key_cap(surface: pygame.Surface, key: str, pos: tuple[float, float], size: int,
            lit: bool = True, anchor: str = "topleft") -> pygame.Rect:
    """A small keyboard key, e.g. [Space]. The keys "<-" and "->" are drawn as arrows."""
    color = theme.TEXT if lit else theme.TEXT_FAINT
    arrow = {"->": 1, "<-": -1}.get(key)
    image = None if arrow else theme.render(key, size, color, bold=True)
    inner_width = image.get_width() if image else size
    inner_height = image.get_height() if image else theme.font(size, bold=True).get_height()
    rect = pygame.Rect(0, 0, max(inner_width + size, round(size * 1.7)), inner_height + max(4, size // 3))
    setattr(rect, anchor, (round(pos[0]), round(pos[1])))
    pygame.draw.rect(surface, theme.CARD_LIGHT if lit else theme.CARD, rect, border_radius=max(3, size // 4))
    pygame.draw.rect(surface, theme.LINE, rect, 1, border_radius=max(3, size // 4))
    pygame.draw.line(surface, theme.LINE, (rect.x + 3, rect.bottom - 2), (rect.right - 4, rect.bottom - 2))
    cx, cy = rect.centerx, rect.centery - 1
    if image:
        surface.blit(image, image.get_rect(center=(cx, cy)))
    else:
        half = size * 0.4
        pygame.draw.line(surface, color, (cx - arrow * half, cy), (cx, cy), max(2, size // 6))
        pygame.draw.polygon(surface, color, [(cx + arrow * half, cy), (cx, cy - half * 0.7), (cx, cy + half * 0.7)])
    return rect


def section(surface: pygame.Surface, title: str, pos: tuple[float, float], size: int, width: int) -> int:
    """A small section heading with a thin line after it. Returns the y below it."""
    rect = theme.draw_text(surface, title, pos, size, theme.TEXT_FAINT, bold=True)
    if rect.right + 10 < pos[0] + width:
        pygame.draw.line(surface, theme.LINE, (rect.right + 10, rect.centery), (pos[0] + width, rect.centery))
    return rect.bottom + max(4, size // 2)


def wrap(text: str, size: int, width: int, bold: bool = False) -> list[str]:
    """Split text into lines that fit `width` pixels (breaking between words)."""
    lines: list[str] = []
    line = ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if not line or theme.text_width(trial, size, bold) <= width:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def fit(text: str, size: int, width: int, bold: bool = False) -> str:
    """Shorten text with '...' until it fits `width` pixels."""
    if theme.text_width(text, size, bold) <= width:
        return text
    while text and theme.text_width(text + "...", size, bold) > width:
        text = text[:-1]
    return text.rstrip() + "..."
