"""
astar.py - A* search ("A-star").

IDEA     Give every frontier tile a score and always expand the tile with the LOWEST score:

             f(n) = g(n) + h(n)
             g(n) = steps already walked from the start to n      (exact)
             h(n) = estimated steps still needed from n to the goal (the heuristic)

         f(n) estimates the length of the whole trip start -> n -> goal, so A* first explores
         the tiles that lie on promising routes, instead of spreading in every direction like BFS.
DATA     A PRIORITY QUEUE: a binary min-heap (heapq). push and pop cost O(log n), and pop always
         returns the entry with the smallest f.
RESULT   With an admissible heuristic (never overestimates) A* is OPTIMAL, like BFS, but it
         usually expands far fewer tiles. With h = 0 it would behave exactly like Dijkstra's
         algorithm; on our maze (every step costs 1) that is the same as BFS.
COST     O(E log V) time in the worst case, O(V) memory.
"""

from __future__ import annotations

import heapq
from collections.abc import Set

from ..maze import Cell, Maze
from .heuristics import manhattan
from .result import SearchResult, reconstruct_path


def astar(maze: Maze, start: Cell, goal: Cell, blocked: Set[Cell] = frozenset()) -> SearchResult:
    """Shortest path from start to goal, guided by the Manhattan-distance heuristic."""
    h_start = manhattan(maze, start, goal)
    # Heap entries are (f, h, tile). Tuples compare item by item, so the heap pops the smallest f;
    # when two tiles have the same f, the one with the smaller h (closer to the goal) goes first.
    frontier: list[tuple[int, int, Cell]] = [(h_start, h_start, start)]
    g_cost: dict[Cell, int] = {start: 0}       # cheapest known number of steps from the start
    came_from: dict[Cell, Cell | None] = {start: None}
    closed: set[Cell] = set()                  # tiles already expanded (their g is final)
    expanded: list[Cell] = []
    max_frontier = 1

    while frontier:
        _, _, current = heapq.heappop(frontier)   # the most promising tile
        if current in closed:
            continue                              # outdated duplicate entry -> skip it
        closed.add(current)
        expanded.append(current)
        if current == goal:
            break
        for neighbor in maze.neighbors(current):
            if neighbor in blocked:
                continue
            new_g = g_cost[current] + 1           # every step costs 1
            if neighbor not in g_cost or new_g < g_cost[neighbor]:
                # first time we reach `neighbor`, or we found a shorter way to it
                g_cost[neighbor] = new_g
                came_from[neighbor] = current
                h = manhattan(maze, neighbor, goal)
                heapq.heappush(frontier, (new_g + h, h, neighbor))
        max_frontier = max(max_frontier, len(frontier))

    return SearchResult("A*", start, goal, reconstruct_path(came_from, goal), expanded, max_frontier)
