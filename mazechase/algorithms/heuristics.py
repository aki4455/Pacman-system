"""
heuristics.py - the "educated guess" used by A* and Greedy best-first search.

A heuristic h(tile) estimates how many steps are still needed to reach the goal.
"""

from __future__ import annotations

from ..maze import Cell, Maze


def manhattan(maze: Maze, a: Cell, b: Cell) -> int:
    """Manhattan distance |d_row| + |d_col|: the number of steps if there were no walls.

    * ADMISSIBLE  - it never overestimates. Walls can only make the real route longer,
                    never shorter. This is what keeps A* optimal.
    * CONSISTENT  - one step changes it by at most 1, so A* never has to re-open a tile.

    With tunnels, going "around" through the side of the map can be shorter, so we take the
    shorter of the two horizontal distances. Otherwise the guess could overestimate, and A*
    could miss the shortest path.
    """
    d_row = abs(a[0] - b[0])
    d_col = abs(a[1] - b[1])
    if maze.has_tunnels:
        d_col = min(d_col, maze.width - d_col)
    return d_row + d_col
