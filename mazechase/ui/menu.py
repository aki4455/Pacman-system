"""
menu.py - the start screen: choose a map, the runner's algorithm and the number of hunters,
then play or open the Algorithm Lab. Works with the keyboard and the mouse.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import pygame

from ..algorithms import ALGORITHM_NAMES, DESCRIPTIONS
from ..config import HUNTERS
from ..game import Game
from . import theme, widgets
from .board import BoardView

if TYPE_CHECKING:
    from .app import App


class MenuScreen:
    def __init__(self, app: App) -> None:
        self.app = app
        self.clock = 0.0
        self.hits: list[tuple[pygame.Rect, Callable[[], None]]] = []   # clickable areas
        self.mouse = (-1, -1)
        self.preview: Game | None = None
        self.preview_board: BoardView | None = None

    @property
    def settings(self):
        return self.app.settings

    # ------------------------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------------------------
    def select_map(self, index: int) -> None:
        self.settings.map_index = index % len(self.app.mazes)

    def select_algorithm(self, name: str) -> None:
        self.settings.runner_algorithm = name

    def shift_algorithm(self, delta: int) -> None:
        index = ALGORITHM_NAMES.index(self.settings.runner_algorithm)
        self.settings.runner_algorithm = ALGORITHM_NAMES[(index + delta) % len(ALGORITHM_NAMES)]

    def set_hunters(self, count: int) -> None:
        self.settings.hunter_count = max(1, min(len(HUNTERS), count))

    def new_random_maze(self) -> None:
        self.settings.map_index = self.app.new_random_maze()

    def toggle_autoplay(self) -> None:
        self.settings.autoplay = not self.settings.autoplay

    # ------------------------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------------------------
    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEMOTION:
            self.mouse = event.pos
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for rect, action in self.hits:
                if rect.collidepoint(event.pos):
                    action()
                    return
        elif event.type == pygame.MOUSEWHEEL:
            self.select_map(self.settings.map_index - event.y)
        elif event.type == pygame.KEYDOWN:
            key = event.key
            if key == pygame.K_UP:
                self.select_map(self.settings.map_index - 1)
            elif key == pygame.K_DOWN:
                self.select_map(self.settings.map_index + 1)
            elif key == pygame.K_LEFT:
                self.shift_algorithm(-1)
            elif key == pygame.K_RIGHT:
                self.shift_algorithm(+1)
            elif pygame.K_1 <= key < pygame.K_1 + len(ALGORITHM_NAMES):
                self.select_algorithm(ALGORITHM_NAMES[key - pygame.K_1])
            elif key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                self.set_hunters(self.settings.hunter_count + 1)
            elif key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                self.set_hunters(self.settings.hunter_count - 1)
            elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self.app.start_game(self.settings.map_index)
            elif key == pygame.K_l:
                self.app.open_lab(self.settings.map_index)
            elif key == pygame.K_g:
                self.new_random_maze()
            elif key == pygame.K_a:
                self.toggle_autoplay()
            elif key in (pygame.K_ESCAPE, pygame.K_q):
                self.app.quit()

    def update(self, dt: float) -> None:
        self.clock += dt

    # ------------------------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------------------------
    def draw(self, surface: pygame.Surface) -> None:
        width, height = surface.get_size()
        u = theme.ui_scale((width, height))
        fs = lambda base: max(11, round(base * u))                      # noqa: E731
        m = round(36 * u)
        self.hits = []
        surface.fill(theme.BACKGROUND)

        # --- title ---------------------------------------------------------------------------
        title = theme.draw_text(surface, "MAZE CHASE AI", (m, m), fs(46), theme.ACCENT, bold=True)
        subtitle = ("A self-playing maze chase: every move of the runner and of the hunters is "
                    "decided by a search algorithm - BFS, DFS, A* or Greedy best-first.")
        y = title.bottom + round(4 * u)
        for line in widgets.wrap(subtitle, fs(18), width - 2 * m):
            theme.draw_text(surface, line, (m, y), fs(18), theme.TEXT_DIM)
            y += round(fs(18) * 1.35)
        top = y + round(22 * u)

        left_width = max(round(width * 0.34), 330)
        left = pygame.Rect(m, top, left_width, height - top - m)
        right = pygame.Rect(left.right + m, top, width - left.right - 2 * m, height - top - m)
        self._draw_options(surface, left, u, fs)
        self._draw_preview(surface, right, u, fs)

    def _button(self, surface: pygame.Surface, rect: pygame.Rect, label: str, hint: str, size: int,
                action: Callable[[], None], primary: bool = False) -> None:
        hover = rect.collidepoint(self.mouse)
        fill = theme.ACCENT if primary else (theme.CARD_LIGHT if hover else theme.CARD)
        if primary and hover:
            fill = theme.mix(theme.ACCENT, theme.WHITE, 0.25)
        widgets.card(surface, rect, fill, None if primary else theme.LINE, radius=rect.h // 2)
        color = theme.INK if primary else theme.TEXT
        theme.draw_text(surface, label, (rect.x + rect.h * 0.55, rect.centery), size, color, bold=True, anchor="midleft")
        theme.draw_text(surface, hint, (rect.right - rect.h * 0.55, rect.centery), round(size * 0.8),
                        theme.INK if primary else theme.TEXT_FAINT, anchor="midright")
        self.hits.append((rect, action))

    def _draw_options(self, surface: pygame.Surface, area: pygame.Rect, u: float, fs) -> None:
        settings, x, width = self.settings, area.x, area.w
        head, body, small = fs(14), fs(18), fs(14)
        y = widgets.section(surface, "MAP   (Up / Down)", (x, area.y), head, width)

        row_height = round(body * 2.0)
        for index, maze in enumerate(self.app.mazes):
            rect = pygame.Rect(x, y, width, row_height - round(5 * u))
            selected = index == settings.map_index
            hover = rect.collidepoint(self.mouse)
            fill = theme.CARD_LIGHT if selected else (theme.CARD if hover else theme.BACKGROUND)
            widgets.card(surface, rect, fill, theme.ACCENT if selected else None, radius=8)
            theme.draw_text(surface, f"{index + 1}", (rect.x + body * 0.8, rect.centery), small,
                            theme.ACCENT if selected else theme.TEXT_FAINT, bold=True, anchor="center")
            name = maze.name if index < len(self.app.mazes) - 1 else "Random Labyrinth"
            theme.draw_text(surface, name, (rect.x + body * 1.7, rect.centery), body,
                                    theme.TEXT if selected else theme.TEXT_DIM, bold=selected, anchor="midleft")
            info = f"{maze.width} x {maze.height}"
            if index == len(self.app.mazes) - 1:
                info = "G = new one   " + info
            theme.draw_text(surface, info, (rect.right - body * 0.7, rect.centery), small, theme.TEXT_FAINT, anchor="midright")
            self.hits.append((rect, lambda index=index: self.select_map(index)))
            y += row_height

        y += round(14 * u)
        y = widgets.section(surface, "RUNNER ALGORITHM   (Left / Right or 1-4)", (x, y), head, width)
        cx = x
        for name in ALGORITHM_NAMES:
            selected = name == settings.runner_algorithm
            chip = widgets.chip(surface, f" {name} ", (cx, y), body, theme.ALGORITHM_COLORS[name], filled=selected)
            self.hits.append((chip, lambda name=name: self.select_algorithm(name)))
            cx = chip.right + round(10 * u)
        y = chip.bottom + round(8 * u)
        theme.draw_text(surface, widgets.fit(DESCRIPTIONS[settings.runner_algorithm], small, width), (x, y), small, theme.TEXT_DIM)
        y += round(small * 2.2)

        y = widgets.section(surface, "HUNTERS   (+ / -)", (x, y), head, width)
        cx = x
        for count in range(1, len(HUNTERS) + 1):
            selected = count == settings.hunter_count
            chip = widgets.chip(surface, f"  {count}  ", (cx, y), body, theme.TEXT, filled=selected)
            self.hits.append((chip, lambda count=count: self.set_hunters(count)))
            cx = chip.right + round(10 * u)
        auto = widgets.chip(surface, f"Autoplay {'ON' if settings.autoplay else 'OFF'}  (A)", (x + width, chip.y),
                            small, theme.GOOD if settings.autoplay else theme.TEXT_FAINT, filled=settings.autoplay,
                            anchor="topright")
        self.hits.append((auto, self.toggle_autoplay))
        y = chip.bottom + round(26 * u)

        button_height = round(body * 2.6)
        gap = round(12 * u)
        buttons_top = max(y, area.bottom - 3 * button_height - 2 * gap)

        # "How it works", in the space left above the buttons
        about = ("The maze is a GRAPH: every open tile is a vertex, neighbouring tiles are joined by an "
                 "edge. On every tile, every agent searches that graph to choose its next step - the runner "
                 "(cyan) with the algorithm chosen above, every hunter with its own. Nobody plays by hand.")
        lines = widgets.wrap(about, small, width)
        if y + head * 2 + len(lines) * small * 1.4 < buttons_top - gap:
            y = widgets.section(surface, "HOW IT WORKS", (x, y), head, width)
            for line in lines:
                theme.draw_text(surface, line, (x, y), small, theme.TEXT_DIM)
                y += round(small * 1.4)
        self._button(surface, pygame.Rect(x, buttons_top, width, button_height), "PLAY", "Enter", fs(21),
                     lambda: self.app.start_game(settings.map_index), primary=True)
        self._button(surface, pygame.Rect(x, buttons_top + button_height + gap, width, button_height),
                     "ALGORITHM LAB", "L", fs(19), lambda: self.app.open_lab(settings.map_index))
        self._button(surface, pygame.Rect(x, buttons_top + 2 * (button_height + gap), width, button_height),
                     "QUIT", "Esc", fs(19), self.app.quit)

    def _draw_preview(self, surface: pygame.Surface, area: pygame.Rect, u: float, fs) -> None:
        settings = self.settings
        maze = self.app.mazes[settings.map_index]
        body, small = fs(17), fs(14)

        # The roster of hunters (bottom), the description (middle), the map preview (top).
        roster_height = round(body * 5.6)
        roster = pygame.Rect(area.x, area.bottom - roster_height, area.w, roster_height)
        text_lines = widgets.wrap(maze.description, body, area.w)[:3]
        info_height = round(len(text_lines) * body * 1.4 + small * 3.2)
        board_area = pygame.Rect(area.x, area.y, area.w, roster.top - info_height - area.y - round(10 * u))

        wanted = (maze, settings.runner_algorithm, settings.hunter_count)
        if self.preview is None or (self.preview.maze, self.preview.runner.algorithm, len(self.preview.hunters)) != wanted:
            self.preview = Game(*wanted, seed=settings.seed)
            self.preview_board = None
        if self.preview_board is None or self.preview_board.maze is not maze:
            self.preview_board = BoardView(maze, board_area)
        board = self.preview_board
        board.resize(board_area)
        board.draw_maze(surface)
        board.draw_food(surface, self.preview.pellets, self.preview.power_orbs, self.clock)
        for hunter in self.preview.hunters:
            board.draw_hunter(surface, hunter, self.clock, 0.0)
        board.draw_runner(surface, self.preview.runner, [], self.clock)

        y = board.rect.bottom + round(12 * u)
        x = board.rect.x
        line_width = board.rect.w
        for line in widgets.wrap(maze.description, body, line_width)[:3]:
            theme.draw_text(surface, line, (x, y), body, theme.TEXT)
            y += round(body * 1.4)
        stats = (f"Graph: {maze.vertex_count} vertices (open tiles), {maze.edge_count} edges"
                 f"   ·   tunnels: {'yes' if maze.has_tunnels else 'no'}   ·   food: {len(maze.pellets) + len(maze.power_orbs)}")
        theme.draw_text(surface, widgets.fit(stats, small, line_width), (x, y + round(4 * u)), small, theme.TEXT_FAINT)

        # roster: one small card per hunter
        gap = round(10 * u)
        card_width = (roster.w - 3 * gap) // 4
        for index, profile in enumerate(HUNTERS):
            rect = pygame.Rect(roster.x + index * (card_width + gap), roster.y, card_width, roster.h)
            active = index < settings.hunter_count
            widgets.card(surface, rect, theme.CARD if active else theme.BACKGROUND,
                         theme.mix(profile.color, theme.BACKGROUND, 0.45) if active else theme.LINE)
            pad = round(12 * u)
            name_color = profile.color if active else theme.TEXT_FAINT
            name = theme.draw_text(surface, profile.name, (rect.x + pad, rect.y + pad), body, name_color, bold=True)
            widgets.chip(surface, profile.algorithm, (rect.right - pad, name.centery), small,
                         profile.color if active else theme.TEXT_FAINT, filled=active, anchor="midright")
            ty = name.bottom + round(6 * u)
            for line in widgets.wrap(profile.summary, small, rect.w - 2 * pad)[:3]:
                theme.draw_text(surface, line, (rect.x + pad, ty), small, theme.TEXT_DIM if active else theme.TEXT_FAINT)
                ty += round(small * 1.35)
