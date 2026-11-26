"""
dfs.py - Depth-First Search.

IDEA     Always continue from the tile discovered MOST RECENTLY: go as deep as possible down
         one corridor, and only when stuck, back up (backtrack) to the last unexplored branch.
DATA     A LIFO STACK (a Python list: append() and pop() at the end are both O(1)). The stack
         replaces the call stack of the recursive version, so very long corridors can never
         cause a "maximum recursion depth" error.
RESULT   DFS always finds a path if one exists (complete on a finite graph), but NOT the
         shortest one: it returns the first route it happened to walk down, often a long
         detour. You can watch this in the game: the DFS hunter and a DFS runner take
         noticeably winding routes.
COST     O(V + E) time, O(V) memory.
"""

from __future__ import annotations

from collections.abc import Set

from ..maze import Cell, Maze
from .result import SearchResult, reconstruct_path


def dfs(maze: Maze, start: Cell, goal: Cell, blocked: Set[Cell] = frozenset()) -> SearchResult:
    """A path from start to goal (not necessarily the shortest). `blocked` tiles count as walls."""
    frontier: list[tuple[Cell, Cell | None]] = [(start, None)]   # stack of (tile, its parent)
    came_from: dict[Cell, Cell | None] = {}    # filled when a tile is EXPANDED (taken off the stack)
    expanded: list[Cell] = []
    max_frontier = 1

    while frontier:
        current, parent = frontier.pop()       # LIFO: the newest tile first -> go deep
        if current in came_from:
            continue                           # already expanded through another branch
        came_from[current] = parent
        expanded.append(current)
        if current == goal:
            break
        # Push in reverse order so that the FIRST neighbour (UP) ends on top of the stack and is
        # explored first - the same order the recursive version of DFS would use.
        for neighbor in reversed(maze.neighbors(current)):
            if neighbor not in came_from and neighbor not in blocked:
                frontier.append((neighbor, current))
        max_frontier = max(max_frontier, len(frontier))

    return SearchResult("DFS", start, goal, reconstruct_path(came_from, goal), expanded, max_frontier)
