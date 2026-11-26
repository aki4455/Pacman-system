"""
benchmark.py - experiments that run WITHOUT a window, as fast as the computer allows.

    python main.py --compare      BFS vs DFS vs A* vs Greedy on every map: tiles explored,
                                  path length, memory (largest frontier), time
    python main.py --benchmark    many complete games per map and runner algorithm:
                                  how often does the runner clear the map?

Both are deterministic: the same seed always gives the same numbers.
"""

from __future__ import annotations

import random
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass

from .algorithms import ALGORITHM_NAMES, bfs_distances, find_path
from .config import TICK, TIME_LIMIT
from .game import CLEARED, Game
from .maze import Cell, Maze


# ----------------------------------------------------------------------------------------
# 1) Algorithm comparison
# ----------------------------------------------------------------------------------------
@dataclass
class AlgorithmStats:
    searches: int = 0
    expanded: int = 0
    path_steps: int = 0
    max_frontier: int = 0
    optimal: int = 0
    time_ms: float = 0.0


def farthest_pair(maze: Maze) -> tuple[Cell, Cell]:
    """The runner's start and the tile farthest away from it (longest shortest path)."""
    distances = bfs_distances(maze, [maze.runner_start])
    return maze.runner_start, max(distances, key=lambda tile: (distances[tile], tile))


def compare_algorithms(mazes: list[Maze], pairs_per_map: int = 200, seed: int = 1) -> None:
    rng = random.Random(seed)
    print(f"\nAlgorithm comparison - {pairs_per_map} random (start, goal) pairs per map, same pairs for every algorithm")
    print("'explored' = tiles expanded, 'memory' = largest frontier, 'optimal' = path as short as BFS's\n")
    header = f"{'map':14s} {'algorithm':9s} {'explored':>9s} {'path':>7s} {'memory':>7s} {'optimal':>8s} {'time':>9s}"
    totals = {name: AlgorithmStats() for name in ALGORITHM_NAMES}
    for maze in mazes:
        print(header)
        pairs = [tuple(rng.sample(maze.open_cells, 2)) for _ in range(pairs_per_map)]
        per_map = {name: AlgorithmStats() for name in ALGORITHM_NAMES}
        for start, goal in pairs:
            shortest = find_path("BFS", maze, start, goal).length
            for name in ALGORITHM_NAMES:
                result = find_path(name, maze, start, goal)
                for stats in (per_map[name], totals[name]):
                    stats.searches += 1
                    stats.expanded += len(result.expanded)
                    stats.path_steps += result.length
                    stats.max_frontier += result.max_frontier
                    stats.optimal += result.length == shortest
                    stats.time_ms += result.time_ms
        for name in ALGORITHM_NAMES:
            print(_stats_line(maze.name, name, per_map[name]))
        print()
    print(header)
    for name in ALGORITHM_NAMES:
        print(_stats_line("ALL MAPS", name, totals[name]))

    print("\nLongest trip on every map (runner start -> farthest tile):")
    print(f"{'map':14s} " + "  ".join(f"{name:^16s}" for name in ALGORITHM_NAMES) + "   (explored / path)")
    for maze in mazes:
        start, goal = farthest_pair(maze)
        cells = []
        for name in ALGORITHM_NAMES:
            result = find_path(name, maze, start, goal)
            cells.append(f"{len(result.expanded):>7d} / {result.length:<6d}")
        print(f"{maze.name:14s} " + "  ".join(f"{cell:>16s}" for cell in cells))


def _stats_line(map_name: str, algorithm: str, stats: AlgorithmStats) -> str:
    n = max(stats.searches, 1)
    return (f"{map_name:14s} {algorithm:9s} {stats.expanded / n:9.1f} {stats.path_steps / n:7.1f} "
            f"{stats.max_frontier / n:7.1f} {100 * stats.optimal / n:7.0f}% {1000 * stats.time_ms / n:7.0f}us")


# ----------------------------------------------------------------------------------------
# 2) Full games
# ----------------------------------------------------------------------------------------
def simulate(maze: Maze, runner_algorithm: str, hunter_count: int = 4, seed: int = 0) -> Game:
    """Play one complete game without a window and return the finished Game object."""
    game = Game(maze, runner_algorithm, hunter_count, seed)
    max_ticks = int((TIME_LIMIT + 30) / TICK)
    for _ in range(max_ticks):
        game.update(TICK)
        if game.is_over:
            break
    return game


def _play_one(job: tuple[Maze, str, int, int]) -> tuple[bool, int, int, float, float, int, int]:
    """Play one game and return only the numbers the table needs (runs in a worker process)."""
    maze, algorithm, hunter_count, seed = job
    game = simulate(maze, algorithm, hunter_count, seed)
    return (game.status == CLEARED, game.deaths, game.hunters_eaten, 1 - game.food_left / game.food_total,
            game.time, game.runner.searches, game.runner.nodes_expanded)


def run_matches(mazes: list[Maze], algorithms: tuple[str, ...] = ALGORITHM_NAMES, games: int = 10,
                hunter_count: int = 4, seed: int = 1, workers: int | None = None) -> None:
    """Play `games` complete games for every (map, runner algorithm) and print a summary.

    The games do not depend on each other, so they are played in parallel on all CPU cores
    (workers=1 plays them one after the other). Game number k always uses seed + k, so the
    table is the same on every run.
    """
    print(f"\nFull games - {games} games per map and runner algorithm, {hunter_count} hunters\n")
    print(f"{'map':14s} {'runner':8s} {'cleared':>8s} {'food eaten':>11s} {'deaths':>7s} {'hunters eaten':>14s} "
          f"{'avg time':>9s} {'tiles explored / decision':>26s}")
    started = time.perf_counter()
    jobs = [(maze, algorithm, hunter_count, seed + number)
            for maze in mazes for algorithm in algorithms for number in range(games)]
    if workers == 1:
        results = map(_play_one, jobs)
        pool = None
    else:
        pool = ProcessPoolExecutor(max_workers=workers)
        results = pool.map(_play_one, jobs)
    try:
        for maze in mazes:
            for algorithm in algorithms:
                cleared = deaths = eaten = searches = expanded = 0
                food = seconds = 0.0
                for _ in range(games):                 # the results arrive in the order of `jobs`
                    won, lost, ate, food_share, game_time, game_searches, game_expanded = next(results)
                    cleared += won
                    deaths += lost
                    eaten += ate
                    food += food_share
                    seconds += game_time
                    searches += game_searches
                    expanded += game_expanded
                print(f"{maze.name:14s} {algorithm:8s} {cleared:>4d}/{games:<3d} {100 * food / games:10.0f}% "
                      f"{deaths / games:7.1f} {eaten / games:14.1f} {seconds / games:8.0f}s "
                      f"{expanded / max(searches, 1):26.1f}")
            print()
    finally:
        if pool is not None:
            pool.shutdown()
    print(f"(simulated in {time.perf_counter() - started:.1f} s)")
