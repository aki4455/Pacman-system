"""
board.py - draws everything that lives inside the maze: walls, food, agents and the
algorithm overlays (planned routes, explored tiles, the runner's territory).

A BoardView knows where on the screen the maze is and how big a tile is. The game screen,
the menu preview and the four panels of the Algorithm Lab each use their own BoardView.
"""

from __future__ import annotations

import math
from collections.abc import Iterable

import pygame

from ..agents import Hunter, Runner
from ..config import RESPAWN_DELAY
from ..maze import Cell, Maze
from . import theme


class BoardView:
    def __init__(self, maze: Maze, area: pygame.Rect) -> None:
        self.maze = maze
        self.area = pygame.Rect(0, 0, 0, 0)
        self.resize(area)

    # ------------------------------------------------------------------------------------
    # Geometry
    # ------------------------------------------------------------------------------------
    def resize(self, area: pygame.Rect) -> None:
        """Fit the maze into `area` with square tiles, centred. Cheap if nothing changed."""
        if pygame.Rect(area) == self.area:
            return
        self.area = pygame.Rect(area)
        self.tile = max(3, min(self.area.w // self.maze.width, self.area.h // self.maze.height))
        self.rect = pygame.Rect(0, 0, self.tile * self.maze.width, self.tile * self.maze.height)
        self.rect.center = self.area.center
        self._static = self._render_static()
        self._fx = pygame.Surface(self.rect.size, pygame.SRCALPHA)   # for see-through drawing
        if pygame.display.get_surface() is not None:                  # match the screen format:
            self._static = self._static.convert()                    # copying is much faster
            self._fx = self._fx.convert_alpha()

    def cell_center(self, cell: Cell) -> tuple[float, float]:
        return self.pos_to_px((float(cell[0]), float(cell[1])))

    def pos_to_px(self, pos: tuple[float, float]) -> tuple[float, float]:
        """(row, col) - possibly between two tiles - to the pixel at the middle of it."""
        row, col = pos
        return (self.rect.x + (col + 0.5) * self.tile, self.rect.y + (row + 0.5) * self.tile)

    def cell_at(self, pixel: tuple[int, int]) -> Cell | None:
        """The open tile under a pixel (mouse clicks), or None."""
        if not self.rect.collidepoint(pixel):
            return None
        cell = ((pixel[1] - self.rect.y) // self.tile, (pixel[0] - self.rect.x) // self.tile)
        return cell if self.maze.is_open(cell) else None

    def _copies(self, x: float) -> list[float]:
        """An agent half-way through a tunnel is drawn on both sides of the maze."""
        xs = [x]
        if self.maze.has_tunnels:
            if x < self.rect.x + self.tile:
                xs.append(x + self.rect.w)
            elif x > self.rect.right - self.tile:
                xs.append(x - self.rect.w)
        return xs

    # ------------------------------------------------------------------------------------
    # The maze itself
    # ------------------------------------------------------------------------------------
    def _render_static(self) -> pygame.Surface:
        """Draw floor and walls once into an image; every frame just copies that image."""
        maze, t = self.maze, self.tile
        floor, fill, edge = theme.MAP_THEMES.get(maze.theme, theme.MAP_THEMES["teal"])
        image = pygame.Surface(self.rect.size)
        image.fill(floor)

        grid_line = theme.mix(floor, edge, 0.07)            # faint grid: the maze is a grid graph
        for cell in maze.open_cells:
            pygame.draw.rect(image, grid_line, (cell[1] * t, cell[0] * t, t, t), 1)

        def is_wall(row: int, col: int) -> bool:
            outside = not (0 <= row < maze.height and 0 <= col < maze.width)
            return outside or (row, col) in maze.walls

        border = max(1, t // 9)
        radius = max(2, t // 3)
        outer_fill = theme.mix(fill, floor, 0.55)          # the outer wall ring is a bit quieter
        for row, col in maze.walls:
            x, y = col * t, row * t
            on_border = row in (0, maze.height - 1) or col in (0, maze.width - 1)
            up, down = is_wall(row - 1, col), is_wall(row + 1, col)
            left, right = is_wall(row, col - 1), is_wall(row, col + 1)
            # round a corner only where both sides of it face open floor
            tl = radius if not up and not left else 0
            tr = radius if not up and not right else 0
            bl = radius if not down and not left else 0
            br = radius if not down and not right else 0
            pygame.draw.rect(image, edge, (x, y, t, t), border_top_left_radius=tl, border_top_right_radius=tr,
                             border_bottom_left_radius=bl, border_bottom_right_radius=br)
            inner = pygame.Rect(x + (0 if left else border), y + (0 if up else border), 0, 0)
            inner.w = t - (0 if left else border) - (0 if right else border)
            inner.h = t - (0 if up else border) - (0 if down else border)
            pygame.draw.rect(image, outer_fill if on_border else fill, inner,
                             border_top_left_radius=max(0, tl - border), border_top_right_radius=max(0, tr - border),
                             border_bottom_left_radius=max(0, bl - border), border_bottom_right_radius=max(0, br - border))
            # inner (concave) corners: both sides are walls, but the diagonal tile is open
            for d_row, d_col, side_a, side_b in ((-1, -1, up, left), (-1, 1, up, right), (1, -1, down, left), (1, 1, down, right)):
                if side_a and side_b and not is_wall(row + d_row, col + d_col):
                    cx = x if d_col < 0 else x + t - border
                    cy = y if d_row < 0 else y + t - border
                    pygame.draw.rect(image, edge, (cx, cy, border, border))
        return image

    def draw_maze(self, surface: pygame.Surface) -> None:
        surface.blit(self._static, self.rect)

    def draw_food(self, surface: pygame.Surface, pellets: Iterable[Cell], orbs: Iterable[Cell], clock: float) -> None:
        t = self.tile
        pellet_radius = max(1.5, t * 0.1)
        for cell in pellets:
            pygame.draw.circle(surface, theme.PELLET, self.cell_center(cell), pellet_radius)
        pulse = 0.5 + 0.5 * math.sin(clock * 5.0)
        for cell in orbs:
            center = self.cell_center(cell)
            pygame.draw.circle(surface, theme.mix(theme.POWER_ORB, theme.BACKGROUND, 0.45), center,
                               t * (0.34 + 0.06 * pulse), max(1, t // 14))
            pygame.draw.circle(surface, theme.POWER_ORB, center, t * (0.17 + 0.05 * pulse))

    # ------------------------------------------------------------------------------------
    # Overlays: see-through layers that show what the algorithms are doing
    # ------------------------------------------------------------------------------------
    def begin_fx(self) -> pygame.Surface:
        self._fx.fill((0, 0, 0, 0))
        return self._fx

    def end_fx(self, surface: pygame.Surface) -> None:
        surface.blit(self._fx, self.rect)

    def shade_cells(self, fx: pygame.Surface, cells: Iterable[Cell], color: theme.Color, alpha: int) -> None:
        t = self.tile
        for row, col in cells:
            fx.fill((*color, alpha), (col * t, row * t, t, t))

    def shade_gradient(self, fx: pygame.Surface, cells: list[Cell], color: theme.Color) -> None:
        """Shade tiles in the order they were explored: early = light, late = strong."""
        t = self.tile
        count = max(1, len(cells))
        for index, (row, col) in enumerate(cells):
            alpha = int(55 + 120 * index / count)
            fx.fill((*color, alpha), (col * t, row * t, t, t))

    def draw_territory(self, fx: pygame.Surface, runner: Runner) -> None:
        """Green = the runner gets there first.  Red = a hunter gets there first (darker = sooner)."""
        if not runner.danger:
            return
        t = self.tile
        for cell in self.maze.open_cells:
            row, col = cell
            if cell in runner.territory:
                fx.fill((*theme.GOOD, 38), (col * t, row * t, t, t))
            else:
                steps = runner.danger.get(cell, 99)
                fx.fill((*theme.BAD, 120 if steps <= 1 else 85 if steps <= 3 else 50), (col * t, row * t, t, t))

    def draw_route(self, fx: pygame.Surface, start: Cell | None, route: list[Cell], goal: Cell | None,
                   color: theme.Color, big: bool = False) -> None:
        """The planned route as a dotted line, plus a target marker on the goal."""
        t = self.tile
        cells = ([start] if start is not None else []) + route
        radius = t * (0.13 if big else 0.1)
        for row, col in cells:
            pygame.draw.circle(fx, (*color, 215 if big else 175), ((col + 0.5) * t, (row + 0.5) * t), radius)
        if goal is not None:
            gx, gy = (goal[1] + 0.5) * t, (goal[0] + 0.5) * t
            pygame.draw.circle(fx, (*color, 230), (gx, gy), t * 0.42, max(2, t // 12))
            pygame.draw.line(fx, (*color, 230), (gx - t * 0.55, gy), (gx + t * 0.55, gy), max(1, t // 16))
            pygame.draw.line(fx, (*color, 230), (gx, gy - t * 0.55), (gx, gy + t * 0.55), max(1, t // 16))

    def draw_path_line(self, fx: pygame.Surface, path: list[Cell], color: theme.Color) -> None:
        """A solid line through a path (used by the Algorithm Lab). Tunnel jumps are not drawn."""
        t = self.tile
        width = max(2, t // 5)
        for a, b in zip(path, path[1:]):
            if abs(a[1] - b[1]) > 1:
                continue
            pygame.draw.line(fx, (*color, 255), ((a[1] + 0.5) * t, (a[0] + 0.5) * t),
                             ((b[1] + 0.5) * t, (b[0] + 0.5) * t), width)
        for row, col in path[:1] + path[-1:]:
            pygame.draw.circle(fx, (*color, 255), ((col + 0.5) * t, (row + 0.5) * t), t * 0.32)

    # ------------------------------------------------------------------------------------
    # Agents
    # ------------------------------------------------------------------------------------
    def draw_runner(self, surface: pygame.Surface, runner: Runner, trail: list[tuple[float, float]],
                    clock: float, hurt: bool = False) -> None:
        t = self.tile
        fx = self.begin_fx()
        for index, pos in enumerate(trail):                     # fading motion trail
            x, y = self.pos_to_px(pos)
            share = (index + 1) / (len(trail) + 1)
            pygame.draw.circle(fx, (*runner.color, int(70 * share)), (x - self.rect.x, y - self.rect.y), t * 0.3 * share)
        x, y = self.pos_to_px(runner.position)
        for gx in self._copies(x):
            pygame.draw.circle(fx, (*runner.color, 45), (gx - self.rect.x, y - self.rect.y), t * 0.75)
        self.end_fx(surface)

        if hurt and int(clock * 8) % 2 == 0:                    # blink after being caught
            return
        radius = t * 0.4
        d_row, d_col = runner.direction if runner.direction != (0, 0) else (0, 1)
        surface.set_clip(self.rect)
        for gx in self._copies(x):
            pygame.draw.circle(surface, theme.mix(runner.color, theme.INK, 0.45), (gx, y), radius)
            pygame.draw.circle(surface, runner.color, (gx, y), radius - max(1, t // 14))
            ex, ey = gx + d_col * radius * 0.32, y + d_row * radius * 0.32
            pygame.draw.circle(surface, theme.WHITE, (ex, ey), radius * 0.36)
            pygame.draw.circle(surface, theme.INK, (ex + d_col * radius * 0.13, ey + d_row * radius * 0.13), radius * 0.17)
        surface.set_clip(None)

    def draw_hunter(self, surface: pygame.Surface, hunter: Hunter, clock: float, power_left: float) -> None:
        t = self.tile
        x, y = self.pos_to_px(hunter.position)
        if not hunter.is_visible:                               # respawning: a ring that fills up
            share = 1.0 - max(0.0, hunter.timer) / RESPAWN_DELAY
            ring = pygame.Rect(0, 0, t * 0.8, t * 0.8)
            ring.center = (round(x), round(y))
            pygame.draw.circle(surface, theme.mix(hunter.color, theme.BACKGROUND, 0.7), ring.center, t * 0.4, 1)
            pygame.draw.arc(surface, hunter.color, ring, math.pi / 2, math.pi / 2 + 2 * math.pi * share, max(2, t // 10))
            return

        size = t * 0.8
        scared = hunter.is_scared
        wobble = math.sin(clock * 18 + hunter.spawn[1]) * t * 0.05 if scared else 0.0
        if scared:
            blinking = power_left < 2.0 and int(clock * 6) % 2 == 0
            body, outline = theme.SCARED_BODY, (theme.WHITE if blinking else hunter.color)
        else:
            body, outline = hunter.color, theme.mix(hunter.color, theme.INK, 0.5)
        d_row, d_col = hunter.direction

        surface.set_clip(self.rect)
        for gx in self._copies(x):
            rect = pygame.Rect(0, 0, size, size)
            rect.center = (round(gx + wobble), round(y))
            pygame.draw.rect(surface, outline, rect, border_radius=int(size * 0.32))
            pygame.draw.rect(surface, body, rect.inflate(-max(2, t // 8), -max(2, t // 8)), border_radius=int(size * 0.28))
            antenna = (rect.centerx, rect.top - t * 0.08)
            pygame.draw.line(surface, outline, (rect.centerx, rect.top + 2), antenna, max(1, t // 16))
            pygame.draw.circle(surface, outline, antenna, max(2, t * 0.07))
            for side in (-1, 1):
                ex, ey = rect.centerx + side * size * 0.2, rect.centery - size * 0.05
                if scared:
                    pygame.draw.circle(surface, theme.WHITE, (ex, ey), size * 0.08)
                else:
                    pygame.draw.circle(surface, theme.WHITE, (ex, ey), size * 0.15)
                    pygame.draw.circle(surface, theme.INK, (ex + d_col * size * 0.06, ey + d_row * size * 0.06), size * 0.075)
            if hunter.mode == "WAITING":                       # countdown ring before release
                share = max(0.0, hunter.timer) / max(hunter.release_delay, 0.001)
                ring = rect.inflate(t * 0.3, t * 0.3)
                pygame.draw.arc(surface, theme.TEXT_DIM, ring, math.pi / 2, math.pi / 2 + 2 * math.pi * share, max(1, t // 14))
        surface.set_clip(None)

    def draw_label(self, surface: pygame.Surface, pos: tuple[float, float], text: str, color: theme.Color,
                   below: bool = False) -> None:
        """A small name tag above (or below) an agent."""
        x, y = self.pos_to_px(pos)
        size = max(10, int(self.tile * 0.34))
        image = theme.render(text, size, color, bold=True)
        if below:
            box = image.get_rect(midtop=(round(x), round(y + self.tile * 0.55)))
        else:
            box = image.get_rect(midbottom=(round(x), round(y - self.tile * 0.55)))
        box.clamp_ip(self.rect)
        pad = box.inflate(8, 2)
        pygame.draw.rect(surface, theme.INK, pad, border_radius=pad.h // 2)
        pygame.draw.rect(surface, theme.mix(color, theme.INK, 0.4), pad, 1, border_radius=pad.h // 2)
        surface.blit(image, box)
