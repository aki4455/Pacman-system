"""
Everything you SEE (pygame). The game logic never imports this package, so the game and the
benchmarks also run without a window.

    app.py           the window, the main loop, switching between screens
    menu.py          the start screen
    game_screen.py   the self-playing game with the AI overlays and the side panel
    lab.py           the Algorithm Lab: BFS, DFS, A* and Greedy side by side
    board.py         draws the maze, the food, the agents and the overlays
    widgets.py       small drawing helpers (cards, chips, bars, key caps)
    theme.py         colours and fonts
"""

import os

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")    # no "Hello from pygame" line

from .app import Settings, run_app  # noqa: E402

__all__ = ["Settings", "run_app"]
