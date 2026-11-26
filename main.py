"""
Maze Chase AI - start here.

    python main.py                  the menu (on Windows you can also double-click run.bat)
    python main.py --play           straight into a game
    python main.py --demo           self-running demo: every round, then the next map
    python main.py --lab            the Algorithm Lab (BFS, DFS, A*, Greedy side by side)

    python main.py --compare        BFS / DFS / A* / Greedy compared on every map   (no window)
    python main.py --benchmark      many complete games per map and algorithm        (no window)
    python main.py --list-maps      the available maps

Options:
    --map 2 | --map arena | --map random     which map (number, name or "random")
    --runner bfs | dfs | astar | greedy      the runner's search algorithm
    --hunters 1-4                            how many hunters
    --speed 0.25-8                           game speed
    --seed N                                 random seed: the same seed gives the same game
    --fullscreen                             start in full screen (F11 switches any time)
"""

from __future__ import annotations

import argparse
import os
import sys

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")     # no "Hello from pygame" line

from mazechase.algorithms import ALGORITHM_NAMES, parse_algorithm  # noqa: E402
from mazechase.config import HUNTERS  # noqa: E402
from mazechase.generator import generate_maze  # noqa: E402
from mazechase.maze import Maze, load_maps  # noqa: E402


def parse_arguments(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="Maze Chase AI - a self-playing maze chase driven by BFS, DFS, A* and Greedy search.",
        epilog="Without options the menu opens. In the game: Space = pause, -> = one step, "
               "1-4 = runner algorithm, P/V/D/L = overlays, M = menu, F11 = full screen.")
    screen = parser.add_mutually_exclusive_group()
    screen.add_argument("--play", action="store_true", help="start a game right away (skip the menu)")
    screen.add_argument("--demo", action="store_true", help="self-running demo: after each round the next map starts")
    screen.add_argument("--lab", action="store_true", help="open the Algorithm Lab")
    screen.add_argument("--compare", action="store_true", help="compare the four algorithms on every map (no window)")
    screen.add_argument("--benchmark", action="store_true", help="play many games without a window and print the results")
    screen.add_argument("--list-maps", action="store_true", help="list the maps and exit")

    parser.add_argument("--map", metavar="MAP", help='map number (1, 2, ...), name ("arena") or "random"')
    parser.add_argument("--runner", metavar="ALGORITHM", help="runner algorithm: bfs, dfs, astar or greedy (default: A*;"
                        " --benchmark without it plays all four)")
    parser.add_argument("--hunters", type=int, default=len(HUNTERS), choices=range(1, len(HUNTERS) + 1),
                        metavar="N", help=f"number of hunters, 1-{len(HUNTERS)} (default: {len(HUNTERS)})")
    parser.add_argument("--speed", type=float, default=1.0, help="game speed: 0.25, 0.5, 1, 2, 4 or 8 (default: 1)")
    parser.add_argument("--seed", type=int, default=1, help="random seed (default: 1)")
    parser.add_argument("--fullscreen", action="store_true", help="start in full screen")
    parser.add_argument("--games", type=int, default=10, help="--benchmark: games per map and algorithm (default: 10)")
    parser.add_argument("--pairs", type=int, default=200, help="--compare: random (start, goal) pairs per map (default: 200)")
    return parser.parse_args(argv)


def find_map(text: str, mazes: list[Maze]) -> int:
    """'2' -> index 1,  'arena' -> the map whose name starts with 'arena',  'random' -> the generated one."""
    text = text.strip().lower()
    if text in ("random", "r", "labyrinth-random"):
        return len(mazes)                                   # the app appends the random labyrinth last
    if text.isdigit():
        number = int(text)
        if 1 <= number <= len(mazes) + 1:
            return number - 1
    else:
        for index, maze in enumerate(mazes):
            if maze.name.lower().startswith(text) or maze.name.lower().replace(" ", "") == text.replace(" ", ""):
                return index
    names = ", ".join(f"{index + 1}={maze.name}" for index, maze in enumerate(mazes))
    raise SystemExit(f"Unknown map {text!r}. Choose a number or a name: {names}, {len(mazes) + 1}=random")


def main(argv: list[str] | None = None) -> int:
    _make_console_safe()
    args = parse_arguments(argv)
    try:
        runner_algorithm = parse_algorithm(args.runner or "A*")
    except ValueError as error:
        raise SystemExit(str(error)) from None
    mazes = load_maps()
    map_index = find_map(args.map, mazes) if args.map else 0

    if args.list_maps:
        print(f"\n{'#':>2s}  {'name':14s} {'size':>7s}  {'vertices':>8s} {'edges':>6s}  tunnels  description")
        for index, maze in enumerate(mazes):
            print(f"{index + 1:>2d}  {maze.name:14s} {maze.width:>3d}x{maze.height:<3d}  {maze.vertex_count:>8d} "
                  f"{maze.edge_count:>6d}  {'yes' if maze.has_tunnels else 'no ':7s}  {maze.description}")
        print(f"{len(mazes) + 1:>2d}  Random         a new labyrinth from the DFS maze generator (use --seed)\n")
        return 0

    if args.compare or args.benchmark:
        from mazechase.benchmark import compare_algorithms, run_matches
        chosen = mazes
        if args.map:
            chosen = [mazes[map_index]] if map_index < len(mazes) else [generate_maze(args.seed)]
        if args.compare:
            compare_algorithms(chosen, pairs_per_map=args.pairs, seed=args.seed)
        else:
            algorithms = (runner_algorithm,) if args.runner else ALGORITHM_NAMES
            run_matches(chosen, algorithms, games=args.games, hunter_count=args.hunters, seed=args.seed)
        return 0

    try:
        from mazechase.ui import Settings, run_app
    except ImportError as error:
        print(f"Could not start the window: {error}\n"
              "pygame is needed for the window. Install it with:   uv sync      (or:  pip install pygame)\n"
              "The experiments work without it:   python main.py --compare   /   python main.py --benchmark")
        return 1

    settings = Settings(map_index=map_index, runner_algorithm=runner_algorithm, hunter_count=args.hunters,
                        speed=args.speed, autoplay=args.demo, seed=args.seed,
                        labyrinth_seed=args.seed, fullscreen=args.fullscreen)
    if args.lab:
        screen = "lab"
    elif args.play or args.demo or args.map:
        screen = "game"
    else:
        screen = "menu"
    run_app(settings, screen)
    return 0


def _make_console_safe() -> None:
    """Some Windows consoles cannot print every character; never crash because of that."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass


if __name__ == "__main__":
    sys.exit(main())
