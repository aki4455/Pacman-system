"""
greedy.py - Greedy Best-First Search.

IDEA     Like A*, but the score is ONLY the heuristic:  f(n) = h(n).
         It always expands the tile that LOOKS closest to the goal and ignores how far it has
         already walked. It rushes straight at the goal and is usually very fast...
RESULT   ...but it is NOT optimal: a wall between it and the goal can lure it into a dead
         end or a long detour, because "looks close" is not "is close". It is complete on a
         finite graph (we never expand a tile twice), so it still finds a path if one exists.
DATA     A PRIORITY QUEUE (binary min-heap, heapq) ordered by h.
COST     O(E log V) time in the worst case, O(V) memory.

Comparing Greedy with A* shows why A* adds g(n): the walked distance keeps it honest.
"""

from __future__ import annotations

import heapq
from collections.abc import Set

from ..maze import Cell, Maze
from .heuristics import manhattan
from .result import SearchResult, reconstruct_path


def greedy_best_first(maze: Maze, start: Cell, goal: Cell, blocked: Set[Cell] = frozenset()) -> SearchResult:
    """A path from start to goal, always following the tile that looks closest to the goal."""
    frontier: list[tuple[int, Cell]] = [(manhattan(maze, start, goal), start)]   # min-heap by h
    came_from: dict[Cell, Cell | None] = {start: None}    # parent pointers, also the "visited" set
    expanded: list[Cell] = []
    max_frontier = 1

    while frontier:
        _, current = heapq.heappop(frontier)   # the tile that looks closest to the goal
        expanded.append(current)
        if current == goal:
            break
        for neighbor in maze.neighbors(current):
            if neighbor in came_from or neighbor in blocked:
                continue
            came_from[neighbor] = current
            heapq.heappush(frontier, (manhattan(maze, neighbor, goal), neighbor))
        max_frontier = max(max_frontier, len(frontier))

    return SearchResult("Greedy", start, goal, reconstruct_path(came_from, goal), expanded, max_frontier)
