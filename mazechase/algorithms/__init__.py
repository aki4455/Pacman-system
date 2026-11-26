"""
The search algorithms. All four have exactly the same signature:

    algorithm(maze, start, goal, blocked=frozenset()) -> SearchResult

`blocked` is a set of extra tiles to treat as walls. The runner uses it to stay away from
hunters, and the hunters use it to forbid U-turns.

Because they are interchangeable, an agent only stores the NAME of its algorithm and calls
find_path(). Switching the runner from A* to DFS in the middle of a game is just a different
name (keys 1-4 in the game).
"""

from __future__ import annotations

import time
from collections.abc import Callable, Set

from ..maze import Cell, Maze
from .astar import astar
from .bfs import bfs, bfs_distances
from .dfs import dfs
from .greedy import greedy_best_first
from .heuristics import manhattan
from .result import SearchResult, reconstruct_path

SearchFunction = Callable[[Maze, Cell, Cell, Set[Cell]], SearchResult]

ALGORITHMS: dict[str, SearchFunction] = {
    "BFS": bfs,
    "DFS": dfs,
    "A*": astar,
    "Greedy": greedy_best_first,
}
ALGORITHM_NAMES = tuple(ALGORITHMS)

DESCRIPTIONS = {
    "BFS": "queue - explores in rings, shortest path guaranteed",
    "DFS": "stack - dives deep first, path is NOT the shortest",
    "A*": "priority queue on f = g + h - shortest path, few tiles explored",
    "Greedy": "priority queue on h only - fast, but path can be long",
}


def find_path(algorithm: str, maze: Maze, start: Cell, goal: Cell,
              blocked: Set[Cell] = frozenset()) -> SearchResult:
    """Run the named algorithm and measure how long it took."""
    started = time.perf_counter()
    result = ALGORITHMS[algorithm](maze, start, goal, blocked)
    result.time_ms = (time.perf_counter() - started) * 1000.0
    return result


def parse_algorithm(text: str) -> str:
    """Accept friendly spellings ('astar', 'a-star', 'bfs', 'greedy', ...) -> official name."""
    key = text.strip().lower().replace("-", "").replace("_", "").replace(" ", "")
    aliases = {"bfs": "BFS", "dfs": "DFS", "a*": "A*", "astar": "A*", "a": "A*",
               "greedy": "Greedy", "gbfs": "Greedy", "greedybestfirst": "Greedy", "bestfirst": "Greedy"}
    if key not in aliases:
        raise ValueError(f"unknown algorithm {text!r} - choose from {', '.join(ALGORITHM_NAMES)}")
    return aliases[key]


__all__ = [
    "ALGORITHMS", "ALGORITHM_NAMES", "DESCRIPTIONS", "SearchResult", "astar", "bfs", "bfs_distances",
    "dfs", "find_path", "greedy_best_first", "manhattan", "parse_algorithm", "reconstruct_path",
]
