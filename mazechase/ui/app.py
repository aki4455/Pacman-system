"""
app.py - the window and the main loop.

The app owns the window, the list of maps and the settings chosen in the menu, and shows one
SCREEN at a time (menu, game or Algorithm Lab). Every screen has the same three methods:

    handle_event(event)   react to a key press or a mouse click
    update(dt)            advance time by dt seconds
    draw(surface)         draw itself (the layout adapts to the window size every frame)

F11 switches between a window and full screen on every screen.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass

import pygame

from ..generator import generate_maze
from ..maze import Maze, load_maps
from . import theme
from .game_screen import GameScreen
from .lab import LabScreen
from .menu import MenuScreen

FPS = 60


@dataclass
class Settings:
    """What the menu lets you choose. The screens read and change these."""

    map_index: int = 0
    runner_algorithm: str = "A*"
    hunter_count: int = 4
    speed: float = 1.0
    autoplay: bool = False
    seed: int = 1                     # random seed of a round (the hunters' patrol choices)
    labyrinth_seed: int = 1           # seed of the randomly generated labyrinth
    fullscreen: bool = False


class App:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.mazes: list[Maze] = load_maps()
        self.mazes.append(generate_maze(settings.labyrinth_seed))     # the last entry: a random maze
        settings.map_index = max(0, min(settings.map_index, len(self.mazes) - 1))

        _make_crisp_on_windows()
        os.environ.setdefault("SDL_VIDEO_CENTERED", "1")
        pygame.init()
        pygame.display.set_caption("Maze Chase AI")
        pygame.display.set_icon(_icon())
        desktop = pygame.display.get_desktop_sizes()[0]
        self.window_size = (max(960, round(desktop[0] * 0.86)), max(600, round(desktop[1] * 0.86)))
        self._open_window()

        self.clock = pygame.time.Clock()
        self.running = True
        self.screen: MenuScreen | GameScreen | LabScreen = MenuScreen(self)

    # ------------------------------------------------------------------------------------
    # Switching screens (called by the screens themselves)
    # ------------------------------------------------------------------------------------
    def show_menu(self) -> None:
        self.screen = MenuScreen(self)

    def start_game(self, map_index: int) -> None:
        self.screen = GameScreen(self, map_index)

    def open_lab(self, map_index: int) -> None:
        self.screen = LabScreen(self, map_index)

    def new_random_maze(self) -> int:
        """Replace the random labyrinth by a new one. Returns its index in `mazes`."""
        self.settings.labyrinth_seed += 1
        self.mazes[-1] = generate_maze(self.settings.labyrinth_seed)
        return len(self.mazes) - 1

    def quit(self) -> None:
        self.running = False

    # ------------------------------------------------------------------------------------
    # The main loop
    # ------------------------------------------------------------------------------------
    def run(self) -> None:
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.1)     # seconds since the last frame
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                    self.settings.fullscreen = not self.settings.fullscreen
                    self._open_window()
                else:
                    self.screen.handle_event(event)
            self.screen.update(dt)
            self.screen.draw(pygame.display.get_surface())
            pygame.display.flip()
        pygame.quit()

    def _open_window(self) -> None:
        if self.settings.fullscreen:
            pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            pygame.display.set_mode(self.window_size, pygame.RESIZABLE)


def run_app(settings: Settings | None = None, screen: str = "menu") -> None:
    """Open the window. `screen` is "menu", "game" or "lab"."""
    app = App(settings or Settings())
    if screen == "game":
        app.start_game(app.settings.map_index)
    elif screen == "lab":
        app.open_lab(app.settings.map_index)
    app.run()


def _make_crisp_on_windows() -> None:
    """Windows scales old-style apps up on high-resolution screens, which blurs them.
    Telling Windows that we handle the pixels ourselves keeps text and lines sharp."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)        # Windows 8.1 and newer
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()             # Windows 7
    except Exception:
        pass                                                       # not important enough to fail


def _icon() -> pygame.Surface:
    """A tiny window icon, drawn in code: the runner in a maze corner."""
    icon = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.rect(icon, theme.MAP_THEMES["teal"][2], (0, 0, 32, 32), 4, border_radius=8)
    pygame.draw.circle(icon, theme.ACCENT, (16, 16), 9)
    pygame.draw.circle(icon, theme.WHITE, (19, 14), 3)
    return icon
