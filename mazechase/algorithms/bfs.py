"""
bfs.py - Breadth-First Search.

IDEA     Explore the maze in rings: first every tile 1 step away, then every tile 2 steps
         away, and so on, like a wave spreading from the start.
DATA     A FIFO QUEUE (collections.deque): new tiles join at the back, we always take the
         oldest tile from the front. Both operations are O(1).
RESULT   When every step costs the same (as in our maze), the first time BFS reaches a tile
         it got there along a SHORTEST path. BFS is complete and optimal.
COST     O(V + E) time and O(V) memory: every tile is queued at most once and every edge is
         looked at at most twice.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable, Set

from ..maze import Cell, Maze
from .result import SearchResult, reconstruct_path


def bfs(maze: Maze, start: Cell, goal: Cell, blocked: Set[Cell] = frozenset()) -> SearchResult:
    """Shortest path from start to goal. Tiles in `blocked` are treated as walls."""
    frontier = deque([start])                 # tiles discovered but not expanded yet
    came_from: dict[Cell, Cell | None] = {start: None}   # parent pointers, also the "visited" set
    expanded: list[Cell] = []
    max_frontier = 1

    while frontier:
        current = frontier.popleft()          # FIFO: the oldest tile first
        expanded.append(current)
        if current == goal:
            break
        for neighbor in maze.neighbors(current):
            if neighbor in came_from or neighbor in blocked:
                continue                      # already discovered, or forbidden
            came_from[neighbor] = current     # remember how we got here
            frontier.append(neighbor)
        max_frontier = max(max_frontier, len(frontier))

    return SearchResult("BFS", start, goal, reconstruct_path(came_from, goal), expanded, max_frontier)


def bfs_distances(maze: Maze, sources: Iterable[Cell], blocked: Set[Cell] = frozenset(),
                  limit: int | None = None) -> dict[Cell, int]:
    """Multi-source BFS: build a DISTANCE MAP {tile: steps from the NEAREST source}.

    The trick: put ALL sources in the queue at distance 0 and run one ordinary BFS. The wave
    then spreads from every source at the same time, so each tile is labelled by whichever
    source reaches it first. One O(V + E) pass instead of one BFS per source.

    The runner uses this to know how quickly the closest hunter can reach every tile.
    With `limit`, the wave stops after that many steps (tiles farther away are left out).
    """
    distance: dict[Cell, int] = {}
    frontier: deque[Cell] = deque()
    for source in sources:
        if source not in distance:
            distance[source] = 0
            frontier.append(source)

    while frontier:
        current = frontier.popleft()
        if limit is not None and distance[current] >= limit:
            continue                          # do not spread further than `limit` steps
        for neighbor in maze.neighbors(current):
            if neighbor not in distance and neighbor not in blocked:
                distance[neighbor] = distance[current] + 1
                frontier.append(neighbor)
    return distance
