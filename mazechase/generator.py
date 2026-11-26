"""
generator.py - random mazes. Here DFS BUILDS a maze instead of solving one.

Step 1  CARVE a "perfect" maze (exactly one route between any two tiles) with a randomized
        DFS, also called the "recursive backtracker". Stand on a tile, pick a random
        unvisited neighbour two tiles away, knock down the wall in between and push the new
        tile on a STACK. When there is no unvisited neighbour left, pop (= backtrack).
Step 2  BRAID it. A perfect maze is full of dead ends, and a dead end is a death trap in a
        chase game. For every dead end we knock down one more wall, which creates loops
        (escape routes). Then we knock down a few more random walls, so long corridors also
        get side exits.
Step 3  MIRROR the left half onto the right half (it looks designed, and it is fair to both
        sides), then place the runner, the hunters, the pellets, the power orbs and a tunnel.

The tiles the DFS walks on sit on odd rows and odd columns (a "lattice"); the tiles between
them are the walls that can be knocked down.
"""

from __future__ import annotations

import random

from .maze import DIRECTIONS, EMPTY, HUNTER_SPAWN, PELLET, POWER_ORB, RUNNER_START, WALL, Maze


def generate_maze(seed: int, half_columns: int = 6, lattice_rows: int = 9, extra_loops: int = 8,
                  name: str | None = None) -> Maze:
    """Build a random, symmetric maze without dead ends.

    The maze is (2 * lattice_rows + 1) tiles high and (4 * half_columns + 1) tiles wide.
    The same seed always gives the same maze.
    """
    rng = random.Random(seed)
    height = 2 * lattice_rows + 1
    center = 2 * half_columns           # the middle column of the full maze (a wall column)
    half_width = center + 1             # we generate columns 0..center, then mirror them
    grid = [[WALL] * half_width for _ in range(height)]

    def is_lattice(row: int, col: int) -> bool:
        return 1 <= row <= height - 2 and 1 <= col <= center - 1

    # --- Step 1: carve a perfect maze with a randomized DFS (explicit stack) ----------------
    start = (1, 1)
    grid[1][1] = PELLET
    stack = [start]
    visited = {start}
    while stack:
        row, col = stack[-1]                                   # look at the top of the stack
        options = [(row + 2 * dr, col + 2 * dc) for dr, dc in DIRECTIONS
                   if is_lattice(row + 2 * dr, col + 2 * dc) and (row + 2 * dr, col + 2 * dc) not in visited]
        if not options:
            stack.pop()                                        # dead end: backtrack
            continue
        next_row, next_col = rng.choice(options)
        grid[(row + next_row) // 2][(col + next_col) // 2] = PELLET   # knock down the wall between
        grid[next_row][next_col] = PELLET
        visited.add((next_row, next_col))
        stack.append((next_row, next_col))

    # Bridges across the middle column (to the mirrored half): top, middle and bottom row.
    middle_row = lattice_rows if lattice_rows % 2 == 1 else lattice_rows + 1
    for row in (1, middle_row, height - 2):
        grid[row][center] = PELLET

    # --- Step 2: braid - give every dead end a second exit -----------------------------------
    def open_sides(row: int, col: int) -> int:
        return sum(grid[row + dr][col + dc] != WALL for dr, dc in DIRECTIONS)

    for row in range(1, height - 1, 2):
        for col in range(1, center, 2):
            if open_sides(row, col) != 1:
                continue                                       # not a dead end
            walls = []
            for dr, dc in DIRECTIONS:
                if grid[row + dr][col + dc] != WALL:
                    continue
                beyond = (row + 2 * dr, col + 2 * dc)
                crosses_middle = beyond[1] == center + 1 and 1 <= beyond[0] <= height - 2
                if is_lattice(*beyond) or crosses_middle:
                    walls.append((dr, dc))
            if walls:
                # prefer joining another dead end: that removes two dead ends at once
                rng.shuffle(walls)
                walls.sort(key=lambda d: 0 if is_lattice(row + 2 * d[0], col + 2 * d[1])
                           and open_sides(row + 2 * d[0], col + 2 * d[1]) == 1 else 1)
                dr, dc = walls[0]
                grid[row + dr][col + dc] = PELLET

    # A few extra loops: knock down random walls that separate two corridors.
    knockable = [(row, col) for row in range(1, height - 1) for col in range(1, center + 1)
                 if grid[row][col] == WALL and (row % 2) != (col % 2)]    # walls between two lattice tiles
    for row, col in rng.sample(knockable, min(extra_loops, len(knockable))):
        grid[row][col] = PELLET

    # --- Step 3: mirror, then place everything -------------------------------------------------
    rows = [line + line[-2::-1] for line in grid]              # columns 0..center + center-1..0
    full = [list(line) for line in rows]
    width = len(full[0])

    full[middle_row][0] = PELLET                               # a tunnel through the middle row
    full[middle_row][width - 1] = PELLET
    for row, col in ((1, 1), (1, width - 2), (height - 2, 1), (height - 2, width - 2)):
        full[row][col] = POWER_ORB                             # power orbs near the four corners
    full[height - 2][center] = RUNNER_START                    # runner: bottom middle
    for col in (center - 1, center, center + 1):
        full[1][col] = HUNTER_SPAWN                            # hunters: top middle
    for row in range(height):
        for col in range(width):
            if full[row][col] == EMPTY:
                full[row][col] = PELLET

    return Maze(name or f"Random Labyrinth #{seed}", ["".join(line) for line in full],
                description=f"Generated by randomized DFS (seed {seed}), braided, mirrored.",
                theme="green")
