"""
lab.py - the Algorithm Lab: ONE search problem, solved by all FOUR algorithms side by side.

Each panel replays the order in which its algorithm expanded the tiles (lighter = earlier,
stronger = later), all at the same speed, and then draws the path it found. So you can watch:

    BFS      spread in rings (FIFO queue)                -> shortest path, many tiles explored
    DFS      dive down one corridor (LIFO stack)         -> some path, usually a long detour
    A*       head for the goal, but check g + h          -> shortest path, few tiles explored
    Greedy   head for the goal, trusting h only          -> fast, but the path can be longer

Left click sets the start, right click sets the goal (in any of the four panels).
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

import pygame

from ..algorithms import ALGORITHM_NAMES, SearchResult, find_path
from ..benchmark import farthest_pair
from ..maze import Cell
from . import theme, widgets
from .board import BoardView

if TYPE_CHECKING:
    from .app import App

ANIMATION_SECONDS = 9.0          # the slowest algorithm takes about this long to replay
FRONTIER_NAMES = {"BFS": "FIFO queue", "DFS": "LIFO stack", "A*": "min-heap on f = g + h", "Greedy": "min-heap on h"}


class LabScreen:
    def __init__(self, app: App, maze_index: int) -> None:
        self.app = app
        self.maze_index = maze_index
        self.rng = random.Random(maze_index)
        self.boards: dict[str, BoardView] = {}
        self.clock = 0.0
        self.load_maze()

    # ------------------------------------------------------------------------------------
    # The search problem
    # ------------------------------------------------------------------------------------
    def load_maze(self) -> None:
        self.maze = self.app.mazes[self.maze_index]
        self.app.settings.map_index = self.maze_index
        self.boards = {}
        self.set_problem(*farthest_pair(self.maze))

    def set_problem(self, start: Cell, goal: Cell) -> None:
        """Run all four algorithms on the same (start, goal) and restart the replay."""
        self.start, self.goal = start, goal
        self.results: dict[str, SearchResult] = {}
        for name in ALGORITHM_NAMES:
            runs = [find_path(name, self.maze, start, goal) for _ in range(5)]
            self.results[name] = min(runs, key=lambda run: run.time_ms)   # least disturbed timing
        self.shortest = self.results["BFS"].length          # BFS is optimal: the reference
        longest = max(len(result.expanded) for result in self.results.values())
        self.rate = max(6.0, longest / ANIMATION_SECONDS)   # tiles revealed per second
        self.shown = 0.0
        self.playing = True

    def random_problem(self) -> None:
        start, goal = self.rng.sample(self.maze.open_cells, 2)
        self.set_problem(start, goal)

    @property
    def finished(self) -> bool:
        return self.shown >= max(len(result.expanded) for result in self.results.values())

    # ------------------------------------------------------------------------------------
    # Input and time
    # ------------------------------------------------------------------------------------
    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (1, 3):
            for board in self.boards.values():
                cell = board.cell_at(event.pos)
                if cell is not None:
                    if event.button == 1 and cell != self.goal:
                        self.set_problem(cell, self.goal)
                    elif event.button == 3 and cell != self.start:
                        self.set_problem(self.start, cell)
                    return
        if event.type != pygame.KEYDOWN:
            return
        key = event.key
        if key == pygame.K_SPACE:
            if self.finished:
                self.shown = 0.0
            self.playing = not self.playing or self.shown == 0.0
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_END):
            self.shown = float(max(len(result.expanded) for result in self.results.values()))
        elif key == pygame.K_RIGHT:
            self.playing = False
            self.shown = float(int(self.shown) + 1)
        elif key == pygame.K_LEFT:
            self.playing = False
            self.shown = float(max(0, int(self.shown) - 1))
        elif key == pygame.K_r:
            self.set_problem(self.start, self.goal)
        elif key == pygame.K_c:
            self.random_problem()
        elif key == pygame.K_f:
            self.set_problem(*farthest_pair(self.maze))
        elif key == pygame.K_x:
            self.set_problem(self.goal, self.start)
        elif key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
            self.rate = min(self.rate * 1.5, 2000.0)
        elif key in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self.rate = max(self.rate / 1.5, 1.0)
        elif key == pygame.K_n:
            self.maze_index = (self.maze_index + 1) % len(self.app.mazes)
            self.load_maze()
        elif key == pygame.K_g:
            self.maze_index = self.app.new_random_maze()
            self.load_maze()
        elif key in (pygame.K_m, pygame.K_ESCAPE):
            self.app.show_menu()

    def update(self, dt: float) -> None:
        self.clock += dt
        if self.playing and not self.finished:
            self.shown += self.rate * dt

    # ------------------------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------------------------
    def draw(self, surface: pygame.Surface) -> None:
        width, height = surface.get_size()
        self.u = u = theme.ui_scale((width, height))
        surface.fill(theme.BACKGROUND)
        m = round(14 * u)
        panel_width = min(max(round(460 * self.u), 300), width // 2)
        panel = pygame.Rect(width - panel_width, 0, panel_width, height)

        header = pygame.Rect(m, m, panel.x - 2 * m, round(56 * u))
        self._draw_header(surface, header)
        grid = pygame.Rect(m, header.bottom + m, header.w, height - header.bottom - 2 * m)
        gap = round(12 * u)
        cell_w, cell_h = (grid.w - gap) // 2, (grid.h - gap) // 2
        for index, name in enumerate(ALGORITHM_NAMES):
            area = pygame.Rect(grid.x + (index % 2) * (cell_w + gap), grid.y + (index // 2) * (cell_h + gap), cell_w, cell_h)
            self._draw_algorithm(surface, name, area)
        self._draw_panel(surface, panel)

    def fs(self, base: float) -> int:
        return max(11, round(base * self.u))

    def _draw_header(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        title = theme.draw_text(surface, "ALGORITHM LAB", (rect.x, rect.y), self.fs(27), theme.ACCENT, bold=True)
        theme.draw_text(surface, f"{self.maze.name}  -  the same search, four algorithms",
                        (title.right + round(16 * self.u), title.bottom - round(4 * self.u)), self.fs(17),
                        theme.TEXT_DIM, anchor="bottomleft")
        problem = (f"From S {self.start} to G {self.goal}:  the shortest route is {self.shortest} steps.   "
                   f"Left click = new start,  right click = new goal.")
        theme.draw_text(surface, widgets.fit(problem, self.fs(15), rect.w), (rect.x, title.bottom + round(4 * self.u)),
                        self.fs(15), theme.TEXT_FAINT)

    def _draw_algorithm(self, surface: pygame.Surface, name: str, area: pygame.Rect) -> None:
        result, color, u = self.results[name], theme.ALGORITHM_COLORS[name], self.u
        widgets.card(surface, area, theme.PANEL, theme.mix(color, theme.BACKGROUND, 0.6), radius=12)
        pad = round(10 * u)
        head, small = self.fs(19), self.fs(14)

        chip = widgets.chip(surface, name, (area.x + pad, area.y + pad), head, color)
        theme.draw_text(surface, FRONTIER_NAMES[name], (chip.right + round(10 * u), chip.centery), small,
                        theme.TEXT_DIM, anchor="midleft")

        shown = min(int(self.shown), len(result.expanded))
        done = shown >= len(result.expanded)
        if done:
            if result.length == self.shortest:
                verdict, verdict_color = f"path {result.length} steps - shortest", theme.GOOD
            else:
                verdict, verdict_color = f"path {result.length} steps - {result.length - self.shortest} longer", theme.WARN
        else:
            verdict, verdict_color = "searching...", theme.TEXT_DIM
        theme.draw_text(surface, verdict, (area.right - pad, chip.centery), small, verdict_color, bold=True, anchor="midright")

        stats_y = area.bottom - pad - small
        explored = f"explored {shown} / {len(result.expanded)} tiles"
        memory = f"frontier peak {result.max_frontier}"
        theme.draw_text(surface, explored, (area.x + pad, stats_y), small, theme.TEXT)
        theme.draw_text(surface, memory, (area.right - pad, stats_y), small, theme.TEXT_DIM, anchor="topright")

        board_area = pygame.Rect(area.x + pad, chip.bottom + pad, area.w - 2 * pad, stats_y - chip.bottom - 2 * pad)
        board = self.boards.get(name)
        if board is None:
            board = self.boards[name] = BoardView(self.maze, board_area)
        board.resize(board_area)
        board.draw_maze(surface)
        fx = board.begin_fx()
        board.shade_gradient(fx, result.expanded[:shown], color)
        if not done and shown > 0:                         # the tile being expanded right now
            board.shade_cells(fx, [result.expanded[shown - 1]], theme.WHITE, 230)
        if done:
            board.draw_path_line(fx, result.path, theme.WHITE)
        board.end_fx(surface)
        self._draw_marker(surface, board, self.start, "S", theme.ACCENT)
        self._draw_marker(surface, board, self.goal, "G", theme.WARN)

    def _draw_marker(self, surface: pygame.Surface, board: BoardView, cell: Cell, letter: str, color: theme.Color) -> None:
        center = board.cell_center(cell)
        radius = max(8, board.tile * 0.62)
        pygame.draw.circle(surface, theme.INK, center, radius + 2)
        pygame.draw.circle(surface, color, center, radius)
        theme.draw_text(surface, letter, center, max(11, round(radius * 1.3)), theme.INK, bold=True, anchor="center")

    def _draw_panel(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        pygame.draw.rect(surface, theme.PANEL, rect)
        pygame.draw.line(surface, theme.LINE, rect.topleft, rect.bottomleft)
        u = self.u
        pad = round(18 * u)
        x, y, width = rect.x + pad, rect.y + pad, rect.w - 2 * pad
        head, body, small = self.fs(13), self.fs(16), self.fs(14)

        # --- results: explored tiles as bars (fewer = better) --------------------------------------
        y = widgets.section(surface, "TILES EXPLORED  (fewer = faster)", (x, y), head, width)
        most = max(len(result.expanded) for result in self.results.values())
        label_width = round(70 * u)
        for name in ALGORITHM_NAMES:
            result = self.results[name]
            color = theme.ALGORITHM_COLORS[name]
            shown = min(int(self.shown), len(result.expanded))
            theme.draw_text(surface, name, (x, y), body, color, bold=True)
            bar = pygame.Rect(x + label_width, y + round(body * 0.25), width - label_width - round(48 * u), round(body * 0.7))
            widgets.bar(surface, bar, shown / max(most, 1), color)
            theme.draw_text(surface, str(shown), (x + width, y), body, theme.TEXT, anchor="topright")
            y += round(body * 1.6)

        y += round(8 * u)
        y = widgets.section(surface, "PATH LENGTH  (BFS = shortest)", (x, y), head, width)
        for name in ALGORITHM_NAMES:
            result = self.results[name]
            done = int(self.shown) >= len(result.expanded)
            theme.draw_text(surface, name, (x, y), body, theme.ALGORITHM_COLORS[name], bold=True)
            if not done:
                text, color = "...", theme.TEXT_FAINT
            elif result.length == self.shortest:
                text, color = f"{result.length} steps   shortest", theme.GOOD
            else:
                text, color = f"{result.length} steps   +{result.length - self.shortest}", theme.WARN
            theme.draw_text(surface, text, (x + label_width, y), body, color)
            theme.draw_text(surface, f"{result.time_ms * 1000:.0f} µs", (x + width, y), small, theme.TEXT_FAINT, anchor="topright")
            y += round(body * 1.5)

        y += round(8 * u)
        y = widgets.section(surface, "WHAT TO NOTICE", (x, y), head, width)
        notes = [
            ("BFS", "spreads in rings, so the first time it reaches the goal it is by a shortest path"),
            ("DFS", "dives down one corridor and keeps the first route it finds - rarely the shortest"),
            ("A*", "BFS with a sense of direction: g + h ranks the tiles, still always the shortest"),
            ("Greedy", "trusts h alone: very few tiles, but walls can trick it into a detour"),
        ]
        for name, note in notes:
            theme.draw_text(surface, name, (x, y), small, theme.ALGORITHM_COLORS[name], bold=True)
            for line in widgets.wrap(note, small, width - label_width):
                theme.draw_text(surface, line, (x + label_width, y), small, theme.TEXT_DIM)
                y += round(small * 1.35)
            y += round(small * 0.35)

        # --- keys, drawn upward from the bottom ---------------------------------------------------
        keys = [("Space", "play / pause"), ("Enter", "show the result"), ("<-", "one tile back"), ("->", "one tile forward"),
                ("+ -", "replay speed"), ("C", "random start + goal"), ("F", "farthest pair"),
                ("X", "swap start and goal"), ("N", "next map"), ("G", "random labyrinth"), ("M", "menu")]
        row = round(small * 1.95)
        column = width // 2
        top = rect.bottom - pad - ((len(keys) + 1) // 2) * row - round(head * 1.8)
        if top > y + pad:
            ky = widgets.section(surface, "KEYS", (x, top), head, width)
            for index, (key, text) in enumerate(keys):
                cap = widgets.key_cap(surface, key, (x + (index % 2) * column, ky + (index // 2) * row), small)
                theme.draw_text(surface, widgets.fit(text, small, column - cap.w - 12), (cap.right + 6, cap.centery),
                                small, theme.TEXT_DIM, anchor="midleft")
