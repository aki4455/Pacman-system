"""
result.py - what every search returns, and the shared path-reconstruction helper.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..maze import Cell


@dataclass
class SearchResult:
    """The outcome of one search.

    path          the route from start to goal, both included   ([] if the goal is unreachable)
    expanded      every tile the algorithm EXPANDED (took out of its frontier), in order.
                  The "explored tiles" overlay and the Algorithm Lab draw exactly this list.
    max_frontier  the largest size the frontier (queue / stack / heap) ever reached = memory used
    time_ms       how long the search took, in milliseconds
    """

    algorithm: str
    start: Cell
    goal: Cell
    path: list[Cell]
    expanded: list[Cell]
    max_frontier: int
    time_ms: float = 0.0

    @property
    def found(self) -> bool:
        return bool(self.path)

    @property
    def length(self) -> int:
        """Number of steps (moves) along the path: 0 if start == goal, -1 if there is no path."""
        return len(self.path) - 1


def reconstruct_path(came_from: dict[Cell, Cell | None], goal: Cell) -> list[Cell]:
    """Turn the parent pointers into a path.

    came_from[tile] is the tile we came from when we reached `tile` (None for the start tile).
    Walking goal -> parent -> parent -> ... therefore ends at the start; reversing that list
    gives the path from start to goal. Runs in O(length of the path).
    """
    if goal not in came_from:
        return []                      # the search never reached the goal
    path = []
    tile: Cell | None = goal
    while tile is not None:
        path.append(tile)
        tile = came_from[tile]
    path.reverse()
    return path
