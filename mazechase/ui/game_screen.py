"""
game_screen.py - the self-playing game, with the AI's thinking made visible.

    left    the board, with switchable overlays:
              P  routes        every agent's planned route and its goal
              V  explored      the tiles the runner's last search expanded
              D  danger map    green = the runner's territory, red = the hunters' side
              L  labels        name and algorithm above every agent
    right   the side panel: what the runner is doing and WHY, every hunter's state,
            recent events and the keys

All game logic lives in game.py. This screen only advances it in fixed time steps, draws it
and reacts to keys.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from ..agents.agent import steps
from ..algorithms import ALGORITHM_NAMES, DESCRIPTIONS
from ..config import POWER_DURATION, START_LIVES, TICK, TIME_LIMIT
from ..game import CAUGHT, CLEARED, GAME_OVER, Game
from . import theme, widgets
from .board import BoardView

if TYPE_CHECKING:
    from .app import App

SPEEDS = (0.25, 0.5, 1.0, 2.0, 4.0, 8.0)
AUTOPLAY_DELAY = 6.0                 # seconds the result card stays up before autoplay moves on
TRAIL_LENGTH = 10
ALGORITHM_KEYS = {**{pygame.K_1 + i: name for i, name in enumerate(ALGORITHM_NAMES)},
                  **{pygame.K_KP1 + i: name for i, name in enumerate(ALGORITHM_NAMES)}}
RUNNER_MODE_COLORS = {"EAT": theme.GOOD, "ESCAPE": theme.WARN, "HUNT": theme.POWER_ORB, "TRAPPED": theme.BAD}
RESULT_TITLES = {CLEARED: ("MAP CLEARED!", theme.GOOD), GAME_OVER: ("GAME OVER", theme.BAD)}


class GameScreen:
    def __init__(self, app: App, maze_index: int) -> None:
        self.app = app
        self.maze_index = maze_index
        self.speed_index = min(range(len(SPEEDS)), key=lambda i: abs(SPEEDS[i] - app.settings.speed))
        self.paused = False
        self.show_routes = True
        self.show_explored = False
        self.show_danger = False
        self.show_labels = True
        self.board: BoardView | None = None
        self.start_round(app.settings.seed)

    # ------------------------------------------------------------------------------------
    # Rounds
    # ------------------------------------------------------------------------------------
    def start_round(self, seed: int) -> None:
        settings = self.app.settings
        settings.map_index, settings.seed = self.maze_index, seed
        self.seed = seed
        self.game = Game(self.app.mazes[self.maze_index], settings.runner_algorithm, settings.hunter_count, seed)
        self.accumulator = 0.0                 # game time owed to the simulation (fixed steps)
        self.trail: list[tuple[float, float]] = []
        self.end_timer = 0.0
        self.clock = 0.0                       # for animations (blinking, pulsing)

    def next_map(self) -> None:
        self.maze_index = (self.maze_index + 1) % len(self.app.mazes)
        self.start_round(self.seed)

    def random_maze(self) -> None:
        self.maze_index = self.app.new_random_maze()
        self.start_round(self.seed)

    def step(self) -> None:
        """Paused: play until the runner reaches its next tile - exactly one more decision."""
        self.paused = True
        game = self.game
        cell, status = game.runner.cell, game.status
        for _ in range(int(3.0 / TICK)):
            game.update(TICK)
            if game.runner.cell != cell or game.status != status:
                break

    # ------------------------------------------------------------------------------------
    # Input and time
    # ------------------------------------------------------------------------------------
    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        key = event.key
        if key == pygame.K_SPACE:
            self.paused = not self.paused
        elif key in (pygame.K_RIGHT, pygame.K_PERIOD):
            self.step()
        elif key in ALGORITHM_KEYS:
            self.app.settings.runner_algorithm = ALGORITHM_KEYS[key]
            self.game.set_runner_algorithm(ALGORITHM_KEYS[key])
        elif key == pygame.K_p:
            self.show_routes = not self.show_routes
        elif key == pygame.K_v:
            self.show_explored = not self.show_explored
        elif key == pygame.K_d:
            self.show_danger = not self.show_danger
        elif key == pygame.K_l:
            self.show_labels = not self.show_labels
        elif key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
            self.speed_index = min(self.speed_index + 1, len(SPEEDS) - 1)
        elif key in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self.speed_index = max(self.speed_index - 1, 0)
        elif key == pygame.K_r:
            self.start_round(self.seed)                  # same seed -> exactly the same game again
        elif key == pygame.K_s:
            self.start_round(self.seed + 1)              # new seed -> hunters patrol differently
        elif key == pygame.K_n:
            self.next_map()
        elif key == pygame.K_g:
            self.random_maze()
        elif key == pygame.K_a:
            self.app.settings.autoplay = not self.app.settings.autoplay
        elif key in (pygame.K_m, pygame.K_ESCAPE):
            self.app.settings.speed = SPEEDS[self.speed_index]
            self.app.show_menu()

    def update(self, dt: float) -> None:
        self.clock += dt
        game = self.game
        if not self.paused and not game.is_over:
            # Fixed time step: the game always advances in steps of exactly TICK seconds, however
            # fast or slow the screen is. That keeps every game repeatable.
            self.accumulator += dt * SPEEDS[self.speed_index]
            steps = 0
            while self.accumulator >= TICK and steps < 120 and not game.is_over:
                game.update(TICK)
                self.accumulator -= TICK
                steps += 1
            if game.status == CAUGHT:
                self.trail.clear()
            elif game.runner.is_moving:
                self.trail.append(game.runner.position)
                del self.trail[:-TRAIL_LENGTH]
        if game.is_over:
            self.end_timer += dt
            if self.app.settings.autoplay and self.end_timer >= AUTOPLAY_DELAY:
                self.next_map()

    # ------------------------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------------------------
    def fs(self, base: float) -> int:
        """A font size that grows and shrinks with the window."""
        return max(11, round(base * self.u))

    def _layout(self, size: tuple[int, int]) -> None:
        width, height = size
        self.u = theme.ui_scale(size)
        m = round(14 * self.u)
        panel_width = min(max(round(460 * self.u), 300), width // 2)
        self.panel_rect = pygame.Rect(width - panel_width, 0, panel_width, height)
        left_width = width - panel_width - 2 * m
        self.top_rect = pygame.Rect(m, m, left_width, round(50 * self.u))
        self.bottom_rect = pygame.Rect(m, height - m - round(34 * self.u), left_width, round(34 * self.u))
        area = pygame.Rect(m, self.top_rect.bottom + m, left_width, self.bottom_rect.top - self.top_rect.bottom - 2 * m)
        if self.board is None or self.board.maze is not self.game.maze:
            self.board = BoardView(self.game.maze, area)
        else:
            self.board.resize(area)

    def draw(self, surface: pygame.Surface) -> None:
        self._layout(surface.get_size())
        surface.fill(theme.BACKGROUND)
        self._draw_board(surface)
        self._draw_top_bar(surface)
        self._draw_bottom_bar(surface)
        self._draw_panel(surface)
        if self.game.status == CAUGHT:
            self._draw_banner(surface, "CAUGHT!  " + self.game.last_message, theme.BAD)
        elif self.paused and not self.game.is_over:
            self._draw_banner(surface, "PAUSED  -  Space continues,  Right arrow = one more step", theme.ACCENT)
        if self.game.is_over:
            self._draw_result(surface)

    # --- the board ---------------------------------------------------------------------------
    def _draw_board(self, surface: pygame.Surface) -> None:
        game, board, runner = self.game, self.board, self.game.runner
        assert board is not None
        board.draw_maze(surface)

        fx = board.begin_fx()
        if self.show_danger:
            board.draw_territory(fx, runner)
        if self.show_explored and runner.last_search is not None:
            board.shade_gradient(fx, runner.last_search.expanded, runner.color)
        if self.show_routes:
            for hunter in game.hunters:
                if hunter.can_move and hunter.plan:
                    goal = None if hunter.mode == "PATROL" else hunter.goal
                    board.draw_route(fx, hunter.next_cell, hunter.plan, goal, hunter.color)
            if runner.plan or runner.goal is not None:
                board.draw_route(fx, runner.next_cell, runner.plan, runner.goal, runner.color, big=True)
        board.end_fx(surface)

        board.draw_food(surface, game.pellets, game.power_orbs, self.clock)
        for hunter in game.hunters:
            board.draw_hunter(surface, hunter, self.clock, game.power_time_left)
        board.draw_runner(surface, runner, self.trail, self.clock, hurt=game.status == CAUGHT)
        if self.show_labels:                       # hunters: their algorithm; runner: below itself
            for hunter in game.hunters:
                if hunter.is_visible:
                    board.draw_label(surface, hunter.position, hunter.algorithm, hunter.color)
            board.draw_label(surface, runner.position, f"Runner · {runner.algorithm}", runner.color, below=True)

    def _draw_banner(self, surface: pygame.Surface, text: str, color: theme.Color) -> None:
        assert self.board is not None
        size = self.fs(17)
        text = widgets.fit(text, size, self.board.rect.w - 6 * size, bold=True)
        image = theme.render(text, size, theme.INK, bold=True)
        rect = image.get_rect(midtop=(self.board.rect.centerx, self.board.rect.y + round(10 * self.u)))
        pill = rect.inflate(size * 2, size)
        pygame.draw.rect(surface, color, pill, border_radius=pill.h // 2)
        surface.blit(image, rect)

    def _draw_result(self, surface: pygame.Surface) -> None:
        game, board, runner = self.game, self.board, self.game.runner
        assert board is not None
        shade = pygame.Surface(board.rect.size, pygame.SRCALPHA)
        shade.fill((*theme.BACKGROUND, 165))
        surface.blit(shade, board.rect)

        title, color = RESULT_TITLES.get(game.status, ("TIME UP", theme.WARN))
        eaten = 100 * (1 - game.food_left / game.food_total)
        searched = runner.nodes_expanded / max(runner.searches, 1)
        lines = [
            (f"{game.maze.name}  -  runner: {runner.algorithm}  vs  {len(game.hunters)} hunters", theme.TEXT_DIM),
            (f"Score {game.score:,}     Time {_clock(game.time)}     Food eaten {eaten:.0f}%", theme.TEXT),
            (f"Lives lost {game.deaths}     Hunters eaten {game.hunters_eaten}", theme.TEXT),
            (f"The runner planned {runner.searches} routes, exploring {searched:.1f} tiles per search", theme.TEXT_DIM),
        ]
        hints = "R replay     S new seed     N next map     M menu"
        if self.app.settings.autoplay:
            hints = f"Autoplay: next map in {max(0.0, AUTOPLAY_DELAY - self.end_timer):.0f} s     (A = stop)"

        big, body = self.fs(40), self.fs(17)
        width = min(board.rect.w - 20, max(theme.text_width(text, body) for text, _ in lines) + 4 * body)
        height = round(big * 1.6 + len(lines) * body * 1.6 + body * 3.2)
        box = pygame.Rect(0, 0, width, height)
        box.center = board.rect.center
        widgets.card(surface, box, theme.PANEL, theme.mix(color, theme.BACKGROUND, 0.4), radius=16)
        y = box.y + round(big * 0.5)
        theme.draw_text(surface, title, (box.centerx, y), big, color, bold=True, anchor="midtop")
        y += round(big * 1.35)
        for text, text_color in lines:
            theme.draw_text(surface, text, (box.centerx, y), body, text_color, anchor="midtop")
            y += round(body * 1.6)
        theme.draw_text(surface, hints, (box.centerx, box.bottom - round(body * 0.9)), body, theme.ACCENT,
                        bold=True, anchor="midbottom")

    # --- the bars above and below the board ---------------------------------------------------
    def _draw_top_bar(self, surface: pygame.Surface) -> None:
        game, rect, u = self.game, self.top_rect, self.u
        label, value = self.fs(12), self.fs(20)
        gap = round(26 * u)
        cy = rect.centery

        name = theme.draw_text(surface, game.maze.name, (rect.x, cy), self.fs(27), theme.TEXT, bold=True, anchor="midleft")
        x = name.right + gap

        def stat(title: str, text: str, color: theme.Color = theme.TEXT) -> None:
            nonlocal x
            top = theme.draw_text(surface, title, (x, cy - 2), label, theme.TEXT_FAINT, bold=True, anchor="bottomleft")
            low = theme.draw_text(surface, text, (x, cy - 2), value, color, bold=True, anchor="topleft")
            x = max(top.right, low.right) + gap

        stat("SCORE", f"{game.score:,}")
        stat("TIME", f"{_clock(game.time)} / {_clock(TIME_LIMIT)}")

        theme.draw_text(surface, "LIVES", (x, cy - 2), label, theme.TEXT_FAINT, bold=True, anchor="bottomleft")
        radius = value * 0.36
        for life in range(START_LIVES):
            center = (x + radius + life * radius * 2.7, cy + value * 0.55)
            if life < game.lives:
                pygame.draw.circle(surface, game.runner.color, center, radius)
            else:
                pygame.draw.circle(surface, theme.LINE, center, radius, max(1, round(2 * u)))
        x += round(radius * 2.7 * START_LIVES) + gap

        food_width = round(150 * u)
        eaten = game.food_total - game.food_left
        theme.draw_text(surface, f"FOOD  {eaten} / {game.food_total}", (x, cy - 2), label, theme.TEXT_FAINT,
                        bold=True, anchor="bottomleft")
        widgets.bar(surface, pygame.Rect(x, cy + round(5 * u), food_width, round(10 * u)),
                    eaten / max(game.food_total, 1), theme.PELLET)
        x += food_width + gap

        if game.power_time_left > 0:
            theme.draw_text(surface, f"POWER  {game.power_time_left:.1f} s", (x, cy - 2), label, theme.POWER_ORB,
                            bold=True, anchor="bottomleft")
            widgets.bar(surface, pygame.Rect(x, cy + round(5 * u), round(110 * u), round(10 * u)),
                        game.power_time_left / POWER_DURATION, theme.POWER_ORB)

    def _draw_bottom_bar(self, surface: pygame.Surface) -> None:
        rect, size = self.bottom_rect, self.fs(13)
        x, cy = rect.x, rect.centery
        speed = SPEEDS[self.speed_index]
        items = [
            ("Space", "Paused" if self.paused else "Pause", True),
            ("->", "Step", True),
            ("+ -", f"Speed {speed:g}x", True),
            None,
            ("P", "Routes", self.show_routes),
            ("V", "Explored", self.show_explored),
            ("D", "Danger map", self.show_danger),
            ("L", "Labels", self.show_labels),
            None,
            ("A", "Autoplay", self.app.settings.autoplay),
        ]
        for item in items:
            if item is None:                                   # a separator
                pygame.draw.line(surface, theme.LINE, (x, cy - size * 0.8), (x, cy + size * 0.8))
                x += round(size * 1.2)
                continue
            key, text, lit = item
            cap = widgets.key_cap(surface, key, (x, cy), size, lit, anchor="midleft")
            label = theme.draw_text(surface, text, (cap.right + size * 0.45, cy), size,
                                    theme.TEXT if lit else theme.TEXT_FAINT, anchor="midleft")
            x = label.right + round(size * 1.3)
            if x > rect.right:
                break

    # --- the side panel ------------------------------------------------------------------------
    def _draw_panel(self, surface: pygame.Surface) -> None:
        rect = self.panel_rect
        pygame.draw.rect(surface, theme.PANEL, rect)
        pygame.draw.line(surface, theme.LINE, rect.topleft, rect.bottomleft)
        pad = round(18 * self.u)
        x, width = rect.x + pad, rect.w - 2 * pad
        keys_top = self._draw_keys(surface, x, rect.bottom - pad, width)
        y = self._draw_runner_info(surface, x, rect.y + pad, width)
        y = self._draw_hunter_info(surface, x, y + pad, width)
        thinking_top = self._draw_thinking(surface, x, keys_top - pad, width, y + pad)
        self._draw_events(surface, x, y + pad, width, thinking_top - pad)

    def _draw_runner_info(self, surface: pygame.Surface, x: int, y: int, width: int) -> int:
        runner, u = self.game.runner, self.u
        head, body, small = self.fs(13), self.fs(16), self.fs(14)
        line = round(body * 1.4)
        y = widgets.section(surface, "RUNNER  (keys 1-4 switch its algorithm)", (x, y), head, width)

        algo = widgets.chip(surface, runner.algorithm, (x, y), body, theme.ALGORITHM_COLORS[runner.algorithm])
        description = widgets.fit(DESCRIPTIONS[runner.algorithm], small, width - algo.w - 10)
        theme.draw_text(surface, description, (algo.right + 10, algo.centery), small, theme.TEXT_DIM, anchor="midleft")
        y = algo.bottom + round(10 * u)

        mode = runner.mode or "START"
        chip = widgets.chip(surface, mode, (x, y), small, RUNNER_MODE_COLORS.get(mode, theme.TEXT_DIM))
        y = chip.bottom + round(6 * u)
        thought = runner.thought.split(" - ", 1)[-1] if runner.thought else "about to make its first decision"
        for text in widgets.wrap(thought[:1].upper() + thought[1:], body, width)[:3]:
            theme.draw_text(surface, text, (x, y), body, theme.TEXT)
            y += line
        y += round(4 * u)

        rows = []
        search = runner.last_search
        if search is not None:
            rows.append(("Last search", f"explored {_tiles(len(search.expanded))}, route {steps(max(search.length, 0))}"))
            rows.append(("", f"frontier peak {_tiles(search.max_frontier)},  {search.time_ms:.2f} ms"))
        if runner.searches:
            rows.append(("All searches", f"{runner.searches} routes,  {runner.nodes_expanded / runner.searches:.1f} tiles each"))
        if runner.danger:
            rows.append(("Territory", f"{_tiles(len(runner.territory))} it reaches first"))
        label_width = round(108 * u)
        for label, text in rows:
            if label:
                theme.draw_text(surface, label, (x, y), small, theme.TEXT_FAINT)
            theme.draw_text(surface, widgets.fit(text, small, width - label_width), (x + label_width, y), small, theme.TEXT_DIM)
            y += round(small * 1.45)
        return y

    def _draw_hunter_info(self, surface: pygame.Surface, x: int, y: int, width: int) -> int:
        hunters, u = self.game.hunters, self.u
        head, body, small = self.fs(13), self.fs(15), self.fs(13)
        y = widgets.section(surface, f"HUNTERS ({len(hunters)})", (x, y), head, width)
        for hunter in hunters:
            swatch = pygame.Rect(x, y + round(body * 0.15), round(body * 0.9), round(body * 0.9))
            pygame.draw.rect(surface, hunter.color, swatch, border_radius=max(2, swatch.w // 4))
            name = theme.draw_text(surface, hunter.name, (swatch.right + round(8 * u), y), body, theme.TEXT, bold=True)
            chip = widgets.chip(surface, hunter.algorithm, (name.right + round(8 * u), name.centery), small,
                                hunter.color, filled=False, anchor="midleft")
            mode_color = {"PATROL": theme.TEXT_DIM, "SCARED": theme.SCARED, "WAITING": theme.TEXT_FAINT,
                          "RESPAWNING": theme.TEXT_FAINT}.get(hunter.mode, hunter.color)
            mode_text = hunter.mode
            if hunter.mode in ("WAITING", "RESPAWNING"):
                mode_text += f" {max(0.0, hunter.timer):.1f}s"
            theme.draw_text(surface, mode_text, (x + width, chip.centery), small, mode_color, bold=True, anchor="midright")
            y = max(name.bottom, chip.bottom) + round(2 * u)
            detail = hunter.thought
            if hunter.last_search is not None and hunter.mode not in ("WAITING", "RESPAWNING", "SCARED"):
                detail += f"  ·  last search {_tiles(len(hunter.last_search.expanded))}"
            theme.draw_text(surface, widgets.fit(detail, small, width - swatch.w - round(8 * u)),
                            (swatch.right + round(8 * u), y), small, theme.TEXT_DIM)
            y += round(small * 1.75)
        return y

    def _draw_events(self, surface: pygame.Surface, x: int, y: int, width: int, bottom: int) -> None:
        head, small = self.fs(13), self.fs(13)
        if y + head * 3 > bottom:
            return
        y = widgets.section(surface, "EVENTS", (x, y), head, width)
        for index, text in enumerate(self.game.log):
            if y + small * 1.4 > bottom:
                break
            theme.draw_text(surface, widgets.fit(text.strip(), small, width), (x, y), small,
                            theme.TEXT if index == 0 else theme.TEXT_FAINT)
            y += round(small * 1.45)

    def _draw_thinking(self, surface: pygame.Surface, x: int, bottom: int, width: int, limit: int) -> int:
        """The runner's decision loop, with the current step lit. Drawn upward from `bottom`;
        skipped if it would not fit below `limit`. Returns its top."""
        runner = self.game.runner
        head, size = self.fs(13), self.fs(14)
        row = round(size * 1.55)
        top = bottom - 4 * row - round(head * 1.8)
        if top < limit + 4 * row:                        # keep room for a few event lines
            return bottom + self.fs(13)
        y = widgets.section(surface, "HOW THE RUNNER THINKS  (every tile)", (x, top), head, width)
        label_width = round(74 * self.u)
        lines = [
            ("SENSE", "BFS distance maps from itself and from every hunter"),
            ("DECIDE", None),
            ("PLAN", f"{runner.algorithm} route that stays inside its territory"),
            ("ACT", "walk to the first tile of that route"),
        ]
        for name, text in lines:
            theme.draw_text(surface, name, (x, y), size, theme.ACCENT, bold=True)
            if text is not None:
                theme.draw_text(surface, widgets.fit(text, size, width - label_width), (x + label_width, y), size, theme.TEXT_DIM)
            else:                                        # the priority order, current mode lit
                cx = x + label_width
                for index, mode in enumerate(("TRAPPED", "HUNT", "ESCAPE", "EAT")):
                    lit = mode == runner.mode
                    word = theme.draw_text(surface, mode, (cx, y), size,
                                           RUNNER_MODE_COLORS[mode] if lit else theme.TEXT_FAINT, bold=lit)
                    cx = word.right
                    if index < 3:
                        cx = theme.draw_text(surface, "  >  ", (cx, y), size, theme.TEXT_FAINT).right
            y += row
        return top

    def _draw_keys(self, surface: pygame.Surface, x: int, bottom: int, width: int) -> int:
        """The key list, drawn upward from the bottom of the panel. Returns its top."""
        head, size = self.fs(13), self.fs(13)
        keys = [("1-4", "runner algorithm"), ("R", "replay (same seed)"), ("S", "new seed"),
                ("N", "next map"), ("G", "random labyrinth"), ("M", "menu"), ("F11", "fullscreen")]
        row = round(size * 1.95)
        column = width // 2
        rows = (len(keys) + 1) // 2
        top = bottom - rows * row - round(head * 1.8)
        y = widgets.section(surface, "MORE KEYS", (x, top), head, width)
        for index, (key, text) in enumerate(keys):
            kx = x + (index % 2) * column
            ky = y + (index // 2) * row
            cap = widgets.key_cap(surface, key, (kx, ky), size)
            theme.draw_text(surface, widgets.fit(text, size, column - cap.w - 12), (cap.right + 6, cap.centery),
                            size, theme.TEXT_DIM, anchor="midleft")
        return top


def _tiles(count: int) -> str:
    return f"{count} tile" if count == 1 else f"{count} tiles"


def _clock(seconds: float) -> str:
    return f"{int(seconds) // 60}:{int(seconds) % 60:02d}"
